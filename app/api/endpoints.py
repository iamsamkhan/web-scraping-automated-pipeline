from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import List, Optional
import asyncio
import time

from app.scraper.university_scrapers import GenericUniversityScraper, DirectoryPageScraper
from app.models.schemas import (
    StudentResponse, 
    UniversityScrapeRequest, 
    ScrapeResponse,
    StudentBase
)
from app.utils.helpers import timing_decorator, validate_url

router = APIRouter()

# In-memory storage (replace with database in production)
students_store = []
scraping_tasks = {}

@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_university_data(
    request: UniversityScrapeRequest,
    background_tasks: BackgroundTasks = None
):
    """
    Scrape student data from a university website
    """
    # Validate URL
    if not validate_url(request.url):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL. Please provide a valid educational institution URL"
        )
    
    # Choose appropriate scraper
    if "directory" in str(request.url).lower() or "people" in str(request.url).lower():
        scraper_class = DirectoryPageScraper
    else:
        scraper_class = GenericUniversityScraper
    
    # Perform scraping
    result, exec_time = await perform_scraping(
        scraper_class, 
        str(request.url), 
        request.university_name,
        request.use_selenium
    )
    
    # Store results
    for student in result:
        student_response = StudentResponse(
            id=len(students_store) + 1,
            name=student.name,
            email=student.email,
            university=student.university,
            department=student.department,
            scraped_at=time.time()
        )
        students_store.append(student_response)
    
    return ScrapeResponse(
        success=True,
        message=f"Successfully scraped {len(result)} students",
        students_found=len(result),
        data=result,
        execution_time=exec_time
    )

@router.get("/students", response_model=List[StudentResponse])
async def get_students(
    university: Optional[str] = Query(None, description="Filter by university name"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Get scraped student data with optional filters
    """
    filtered_students = students_store
    
    if university:
        filtered_students = [
            s for s in filtered_students 
            if university.lower() in s.university.lower()
        ]
    
    return filtered_students[offset:offset + limit]

@router.get("/students/search")
async def search_students(
    name: Optional[str] = Query(None, description="Search by student name"),
    email: Optional[str] = Query(None, description="Search by email"),
    university: Optional[str] = Query(None, description="Search by university")
):
    """
    Search students by various criteria
    """
    results = students_store
    
    if name:
        results = [s for s in results if name.lower() in s.name.lower()]
    
    if email:
        results = [s for s in results if email.lower() in s.email.lower()]
    
    if university:
        results = [s for s in results if university.lower() in s.university.lower()]
    
    return {
        "count": len(results),
        "students": results[:100]  # Limit results
    }

@router.get("/universities")
async def get_scraped_universities():
    """
    Get list of universities that have been scraped
    """
    universities = set()
    for student in students_store:
        universities.add(student.university)
    
    return {
        "count": len(universities),
        "universities": sorted(list(universities))
    }

@router.delete("/students")
async def clear_students():
    """
    Clear all stored student data
    """
    global students_store
    count = len(students_store)
    students_store = []
    
    return {
        "message": f"Cleared {count} student records",
        "cleared_count": count
    }

async def perform_scraping(scraper_class, url: str, university_name: str, use_selenium: bool = False):
    """
    Perform the actual scraping with timing
    """
    @timing_decorator
    async def scrape():
        async with scraper_class(timeout=30) as scraper:
            if use_selenium:
                html = scraper.fetch_with_selenium(url)
            else:
                html = await scraper.fetch_html(url)
            
            if not html:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to fetch page content"
                )
            
            students = await scraper.extract_students(html, url)
            
            # If no students found with generic scraper, try selenium
            if not students and not use_selenium:
                print("No students found with basic scraping, trying Selenium...")
                html_js = scraper.fetch_with_selenium(url)
                if html_js:
                    students = await scraper.extract_students(html_js, url)
            
            return students
    
    return await scrape()