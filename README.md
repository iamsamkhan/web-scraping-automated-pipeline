# web-scraping-automated-pipeline
# University Student Scraper API

A FastAPI-based web scraping application that extracts student names and email IDs from university websites.

## Features

- **Multiple Scraping Strategies**: Uses BeautifulSoup4 for static pages and Selenium for JavaScript-rendered content
- **Intelligent Parsing**: Automatically detects student information from various page structures
- **Email Validation**: Cleans and validates extracted email addresses
- **Rate Limiting**: Built-in rate limiting to respect website policies
- **RESTful API**: Easy-to-use endpoints for scraping and data retrieval
- **Asynchronous Processing**: High-performance async scraping
- **Error Handling**: Comprehensive error handling and logging

## Installation

1. **Clone the repository:**
```bash
git clone <https://github.com/iamsamkhan/web-scraping-automated-pipeline.git>

cd web-scraping-automated-pipeline.



Features of the Complete System:
1. Paper Generation Features:
AI-powered paper content generation

Multiple model support (OpenAI, Llama, fallback)

Personalized for each student

Professional DOCX formatting

Includes abstract, references, sections

2. Email Automation Features:
Bulk email sending with rate limiting

Personalized email templates

DOCX attachment support

Test mode for safe testing

Email sending history and logs

Success/failure tracking

3. API Features:
Complete RESTful API

Background task processing

Real-time status monitoring

Download options (individual/ZIP)

Template management

Statistics and analytics

4. Security Features:
Email configuration validation

Rate limiting

Error handling

Logging

Background processing for long tasks

This complete system provides end-to-end automation from student data scraping to personalized paper generation and email distribution, all through a robust FastAPI interface.

5. Complete API Documentation
Available Endpoints:
1. Paper Generation
POST /api/v1/email/generate-papers - Generate academic papers for students

GET /api/v1/email/download-paper/{student_id} - Download specific paper

GET /api/v1/email/download-papers - Download multiple papers as ZIP

2. Email Sending
POST /api/v1/email/send-emails - Send emails with paper attachments

GET /api/v1/email/status/{task_id} - Check email sending status

GET /api/v1/email/sent-emails - Get sent email history

POST /api/v1/email/test-email - Send test email

3. Batch Processing
POST /api/v1/email/batch-process - Complete batch workflow

GET /api/v1/email/batch-status/{task_id} - Check batch status

4. Template Management
GET /api/v1/email/templates - List available templates

POST /api/v1/email/templates/upload - Upload new template

5. Statistics & Monitoring
GET /api/v1/email/statistics - Get email statistics
6. How to Run the Complete System:
Install dependencies:

bash
pip install -r requirements.txt
Set up environment variables:

bash
cp .env.example .env
# Edit .env with your email credentials
Create necessary directories:

bash
mkdir -p templates/email_templates output/papers logs data/journals models
Create default templates:

bash
# The system will create default templates automatically on first run
# Or you can create your own templates in templates/email_templates/
Run the FastAPI server:

bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Access the API documentation:

Swagger UI: http://localhost:8000/docs

ReDoc: http://localhost:8000/redoc

Test the API:

bash
python test_email_api.py
