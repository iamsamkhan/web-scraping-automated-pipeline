"""
Comprehensive unit tests for web scraper
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import asyncio
from bs4 import BeautifulSoup
import json
from pathlib import Path

from app.scraper.base_scraper import BaseScraper
from app.scraper.university_scrapers import GenericUniversityScraper, DirectoryPageScraper
from app.models.schemas import StudentBase

class TestBaseScraper:
    """Test base scraper functionality"""
    
    @pytest.fixture
    def scraper(self):
        """Create base scraper instance"""
        return BaseScraper(timeout=10)
    
    @pytest.mark.asyncio
    async def test_normalize_email_valid(self, scraper):
        """Test email normalization with valid emails"""
        test_cases = [
            ("john.doe@university.edu", "john.doe@university.edu"),
            ("JANE.SMITH@COLLEGE.EDU", "jane.smith@college.edu"),
            ("  bob.johnson@institute.edu  ", "bob.johnson@institute.edu"),
            ("Contact: alice@domain.ac.uk", "alice@domain.ac.uk"),
            ("Email: test@sub.domain.edu", "test@sub.domain.edu"),
        ]
        
        for input_email, expected in test_cases:
            result = scraper.normalize_email(input_email)
            assert result == expected, f"Failed for: {input_email}"
    
    @pytest.mark.asyncio
    async def test_normalize_email_invalid(self, scraper):
        """Test email normalization with invalid emails"""
        invalid_emails = [
            "",
            "not-an-email",
            "missing@domain",
            "@domain.com",
            "spaces in@email.com",
        ]
        
        for email in invalid_emails:
            result = scraper.normalize_email(email)
            assert result is None, f"Should return None for: {email}"
    
    @pytest.mark.asyncio
    async def test_normalize_name(self, scraper):
        """Test name normalization"""
        test_cases = [
            ("john doe", "John Doe"),
            ("JANE SMITH", "Jane Smith"),
            ("bob  johnson  ", "Bob Johnson"),
            ("mary-jane parker", "Mary-Jane Parker"),
            ("DR. JOHN DOE PHD", "Dr. John Doe Phd"),
            ("alice van der merwe", "Alice Van Der Merwe"),
        ]
        
        for input_name, expected in test_cases:
            result = scraper.normalize_name(input_name)
            assert result == expected, f"Failed for: {input_name}"
    
    @pytest.mark.asyncio
    async def test_fetch_html_success(self, scraper):
        """Test successful HTML fetch"""
        mock_html = "<html><body>Test content</body></html>"
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text.return_value = mock_html
            mock_get.return_value.__aenter__.return_value = mock_response
            
            async with scraper:
                result = await scraper.fetch_html("http://example.com")
                
                assert result == mock_html
                mock_get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_html_failure(self, scraper):
        """Test failed HTML fetch"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_get.return_value.__aenter__.return_value = mock_response
            
            async with scraper:
                result = await scraper.fetch_html("http://example.com")
                
                assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_with_selenium(self, scraper):
        """Test Selenium fetch"""
        mock_html = "<html><body>JavaScript rendered content</body></html>"
        
        with patch.object(scraper, 'setup_selenium') as mock_setup, \
             patch('selenium.webdriver.Chrome') as mock_driver:
            
            mock_driver_instance = Mock()
            mock_driver_instance.page_source = mock_html
            mock_driver.return_value = mock_driver_instance
            
            result = scraper.fetch_with_selenium("http://example.com")
            
            assert result == mock_html
            mock_setup.assert_called_once()

