from typing import Optional
from pydantic import BaseModel, Field


class ListSessionsRequest(BaseModel):
    pageSize: int = Field(10, gt=0, le=50)
    cursor: Optional[str] = None
