import asyncio
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from urllib.parse import urljoin
import aiohttp
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from app.models.schemas import StudentBase

class BaseScraper(ABC):
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = None
        self.driver = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        if self.driver:
            self.driver.quit()
    
    @abstractmethod
    async def extract_students(self, html: str, url: str) -> List[StudentBase]:
        """Extract student data from HTML content"""
        pass
    
    def normalize_email(self, email: str) -> Optional[str]:
        """Clean and validate email"""
        if not email:
            return None
        
        email = email.strip().lower()
        
        # Common email patterns in universities
        patterns = [
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z]+\.[a-zA-Z]+\.[a-zA-Z]{2,}'  # For subdomains
        ]
        
        for pattern in patterns:
            match = re.search(pattern, email)
            if match:
                return match.group()
        
        return None
    
    def normalize_name(self, name: str) -> str:
        """Clean and format student name"""
        if not name:
            return ""
        
        # Remove extra whitespace and newlines
        name = re.sub(r'\s+', ' ', name.strip())
        
        # Title case for names
        parts = name.split()
        formatted_parts = []
        for part in parts:
            if part.isupper() or part.islower():
                formatted_parts.append(part.title())
            else:
                formatted_parts.append(part)
        
        return ' '.join(formatted_parts)
    
    async def fetch_html(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL"""
        try:
            async with self.session.get(url, timeout=self.timeout) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    print(f"Failed to fetch {url}: Status {response.status}")
                    return None
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
            return None
    
    def setup_selenium(self):
        """Setup Selenium WebDriver for JavaScript-rendered pages"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
    
    def fetch_with_selenium(self, url: str) -> Optional[str]:
        """Fetch HTML using Selenium for JavaScript-rendered pages"""
        try:
            if not self.driver:
                self.setup_selenium()
            
            self.driver.get(url)
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            return self.driver.page_source
        except Exception as e:
            print(f"Error with Selenium for {url}: {str(e)}")
            return None