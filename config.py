import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    ALIS_S3_BUCKET = os.getenv("ALIS_S3_BUCKET")
    ALIS_S3_REGION = os.getenv("ALIS_S3_REGION", "us-east-1")
    REDIS_URL = os.getenv("REDIS_URL", "redis://default:n1VA7VysS6YXtlKTgLnce72cqY4mKLE3@sugar-large-poised-30985.db.redis.io:10090/0")
    JAVA_CALLBACK_SECRET = os.getenv("JAVA_CALLBACK_SECRET")
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
    MAX_PAGES = int(os.getenv("MAX_PAGES", 500))
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 8192))
    MAX_TEXT_CHARS = 500000

config = Config()
