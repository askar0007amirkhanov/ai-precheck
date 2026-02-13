from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class PolicyTemplateCreate(BaseModel):
    slug: str
    name: str
    content_template: str
    version: int = 1

class PolicyTemplateResponse(PolicyTemplateCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WidgetResponse(BaseModel):
    html_content: str
    json_ld: Dict[str, Any]
