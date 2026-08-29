from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    user_id: int = 1
    mode: Literal["company", "chat"] = Field(
        default="company",
        description="'company' runs the full multi-agent workflow; 'chat' is a single reasoning turn.",
    )


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    max_results: int = Field(default=5, ge=1, le=20)


class MemoryRequest(BaseModel):
    user_id: int = 1
    memory: str = Field(..., min_length=1, max_length=4000)


class VisionRequest(BaseModel):
    prompt: str = "Describe this image in detail."


class RagRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=50)
