from pydantic import BaseModel, Field

class ProcessRequest(BaseModel):
    document_id: int = Field(..., description="Unique ID for the document")
    client_id: int = Field(..., description="Unique ID for the client")
    document_title: str = Field(..., description="Title of the document")
    document_type: str = Field(..., description="EMPLOYMENT/NDA/SERVICE/LEASE/OTHER")
    file_url: str = Field(..., description="Firebase URL to download PDF")
    callback_url: str = Field(..., description="Java backend webhook URL")
    jurisdiction: str = Field(default="South Africa", description="Legal jurisdiction")