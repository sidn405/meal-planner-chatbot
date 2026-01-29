#!/usr/bin/env python3
"""
Healthy Eating Guru - AI Meal Planning Assistant
Version 2.0.0 - Direct Chat Interface (No Dialogflow)
"""

import datetime
import os
import json
import re
import logging

from flask import Flask, request, jsonify, send_file, render_template, send_from_directory
from flask_compress import Compress
from flask_cors import CORS
import requests

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors

# Configuration
APP_VERSION = "2.0.0-Direct-Chat"
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__, 
            static_folder='templates/static',
            static_url_path='/static')
Compress(app)
CORS(app)

# Brand colors (Green/Fresh theme)
BRAND_COLOR = colors.HexColor('#fe980a')  # Main
ACCENT_COLOR = colors.HexColor('#27a130')  # Light green
SECONDARY_COLOR = colors.HexColor('#ff6f00')  # Orange

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "templates/static/logo.png")
BANNER_DIR = os.path.join(BASE_DIR, "graphics/Banner_ads")

# Banner ads (PLACEHOLDERS)
BANNER_ADS = [
    {
        "path": os.path.join(BANNER_DIR, "banner-1.jpg"),
        "link": "https://your-affiliate-link-1.com",
        "alt": "Premium Kitchen Equipment - Save 20%"
    },
    {
        "path": os.path.join(BANNER_DIR, "banner-2.jpg"),
        "link": "https://your-affiliate-link-2.com",
        "alt": "Fresh Meal Kits Delivered Weekly"
    },
    {
        "path": os.path.join(BANNER_DIR, "banner-3.jpg"),
        "link": "https://healthyeatingguru.com",
        "alt": "Healthy Eating Guru"
    }
]

# Affiliate links (PLACEHOLDERS)
affiliate_links = {
    "kitchen_equipment": [
        {
            "product": "Air Fryer",
            "brand": "Ninja",
            "link": "https://amzn.to/PLACEHOLDER1",
        },
        {
            "product": "Food Processor",
            "brand": "Cuisinart",
            "link": "https://amzn.to/PLACEHOLDER2",
        },
        {
            "product": "Instant Pot",
            "brand": "Instant Pot",
            "link": "https://amzn.to/PLACEHOLDER3",
        },
    ],
    "meal_services": [
        {
            "service": "HelloFresh",
            "link": "https://www.hellofresh.com/PLACEHOLDER",
        },
        {
            "service": "Blue Apron",
            "link": "https://www.blueapron.com/PLACEHOLDER",
        },
    ]
}


def load_local_image(file_path):
    """Load image from local file."""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading image {file_path}: {e}")
    else:
        logger.warning(f"Image not found: {file_path}")
    return None


