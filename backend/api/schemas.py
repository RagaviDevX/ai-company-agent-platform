from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    user_id: int = 1
    mode: str = Field(default="company", description="company | chat")


class SearchRequest(BaseModel):
    query: str
    max_results: int = 5


class MemoryRequest(BaseModel):
    user_id: int = 1
    memory: str


class VisionRequest(BaseModel):
    prompt: str = "Describe this image in detail."


class RagRequest(BaseModel):
    query: str
    limit: int = 5
