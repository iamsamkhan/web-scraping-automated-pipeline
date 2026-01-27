from pydantic import BaseModel, EmailStr, HttpUrl
from typing import List, Optional
from datetime import datetime

class StudentBase(BaseModel):
    name: str
    email: EmailStr
    university: str
    department: Optional[str] = None

class StudentCreate(StudentBase):
    pass

class StudentResponse(StudentBase):
    id: int
    scraped_at: datetime
    
    class Config:
        from_attributes = True

class UniversityScrapeRequest(BaseModel):
    url: HttpUrl
    university_name: str
    selectors: Optional[dict] = None
    use_selenium: bool = False

class ScrapeResponse(BaseModel):
    success: bool
    message: str
    students_found: int
    data: List[StudentResponse]
    execution_time: float