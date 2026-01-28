"""
Comprehensive unit tests for FastAPI endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime

from app.main import app
from app.models.schemas import StudentBase, StudentResponse, UniversityScrapeRequest

class TestScrapingEndpoints:
    """Test scraping-related API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        with TestClient(app) as client:
            yield client
    
    @pytest.fixture
    def mock_scraper(self):
        """Mock scraper"""
        with patch('app.api.endpoints.GenericUniversityScraper') as mock:
            scraper_instance = AsyncMock()
            scraper_instance.extract_students.return_value = [
                StudentBase(
                    name="John Doe",
                    email="john.doe@test.edu",
                    university="Test University"
                )
            ]
            scraper_instance.fetch_html.return_value = "<html>Test</html>"
            mock.return_value.__aenter__.return_value = scraper_instance
            yield mock
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "endpoints" in data
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    @patch('app.api.endpoints.validate_url')
    @patch('app.api.endpoints.perform_scraping')
    def test_scrape_endpoint_success(self, mock_perform_scraping, mock_validate_url, client):
        """Test successful scrape endpoint"""
        # Setup mocks
        mock_validate_url.return_value = True
        mock_perform_scraping.return_value = ([
            StudentBase(
                name="John Doe",
                email="john.doe@test.edu",
                university="Test University"
            )
        ], 1.5)  # 1.5 seconds execution time
        
        # Test data
        scrape_request = {
            "url": "https://www.testuniversity.edu/directory",
            "university_name": "Test University",
            "use_selenium": False
        }
        
        response = client.post("/api/v1/scrape", json=scrape_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["students_found"] == 1
        assert "execution_time" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["email"] == "john.doe@test.edu"
    
    @patch('app.api.endpoints.validate_url')
    def test_scrape_endpoint_invalid_url(self, mock_validate_url, client):
        """Test scrape endpoint with invalid URL"""
        mock_validate_url.return_value = False
        
        scrape_request = {
            "url": "https://not-a-university.com",
            "university_name": "Test",
            "use_selenium": False
        }
        
        response = client.post("/api/v1/scrape", json=scrape_request)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "invalid" in data["detail"].lower()
    
    @patch('app.api.endpoints.perform_scraping')
    def test_scrape_endpoint_failure(self, mock_perform_scraping, client):
        """Test scrape endpoint when scraping fails"""
        mock_perform_scraping.side_effect = Exception("Scraping failed")
        
        scrape_request = {
            "url": "https://www.testuniversity.edu/directory",
            "university_name": "Test University",
            "use_selenium": False
        }
        
        response = client.post("/api/v1/scrape", json=scrape_request)
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
    
    def test_get_students_empty(self, client):
        """Test getting students when none exist"""
        # Clear any existing students
        from app.api.endpoints import students_store
        students_store.clear()
        
        response = client.get("/api/v1/students")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_get_students_with_data(self, client):
        """Test getting students with data"""
        from app.api.endpoints import students_store
        
        # Add test data
        students_store.clear()
        students_store.append(StudentResponse(
            id=1,
            name="John Doe",
            email="john.doe@test.edu",
            university="Test University",
            scraped_at=datetime.now().timestamp()
        ))
        
        response = client.get("/api/v1/students")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "John Doe"
    
    def test_get_students_with_filters(self, client):
        """Test getting students with filters"""
        from app.api.endpoints import students_store
        
        # Add test data
        students_store.clear()
        students_store.extend([
            StudentResponse(
                id=1,
                name="John Doe",
                email="john@university1.edu",
                university="University 1",
                scraped_at=datetime.now().timestamp()
            ),
            StudentResponse(
                id=2,
                name="Jane Smith",
                email="jane@university2.edu",
                university="University 2",
                scraped_at=datetime.now().timestamp()
            )
        ])
        
        # Filter by university
        response = client.get("/api/v1/students?university=University%201")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["university"] == "University 1"
        
        # Test limit
        response = client.get("/api/v1/students?limit=1")
        data = response.json()
        assert len(data) == 1
        
        # Test offset
        response = client.get("/api/v1/students?offset=1")
        data = response.json()
        assert len(data) == 1  # Only one left after offset
    
    def test_search_students(self, client):
        """Test student search endpoint"""
        from app.api.endpoints import students_store
        
        # Add test data
        students_store.clear()
        students_store.append(StudentResponse(
            id=1,
            name="John Doe",
            email="john.doe@test.edu",
            university="Test University",
            scraped_at=datetime.now().timestamp()
        ))
        
        # Search by name
        response = client.get("/api/v1/students/search?name=John")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert len(data["students"]) == 1
        assert "John" in data["students"][0]["name"]
        
        # Search by email
        response = client.get("/api/v1/students/search?email=test.edu")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        
        # Search by university
        response = client.get("/api/v1/students/search?university=Test")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
    
    def test_search_no_results(self, client):
        """Test search with no results"""
        response = client.get("/api/v1/students/search?name=Nonexistent")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert len(data["students"]) == 0
    
    def test_get_universities(self, client):
        """Test getting list of universities"""
        from app.api.endpoints import students_store
        
        # Add test data
        students_store.clear()
        students_store.extend([
            StudentResponse(
                id=1,
                name="John Doe",
                email="john@uni1.edu",
                university="University A",
                scraped_at=datetime.now().timestamp()
            ),
            StudentResponse(
                id=2,
                name="Jane Smith",
                email="jane@uni1.edu",
                university="University A",
                scraped_at=datetime.now().timestamp()
            ),
            StudentResponse(
                id=3,
                name="Bob Johnson",
                email="bob@uni2.edu",
                university="University B",
                scraped_at=datetime.now().timestamp()
            )
        ])
        
        response = client.get("/api/v1/universities")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 2  # Two unique universities
        assert "University A" in data["universities"]
        assert "University B" in data["universities"]
    
    def test_clear_students(self, client):
        """Test clearing all student data"""
        from app.api.endpoints import students_store
        
        # Add some data
        students_store.append(StudentResponse(
            id=1,
            name="Test",
            email="test@test.edu",
            university="Test",
            scraped_at=datetime.now().timestamp()
        ))
        
        response = client.delete("/api/v1/students")
        
        assert response.status_code == 200
        data = response.json()
        assert "cleared_count" in data
        assert data["cleared_count"] == 1
        
        # Verify data was cleared
        assert len(students_store) == 0

class TestEmailEndpoints:
    """Test email-related API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        with TestClient(app) as client:
            yield client
    
    @pytest.fixture
    def sample_student_data(self):
        """Create sample student data"""
        return {
            "id": 1,
            "name": "John Doe",
            "email": "john.doe@test.edu",
            "university": "Test University",
            "department": "Computer Science"
        }
    
    @patch('app.api.email_endpoints.get_email_service')
    @patch('app.api.email_endpoints.get_paper_generator')
    @patch('app.api.email_endpoints.get_docx_generator')
    def test_generate_papers_endpoint(
        self, mock_docx_gen, mock_paper_gen, mock_email_service, client, sample_student_data
    ):
        """Test paper generation endpoint"""
        # Setup mocks
        mock_docx_instance = Mock()
        mock_docx_instance.generate_personalized_paper.return_value = {
            'student_name': 'John Doe',
            'student_email': 'john.doe@test.edu',
            'paper_title': 'Test Paper',
            'abstract': 'Test abstract...',
            'docx_path': '/tmp/test.docx',
            'file_size': 1024
        }
        mock_docx_gen.return_value = mock_docx_instance
        
        mock_paper_instance = Mock()
        mock_paper_gen.return_value = mock_paper_instance
        
        # Mock students store
        with patch('app.api.email_endpoints.students_store') as mock_store:
            mock_store.__iter__.return_value = [Mock(**sample_student_data)]
            
            request_data = {
                "student_ids": [1],
                "model_type": "fallback",
                "output_format": "docx"
            }
            
            response = client.post("/api/v1/email/generate-papers", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_students"] == 1
            assert data["papers_generated"] == 1
            assert "download_url" in data
    
    @patch('app.api.email_endpoints.EmailSender')
    def test_send_emails_endpoint(self, mock_email_sender, client):
        """Test email sending endpoint"""
        # Setup mock
        mock_instance = Mock()
        mock_instance.send_bulk_emails.return_value = {
            'total': 1,
            'success': 1,
            'failed': 0,
            'details': []
        }
        mock_email_sender.return_value = mock_instance
        
        # Mock students store and generated papers
        with patch('app.api.email_endpoints.students_store') as mock_store, \
             patch('app.api.email_endpoints.generated_papers') as mock_papers:
            
            mock_store.__iter__.return_value = [Mock(
                id=1,
                name="John Doe",
                email="john@test.edu",
                university="Test University"
            )]
            
            mock_papers.values.return_value = [{
                'student_id': 1,
                'paper_title': 'Test Paper',
                'abstract': 'Test...',
                'docx_path': '/tmp/test.docx',
                'generated_at': '2024-01-01T00:00:00'
            }]
            
            request_data = {
                "student_ids": [1],
                "subject_template": "Test {paper_title}",
                "test_mode": True
            }
            
            response = client.post("/api/v1/email/send-emails", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert "task_id" in data
            assert data["status"] == "queued"
            assert data["total_emails"] == 1
    
    def test_get_email_status(self, client):
        """Test getting email sending status"""
        from app.api.email_endpoints import processing_status
        
        # Add test status
        task_id = "test_task_123"
        processing_status[task_id] = {
            'status': 'completed',
            'total': 5,
            'sent': 5,
            'failed': 0,
            'started_at': '2024-01-01T00:00:00',
            'completed_at': '2024-01-01T00:01:00'
        }
        
        response = client.get(f"/api/v1/email/status/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "completed"
        assert data["total"] == 5
        assert data["sent"] == 5
    
    def test_get_email_status_not_found(self, client):
        """Test getting status for non-existent task"""
        response = client.get("/api/v1/email/status/nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    @patch('app.api.email_endpoints.os.path.exists')
    @patch('app.api.email_endpoints.generated_papers')
    def test_download_paper(self, mock_papers, mock_exists, client):
        """Test paper download endpoint"""
        # Setup mocks
        mock_exists.return_value = True
        
        mock_papers.values.return_value = [{
            'student_id': 1,
            'docx_path': '/tmp/test.docx',
            'student_name': 'John Doe',
            'paper_title': 'Test Paper',
            'generated_at': '2024-01-01T00:00:00'
        }]
        
        with patch('app.api.email_endpoints.FileResponse') as mock_response:
            mock_response.return_value = Mock(
                headers={'Content-Disposition': 'attachment'},
                status_code=200
            )
            
            response = client.get("/api/v1/email/download-paper/1")
            
            # FileResponse is returned directly, not JSON
            assert response.status_code == 200
    
    def test_get_templates(self, client, tmp_path):
        """Test getting email templates"""
        with patch('app.api.email_endpoints.Path') as mock_path:
            mock_template_dir = tmp_path / "templates"
            mock_template_dir.mkdir()
            
            # Create test template
            test_template = mock_template_dir / "test.html"
            test_template.write_text("<h1>Test</h1>")
            
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.absolute.return_value = mock_template_dir
            mock_path.return_value.glob.return_value = [test_template]
            
            response = client.get("/api/v1/email/templates")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "templates" in data
            assert len(data["templates"]) == 1
            assert data["templates"][0]["name"] == "test"
    
    @patch('app.api.email_endpoints.sent_emails')
    def test_get_sent_emails_history(self, mock_sent_emails, client):
        """Test getting sent email history"""
        # Setup mock data
        mock_sent_emails.__iter__.return_value = [
            {
                'timestamp': 1704067200,  # 2024-01-01
                'student_email': 'test@example.com',
                'student_name': 'Test User',
                'success': True,
                'message': 'Sent successfully'
            }
        ]
        
        response = client.get("/api/v1/email/sent-emails?days=7&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "emails" in data
        assert len(data["emails"]) == 1
    
    @patch('app.api.email_endpoints.generated_papers')
    def test_get_statistics(self, mock_generated_papers, client):
        """Test getting email statistics"""
        # Setup mock data
        mock_sent_emails = [
            {
                'timestamp': 1704067200,  # Recent
                'success': True
            },
            {
                'timestamp': 1704067200,
                'success': True
            },
            {
                'timestamp': 1704067200,
                'success': False
            }
        ]
        
        with patch('app.api.email_endpoints.sent_emails', mock_sent_emails):
            mock_generated_papers.__len__.return_value = 5
            
            response = client.get("/api/v1/email/statistics?period=week")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_emails"] == 3
            assert data["successful_emails"] == 2
            assert data["failed_emails"] == 1
            assert data["success_rate"] == (2/3 * 100)
            assert data["generated_papers"] == 5

class TestAPIErrorHandling:
    """Test API error handling"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        with TestClient(app) as client:
            yield client
    
    def test_invalid_json_request(self, client):
        """Test handling of invalid JSON in request body"""
        response = client.post(
            "/api/v1/scrape",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_missing_required_fields(self, client):
        """Test handling of missing required fields"""
        incomplete_request = {
            "url": "https://test.edu"
            # Missing university_name
        }
        
        response = client.post("/api/v1/scrape", json=incomplete_request)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_invalid_url_format(self, client):
        """Test handling of invalid URL format"""
        invalid_request = {
            "url": "not-a-valid-url",
            "university_name": "Test"
        }
        
        response = client.post("/api/v1/scrape", json=invalid_request)
        
        assert response.status_code == 422
    
    def test_rate_limiting(self, client):
        """Test rate limiting (if implemented)"""
        # This would test if rate limiting middleware is working
        # For now, just verify endpoint is accessible
        for _ in range(5):
            response = client.get("/api/v1/students")
            assert response.status_code == 200
    
    def test_cors_headers(self, client):
        """Test CORS headers are present"""
        response = client.options("/")
        
        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
    
    def test_not_found_endpoint(self, client):
        """Test handling of non-existent endpoint"""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

class TestAPIPerformance:
    """Test API performance"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        with TestClient(app) as client:
            yield client
    
    def test_response_time_root(self, client):
        """Test response time for root endpoint"""
        import time
        
        start_time = time.time()
        response = client.get("/")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 1.0, f"Response too slow: {response_time:.3f}s"
        
        print(f"\nRoot endpoint response time: {response_time:.3f}s")
    
    def test_response_time_health(self, client):
        """Test response time for health check"""
        import time
        
        start_time = time.time()
        response = client.get("/health")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 0.5, f"Health check too slow: {response_time:.3f}s"
        
        print(f"\nHealth check response time: {response_time:.3f}s")
    
    def test_concurrent_requests(self, client):
        """Test handling of concurrent requests"""
        import concurrent.futures
        import time
        
        def make_request():
            start = time.time()
            response = client.get("/health")
            end = time.time()
            return end - start, response.status_code
        
        # Make multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        response_times = [r[0] for r in results]
        status_codes = [r[1] for r in results]
        
        # All requests should succeed
        assert all(code == 200 for code in status_codes)
        
        # Response times should be reasonable
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        
        assert avg_time < 0.5, f"Average response time too high: {avg_time:.3f}s"
        assert max_time < 2.0, f"Maximum response time too high: {max_time:.3f}s"
        
        print(f"\nConcurrent requests (20):")
        print(f"  Average response time: {avg_time:.3f}s")
        print(f"  Maximum response time: {max_time:.3f}s")

# Test authentication and authorization (if implemented)
class TestAPIAuthentication:
    """Test API authentication (if implemented)"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        with TestClient(app) as client:
            yield client
    
    def test_protected_endpoints(self, client):
        """Test that protected endpoints require authentication"""
        # If authentication is implemented, test here
        # For now, just verify endpoints are accessible
        response = client.get("/api/v1/students")
        assert response.status_code == 200
    
    def test_invalid_token(self, client):
        """Test handling of invalid authentication tokens"""
        # If authentication is implemented, test here
        pass
    
    def test_rate_limiting_with_auth(self, client):
        """Test rate limiting with authentication"""
        # If authentication is implemented, test here
        pass