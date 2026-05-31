import json
import uuid
import gc
import os
import logging
import tempfile
import httpx
from datetime import datetime
from urllib.parse import urlparse
from celery import Celery
import redis
from config import config

from utils.temp_file_manager import manage_temp_file
from utils.text_cleaner import clean_text
from services.pdf_extractor import extract_text_generator
from services.gemini_client import analyze_document
from services.report_generator import generate_report_bytes
from services.s3_client import upload_and_presign
from services.webhook_client import send_webhook

logger = logging.getLogger(__name__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
celery_app = Celery('alis_tasks', broker=config.REDIS_URL, backend=config.REDIS_URL)
redis_client = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)

def update_status(task_id: str, document_id: int, status: str, progress: int, error: str = None):
    key = f"task:{task_id}"
    now = datetime.utcnow().isoformat() + "Z"
    
    existing = redis_client.get(key)
    if existing:
        data = json.loads(existing)
    else:
        data = {"task_id": task_id, "document_id": document_id, "startedAt": now}
        
    data.update({
        "status": status,
        "progress": progress,
        "updatedAt": now,
        "error": error
    })
    
    redis_client.setex(key, 86400, json.dumps(data))

@celery_app.task(bind=True, name="process_document")
def process_document_task(self, request_data: dict):
    task_id = request_data['task_id']
    document_id = request_data['document_id']
    temp_input = os.path.join(tempfile.gettempdir(), f"{task_id}.input")
    
    try:
        # STAGE 2: ASYNC PROCESSING (Download)
        update_status(task_id, document_id, "EXTRACTING", 10)
        
        with manage_temp_file(temp_input) as input_path:
            with httpx.stream("GET", request_data['file_url']) as r:
                if r.is_error:
                    error_body = r.read().decode("utf-8", errors="replace")[:1000]
                    raise RuntimeError(
                        f"File download failed with HTTP {r.status_code}: {error_body}"
                    )
                content_type = r.headers.get("content-type", "").lower()
                with open(input_path, 'wb') as f:
                    for chunk in r.iter_bytes(chunk_size=config.CHUNK_SIZE):
                        f.write(chunk)
            
            # Basic validation
            file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
            if file_size_mb > config.MAX_FILE_SIZE_MB:
                raise ValueError(f"File exceeds {config.MAX_FILE_SIZE_MB}MB")
                
            with open(input_path, 'rb') as f:
                header = f.read(5)

            file_path = urlparse(request_data['file_url']).path.lower()
            is_pdf = header == b'%PDF-'
            is_text = content_type.startswith("text/") or file_path.endswith(".txt")

            if is_pdf:
                # STAGE 3: PDF TEXT EXTRACTION
                extracted_chunks = []
                char_count = 0

                for text_chunk in extract_text_generator(input_path):
                    if char_count + len(text_chunk) > config.MAX_TEXT_CHARS:
                        # Truncate and stop extracting to protect memory
                        remaining = config.MAX_TEXT_CHARS - char_count
                        extracted_chunks.append(text_chunk[:remaining])
                        break
                    extracted_chunks.append(text_chunk)
                    char_count += len(text_chunk)

                full_text = "\n".join(extracted_chunks)
                del extracted_chunks
                gc.collect()
            elif is_text:
                # STAGE 3: TEXT FILE EXTRACTION
                with open(input_path, "r", encoding="utf-8", errors="replace") as f:
                    full_text = clean_text(f.read(config.MAX_TEXT_CHARS))
            else:
                raise ValueError(f"Unsupported document type: content-type={content_type or 'unknown'}")
            
            if not full_text.strip():
                raise ValueError("No extractable text found in document")
                
        # Temporary input file is strictly deleted here by manage_temp_file exit
        
        # STAGE 4: AI ANALYSIS
        update_status(task_id, document_id, "ANALYSING", 30)
        analysis_result = analyze_document(
            request_data['document_type'], 
            request_data['jurisdiction'], 
            full_text
        )
        del full_text
        gc.collect()
        
        # --- LOCAL ARCHIVE LOGIC INSERTION ---
        local_report_path = None
        try:
            local_reports_dir = os.path.join(PROJECT_ROOT, "reports")
            os.makedirs(local_reports_dir, exist_ok=True)
            
            # Compose unique report name matching your running execution schema
            timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            local_report_name = f"compliance_report_{document_id}_{timestamp_str}.json"
            local_report_path = os.path.join(local_reports_dir, local_report_name)
            
            # Write analysis out to disk safely
            with open(local_report_path, "w", encoding="utf-8") as file_out:
                json.dump(analysis_result, file_out, indent=2)
            logger.info("Compliance report archived locally: %s", local_report_path)
        except Exception as local_save_err:
            logger.warning("Failed to archive report copy locally: %s", local_save_err)
        # -------------------------------------
        
        # STAGE 5: REPORT GENERATION
        update_status(task_id, document_id, "GENERATING_REPORT", 60)
        pdf_bytes_io = generate_report_bytes(
            task_id, 
            request_data['document_title'], 
            request_data['client_id'], 
            analysis_result
        )

        local_pdf_path = None
        try:
            local_reports_dir = os.path.join(PROJECT_ROOT, "reports")
            os.makedirs(local_reports_dir, exist_ok=True)
            local_pdf_name = f"compliance_report_{document_id}_{task_id}.pdf"
            local_pdf_path = os.path.join(local_reports_dir, local_pdf_name)
            with open(local_pdf_path, "wb") as file_out:
                file_out.write(pdf_bytes_io.getvalue())
            logger.info("Compliance PDF archived locally: %s", local_pdf_path)
        except Exception as local_pdf_save_err:
            logger.warning("Failed to archive PDF copy locally: %s", local_pdf_save_err)
        
        # STAGE 6: S3 UPLOAD
        update_status(task_id, document_id, "UPLOADING", 80)
        s3_key, s3_url = upload_and_presign(document_id, task_id, pdf_bytes_io)
        
        # Release bytesIO memory
        pdf_bytes_io.close()
        del pdf_bytes_io
        gc.collect()
        
        # STAGE 7: WEBHOOK CALLBACK
        update_status(task_id, document_id, "DELIVERING", 90)
        webhook_payload = {
            "task_id": task_id,
            "document_id": document_id,
            "client_id": request_data['client_id'],
            "status": "COMPLETED",
            "riskLevel": analysis_result.get("riskLevel", "MEDIUM"),
            "complianceScore": analysis_result.get("complianceScore", 0),
            "reportS3Url": s3_url,
            "reportS3Key": s3_key,
            "reportLocalPath": local_pdf_path,
            "analysisLocalPath": local_report_path,
            "analysisJson": analysis_result,
            "processedAt": datetime.utcnow().isoformat() + "Z"
        }
        
        try:
            send_webhook(request_data['callback_url'], webhook_payload)
            update_status(task_id, document_id, "COMPLETED", 100)
        except RuntimeError:
            logger.exception("Webhook callback failed for task %s", task_id)
            update_status(task_id, document_id, "WEBHOOK_FAILED", 95, "Failed to deliver webhook")
            
        del analysis_result
        del webhook_payload
        gc.collect()

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.exception("Task %s failed while processing document %s", task_id, document_id)
        update_status(task_id, document_id, "FAILED", 0, error_msg)
        
        # Send failure webhook
        failure_payload = {
            "task_id": task_id,
            "document_id": document_id,
            "status": "FAILED",
            "error": error_msg,
            "processedAt": datetime.utcnow().isoformat() + "Z"
        }
        try:
            send_webhook(request_data['callback_url'], failure_payload)
        except Exception:
            logger.exception("Failure webhook could not be delivered for task %s", task_id)
            pass # Failing gracefully on failure webhook
            
        # Ensure memory is swept on failure
        gc.collect()
        raise
