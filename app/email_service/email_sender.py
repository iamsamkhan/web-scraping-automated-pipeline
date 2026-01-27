import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Optional, Tuple
import os
from pathlib import Path
import time
from datetime import datetime
import json
import traceback
from jinja2 import Template
import premailer

class EmailSender:
    """Send emails with DOCX attachments"""
    
    def __init__(self, 
                 smtp_server: str = "smtp.gmail.com",
                 smtp_port: int = 587,
                 use_ssl