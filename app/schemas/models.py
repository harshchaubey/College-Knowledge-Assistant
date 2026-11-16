from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(
        ..., min_length=1, max_length=1000, description="User question about college docs"
    )


class Source(BaseModel):
    document: str = Field(..., description="Original PDF filename")
    page: int = Field(..., description="1-based page number in the PDF")
    snippet: str = Field(..., description="Short preview of the retrieved chunk")


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


class UploadResponse(BaseModel):
    message: str
    filename: str
    pages: int
    chunks: int
    replaced: bool = False


class DocumentInfo(BaseModel):
    filename: str
    pages: int
    chunks: int