class TestGenericUniversityScraper:
    """Test generic university scraper"""
    
    @pytest.fixture
    def html_directory(self):
        """Load test HTML directory"""
        html_path = Path("tests/test_data/sample_html/university_directory.html")
        return html_path.read_text(encoding='utf-8')
    
    @pytest.fixture
    def html_with_emails(self):
        """Create HTML with email addresses"""
        return """
        <html>
            <body>
                <h1>Faculty Directory</h1>
                <table>
                    <tr>
                        <td>John Doe</td>
                        <td>john.doe@university.edu</td>
                    </tr>
                    <tr>
                        <td>Jane Smith</td>
                        <td>jane.smith@college.edu</td>
                    </tr>
                </table>
                <p>Contact: bob.johnson@institute.edu</p>
                <a href="mailto:alice.wonder@domain.edu">Email Alice</a>
            </body>
        </html>
        """
    
    @pytest.mark.asyncio
    async def test_extract_students_from_table(self, html_with_emails):
        """Test student extraction from HTML table"""
        scraper = GenericUniversityScraper()
        
        students = await scraper.extract_students(html_with_emails, "http://example.com")
        
        assert len(students) >= 3  # Should find at least 3 students
        
        # Check specific students
        emails = [student.email for student in students]
        assert "john.doe@university.edu" in emails
        assert "jane.smith@college.edu" in emails
        assert "alice.wonder@domain.edu" in emails
        
        # Check names
        names = [student.name for student in students]
        assert "John Doe" in names
    
    @pytest.mark.asyncio
    async def test_extract_university_name_from_url(self):
        """Test university name extraction from URL"""
        scraper = GenericUniversityScraper()
        
        test_cases = [
            ("https://www.harvard.edu/directory", "Harvard"),
            ("http://mit.edu/people", "Mit"),
            ("https://stanford.edu/faculty", "Stanford"),
            ("https://oxford.ac.uk/staff", "Oxford"),
        ]
        
        for url, expected in test_cases:
            soup = BeautifulSoup("<html><title>Test</title></html>", "html.parser")
            result = scraper._extract_university_name(url, soup)
            assert expected in result
    
    @pytest.mark.asyncio
    async def test_extract_from_text_patterns(self):
        """Test student extraction from text patterns"""
        scraper = GenericUniversityScraper()
        
        test_texts = [
            "John Doe <john.doe@university.edu>",
            "Jane Smith (jane.smith@college.edu)",
            "Bob Johnson - bob.johnson@institute.edu",
            "Email: alice@domain.edu",
            "Contact at: charlie.brown@school.edu for more info",
        ]
        
        for text in test_texts:
            student = scraper._extract_from_text(text, "Test University")
            assert student is not None
            assert "@" in student.email
            assert student.name
    
    @pytest.mark.asyncio
    async def test_no_duplicate_emails(self, html_with_emails):
        """Test that duplicate emails are removed"""
        # Create HTML with duplicate emails
        duplicate_html = html_with_emails + """
        <div>
            <p>John Doe - john.doe@university.edu (duplicate)</p>
            <p>Also John: john.doe@university.edu</p>
        </div>
        """
        
        scraper = GenericUniversityScraper()
        students = await scraper.extract_students(duplicate_html, "http://example.com")
        
        # Count unique emails
        emails = [student.email for student in students]
        unique_emails = set(emails)
        
        assert len(emails) == len(unique_emails), "Duplicate emails found"
    
    @pytest.mark.asyncio
    async def test_empty_html(self):
        """Test extraction from empty HTML"""
        scraper = GenericUniversityScraper()
        students = await scraper.extract_students("", "http://example.com")
        
        assert len(students) == 0
    
    @pytest.mark.asyncio
    async def test_html_without_emails(self):
        """Test extraction from HTML without emails"""
        html_no_emails = """
        <html>
            <body>
                <h1>No emails here</h1>
                <p>Just some text without email addresses</p>
                <div>Contact us at the office</div>
            </body>
        </html>
        """
        
        scraper = GenericUniversityScraper()
        students = await scraper.extract_students(html_no_emails, "http://example.com")
        
        assert len(students) == 0

