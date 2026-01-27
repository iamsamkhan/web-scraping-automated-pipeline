from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends, File, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, validator
import asyncio
import time
import os
import zipfile
import io
from datetime import datetime
from pathlib import Path

from app.models.schemas import StudentResponse
from app.email_service.email_sender import EmailSender
from app.email_service.ai_paper_generator import AIPaperGenerator
from app.document_generator.docx_generator import DocxGenerator
from app.utils.helpers import timing_decorator

# Create router
router = APIRouter(prefix="/email", tags=["Email & Document Services"])

# Pydantic Models
class EmailConfig(BaseModel):
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str
    sender_password: str
    sender_name: str = "Academic Research Team"
    use_ssl: bool = False

class EmailRequest(BaseModel):
    student_ids: Optional[List[int]] = None
    subject_template: str = "Research Paper Draft for {name} - {paper_title}"
    body_template: str = "journal_invitation"
    test_mode: bool = True
    delay_seconds: int = 2
    email_config: Optional[EmailConfig] = None

class PaperGenerationRequest(BaseModel):
    student_ids: Optional[List[int]] = None
    model_type: str = "fallback"  # openai, llama, fallback
    api_key: Optional[str] = None
    output_format: str = "docx"  # docx, pdf, txt
    include_abstract: bool = True
    include_references: bool = True

class BatchProcessRequest(BaseModel):
    generate_papers: bool = True
    send_emails: bool = True
    paper_config: Optional[PaperGenerationRequest] = None
    email_config: Optional[EmailRequest] = None

class EmailStatus(BaseModel):
    email: EmailStr
    status: str  # pending, sent, failed
    message: str
    timestamp: datetime
    paper_generated: bool = False
    paper_path: Optional[str] = None

# In-memory storage
email_queue = []
processing_status = {}
sent_emails = []
generated_papers = {}

# Dependency for email service
def get_email_service():
    return EmailSender()

def get_paper_generator(model_type: str = "fallback", api_key: Optional[str] = None):
    return AIPaperGenerator(model_type=model_type, api_key=api_key)

def get_docx_generator():
    return DocxGenerator()