def call_openai(prompt):
    """Call OpenAI API."""
    logger.info(f"Calling OpenAI with prompt: {prompt[:100]}...")
    try:
        headers = {'Authorization': f'Bearer {OPENAI_API_KEY}'}
        data = {
            'model': 'gpt-4',
            'messages': [
                {'role': 'system', 'content': 'You are a professional nutritionist and chef specializing in healthy, delicious meals.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 2000
        }
        response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()['choices'][0]['message']['content'].strip()
        logger.info(f"OpenAI response received: {len(result)} characters")
        return result
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return f"Error generating content: {str(e)}"


def clean_text_for_pdf(text):
    """Clean text for PDF generation."""
    if not text:
        return ""
    
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    
    return text.strip()


def extract_parameters(message):
    """Extract meal planning parameters from user message."""
    message_lower = message.lower()
    
    params = {
        'type': None,  # 'recipe', 'meal_plan', 'grocery_list'
        'days': None,
        'cuisine': None,
        'dietary': None,
        'servings': 4,
        'budget': 'moderate'
    }
    
    # Detect intent
    if any(word in message_lower for word in ['recipe', 'cook', 'make', 'prepare', 'how to make', 'how do i make']):
        params['type'] = 'recipe'
    elif any(word in message_lower for word in ['meal plan', 'weekly plan', 'day plan', 'meal schedule']):
        params['type'] = 'meal_plan'
    elif any(word in message_lower for word in ['grocery', 'shopping', 'shopping list', 'ingredients list']):
        params['type'] = 'grocery_list'
    
    # Extract number of days
    import re
    day_match = re.search(r'(\d+)\s*day', message_lower)
    if day_match:
        params['days'] = int(day_match.group(1))
    
    # Extract cuisine
    cuisines = ['italian', 'mexican', 'chinese', 'japanese', 'indian', 'thai', 'mediterranean', 
                'french', 'american', 'greek', 'korean', 'vietnamese', 'spanish']
    for cuisine in cuisines:
        if cuisine in message_lower:
            params['cuisine'] = cuisine
            break
    
    # Extract dietary preferences (including kosher and halal)
    diets = ['vegan', 'vegetarian', 'keto', 'paleo', 'gluten-free', 'dairy-free', 'low-carb', 
             'high-protein', 'kosher', 'halal', 'pescatarian', 'whole30']
    for diet in diets:
        if diet in message_lower or diet.replace('-', ' ') in message_lower:
            params['dietary'] = diet
            break
    
    # Extract servings
    serving_match = re.search(r'(\d+)\s*(people|person|serving)', message_lower)
    if serving_match:
        params['servings'] = int(serving_match.group(1))
    
    return params


def create_branded_pdf(content, filename, doc_type="recipe"):
    """Create branded PDF with logo, banners, and affiliate links."""
    try:
        pdf_dir = "/tmp/meal-pdfs"
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_path = os.path.join(pdf_dir, filename)
        
        doc = SimpleDocTemplate(pdf_path, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []
        
        # Styles
        title_style = ParagraphStyle(
            name='Title',
            fontName='Helvetica-Bold',
            fontSize=24,
            textColor=BRAND_COLOR,
            alignment=TA_CENTER,
            spaceAfter=20,  # Increased from 10 for more space
        )
        
        subtitle_style = ParagraphStyle(
            name='Subtitle',
            fontName='Helvetica-Oblique',
            fontSize=14,
            textColor=ACCENT_COLOR,
            alignment=TA_CENTER,
            spaceAfter=30,  # Increased from 20 for more space
        )
        
        section_title_style = ParagraphStyle(
            name='SectionTitle',
            fontName='Helvetica-Bold',
            fontSize=14,
            textColor=BRAND_COLOR,
            spaceAfter=8,
        )
        
        normal_style = ParagraphStyle(
            name='Normal',
            fontName='Helvetica',
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#333333'),
            alignment=TA_JUSTIFY,
        )
        
        # Logo
        logo_data = load_local_image(LOGO_PATH)
        if logo_data:
            from io import BytesIO
            logo_img = Image(BytesIO(logo_data), width=1.5*inch, height=1.5*inch)
            logo_img.hAlign = 'CENTER'
            story.append(logo_img)
            story.append(Spacer(1, 0.2 * inch))
        
        # Title
        story.append(Paragraph("Healthy Eating Guru", title_style))
        
        # Subtitle
        doc_titles = {
            "recipe": "Delicious & Nutritious Recipe",
            "meal_plan": "Your Personalized Meal Plan",
            "grocery_list": "Smart Shopping List"
        }
        story.append(Paragraph(doc_titles.get(doc_type, "Healthy Recipe"), subtitle_style))
        story.append(Spacer(1, 0.3 * inch))  # Increased from 0.3 inch for better spacing
        
        # First banner
        banner = BANNER_ADS[0]
        img_data = load_local_image(banner['path'])
        if img_data:
            from io import BytesIO
            img = Image(BytesIO(img_data), width=6*inch, height=1.5*inch)
            img.hAlign = 'CENTER'
            story.append(img)
            story.append(Spacer(1, 0.1 * inch))
            link_para = Paragraph(f'<a href="{banner["link"]}">{banner["alt"]}</a>', 
                                ParagraphStyle(name='Link', alignment=TA_CENTER, textColor=ACCENT_COLOR, fontSize=10))
            story.append(link_para)
            story.append(Spacer(1, 0.3 * inch))
        
        # Content
        sections = content.split('\n\n')
        banner_idx = 1
        
        for section in sections:
            if not section.strip():
                continue
            
            lines = section.split('\n')
            for line in lines:
                if not line.strip():
                    continue
                
                line_clean = clean_text_for_pdf(line)
                
                if line.strip().endswith(':') or line.strip().startswith('###'):
                    story.append(Paragraph(line_clean, section_title_style))
                else:
                    story.append(Paragraph(line_clean, normal_style))
                story.append(Spacer(1, 0.08 * inch))
            
            # Add banner every few sections
            if banner_idx < len(BANNER_ADS) and len(story) > 30:
                story.append(Spacer(1, 0.3 * inch))
                banner = BANNER_ADS[banner_idx]
                img_data = load_local_image(banner['path'])
                if img_data:
                    from io import BytesIO
                    img = Image(BytesIO(img_data), width=6*inch, height=1.5*inch)
                    img.hAlign = 'CENTER'
                    story.append(img)
                    story.append(Spacer(1, 0.05 * inch))
                    link_para = Paragraph(f'<a href="{banner["link"]}">{banner["alt"]}</a>', 
                                        ParagraphStyle(name='Link', alignment=TA_CENTER, textColor=ACCENT_COLOR, fontSize=10))
                    story.append(link_para)
                    story.append(Spacer(1, 0.3 * inch))
                banner_idx += 1
        
        # Recommended Products
        story.append(Spacer(1, 0.5 * inch))
        story.append(Paragraph("<b>Recommended Kitchen Tools:</b>", section_title_style))
        story.append(Spacer(1, 0.1 * inch))
        
        link_style = ParagraphStyle(
            name='ProductLink',
            fontName='Helvetica-Bold',
            fontSize=11,
            textColor=ACCENT_COLOR,
            leading=16,
        )
        
        for equipment in affiliate_links["kitchen_equipment"][:3]:
            link = f'<a href="{equipment["link"]}" color="blue"><u>{equipment["product"]} by {equipment["brand"]} →</u></a>'
            story.append(Paragraph(link, link_style))
            story.append(Spacer(1, 0.08 * inch))
        
        doc.build(story)
        logger.info(f"PDF created: {pdf_path}")
        return pdf_path
    except Exception as e:
        logger.error(f"Error creating PDF: {e}")
        logger.exception(e)
        return None


@app.route('/')
def index():
    """Main chat interface."""
    return render_template('index.html', version=APP_VERSION)


@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages."""
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        logger.info(f"Chat: {message}")
        
        # Extract parameters
        params = extract_parameters(message)
        logger.info(f"Parameters: {params}")
        
        # Determine what to generate
        if params['type'] == 'recipe':
            # Generate recipe - just use the user's original message
            prompt = f"Create a detailed, professional recipe based on this request: '{message}'\n\n"
            
            if params['cuisine']:
                prompt += f"Cuisine style: {params['cuisine']}\n"
            if params['dietary']:
                prompt += f"Dietary requirement: {params['dietary']} (follow all {params['dietary']} rules strictly)\n"
            prompt += f"Servings: {params['servings']}\n\n"
            prompt += """Format:
**Recipe Name:**

**Ingredients:**
(List with measurements)

**Instructions:**
(Step-by-step numbered)

**Nutrition Information:**
(Per serving)

**Chef's Tips:**
(Pro tips)"""
            
            content = call_openai(prompt)
            
            # Create PDF
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"recipe-{timestamp}.pdf"
            pdf_path = create_branded_pdf(content, filename, doc_type="recipe")
            
            response = {
                'response': "Here's your recipe! 🍳",
                'content': content[:500] + "..." if len(content) > 500 else content,
                'pdf_url': f'/download/{filename}' if pdf_path else None
            }
            
        elif params['type'] == 'meal_plan':
            # Generate meal plan
            days = params['days'] or 7
            
            prompt = f"Create a detailed {days}-day meal plan.\n\n"
            if params['cuisine']:
                prompt += f"Cuisine preference: {params['cuisine']}\n"
            if params['dietary']:
                prompt += f"Dietary preference: {params['dietary']}\n"
            prompt += f"Budget: {params['budget']}\n\n"
            prompt += f"""Format each day clearly:

### Day X
**Breakfast:**
**Lunch:**
**Dinner:**

Include nutritional highlights and prep tips."""
            
            content = call_openai(prompt)
            
            # Create PDF
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"meal-plan-{days}days-{timestamp}.pdf"
            pdf_path = create_branded_pdf(content, filename, doc_type="meal_plan")
            
            response = {
                'response': f"Here's your {days}-day meal plan! 📅",
                'content': content[:500] + "..." if len(content) > 500 else content,
                'pdf_url': f'/download/{filename}' if pdf_path else None
            }
            
        elif params['type'] == 'grocery_list':
            # Generate grocery list
            prompt = f"Generate a complete grocery shopping list.\n\n"
            if params['dietary']:
                prompt += f"Dietary preference: {params['dietary']}\n"
            prompt += f"Servings: {params['servings']} people\n"
            prompt += f"Budget: {params['budget']}\n\n"
            prompt += """Format by category:

**Fresh Produce:**
**Proteins:**
**Dairy:**
**Pantry Staples:**
**Spices & Seasonings:**

Include quantities and budget tips."""
            
            content = call_openai(prompt)
            
            # Create PDF
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"grocery-list-{timestamp}.pdf"
            pdf_path = create_branded_pdf(content, filename, doc_type="grocery_list")
            
            response = {
                'response': "Here's your grocery list! 🛒",
                'content': content[:500] + "..." if len(content) > 500 else content,
                'pdf_url': f'/download/{filename}' if pdf_path else None
            }
            
        else:
            # General response
            response = {
                'response': """Welcome to Healthy Eating Guru! 🥗

I can help you with:
• **Recipes** - "Recipe with chicken and vegetables"
• **Meal Plans** - "Create a 7-day vegan meal plan"
• **Grocery Lists** - "Generate grocery list for 4 people"

What would you like today?"""
            }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        logger.exception(e)
        return jsonify({'error': str(e)}), 500
    
from flask import request, jsonify
import time

def call_openai_alexa(prompt: str) -> str:
    # IMPORTANT: low max_tokens + concise instruction
    # Implement using your existing OpenAI client
    return call_openai(prompt, max_tokens=300, temperature=0.7)

@app.route('/alexa', methods=['POST'])
def alexa():
    """
    Alexa-optimized endpoint:
    - fast responses
    - no PDF generation
    - voice-friendly formatting
    """
    try:
        data = request.get_json() or {}
        message = (data.get('message') or '').strip()
        if not message:
            return jsonify({"response": "Tell me what you want, like: recipe for grilled chicken."}), 400

        logger.info(f"[ALEXA] Chat: {message}")

        params = extract_parameters(message)
        logger.info(f"[ALEXA] Parameters: {params}")

        # Force "fast" behavior
        start = time.time()

        if params['type'] == 'recipe':
            prompt = f"""
You are a voice assistant. Create a QUICK, speakable recipe for: "{message}"

Rules:
- Keep it short.
- No markdown.
- Ingredients: max 8 items.
- Steps: max 6 short steps.
- Include: total time + servings.
- End by asking: "Want the full detailed version in the app?"
"""
            content = call_openai_alexa(prompt)  # separate OpenAI helper for Alexa
            speech = content.strip()

        elif params['type'] == 'meal_plan':
            days = params['days'] or 7
            prompt = f"""
You are a voice assistant. Create a QUICK {days}-day meal plan for: "{message}"

Rules:
- Keep it short.
- For each day, give Breakfast/Lunch/Dinner with very short titles.
- No long explanations.
- End by asking: "Want the full detailed plan in the app?"
"""
            speech = call_openai_alexa(prompt).strip()

        elif params['type'] == 'grocery_list':
            prompt = f"""
You are a voice assistant. Create a QUICK grocery list for: "{message}"

Rules:
- Group into: Produce, Proteins, Pantry, Dairy/Alt, Spices.
- Max 6 items per group.
- No markdown.
- End by asking: "Want the full detailed list in the app?"
"""
            speech = call_openai_alexa(prompt).strip()

        else:
            speech = ("I can help with recipes, meal plans, or grocery lists. "
                      "Try: recipe for chicken alfredo, or create a 7 day vegan meal plan.")

        elapsed = time.time() - start
        logger.info(f"[ALEXA] Completed in {elapsed:.2f}s")

        # Alexa endpoint returns only what Alexa needs
        return jsonify({
            "response": speech,
            "pdf_url": None
        })

    except Exception as e:
        logger.error(f"[ALEXA] Error: {e}")
        logger.exception(e)
        return jsonify({"response": "Sorry, something went wrong. Please try again."}), 500


@app.route('/download/<filename>')
def download_pdf(filename):
    """Download PDF file."""
    pdf_dir = "/tmp/meal-pdfs"
    return send_file(os.path.join(pdf_dir, filename), as_attachment=True)


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory(app.static_folder, filename)


def validate_assets():
    """Validate required assets."""
    logger.info("Validating assets...")
    
    if not os.path.exists(LOGO_PATH):
        logger.warning(f"Logo not found at {LOGO_PATH}")
    else:
        logger.info(f"✓ Logo found")
    
    for banner in BANNER_ADS:
        if not os.path.exists(banner['path']):
            logger.warning(f"Banner not found: {banner['path']}")
        else:
            logger.info(f"✓ Banner found: {banner['path']}")


if __name__ == '__main__':
    validate_assets()
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting Healthy Eating Guru v{APP_VERSION} on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)