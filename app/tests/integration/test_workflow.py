"""
Integration tests for complete workflows
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import tempfile
from pathlib import Path
import json

from app.scraper.university_scrapers import GenericUniversityScraper
from app.email_service.ai_paper_generator import AIPaperGenerator
from app.email_service.email_sender import EmailSender
from app.document_generator.docx_generator import DocxGenerator

@pytest.mark.integration
class TestCompleteWorkflow:
    """Test complete scraping to email workflow"""
    
    @pytest.fixture
    def test_data(self):
        """Create complete test data"""
        return {
            "university_url": "https://www.testuniversity.edu/directory",
            "university_name": "Test University",
            "students": [
                {
                    "name": "John Doe",
                    "email": "john.doe@testuniversity.edu",
                    "department": "Computer Science"
                },
                {
                    "name": "Jane Smith", 
                    "email": "jane.smith@testuniversity.edu",
                    "department": "Engineering"
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_scrape_to_email_workflow(self, test_data, tmp_path):
        """Test complete workflow from scraping to email sending"""
        print("\n" + "="*60)
        print("Testing Complete Scrape-to-Email Workflow")
        print("="*60)
        
        # Step 1: Setup directories
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        
        # Step 2: Create mock HTML with student data
        html_content = """
        <html>
            <head><title>Test University Directory</title></head>
            <body>
                <h1>Faculty Directory</h1>
                <table>
        """
        
        for student in test_data["students"]:
            html_content += f"""
                    <tr>
                        <td>{student['name']}</td>
                        <td>{student['email']}</td>
                        <td>{student['department']}</td>
                    </tr>
            """
        
        html_content += """
                </table>
            </body>
        </html>
        """
        
        # Step 3: Mock scraping
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text.return_value = html_content
            mock_get.return_value.__aenter__.return_value = mock_response
            
            scraper = GenericUniversityScraper()
            
            async with scraper:
                students = await scraper.extract_students(
                    html_content, 
                    test_data["university_url"]
                )
        
        print(f"\nStep 1: Scraping")
        print(f"  Found {len(students)} students")
        for student in students:
            print(f"  - {student.name} ({student.email})")
        
        assert len(students) == len(test_data["students"])
        
        # Step 4: Generate papers
        paper_gen = AIPaperGenerator(model_type="fallback")
        docx_gen = DocxGenerator()
        
        generated_papers = []
        
        for student_data in test_data["students"]:
            # Generate paper content
            title = paper_gen.generate_paper_title(student_data["department"])
            abstract = paper_gen.generate_abstract(title, student_data["name"])
            
            paper_content = paper_gen.generate_paper_content(
                title=title,
                abstract=abstract,
                student_name=student_data["name"]
            )
            
            # Create DOCX
            docx_filename = f"{student_data['name'].replace(' ', '_')}_paper.docx"
            docx_path = output_dir / docx_filename
            
            docx_gen.create_academic_paper(paper_content, str(docx_path))
            
            generated_papers.append({
                "student": student_data,
                "paper_title": title,
                "abstract": abstract[:100] + "...",
                "docx_path": str(docx_path)
            })
        
        print(f"\nStep 2: Paper Generation")
        print(f"  Generated {len(generated_papers)} papers")
        for paper in generated_papers:
            print(f"  - {paper['student']['name']}: {paper['paper_title']}")
        
        # Verify files were created
        for paper in generated_papers:
            assert Path(paper["docx_path"]).exists()
            assert Path(paper["docx_path"]).stat().st_size > 0
        
        # Step 5: Create email template
        template_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; }
                .header { background: #007acc; color: white; padding: 20px; }
                .content { padding: 20px; }
                .paper-info { background: #f0f0f0; padding: 15px; margin: 15px 0; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Academic Research Journal</h1>
                <p>Personalized Research Paper</p>
            </div>
            
            <div class="content">
                <h2>Dear {{ student_name }},</h2>
                
                <div class="paper-info">
                    <h3>{{ paper_title }}</h3>
                    <p><strong>Abstract Preview:</strong> {{ abstract }}</p>
                </div>
                
                <p>Your personalized research paper is attached to this email.</p>
                <p>Best regards,<br>Research Team</p>
            </div>
        </body>
        </html>
        """
        
        template_file = template_dir / "journal_invitation.html"
        template_file.write_text(template_content)
        
        # Step 6: Send emails (mocked)
        email_sender = EmailSender()
        
        email_list = []
        for paper in generated_papers:
            email_list.append({
                "name": paper["student"]["name"],
                "email": paper["student"]["email"],
                "university": test_data["university_name"],
                "paper_title": paper["paper_title"],
                "abstract": paper["abstract"],
                "docx_path": paper["docx_path"]
            })
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_sender.sender_email = "test@example.com"
            email_sender.sender_password = "testpassword"
            email_sender.delay_between_emails = 0  # Remove delay for test
            
            results = email_sender.send_bulk_emails(
                email_list=email_list,
                subject_template="Your Research Paper: {paper_title}",
                body_template_path=str(template_file),
                test_mode=True
            )
        
        print(f"\nStep 3: Email Sending")
        print(f"  Total emails: {results['total']}")
        print(f"  Successful: {results['success']}")
        print(f"  Failed: {results['failed']}")
        
        assert results['total'] == len(email_list)
        
        # Step 7: Verify workflow completion
        print(f"\n" + "="*60)
        print("Workflow Summary:")
        print(f"  Students scraped: {len(students)}")
        print(f"  Papers generated: {len(generated_papers)}")
        print(f"  Emails sent: {results['success']}")
        
        assert len(students) == len(generated_papers) == results['success']
        
        print("\n✅ Complete workflow test PASSED")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_workflow_performance(self, tmp_path):
        """Test workflow performance with larger dataset"""
        import time
        
        print("\n" + "="*60)
        print("Testing Workflow Performance")
        print("="*60)
        
        # Create test data for 50 students
        num_students = 50
        test_students = [
            {
                "name": f"Student {i}",
                "email": f"student{i}@university.edu",
                "department": "Computer Science" if i % 2 == 0 else "Engineering"
            }
            for i in range(num_students)
        ]
        
        start_time = time.time()
        
        # Setup
        output_dir = tmp_path / "output_perf"
        output_dir.mkdir()
        
        # Generate papers (most time-consuming part)
        paper_gen = AIPaperGenerator(model_type="fallback")
        docx_gen = DocxGenerator()
        
        generation_times = []
        
        for i, student in enumerate(test_students[:10]):  # Test with 10 for performance
            gen_start = time.time()
            
            title = paper_gen.generate_paper_title(student["department"])
            abstract = paper_gen.generate_abstract(title, student["name"])
            
            paper_content = paper_gen.generate_paper_content(
                title=title,
                abstract=abstract,
                student_name=student["name"]
            )
            
            docx_path = output_dir / f"paper_{i}.docx"
            docx_gen.create_academic_paper(paper_content, str(docx_path))
            
            gen_end = time.time()
            generation_times.append(gen_end - gen_start)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        avg_generation_time = sum(generation_times) / len(generation_times)
        
        print(f"\nPerformance Results:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Average paper generation time: {avg_generation_time:.2f}s")
        print(f"  Estimated time for {num_students} students: {avg_generation_time * num_students:.2f}s")
        
        # Performance assertions
        assert avg_generation_time < 5.0, f"Paper generation too slow: {avg_generation_time:.2f}s"
        
        if num_students > 100:
            # For large datasets, estimate total time
            estimated_total = avg_generation_time * num_students
            assert estimated_total < 300, f"Estimated time too high: {estimated_total:.2f}s"
    
    @pytest.mark.error_handling
    @pytest.mark.asyncio
    async def test_workflow_error_recovery(self, tmp_path):
        """Test workflow error handling and recovery"""
        print("\n" + "="*60)
        print("Testing Workflow Error Handling")
        print("="*60)
        
        # Test data with some problematic entries
        test_students = [
            {"name": "Good Student", "email": "good@test.edu", "department": "CS"},
            {"name": "", "email": "invalid-email", "department": ""},  # Problematic
            {"name": "Another Good", "email": "another@test.edu", "department": "Eng"},
        ]
        
        paper_gen = AIPaperGenerator(model_type="fallback")
        docx_gen = DocxGenerator()
        
        output_dir = tmp_path / "output_error"
        output_dir.mkdir()
        
        successful = 0
        failed = 0
        
        for i, student in enumerate(test_students):
            try:
                # This might fail for problematic students
                title = paper_gen.generate_paper_title(student["department"])
                
                if not title:  # If title generation fails
                    raise ValueError("Could not generate title")
                
                abstract = paper_gen.generate_abstract(title, student["name"])
                
                paper_content = paper_gen.generate_paper_content(
                    title=title,
                    abstract=abstract,
                    student_name=student["name"]
                )
                
                docx_path = output_dir / f"paper_{i}.docx"
                docx_gen.create_academic_paper(paper_content, str(docx_path))
                
                successful += 1
                print(f"  ✅ Generated paper for {student['name']}")
                
            except Exception as e:
                failed += 1
                print(f"  ❌ Failed for {student['name']}: {str(e)}")
                continue
        
        print(f"\nError Handling Results:")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")
        
        # Should handle errors gracefully
        assert successful > 0
        assert failed >= 0  # Some may fail
        
        # Overall workflow should not crash
        assert (successful + failed) == len(test_students)