@router.post("/generate-papers", summary="Generate academic papers for students")
async def generate_papers(
    request: PaperGenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate personalized academic papers for selected students
    
    - **student_ids**: List of student IDs to generate papers for (if empty, use all)
    - **model_type**: AI model to use (openai, llama, fallback)
    - **api_key**: API key for AI service (if using OpenAI)
    - **output_format**: Output format (docx, pdf, txt)
    """
    
    # Get students (in production, from database)
    from app.api.endpoints import students_store
    students = students_store
    
    if request.student_ids:
        students = [s for s in students if s.id in request.student_ids]
    
    if not students:
        raise HTTPException(status_code=404, detail="No students found")
    
    # Initialize generators
    paper_gen = get_paper_generator(request.model_type, request.api_key)
    docx_gen = get_docx_generator()
    
    results = []
    
    for student in students:
        try:
            student_data = {
                'id': student.id,
                'name': student.name,
                'email': student.email,
                'university': student.university,
                'field': student.department or "Computer Science"
            }
            
            # Generate paper
            paper_result = docx_gen.generate_personalized_paper(
                student_data=student_data,
                output_dir="output/papers"
            )
            
            # Store result
            paper_key = f"{student.id}_{datetime.now().strftime('%Y%m%d')}"
            generated_papers[paper_key] = {
                **paper_result,
                'student_id': student.id,
                'generated_at': datetime.now().isoformat(),
                'model_type': request.model_type
            }
            
            results.append({
                'student_id': student.id,
                'student_name': student.name,
                'paper_title': paper_result['paper_title'],
                'file_path': paper_result['docx_path'],
                'file_size': paper_result['file_size'],
                'status': 'success'
            })
            
        except Exception as e:
            results.append({
                'student_id': student.id,
                'student_name': student.name,
                'error': str(e),
                'status': 'failed'
            })
    
    # Queue for email sending if requested
    if request.email_config:
        email_request = EmailRequest(
            student_ids=request.student_ids,
            subject_template="Your Research Paper: {paper_title}",
            test_mode=True
        )
        background_tasks.add_task(queue_emails_for_papers, email_request, results)
    
    return {
        'total_students': len(students),
        'papers_generated': len([r for r in results if r['status'] == 'success']),
        'failed': len([r for r in results if r['status'] == 'failed']),
        'results': results,
        'download_url': f"/email/download-papers?ids={','.join(str(s.id) for s in students)}"
    }

@router.post("/send-emails", summary="Send emails with paper attachments")
async def send_emails(
    request: EmailRequest,
    background_tasks: BackgroundTasks,
    email_service: EmailSender = Depends(get_email_service)
):
    """
    Send personalized emails with academic paper attachments to students
    
    - **student_ids**: List of student IDs (if empty, use all with generated papers)
    - **subject_template**: Email subject template with placeholders
    - **body_template**: Template name for email body
    - **test_mode**: If True, only send first 5 emails
    - **delay_seconds**: Delay between emails
    """
    
    # Configure email service if config provided
    if request.email_config:
        email_service = EmailSender(
            smtp_server=request.email_config.smtp_server,
            smtp_port=request.email_config.smtp_port,
            use_ssl=request.email_config.use_ssl
        )
        email_service.sender_email = request.email_config.sender_email
        email_service.sender_password = request.email_config.sender_password
        email_service.sender_name = request.email_config.sender_name
    
    # Get students and their papers
    from app.api.endpoints import students_store
    students = students_store
    
    if request.student_ids:
        students = [s for s in students if s.id in request.student_ids]
    
    # Find papers for these students
    email_list = []
    for student in students:
        # Find latest paper for this student
        student_papers = [
            p for p in generated_papers.values() 
            if p.get('student_id') == student.id
        ]
        
        if student_papers:
            latest_paper = max(student_papers, key=lambda x: x.get('generated_at', ''))
            
            email_list.append({
                'id': student.id,
                'name': student.name,
                'email': student.email,
                'university': student.university,
                'department': student.department,
                'paper_title': latest_paper.get('paper_title', 'Research Paper'),
                'abstract': latest_paper.get('abstract', ''),
                'docx_path': latest_paper.get('docx_path'),
                'paper_generated_at': latest_paper.get('generated_at')
            })
    
    if not email_list:
        raise HTTPException(
            status_code=404, 
            detail="No students with generated papers found"
        )
    
    # Set rate limiting
    email_service.delay_between_emails = request.delay_seconds
    
    # Queue email sending
    task_id = f"email_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    processing_status[task_id] = {
        'status': 'queued',
        'total': len(email_list),
        'sent': 0,
        'failed': 0,
        'started_at': None,
        'completed_at': None
    }
    
    # Start background task
    background_tasks.add_task(
        process_email_batch,
        task_id,
        email_list,
        request,
        email_service
    )
    
    return {
        'task_id': task_id,
        'status': 'queued',
        'total_emails': len(email_list),
        'test_mode': request.test_mode,
        'monitor_url': f"/email/status/{task_id}"
    }

@router.get("/status/{task_id}", summary="Check email sending status")
async def get_email_status(task_id: str):
    """
    Get the status of an email sending batch task
    """
    if task_id not in processing_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    status = processing_status[task_id]
    
    # Add recent sent emails if available
    recent_sent = [
        email for email in sent_emails 
        if email.get('task_id') == task_id
    ][-10:]  # Last 10 emails
    
    return {
        **status,
        'recent_emails': recent_sent,
        'progress_percentage': (status['sent'] + status['failed']) / status['total'] * 100 if status['total'] > 0 else 0
    }

@router.get("/download-paper/{student_id}", summary="Download generated paper")
async def download_paper(
    student_id: int,
    version: Optional[str] = Query(None, description="Paper version (latest if not specified)")
):
    """
    Download a generated academic paper for a specific student
    """
    # Find papers for this student
    student_papers = [
        p for p in generated_papers.values() 
        if p.get('student_id') == student_id
    ]
    
    if not student_papers:
        raise HTTPException(status_code=404, detail="No papers found for this student")
    
    if version:
        # Find specific version
        paper = next((p for p in student_papers if p.get('version') == version), None)
    else:
        # Get latest paper
        paper = max(student_papers, key=lambda x: x.get('generated_at', ''))
    
    if not paper or 'docx_path' not in paper:
        raise HTTPException(status_code=404, detail="Paper file not found")
    
    file_path = paper['docx_path']
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Paper file does not exist")
    
    filename = os.path.basename(file_path)
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

@router.get("/download-papers", summary="Download multiple papers as ZIP")
async def download_papers_batch(
    student_ids: str = Query(..., description="Comma-separated student IDs"),
    format: str = Query("zip", description="Output format: zip or tar")
):
    """
    Download multiple generated papers as a compressed archive
    """
    ids = [int(id.strip()) for id in student_ids.split(',')]
    
    papers_to_download = []
    for student_id in ids:
        student_papers = [
            p for p in generated_papers.values() 
            if p.get('student_id') == student_id
        ]
        if student_papers:
            latest_paper = max(student_papers, key=lambda x: x.get('generated_at', ''))
            if 'docx_path' in latest_paper and os.path.exists(latest_paper['docx_path']):
                papers_to_download.append(latest_paper)
    
    if not papers_to_download:
        raise HTTPException(status_code=404, detail="No papers found for the specified students")
    
    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for paper in papers_to_download:
            file_path = paper['docx_path']
            student_name = paper['student_name'].replace(' ', '_')
            paper_title = paper['paper_title'].replace(' ', '_')[:50]
            
            filename = f"{student_name}_{paper_title}.docx"
            zip_file.write(file_path, filename)
    
    zip_buffer.seek(0)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f"research_papers_{timestamp}.zip"
    
    return StreamingResponse(
        zip_buffer,
        media_type='application/zip',
        headers={'Content-Disposition': f'attachment; filename="{zip_filename}"'}
    )

@router.get("/templates", summary="Get available email templates")
async def get_templates():
    """
    List all available email templates
    """
    template_dir = Path("templates/email_templates")
    
    if not template_dir.exists():
        return {"templates": [], "message": "Template directory not found"}
    
    templates = []
    for file in template_dir.glob("*.html"):
        templates.append({
            'name': file.stem,
            'filename': file.name,
            'size': file.stat().st_size,
            'modified': datetime.fromtimestamp(file.stat().st_mtime).isoformat()
        })
    
    return {
        'template_dir': str(template_dir.absolute()),
        'templates': templates
    }

@router.post("/templates/upload", summary="Upload new email template")
async def upload_template(
    name: str = Form(...),
    template_file: UploadFile = File(...)
):
    """
    Upload a new email template
    """
    if not template_file.filename.endswith('.html'):
        raise HTTPException(status_code=400, detail="Only HTML templates are supported")
    
    template_dir = Path("templates/email_templates")
    template_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = template_dir / f"{name}.html"
    
    # Save template
    content = await template_file.read()
    file_path.write_bytes(content)
    
    return {
        'status': 'success',
        'message': f'Template {name} uploaded successfully',
        'path': str(file_path.absolute()),
        'size': len(content)
    }

@router.get("/sent-emails", summary="Get sent email history")
async def get_sent_email_history(
    days: int = Query(7, description="Number of days to look back"),
    limit: int = Query(100, description="Maximum number of records"),
    student_id: Optional[int] = None
):
    """
    Get history of sent emails
    """
    # In production, this would query a database
    # For now, use in-memory storage
    
    cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
    
    filtered_emails = [
        email for email in sent_emails
        if email.get('timestamp', 0) > cutoff_date
    ]
    
    if student_id:
        filtered_emails = [
            email for email in filtered_emails
            if email.get('student_id') == student_id
        ]
    
    # Sort by timestamp (newest first)
    filtered_emails.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    
    return {
        'total': len(filtered_emails),
        'days': days,
        'emails': filtered_emails[:limit]
    }

@router.post("/batch-process", summary="Complete batch processing")
async def batch_process(
    request: BatchProcessRequest,
    background_tasks: BackgroundTasks
):
    """
    Complete batch process: Generate papers and send emails
    
    - **generate_papers**: Whether to generate papers
    - **send_emails**: Whether to send emails
    - **paper_config**: Paper generation configuration
    - **email_config**: Email sending configuration
    """
    
    task_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    processing_status[task_id] = {
        'status': 'starting',
        'phase': 'initializing',
        'progress': 0,
        'details': {},
        'started_at': datetime.now().isoformat()
    }
    
    # Start background processing
    background_tasks.add_task(
        process_batch_workflow,
        task_id,
        request
    )
    
    return {
        'task_id': task_id,
        'status': 'started',
        'phases': [
            'paper_generation' if request.generate_papers else None,
            'email_sending' if request.send_emails else None
        ],
        'monitor_url': f"/email/batch-status/{task_id}"
    }

@router.get("/batch-status/{task_id}", summary="Check batch process status")
async def get_batch_status(task_id: str):
    """
    Get status of a batch processing task
    """
    if task_id not in processing_status:
        raise HTTPException(status_code=404, detail="Batch task not found")
    
    status = processing_status[task_id]
    
    return {
        **status,
        'estimated_time_remaining': estimate_remaining_time(status),
        'current_phase': status.get('phase', 'unknown')
    }

@router.get("/statistics", summary="Get email statistics")
async def get_statistics(
    period: str = Query("week", description="Time period: day, week, month, year")
):
    """
    Get email sending statistics
    """
    # Calculate time cutoff
    now = datetime.now()
    if period == "day":
        cutoff = now.timestamp() - (24 * 60 * 60)
    elif period == "week":
        cutoff = now.timestamp() - (7 * 24 * 60 * 60)
    elif period == "month":
        cutoff = now.timestamp() - (30 * 24 * 60 * 60)
    elif period == "year":
        cutoff = now.timestamp() - (365 * 24 * 60 * 60)
    else:
        cutoff = now.timestamp() - (7 * 24 * 60 * 60)
    
    # Filter sent emails
    period_emails = [
        email for email in sent_emails
        if email.get('timestamp', 0) > cutoff
    ]
    
    # Calculate statistics
    total_emails = len(period_emails)
    successful_emails = len([e for e in period_emails if e.get('success')])
    failed_emails = total_emails - successful_emails
    
    # Group by day
    emails_by_day = {}
    for email in period_emails:
        date = datetime.fromtimestamp(email.get('timestamp', 0)).strftime('%Y-%m-%d')
        emails_by_day[date] = emails_by_day.get(date, 0) + 1
    
    # Success rate
    success_rate = (successful_emails / total_emails * 100) if total_emails > 0 else 0
    
    return {
        'period': period,
        'total_emails': total_emails,
        'successful_emails': successful_emails,
        'failed_emails': failed_emails,
        'success_rate': round(success_rate, 2),
        'emails_by_day': emails_by_day,
        'average_per_day': total_emails / max(len(emails_by_day), 1),
        'generated_papers': len(generated_papers)
    }

# Background task functions
async def process_email_batch(
    task_id: str,
    email_list: List[Dict],
    request: EmailRequest,
    email_service: EmailSender
):
    """Background task to process email batch"""
    
    processing_status[task_id]['status'] = 'processing'
    processing_status[task_id]['started_at'] = datetime.now().isoformat()
    processing_status[task_id]['phase'] = 'sending_emails'
    
    template_path = f"templates/email_templates/{request.body_template}.html"
    
    if not os.path.exists(template_path):
        template_path = "templates/email_templates/journal_invitation.html"
    
    results = email_service.send_bulk_emails(
        email_list=email_list,
        subject_template=request.subject_template,
        body_template_path=template_path,
        test_mode=request.test_mode
    )
    
    # Update sent emails
    for detail in results['details']:
        sent_emails.append({
            'task_id': task_id,
            'timestamp': time.time(),
            'student_email': detail['email'],
            'student_name': detail['name'],
            'success': detail['success'],
            'message': detail['message']
        })
    
    # Update processing status
    processing_status[task_id].update({
        'status': 'completed',
        'completed_at': datetime.now().isoformat(),
        'sent': results['success'],
        'failed': results['failed'],
        'details': results
    })

async def queue_emails_for_papers(request: EmailRequest, paper_results: List[Dict]):
    """Queue emails for papers that were generated"""
    # This would be implemented to connect paper generation with email sending
    pass

async def process_batch_workflow(task_id: str, request: BatchProcessRequest):
    """Process complete batch workflow"""
    
    try:
        # Phase 1: Paper Generation
        if request.generate_papers and request.paper_config:
            processing_status[task_id].update({
                'phase': 'generating_papers',
                'progress': 25
            })
            
            # Generate papers (simplified - in reality would call the endpoint)
            await asyncio.sleep(2)  # Simulate work
            
            processing_status[task_id]['progress'] = 50
        
        # Phase 2: Email Sending
        if request.send_emails and request.email_config:
            processing_status[task_id].update({
                'phase': 'sending_emails',
                'progress': 75
            })
            
            # Send emails (simplified)
            await asyncio.sleep(3)  # Simulate work
            
            processing_status[task_id]['progress'] = 100
        
        processing_status[task_id].update({
            'status': 'completed',
            'phase': 'completed',
            'completed_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        processing_status[task_id].update({
            'status': 'failed',
            'error': str(e),
            'completed_at': datetime.now().isoformat()
        })

def estimate_remaining_time(status: Dict) -> Optional[str]:
    """Estimate remaining time for batch process"""
    if status.get('status') not in ['processing', 'starting']:
        return None
    
    progress = status.get('progress', 0)
    if progress <= 0:
        return "Estimating..."
    
    started_at = status.get('started_at')
    if not started_at:
        return "Estimating..."
    
    try:
        start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
        elapsed = (datetime.now() - start_time).total_seconds()
        
        if progress > 0:
            total_estimated = elapsed / (progress / 100)
            remaining = total_estimated - elapsed
            
            if remaining > 3600:
                return f"{remaining/3600:.1f} hours"
            elif remaining > 60:
                return f"{remaining/60:.1f} minutes"
            else:
                return f"{remaining:.0f} seconds"
    except:
        pass
    
    return "Estimating..."

# Test endpoint
@router.post("/test-email", summary="Send test email")
async def send_test_email(
    recipient: EmailStr,
    email_config: EmailConfig
):
    """
    Send a test email to verify email configuration
    """
    try:
        email_service = EmailSender(
            smtp_server=email_config.smtp_server,
            smtp_port=email_config.smtp_port,
            use_ssl=email_config.use_ssl
        )
        email_service.sender_email = email_config.sender_email
        email_service.sender_password = email_config.sender_password
        email_service.sender_name = email_config.sender_name
        
        # Simple test email
        success, message = email_service.send_email(
            recipient_email=recipient,
            subject="Test Email from Academic Research System",
            body_html="""
            <h1>Test Email</h1>
            <p>This is a test email sent from the Academic Research System.</p>
            <p>If you received this, your email configuration is working correctly.</p>
            """,
            body_text="Test email from Academic Research System"
        )
        
        if success:
            return {
                "status": "success",
                "message": "Test email sent successfully",
                "recipient": recipient
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to send test email: {message}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email configuration error: {str(e)}")