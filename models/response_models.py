from pydantic import BaseModel
from typing import Optional

class ProcessResponse(BaseModel):
    task_id: str
    status: str
    message: str

class TaskStatusResponse(BaseModel):
    task_id: str
    document_id: int
    status: str
    progress: int
    startedAt: str
    updatedAt: str
    error: Optional[str] = None