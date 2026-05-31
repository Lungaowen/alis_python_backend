import httpx
import time
import logging
from config import config

logger = logging.getLogger(__name__)

def send_webhook(url: str, payload: dict):
    backoff_times = [2, 4, 8, 16, 32]
    last_error = None
    headers = {
        "Content-Type": "application/json",
        "X-ALIS-Signature": config.JAVA_CALLBACK_SECRET
    }
    
    with httpx.Client() as client:
        for attempt, delay in enumerate(backoff_times):
            try:
                response = client.post(url, json=payload, headers=headers, timeout=10.0)
                response.raise_for_status()
                return True
            except httpx.HTTPError as e:
                last_error = e
                logger.warning("Webhook attempt %s failed: %s", attempt + 1, e)
                if attempt < len(backoff_times) - 1:
                    time.sleep(delay)
                    
    raise RuntimeError(f"All webhook retries failed: {last_error}")
