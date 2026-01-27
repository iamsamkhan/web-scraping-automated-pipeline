"""
Test script for the Email Automation API
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"

def test_generate_papers():
    """Test paper generation endpoint"""
    
    print("Testing paper generation...")
    
    # First, get some students
    students_response = requests.get(f"{BASE_URL}/students?limit=3")
    students = students_response.json()
    
    if not students:
        print("No students found. Please scrape some first.")
        return
    
    student_ids = [s['id'] for s in students]
    
    # Generate papers
    payload = {
        "student_ids": student_ids,
        "model_type": "fallback",
        "output_format": "docx",
        "include_abstract": True,
        "include_references": True
    }
    
    response = requests.post(
        f"{BASE_URL}/email/generate-papers",
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nGenerated {result['papers_generated']} papers:")
        for paper in result['results']:
            status = "✓" if paper['status'] == 'success' else "✗"
            print(f"  {status} {paper['student_name']}: {paper.get('paper_title', 'N/A')}")
        
        # Download papers
        download_url = f"{BASE_URL}/email/download-papers?ids={','.join(map(str, student_ids))}"
        print(f"\nDownload papers: {download_url}")
        
        return student_ids
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

def test_send_emails(student_ids):
    """Test email sending endpoint"""
    
    print("\nTesting email sending...")
    
    # Note: Update with your actual email configuration
    email_config = {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender_email": "your-email@gmail.com",  # CHANGE THIS
        "sender_password": "your-app-password",  # CHANGE THIS
        "sender_name": "Academic Research Team",
        "use_ssl": False
    }
    
    payload = {
        "student_ids": student_ids,
        "subject_template": "Research Opportunity: {paper_title}",
        "body_template": "journal_invitation",
        "test_mode": True,  # Set to False for actual sending
        "delay_seconds": 1,
        "email_config": email_config
    }
    
    response = requests.post(
        f"{BASE_URL}/email/send-emails",
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nEmail task started:")
        print(f"  Task ID: {result['task_id']}")
        print(f"  Status: {result['status']}")
        print(f"  Total emails: {result['total_emails']}")
        print(f"  Test mode: {result['test_mode']}")
        
        # Monitor task
        task_id = result['task_id']
        monitor_url = f"{BASE_URL}/email/status/{task_id}"
        print(f"\nMonitor task: {monitor_url}")
        
        # Wait and check status
        time.sleep(3)
        status_response = requests.get(monitor_url)
        if status_response.status_code == 200:
            status = status_response.json()
            print(f"\nCurrent status:")
            print(f"  Phase: {status.get('phase', 'N/A')}")
            print(f"  Sent: {status.get('sent', 0)}")
            print(f"  Failed: {status.get('failed', 0)}")
            print(f"  Progress: {status.get('progress_percentage', 0):.1f}%")
        
        return task_id
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

def test_batch_process():
    """Test complete batch processing"""
    
    print("\nTesting batch processing...")
    
    payload = {
        "generate_papers": True,
        "send_emails": False,  # Set to True with proper email config
        "paper_config": {
            "model_type": "fallback",
            "output_format": "docx"
        },
        "email_config": {
            "subject_template": "Your Research Paper Draft",
            "test_mode": True
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/email/batch-process",
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nBatch process started:")
        print(f"  Task ID: {result['task_id']}")
        print(f"  Status: {result['status']}")
        print(f"  Phases: {result['phases']}")
        
        return result['task_id']
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

def test_templates():
    """Test template management"""
    
    print("\nTesting template management...")
    
    response = requests.get(f"{BASE_URL}/email/templates")
    
    if response.status_code == 200:
        templates = response.json()
        print(f"Template directory: {templates.get('template_dir')}")
        print(f"\nAvailable templates:")
        for template in templates.get('templates', []):
            print(f"  • {template['name']} ({template['filename']})")
    else:
        print(f"Error: {response.status_code}")

def test_statistics():
    """Test statistics endpoint"""
    
    print("\nTesting statistics...")
    
    response = requests.get(f"{BASE_URL}/email/statistics?period=week")
    
    if response.status_code == 200:
        stats = response.json()
        print(f"\nEmail Statistics (Last {stats['period']}):")
        print(f"  Total emails: {stats['total_emails']}")
        print(f"  Successful: {stats['successful_emails']}")
        print(f"  Failed: {stats['failed_emails']}")
        print(f"  Success rate: {stats['success_rate']}%")
        print(f"  Generated papers: {stats['generated_papers']}")
    else:
        print(f"Error: {response.status_code}")

def test_download_papers(student_ids):
    """Test paper download"""
    
    if not student_ids:
        print("No student IDs to download")
        return
    
    print(f"\nTesting paper download for students: {student_ids}")
    
    ids_param = ','.join(map(str, student_ids))
    response = requests.get(f"{BASE_URL}/email/download-papers?ids={ids_param}")
    
    if response.status_code == 200:
        # Save the ZIP file
        filename = f"research_papers_{int(time.time())}.zip"
        with open(filename, 'wb') as f:
            f.write(response.content)
        
        print(f"✓ Papers downloaded to: {filename}")
        print(f"  Content-Type: {response.headers.get('content-type')}")
        print(f"  File size: {len(response.content)} bytes")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

def main():
    """Main test function"""
    
    print("Academic Email Automation API Test")
    print("=" * 50)
    
    # Check if API is running
    try:
        health = requests.get("http://localhost:8000/health", timeout=5)
        if health.status_code != 200:
            print("API is not running. Please start it with: uvicorn app.main:app --reload")
            return
    except:
        print("API is not running. Please start it with: uvicorn app.main:app --reload")
        return
    
    # Run tests
    test_templates()
    
    # Generate papers for first 3 students
    student_ids = test_generate_papers()
    
    if student_ids:
        # Test download
        test_download_papers(student_ids[:2])  # Download for first 2
        
        # Test email sending (requires email configuration)
        # Uncomment and configure email settings to test
        # test_send_emails(student_ids)
    
    # Test batch process
    # batch_task_id = test_batch_process()
    
    # Test statistics
    test_statistics()
    
    print("\n" + "=" * 50)
    print("API Documentation: http://localhost:8000/docs")

if __name__ == "__main__":
    main()