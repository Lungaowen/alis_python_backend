import os
import gc
from contextlib import contextmanager

@contextmanager
def manage_temp_file(filepath: str):
    """Context manager to ensure temp files are deleted immediately."""
    try:
        yield filepath
    finally:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
        # Force garbage collection after file drop to clear memory
        gc.collect()