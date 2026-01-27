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
git clone <repository-url>
cd university_scraper.
