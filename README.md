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
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
Access the API documentation:

Swagger UI: http://localhost:8000/docs

ReDoc: http://localhost:8000/redoc

Test the API:

bash
python test_email_api.py




🌟 Features
1. Web Scraping Module
Scrapes student names and email IDs from university websites

Supports both static pages (BeautifulSoup4) and JavaScript-rendered content (Selenium)

Intelligent parsing of various website structures

Email validation and normalization

Multiple scraping strategies

2. AI-Powered Paper Generation
Generates personalized academic papers for each student

Multiple AI backend support (OpenAI, Llama 2, fallback mode)

Professional DOCX formatting with styles

Includes all academic paper sections:

Abstract

Introduction

Literature Review

Methodology

Results

Discussion

Conclusion

References

3. Email Automation System
Bulk email sending with rate limiting

Personalized email templates with Jinja2

DOCX attachment support

Test mode for safe testing

Comprehensive logging and tracking

Email configuration validation

4. RESTful API
FastAPI-based endpoints

Interactive API documentation (Swagger/ReDoc)

Background task processing

Real-time status monitoring

File download endpoints

Statistics and analytics

📁 Project Structure
text
university_scraper/
├── app/
│   ├── api/
│   │   ├── endpoints.py          # Scraping endpoints
│   │   └── email_endpoints.py    # Email & document endpoints
│   ├── core/
│   │   └── config.py            # Configuration management
│   ├── models/
│   │   └── schemas.py           # Pydantic schemas
│   ├── scraper/
│   │   ├── base_scraper.py      # Base scraper class
│   │   └── university_scrapers.py # University-specific scrapers
│   ├── email_service/
│   │   ├── ai_paper_generator.py # AI paper generation
│   │   ├── email_sender.py      # Email sending logic
│   │   └── template_manager.py  # Template management
│   ├── document_generator/
│   │   ├── docx_generator.py    # DOCX document generation
│   │   └── content_formatter.py # Content formatting
│   └── utils/
│       └── helpers.py           # Utility functions
├── templates/
│   ├── email_templates/         # Email HTML templates
│   └── paper_templates/         # Paper templates
├── output/
│   └── papers/                  # Generated papers storage
├── logs/                        # Application logs
├── data/                        # Data files
└── models/                      # AI model storage (optional)
🚀 Quick Start
Prerequisites
Python 3.8+

Chrome/Firefox browser (for Selenium)

Git

Installation
Clone the repository:

bash
git clone <repository-url>
cd university_scraper
Create virtual environment:

bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install dependencies:

bash
pip install -r requirements.txt
Set up environment variables:

bash
cp .env.example .env
# Edit .env with your configuration
Install ChromeDriver (for Selenium):

bash
# On Ubuntu/Debian:
sudo apt-get install -y chromium-chromedriver

# On macOS:
brew install --cask chromedriver

# On Windows: Automatically installed by webdriver-manager
⚙️ Configuration
Edit .env file:

env
# API Configuration
API_V1_PREFIX=/api/v1
PROJECT_NAME=Academic Research Automation
VERSION=2.0.0

# Email Configuration (Required for email sending)
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password  # Use app password for Gmail
EMAIL_SENDER_NAME=Academic Research Team
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
USE_SSL=false

# AI Configuration (Optional)
OPENAI_API_KEY=your-openai-api-key
LLAMA_MODEL_PATH=models/llama-2-7b-chat.Q4_K_M.gguf

# Rate Limiting
EMAILS_PER_HOUR=500
DELAY_BETWEEN_EMAILS=2
🏃‍♂️ Running the Application
Start the FastAPI server:
bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
The API will be available at:

API Documentation: http://localhost:8000/docs

ReDoc Documentation: http://localhost:8000/redoc

Health Check: http://localhost:8000/health

📚 API Endpoints
Scraping Endpoints (/api/v1)
POST /scrape - Scrape student data from university URLs

GET /students - Get scraped student data

GET /students/search - Search students

GET /universities - Get list of scraped universities

Email Automation Endpoints (/api/v1/email)
POST /generate-papers - Generate academic papers

POST /send-emails - Send emails with paper attachments

POST /batch-process - Complete batch workflow

GET /status/{task_id} - Check email sending status

GET /download-papers - Download papers as ZIP

GET /templates - List email templates

GET /statistics - Get email statistics

🎯 Usage Examples
1. Scrape University Data
python
import requests

scrape_data = {
    "url": "https://www.university.edu/directory",
    "university_name": "Example University",
    "use_selenium": False
}

response = requests.post(
    "http://localhost:8000/api/v1/scrape",
    json=scrape_data
)
print(response.json())
2. Generate Papers for Students
python
paper_config = {
    "student_ids": [1, 2, 3],
    "model_type": "fallback",
    "output_format": "docx"
}

