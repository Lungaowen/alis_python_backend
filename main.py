import uuid
import json
from datetime import datetime
from typing import Any
from fastapi import FastAPI, HTTPException, Request
import redis

from config import config
from models.request_models import ProcessRequest
from models.response_models import ProcessResponse, TaskStatusResponse
from tasks.processing_pipeline import process_document_task, update_status

app = FastAPI(title="ALIS Document Processing API")
redis_client = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)

@app.post("/api/process", response_model=ProcessResponse)
async def process_document(request: ProcessRequest):
    task_id = str(uuid.uuid4())
    
    request_data = request.model_dump()
    request_data['task_id'] = task_id
    
    # Initialize state in Redis
    update_status(task_id, request.document_id, "QUEUED", 0)
    
    # Push to Celery
    process_document_task.delay(request_data)
    
    return ProcessResponse(
        task_id=task_id,
        status="QUEUED",
        message="Document queued for processing"
    )

@app.get("/api/status/{task_id}", response_model=TaskStatusResponse)
async def get_status(task_id: str):
    key = f"task:{task_id}"
    data = redis_client.get(key)
    
    if not data:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return json.loads(data)

@app.post("/api/mock-java-backend")
async def mock_java_backend(payload: dict[str, Any], request: Request):
    received = {
        "receivedAt": datetime.utcnow().isoformat() + "Z",
        "signaturePresent": bool(request.headers.get("X-ALIS-Signature")),
        "payload": payload
    }
    task_id = payload.get("task_id")

    redis_client.setex("mock:last-webhook", 86400, json.dumps(received))
    if task_id:
        redis_client.setex(f"mock:webhook:{task_id}", 86400, json.dumps(received))

    return {
        "ok": True,
        "message": "Mock Java backend received webhook",
        "task_id": task_id,
        "status": payload.get("status")
    }

@app.get("/api/mock-java-backend/latest")
async def get_latest_mock_webhook():
    data = redis_client.get("mock:last-webhook")
    if not data:
        raise HTTPException(status_code=404, detail="No mock webhook received yet")

    return json.loads(data)

# Run server using: uvicorn main:app --host 0.0.0.0 --port 8000
