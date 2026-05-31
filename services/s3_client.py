import boto3
from config import config

s3 = boto3.client(
    's3',
    aws_access_key_id=config.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
    region_name=config.ALIS_S3_REGION
)

def upload_and_presign(document_id: int, task_id: str, pdf_bytes_io) -> tuple[str, str]:
    key = f"reports/document_{document_id}/report_{task_id}.pdf"
    
    # Upload from buffer
    s3.put_object(
        Bucket=config.ALIS_S3_BUCKET,
        Key=key,
        Body=pdf_bytes_io.getvalue(),
        ContentType='application/pdf'
    )
    
    # Generate Presigned URL (24hr expiry)
    url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={'Bucket': config.ALIS_S3_BUCKET, 'Key': key},
        ExpiresIn=86400
    )
    
    return key, url