response = requests.post(
    "http://localhost:8000/api/v1/email/generate-papers",
    json=paper_config
)
print(response.json())
3. Send Emails with Papers
python
email_config = {
    "student_ids": [1, 2, 3],
    "subject_template": "Research Paper: {paper_title}",
    "test_mode": True,
    "email_config": {
        "sender_email": "your-email@gmail.com",
        "sender_password": "your-password",
        "sender_name": "Research Team"
    }
}

response = requests.post(
    "http://localhost:8000/api/v1/email/send-emails",
    json=email_config
)
print(response.json())
4. Complete Batch Processing
bash
curl -X POST "http://localhost:8000/api/v1/email/batch-process" \
  -H "Content-Type: application/json" \
  -d '{
    "generate_papers": true,
    "send_emails": true,
    "paper_config": {
      "model_type": "fallback"
    },
    "email_config": {
      "test_mode": true
    }
  }'
🔧 Advanced Configuration
AI Model Configuration
Using OpenAI:

python
paper_config = {
    "model_type": "openai",
    "api_key": "your-openai-api-key",
    "output_format": "docx"
}
Using Local Llama Model:

Download Llama 2 model:

bash
mkdir -p models
# Download Llama 2 7B Chat model (GGUF format)
# Place in models/ directory
Configure:

python
paper_config = {
    "model_type": "llama",
    "output_format": "docx"
}
Custom Email Templates
Create custom template in templates/email_templates/:

html
<!-- custom_template.html -->
{% extends "base.html" %}

{% block content %}
    <h2>Dear {{ student_name }},</h2>
    <!-- Your custom content -->
{% endblock %}
Use custom template:

python
email_config = {
    "body_template": "custom_template",
    # ... other config
}
📊 Monitoring and Logs
View Logs
bash
# Email logs
tail -f logs/email_log.json

# Application logs (if using uvicorn with --log-config)
Check Statistics
bash
curl "http://localhost:8000/api/v1/email/statistics?period=week"
Monitor Background Tasks
bash
# Check status of a task
curl "http://localhost:8000/api/v1/email/status/{task_id}"
🐛 Troubleshooting
Common Issues
Email sending fails:

Verify SMTP credentials in .env

Use app password for Gmail (not regular password)

Check firewall/port settings

Selenium scraping fails:

Ensure Chrome/Firefox is installed

Update webdriver: webdriver-manager update

Check browser compatibility

AI generation fails:

Verify API keys for OpenAI/Anthropic

Check internet connection for API calls

Ensure model files exist for local models

Rate limiting issues:

Adjust EMAILS_PER_HOUR in .env

Increase DELAY_BETWEEN_EMAILS

Debug Mode
Run with verbose logging:

bash
uvicorn app.main:app --reload --log-level debug
🔒 Security Considerations
Email Credentials:

Never commit .env file to version control

Use app-specific passwords

Rotate passwords regularly

API Security:

Use HTTPS in production

Implement authentication/authorization

Rate limit endpoints

Data Privacy:

Comply with GDPR/other regulations

Anonymize student data when possible

Secure storage of generated documents

Web Scraping Ethics:

Respect robots.txt

Implement rate limiting

Use for educational purposes only

🧪 Testing
Run Test Suite
bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
Manual Testing
Use the provided test script:

bash
python test_email_api.py
📈 Performance Optimization
Database Integration:

Add PostgreSQL/MySQL for production

Implement connection pooling

Add database migrations with Alembic

Caching:

Add Redis for caching

Cache frequently accessed data

Implement request caching

Background Processing:

Use Celery for heavy tasks

Implement task queues

Add retry mechanisms

File Storage:

Use cloud storage (S3, GCS)

Implement CDN for file distribution

Add file compression

🤝 Contributing
Fork the repository

Create a feature branch

Commit your changes

Push to the branch

Open a Pull Request

Development Guidelines
Follow PEP 8 style guide

Add type hints for new functions

Write docstrings for all public methods

Add tests for new features

Update documentation

📄 License
This project is licensed under the apache License - see the LICENSE file for details.

🙏 Acknowledgments
FastAPI for the web framework

BeautifulSoup4 for web scraping

Selenium for browser automation

OpenAI for AI capabilities

python-docx for document generation

  Support
For issues and questions:

Check the Issues page

Create a new issue with detailed description

Email: smshad0001S.com