class TestDirectoryPageScraper:
    """Test directory page scraper"""
    
    @pytest.fixture
    def html_directory_page(self):
        """Create directory page HTML"""
        return """
        <html>
            <body>
                <section class="people-directory">
                    <div class="profile-card">
                        <h3 class="person-name">Dr. John Doe</h3>
                        <p>Professor of Computer Science</p>
                        <a href="mailto:john.doe@university.edu">Email</a>
                    </div>
                    <article class="profile">
                        <h4>Jane Smith</h4>
                        <p>Research Assistant</p>
                        <p>Email: jane.smith@college.edu</p>
                    </article>
                    <li class="directory-item">
                        <strong>Bob Johnson</strong>
                        <p>Contact: bob.j@institute.edu</p>
                    </li>
                </section>
                <div class="other-content">
                    <p>Not a profile - test@example.com</p>
                </div>
            </body>
        </html>
        """
    
    @pytest.mark.asyncio
    async def test_extract_from_directory_section(self, html_directory_page):
        """Test extraction from directory sections"""
        scraper = DirectoryPageScraper()
        
        students = await scraper.extract_students(html_directory_page, "http://example.com")
        
        assert len(students) >= 3
        
        emails = [student.email for student in students]
        assert "john.doe@university.edu" in emails
        assert "jane.smith@college.edu" in emails
        assert "bob.j@institute.edu" in emails
    
    @pytest.mark.asyncio
    async def test_extract_from_card(self):
        """Test extraction from profile cards"""
        scraper = DirectoryPageScraper()
        
        test_cards = [
            # Card with mailto link
            """
            <div class="profile-card">
                <h2>Alice Wonder</h2>
                <a href="mailto:alice@wonder.edu">Contact</a>
            </div>
            """,
            # Card with email in text
            """
            <article class="person">
                <h3>Bob Builder</h3>
                <p>bob.builder@construction.edu</p>
            </article>
            """,
            # Card with name class
            """
            <div class="card">
                <div class="name">Charlie Brown</div>
                <div>charlie@peanuts.com</div>
            </div>
            """,
        ]
        
        for card_html in test_cards:
            soup = BeautifulSoup(card_html, "html.parser")
            card = soup.find(['div', 'article'])
            
            student = scraper._extract_from_card(card, "Test University")
            
            assert student is not None
            assert student.name
            assert student.email
    
    @pytest.mark.asyncio
    async def test_multiple_extraction_strategies(self):
        """Test that multiple extraction strategies work together"""
        html = """
        <html>
            <body>
                <!-- Table extraction -->
                <table>
                    <tr><td>Table User</td><td>table@email.com</td></tr>
                </table>
                
                <!-- Directory extraction -->
                <div class="directory">
                    <div class="profile">Directory User<dir@email.com></div>
                </div>
                
                <!-- Text pattern extraction -->
                <p>Text User (text@email.com)</p>
            </body>
        </html>
        """
        
        scraper = DirectoryPageScraper()
        students = await scraper.extract_students(html, "http://example.com")
        
        # Should find all three
        assert len(students) >= 3
        
        emails = [student.email for student in students]
        assert "table@email.com" in emails
        assert "dir@email.com" in emails
        assert "text@email.com" in emails

@pytest.mark.integration
class TestScraperIntegration:
    """Integration tests for scraper"""
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_real_website_scraping(self):
        """Test scraping from a real (test) website"""
        # Note: This test uses a controlled test website
        # In production, use a mock server or test pages
        
        import aiohttp
        
        scraper = GenericUniversityScraper()
        
        # Use a simple test page
        test_url = "http://httpbin.org/html"
        
        async with scraper:
            html = await scraper.fetch_html(test_url)
            
            if html:
                students = await scraper.extract_students(html, test_url)
                
                # Just verify it doesn't crash
                assert isinstance(students, list)
            else:
                # If fetch fails, skip test
                pytest.skip("Failed to fetch test page")
    
    @pytest.mark.asyncio
    async def test_scraper_with_mocked_responses(self):
        """Test scraper with mocked HTTP responses"""
        from unittest.mock import AsyncMock
        
        mock_html = """
        <html>
            <body>
                <h1>Test University Directory</h1>
                <table>
                    <tr><td>Test User</td><td>test@university.edu</td></tr>
                </table>
            </body>
        </html>
        """
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text.return_value = mock_html
            mock_get.return_value.__aenter__.return_value = mock_response
            
            scraper = GenericUniversityScraper()
            
            async with scraper:
                students = await scraper.extract_students(mock_html, "http://test.edu")
                
                assert len(students) == 1
                assert students[0].email == "test@university.edu"
                assert students[0].name == "Test User"