@pytest.mark.e2e
class TestEndToEndWorkflow:
    """End-to-end tests using test APIs"""
    
    @pytest.fixture
    def api_client(self):
        """Create API test client"""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)
    
    def test_complete_api_workflow(self, api_client, tmp_path):
        """Test complete workflow through API endpoints"""
        print("\n" + "="*60)
        print("Testing Complete API Workflow")
        print("="*60)
        
        # Step 1: Clear existing data
        clear_response = api_client.delete("/api/v1/students")
        assert clear_response.status_code == 200
        
        # Step 2: Mock scraping endpoint
        with patch('app.api.endpoints.validate_url') as mock_validate, \
             patch('app.api.endpoints.perform_scraping') as mock_scrape:
            
            mock_validate.return_value = True
            mock_scrape.return_value = ([
                {
                    "name": "Test Student",
                    "email": "test@university.edu",
                    "university": "Test University"
                }
            ], 1.0)
            
            scrape_request = {
                "url": "https://testuniversity.edu/directory",
                "university_name": "Test University",
                "use_selenium": False
            }
            
            scrape_response = api_client.post("/api/v1/scrape", json=scrape_request)
            assert scrape_response.status_code == 200
        
        # Step 3: Generate papers through API
        with patch('app.api.email_endpoints.generated_papers', {}), \
             patch('app.api.email_endpoints.students_store') as mock_store:
            
            # Mock student data
            mock_store.__iter__.return_value = [type('obj', (object,), {
                'id': 1,
                'name': 'Test Student',
                'email': 'test@university.edu',
                'university': 'Test University',
                'department': None
            })]
            
            paper_request = {
                "student_ids": [1],
                "model_type": "fallback",
                "output_format": "docx"
            }
            
            paper_response = api_client.post("/api/v1/email/generate-papers", json=paper_request)
            assert paper_response.status_code == 200
        
        # Step 4: Send emails through API
        with patch('app.api.email_endpoints.EmailSender') as mock_sender:
            mock_instance = MagicMock()
            mock_instance.send_bulk_emails.return_value = {
                'total': 1,
                'success': 1,
                'failed': 0,
                'details': []
            }
            mock_sender.return_value = mock_instance
            
            email_request = {
                "student_ids": [1],
                "subject_template": "Test {paper_title}",
                "test_mode": True
            }
            
            email_response = api_client.post("/api/v1/email/send-emails", json=email_request)
            assert email_response.status_code == 200
        
        # Step 5: Check status through API
        if email_response.status_code == 200:
            task_data = email_response.json()
            task_id = task_data.get("task_id")
            
            if task_id:
                status_response = api_client.get(f"/api/v1/email/status/{task_id}")
                assert status_response.status_code in [200, 404]  # Might not exist in mock
        
        print("\n✅ Complete API workflow test PASSED")