🎨 System Architecture Diagram
text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   University    │    │    FastAPI      │    │   Email/SMTP    │
│     Websites    ├───►│     Server      ├───►│     Server      │
│                 │    │                 │    │                 │
└─────────────────┘    └────────┬────────┘    └─────────────────┘
                                 │
                                 │
                    ┌────────────▼────────────┐
                    │                         │
                    │      Background         │
                    │       Workers           │
                    │                         │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │                         │
                    │       Storage           │
                    │  (Database/Files/Logs)  │
                    │                         │
                    └─────────────────────────┘
🔄 Workflow
Scrape Phase:

Collect student data from universities

Validate and normalize emails

Store in temporary database

Generation Phase:

Generate personalized papers using AI

Create professional DOCX documents

Store in output directory

Distribution Phase:

Send emails with paper attachments

Track delivery status

Generate reports

Monitoring Phase:

Monitor system health

Generate statistics

Handle failures




 🚀 CI/CD Pipeline
This project includes a comprehensive CI/CD pipeline for automated testing, building, and deployment.

Pipeline Stages
Code Quality & Testing

Python linting (Black, Flake8)

Type checking (MyPy)

Security scanning (Bandit, Safety)

Unit tests with coverage

Integration tests

Docker Build & Scan

Multi-architecture Docker builds

Security vulnerability scanning (Trivy)

Image optimization

Deployment

Staging deployment (auto on develop)

Production deployment (manual approval)

Blue-green deployment strategy

Monitoring

Performance metrics collection

Alert configuration

Log aggregation

Deployment Environments
Development: Local Docker Compose

Staging: AWS ECS with test data

Production: AWS EKS with high availability

Running Locally
bash
# Development environment
docker-compose -f docker-compose.dev.yml up

# Production simulation
docker-compose -f docker-compose.prod.yml up

# Run tests
docker-compose -f docker-compose.test.yml run --rm api pytest

# Run linting
docker-compose -f docker-compose.test.yml run --rm api black --check app/
Infrastructure
Managed with Terraform:

bash
# Initialize
cd terraform && terraform init

# Plan changes
terraform plan -var-file=vars/production.tfvars

# Apply changes
terraform apply -var-file=vars/production.tfvars
Monitoring
Access monitoring dashboards:

Grafana: http://localhost:3000

Prometheus: http://localhost:9090

Alertmanager: http://localhost:9093

📊 Performance Metrics
The pipeline collects and reports:

Test coverage percentage

Code quality scores

Security vulnerability counts

Build times

Deployment success rates

API response times

🔧 Troubleshooting Pipeline Issues
Build fails:

bash
# Check logs
cat .github/workflows/ci-cd.yml | grep -A 5 -B 5 "failed"

# Run locally
act -j code-quality
Deployment fails:

Check AWS credentials

Verify ECS/EKS cluster status

Check resource limits

Tests fail:

bash
# Run specific test
pytest tests/test_specific.py -v

# Debug with pdb
pytest --pdb tests/
🔐 Security
All secrets stored in GitHub Secrets

Regular security scans

Dependency updates automated via Dependabot

Least privilege IAM roles

Encrypted data at rest and in transit

This complete CI/CD pipeline ensures automated, reliable, and secure deployments of the Academic Research Automation System across all environments.



📊 Deployment Strategies Comparison
Strategy	Pros	Cons	Best For
Blue-Green	Zero downtime, Instant rollback, Easy testing	Double infrastructure cost, Database migration complexity	Critical production applications
Canary	Gradual risk mitigation, Real user testing, Performance monitoring	Complex traffic routing, Longer deployment time	Applications with many users
Rolling Update	Resource efficient, Simple to implement	Potential service disruption, Rollback takes time	Non-critical applications
🚀 Quick Start Commands
bash
# Initialize Blue-Green deployment
kubectl apply -f k8s/blue-green/

# Deploy new version with canary strategy
python scripts/blue-green-deploy.py --action canary --image-tag v1.3.0

# Check deployment status
python scripts/blue-green-deploy.py --action status

# Monitor deployments
python scripts/monitor-blue-green.py --prometheus-url http://localhost:9090 --action monitor

# Rollback if needed
python scripts/blue-green-deploy.py --action rollback

# Using GitHub Actions
gh workflow run blue-green.yml --ref main \
  -f environment=production \
  -f deployment_strategy=canary
🎯 Benefits of Blue-Green Deployment
Zero Downtime: Switch traffic instantly between environments

Instant Rollback: Revert to previous version in seconds

Safe Testing: Test new version with real traffic before full switch

Reduced Risk: Isolate failures to single environment

Easy Validation: Compare performance between versions in real-time

This comprehensive Blue-Green deployment strategy ensures reliable, zero-downtime deployments for the Academic Research Automation System with full monitoring, automation, and rollback capabilities.


Happy Researching! 🎓📚
 
 Shamshad Ahmed 