# Performance tests
@pytest.mark.performance
class TestScraperPerformance:
    """Performance tests for scraper"""
    
    @pytest.mark.asyncio
    async def test_scraper_performance_large_html(self):
        """Test scraper performance with large HTML"""
        import time
        
        # Generate large HTML with many students
        large_html = "<html><body><table>"
        for i in range(1000):
            large_html += f"""
            <tr>
                <td>User {i}</td>
                <td>user{i}@university.edu</td>
            </tr>
            """
        large_html += "</table></body></html>"
        
        scraper = GenericUniversityScraper()
        
        start_time = time.time()
        students = await scraper.extract_students(large_html, "http://example.com")
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Should complete in reasonable time
        assert execution_time < 5.0, f"Scraping took too long: {execution_time:.2f}s"
        
        # Should find all students
        assert len(students) == 1000
        
        # Check performance metrics
        print(f"\nPerformance: Processed 1000 students in {execution_time:.2f}s")
        print(f"Rate: {len(students)/execution_time:.1f} students/sec")
    
    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """Test memory usage during scraping"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create moderately large HTML
        html = "<html><body>"
        for i in range(500):
            html += f"<p>User {i} <user{i}@test.edu></p>"
        html += "</body></html>"
        
        scraper = GenericUniversityScraper()
        students = await scraper.extract_students(html, "http://example.com")
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable
        assert memory_increase < 50, f"Memory increased by {memory_increase:.1f}MB"
        
        print(f"\nMemory usage: Increased by {memory_increase:.1f}MB")

# Error handling tests
@pytest.mark.error_handling
class TestScraperErrorHandling:
    """Test scraper error handling"""
    
    @pytest.mark.asyncio
    async def test_network_timeout(self):
        """Test handling of network timeouts"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = asyncio.TimeoutError("Request timed out")
            
            scraper = GenericUniversityScraper(timeout=1)
            
            async with scraper:
                result = await scraper.fetch_html("http://example.com")
                
                assert result is None
    
    @pytest.mark.asyncio
    async def test_invalid_html_parsing(self):
        """Test handling of invalid HTML"""
        invalid_html = """
        <html>
            <body>
                <table>
                    <tr>
                        <td>Unclosed tag
                </table>
            </body>
        </html>
        """
        
        scraper = GenericUniversityScraper()
        
        # Should not crash
        students = await scraper.extract_students(invalid_html, "http://example.com")
        
        assert isinstance(students, list)
    
    @pytest.mark.asyncio
    async def test_malformed_emails(self):
        """Test handling of malformed emails"""
        html_with_bad_emails = """
        <html>
            <body>
                <p>Good: good@email.com</p>
                <p>Bad: not-an-email</p>
                <p>Empty: </p>
                <p>Another good: another@good.com</p>
            </body>
        </html>
        """
        
        scraper = GenericUniversityScraper()
        students = await scraper.extract_students(html_with_bad_emails, "http://example.com")
        
        # Should only extract valid emails
        assert len(students) == 2
        
        emails = [student.email for student in students]
        assert "good@email.com" in emails
        assert "another@good.com" in emails
        assert "not-an-email" not in emails

# Security tests
@pytest.mark.security
class TestScraperSecurity:
    """Security tests for scraper"""
    
    @pytest.mark.asyncio
    async def test_html_injection_safety(self):
        """Test that HTML injection doesn't break scraper"""
        malicious_html = """
        <html>
            <body>
                <script>alert('XSS')</script>
                <p>Email: <img src="x" onerror="alert(1)">test@email.com</p>
                <table>
                    <tr>
                        <td><iframe src="malicious.com"></iframe></td>
                        <td>user@test.com</td>
                    </tr>
                </table>
            </body>
        </html>
        """
        
        scraper = GenericUniversityScraper()
        
        # Should extract email without executing scripts
        students = await scraper.extract_students(malicious_html, "http://example.com")
        
        assert len(students) >= 1
        assert students[0].email == "test@email.com"
    
    @pytest.mark.asyncio
    async def test_large_input_handling(self):
        """Test handling of excessively large input"""
        # Create very large HTML (10MB)
        large_html = "<html><body>" + ("A" * 10_000_000) + "</body></html>"
        
        scraper = GenericUniversityScraper()
        
        import time
        start_time = time.time()
        
        # Should handle gracefully (timeout or return empty)
        students = await scraper.extract_students(large_html, "http://example.com")
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should not hang forever
        assert execution_time < 30.0, f"Took too long: {execution_time:.1f}s"
        
        # Result should be empty or reasonable
        assert len(students) == 0 or isinstance(students, list)