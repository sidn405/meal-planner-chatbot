#!/usr/bin/env python3
"""
Healthy Eating Guru - AI Meal Planner Assistant
Version 2.3.4 - Healthy Eating-based affiliate links with random selection
"""

import datetime
import os
import json
import re
import logging
import sys

from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_compress import Compress
import requests

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.enums import TA_CENTER

# Setup logging
env = os.getenv("ENV", "production")
logging_level = logging.DEBUG if env == "development" else logging.INFO

logging.basicConfig(
    level=logging_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("healthy_eating_guru")

# Initialize Flask with static folder configuration
app = Flask(__name__, 
            static_folder='templates/static',
            static_url_path='/static')
Compress(app)

APP_VERSION = "2.3.4-Healthy Eating-Affiliates"

# Storage
STORAGE_DIR = os.getenv("STORAGE_DIR", "/tmp/recipes-pdfs")
os.makedirs(STORAGE_DIR, exist_ok=True)

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY environment variable is missing!")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {OPENAI_API_KEY.strip()}",
    "Content-Type": "application/json",
}

# Branding
BRAND_NAME = "Healthy Eating Guru"
BRAND_COLOR = HexColor("#fe980a")
ACCENT_COLOR = HexColor("#27a130")

# Local file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "templates/static/logo.png")
BANNER_DIR = os.path.join(BASE_DIR, "graphics/Banner_ads")

# PDF Styles
title_style = ParagraphStyle(
    name="BrandTitle",
    fontName="Helvetica-Bold",
    fontSize=28,
    alignment=TA_CENTER,
    textColor=BRAND_COLOR,
    spaceAfter=20,
)

subtitle_style = ParagraphStyle(
    name="Subtitle",
    fontName="Helvetica-Bold",
    fontSize=20,
    alignment=TA_CENTER,
    textColor=BRAND_COLOR,
    spaceAfter=10,
)

section_title_style = ParagraphStyle(
    name="SectionTitle",
    fontName="Helvetica-Bold",
    fontSize=16,
    textColor=BRAND_COLOR,
    spaceAfter=8,
)

normal_style = ParagraphStyle(
    name="Normal",
    fontName="Helvetica",
    fontSize=11,
    textColor=black,
    leading=14,
)

small_style = ParagraphStyle(
    name="Small",
    fontName="Helvetica",
    fontSize=9,
    textColor=black,
    leading=11,
)