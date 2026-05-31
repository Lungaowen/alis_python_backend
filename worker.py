import logging

from tasks.processing_pipeline import celery_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)

# Entry point for Celery
# Windows: celery -A worker.celery_app worker --loglevel=info --pool=solo
