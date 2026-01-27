import re
from typing import List, Optional
from bs4 import BeautifulSoup
import pandas as pd

from app.scraper.base_scraper import BaseScraper
from app.models.schemas import StudentBase

class GenericUniversityScraper(BaseScraper):
    """Generic scraper for university websites"""
    
    async def extract_students(self, html: str, url: str) -> List[StudentBase]:
        students = []
        
        if not html:
            return students
        
        soup = BeautifulSoup(html, 'lxml')
        university_name = self._extract_university_name(url, soup)
        
        # Try multiple strategies to find student data
        
        # Strategy 1: Look for tables with student information
        tables = soup.find_all('table')
        for table in tables:
            table_students = self._extract_from_table(table, university_name)
            students.extend(table_students)
        
        # Strategy 2: Look for list items or divs with student info
        list_items = soup.find_all(['li', 'div', 'p'])
        for item in list_items:
            text = item.get_text()
            student = self._extract_from_text(text, university_name)
            if student:
                students.append(student)
        
        # Strategy 3: Look for email links
        email_links = soup.find_all('a', href=re.compile(r'mailto:'))
        for link in email_links:
            email = link['href'].replace('mailto:', '').strip()
            name = link.get_text().strip()
            if email and name:
                student = StudentBase(
                    name=self.normalize_name(name),
                    email=self.normalize_email(email),
                    university=university_name
                )
                students.append(student)
        
        # Remove duplicates
        unique_students = []
        seen_emails = set()
        for student in students:
            if student.email and student.email not in seen_emails:
                seen_emails.add(student.email)
                unique_students.append(student)
        
        return unique_students
    
    def _extract_university_name(self, url: str, soup: BeautifulSoup) -> str:
        """Extract university name from URL or page title"""
        # Try to get from URL
        domain = url.split('//')[-1].split('/')[0]
        name_parts = domain.replace('www.', '').split('.')
        
        if len(name_parts) > 1:
            university_name = name_parts[-2].title()
        else:
            university_name = name_parts[0].title()
        
        # Try to get from page title
        title = soup.find('title')
        if title:
            title_text = title.get_text()
            # Common patterns in university titles
            patterns = [
                r'([A-Za-z\s&]+(?:University|College|Institute|School))',
                r'([A-Za-z\s&]+(?:Univ\.?|Coll\.?|Inst\.?))'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, title_text)
                if match:
                    return match.group(1).strip()
        
        return university_name
    
    def _extract_from_table(self, table, university_name: str) -> List[StudentBase]:
        """Extract student data from HTML tables"""
        students = []
        
        try:
            # Try to read table with pandas
            dfs = pd.read_html(str(table))
            for df in dfs:
                for _, row in df.iterrows():
                    student = self._find_student_in_row(row, university_name)
                    if student:
                        students.append(student)
        except:
            # Fallback to manual extraction
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                for cell in cells:
                    text = cell.get_text()
                    student = self._extract_from_text(text, university_name)
                    if student:
                        students.append(student)
        
        return students
    
    def _extract_from_text(self, text: str, university_name: str) -> Optional[StudentBase]:
        """Extract student info from text content"""
        # Look for email pattern
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        
        if email_match:
            email = self.normalize_email(email_match.group())
            
            # Try to find name before email
            # Common patterns: "John Doe <johndoe@email.com>", "John Doe (johndoe@email.com)"
            name_patterns = [
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*[<\(]',
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+at\s+',
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+-\s+'
            ]
            
            name = None
            for pattern in name_patterns:
                match = re.search(pattern, text[:email_match.start()])
                if match:
                    name = match.group(1).strip()
                    break
            
            # If no pattern found, use text before email
            if not name:
                name_text = text[:email_match.start()].strip()
                # Take last 2-3 words as possible name
                words = name_text.split()
                if len(words) >= 2:
                    name = ' '.join(words[-2:])
            
            if name and email:
                return StudentBase(
                    name=self.normalize_name(name),
                    email=email,
                    university=university_name
                )
        
        return None
    
    def _find_student_in_row(self, row, university_name: str) -> Optional[StudentBase]:
        """Find student data in a table row"""
        for cell in row:
            if isinstance(cell, str):
                student = self._extract_from_text(str(cell), university_name)
                if student:
                    return student
        return None


class DirectoryPageScraper(GenericUniversityScraper):
    """Specialized scraper for directory/contact pages"""
    
    async def extract_students(self, html: str, url: str) -> List[StudentBase]:
        students = []
        
        if not html:
            return students
        
        soup = BeautifulSoup(html, 'lxml')
        university_name = self._extract_university_name(url, soup)
        
        # Look for specific directory structures
        directory_sections = soup.find_all(['section', 'div'], class_=re.compile(
            r'directory|people|students?|contacts?|profiles?|members?', re.I
        ))
        
        for section in directory_sections:
            # Look for profile cards
            cards = section.find_all(['div', 'article', 'li'], class_=re.compile(
                r'card|profile|person|item|entry', re.I
            ))
            
            for card in cards:
                student = self._extract_from_card(card, university_name)
                if student:
                    students.append(student)
        
        # Also use parent class extraction methods
        parent_students = await super().extract_students(html, url)
        students.extend(parent_students)
        
        # Remove duplicates
        unique_students = []
        seen_emails = set()
        for student in students:
            if student.email and student.email not in seen_emails:
                seen_emails.add(student.email)
                unique_students.append(student)
        
        return unique_students
    
    def _extract_from_card(self, card, university_name: str) -> Optional[StudentBase]:
        """Extract student info from profile cards"""
        # Try to find name
        name_elem = card.find(['h2', 'h3', 'h4', 'div'], class_=re.compile(
            r'name|title|person-name', re.I
        ))
        
        if not name_elem:
            name_elem = card.find(['strong', 'b'])
        
        name = name_elem.get_text().strip() if name_elem else ""
        
        # Try to find email
        email = None
        email_elem = card.find('a', href=re.compile(r'mailto:'))
        if email_elem:
            email = email_elem['href'].replace('mailto:', '').strip()
        else:
            # Search for email in text
            text = card.get_text()
            email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
            if email_match:
                email = email_match.group()
        
        if name and email:
            return StudentBase(
                name=self.normalize_name(name),
                email=self.normalize_email(email),
                university=university_name
            )
        
        return None