from pydantic import BaseModel
from typing import Optional

class PRDetails(BaseModel):
    repo_url: str
    pr_number: int
    github_token: Optional[str] = None

class CodeAnalysisRequest(BaseModel):
    repo_url: str
    pr_number: int
    github_token: Optional[str] = None
    groq_lpu: str  
    model_name: str  
