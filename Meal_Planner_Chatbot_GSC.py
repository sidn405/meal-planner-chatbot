
#!/usr/bin/env python3
import datetime
from flask import Flask, request, jsonify, send_file, url_for
import requests
import os
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
from google.cloud import storage
from google.auth import default
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import re
import traceback

app = Flask(__name__)

# 1. Function to sanitize the filename for safe GCS storage
def sanitize_filename(ingredient_list):
    """
    Converts the list of ingredients into a safe filename format.
    """
    try:
        # Join the list of ingredients into a single string
        ingredients_str = "-".join(ingredient_list)
        # Remove any characters that are not alphanumeric or dashes/underscores
        filename = re.sub(r'[^a-zA-Z0-9_-]', '', ingredients_str)
        # Add a suffix like 'recipe.pdf' at the end
        filename += '-recipe.pdf'
        print(f"Sanitized filename: {filename}")
        return filename
    except Exception as e:
        print(f"Error in sanitize_filename: {str(e)}")
        traceback.print_exc()
    
# 2. Function to authenticate and retrieve the access token for GCS JSON API
def authenticate_service_account():
    """
    Use default application credentials (attached service account).
    """
    try:
        credentials, project = default()
        credentials.refresh(Request())  # Ensure the token is refreshed
        return credentials.token
    except Exception as e:
        print(f"Error using default service account: {str(e)}")
        traceback.print_exc()        

# Make Objects Publicly Accessible  
def make_gcs_object_public(bucket_name, blob_name):
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.make_public()  # Makes the object publicly accessible
        print(f"The file {blob_name} is now publicly accessible at {blob.public_url}")
        return blob.public_url
    except Exception as e:
        print(f"Failed to make object public: {str(e)}")
        traceback.print_exc()
        return None

# 3. Function to upload a PDF to GCS using JSON API
def upload_to_gcs_json_api(bucket_name, blob_name, file_path):
    """
    Uploads a file to Google Cloud Storage using the JSON API and makes it publicly accessible.
    """
    try:
        access_token = authenticate_service_account()
        print(f"Access Token: {access_token}")
        upload_url = f"https://www.googleapis.com/upload/storage/v1/b/{bucket_name}/o?uploadType=media&name={blob_name}"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/pdf"}

        with open(file_path, 'rb') as file_data:
            response = requests.post(upload_url, headers=headers, data=file_data)

            # Log the response status and text to debug the issue
            print(f"Upload response status: {response.status_code}, response: {response.text}")

            if response.status_code == 200:
                print(f"File {blob_name} uploaded successfully.")

                # Make the file publicly accessible
                public_url = make_gcs_object_public(bucket_name, blob_name)
                if public_url:
                    print(f"Public URL: {public_url}")
                    return {"bucket": bucket_name, "name": blob_name, "public_url": public_url}
                else:
                    print("Failed to make the file publicly accessible.")
                    return None
            else:
                print(f"Error uploading file: {response.status_code}, {response.text}")
                return None
    except Exception as e:
        print(f"Error uploading to GCS using JSON API: {str(e)}")
        traceback.print_exc()
        return None

   
# 4. Function to download a PDF from GCS using JSON API    
def generate_download_json_api(bucket_name, blob_name, destination_file_path):
    """
    Downloads a file from Google Cloud Storage using the JSON API.
    """
    
    try:
        access_token = authenticate_service_account()
        print(f"Access Token: {access_token}")

    except Exception as e:
        print(f"Authentication error: {e}")
        metadata_url = f"https://storage.googleapis.com/storage/v1/b/pdf-viewer-bucket/o/{blob_name}?alt=media"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(metadata_url, headers=headers)
        if response.status_code == 200:
            print(f"File {blob_name} is available for download.")
            return metadata_url
        else:
            print(f"Error generating download URL: {response.text}")
            return None
    except Exception as e:
        print(f"Error downloading from GCS using JSON API: {str(e)}")
        traceback.print_exc()
        return None
        

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    print("API key is missing!")

# In-memory session storage
session_storage = {}

# Mock data store (replace with actual data store queries)
healthy_eating_guru_01 = {
    "chicken and rice": "Here is a simple recipe for chicken and rice...",
    "salmon": "Here is a simple recipe for salmon...",
    "grilled salmon": "Here is a recipe for grilled salmon..."
}
# 5. Function to call OpenAI for recipe generation
def call_openai(prompt):
    print(f"Calling OpenAI with prompt: {prompt}")  # Debugging
    headers = {'Authorization': f'Bearer {OPENAI_API_KEY}'}
    data = {'model': 'gpt-4', 'messages': [{'role': 'system', 'content': 'You are a helpful assistant.'}, {'role': 'user', 'content': prompt}], 'max_tokens': 1500}
    response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
    print(f"OpenAI response: {response.json()}")  # Debugging
    return response.json()['choices'][0]['message']['content'].strip()


# 6. Function to create a PDF using the recipe content
def create_pdf_with_reportlab(content, filename):
    try:
        # Save the file in /tmp directory for Cloud Run compatibility
        save_path = os.path.join('/tmp', filename)
        doc = SimpleDocTemplate(save_path, pagesize=letter)
        # Get a sample stylesheet
        styles = getSampleStyleSheet()
        story = []
        
        # Add the title to the first page
        title_style = styles['Title']
        title_style.textColor = colors.darkblue
        title_style.fontSize = 24
        title = Paragraph("Healthy Eating Guru", title_style)
        story.append(title)
        story.append(Spacer(1, 0.5 * inch))  # Add space after the title

        # Split the content into lines and add paragraphs with automatic word wrap
        for line in content.split('\n'):
            paragraph = Paragraph(line, styles['Normal'])
            story.append(paragraph)
            story.append(Spacer(1, 0.2 * inch))  # Adds space between paragraphs
        
        # Build the PDF
        doc.build(story)

        # Verify file creation
        if os.path.exists(save_path):
            print(f"PDF successfully created at: {save_path}")
            file_size = os.path.getsize(save_path)
            print(f"PDF file size: {file_size} bytes")
        else:
            print("PDF creation failed.")
        
        return save_path  # Return the path of the created PDF
    except Exception as e:
        print(f"Error creating PDF: {e}")
        traceback.print_exc()
        return None


def fallback_recipe_search(ingredients):
    for key in healthy_eating_guru_01:
        if all(item in key.lower() for item in ingredients):
            return healthy_eating_guru_01[key]
    return "Sorry, I couldn't find a predefined recipe. Please try again with different ingredients."

# 7. Webhook handler for Dialogflow
@app.route('/dialogflowWebhook', methods=['POST'])
def dialogflow_webhook():
    try:
        req_data = request.get_json()
        session_info = req_data.get('sessionInfo', {})
        parameters = session_info.get('parameters', {})
        ingredients_preference = parameters.get('ingredients_preference', [])
        print(f"Received parameters: {parameters}")

        # Check intent
        fulfillment_info = req_data.get('fulfillmentInfo', {})
        intent = fulfillment_info.get('tag', '')

        if intent == 'GetRecipes':
            # Code for handling the GetRecipes intent
            cuisine_preference = parameters.get('cuisine_preference', [])
            skill_level = parameters.get('skill_level', 'intermediate')
            cooking_time = parameters.get('cooking_time', '2 hours')
            
            
            # Create the prompt for OpenAI based on ingredient preferences and other details
            prompt = f"Creating a recipe using: {', '.join(ingredients_preference)}. Cuisine preference: {cuisine_preference}. Skill level: {skill_level}. Estimated cooking time: {cooking_time}."
            
            # Call OpenAI to get the recipe
            response_text = call_openai(prompt)
            print(f"OpenAI response: {response_text}")

            # Generate a safe filename using the ingredients
            filename = sanitize_filename(ingredients_preference)

            # Create the PDF with the recipe content and save it with the generated filename
            pdf_path = create_pdf_with_reportlab(response_text, filename)
            print(f"PDF generated successfully and saved at: {pdf_path}")

            if pdf_path:
                # Upload to GCS
                print(f"PDF successfully created at: {pdf_path}")
                upload_response = upload_to_gcs_json_api("pdf-viewer-bucket", f"pdfs/{filename}", pdf_path)

                if upload_response:
                    download_url = upload_response.get("public_url", f"https://storage.googleapis.com/{upload_response['bucket']}/{upload_response['name']}")
                    print(f"Download URL: {download_url}")

                    # Optionally make the object public
                    download_url = make_gcs_object_public(upload_response['bucket'], upload_response['name'])

                    # Return download link to the user
                    return jsonify({
                        "fulfillmentMessages": [
                            {"text": {"text": ["Great, here is your recipe. Bon appetit!"]}},
                            {"payload": {"richContent": [{"title": "Your Recipe", "subtitle": "Click below to download.", "actionLink": download_url, "type": "info"}]}},
                            {"text": {"text": ["Is there anything else I can help you with today?"]}}
                        ],
                        "sessionInfo": {"parameters": {"download_url": download_url}}
                    })
                else:
                    print("Error uploading to GCS")
                    return jsonify({'fulfillmentText': 'Error uploading the PDF.'}), 500
            else:
                print("Error creating the PDF")
                return jsonify({'fulfillmentText': 'Error creating the PDF.'}), 500

        # Return a fallback response if the intent is not recognized
        return jsonify({
            "fulfillmentText": "I couldn't understand your request. Could you please clarify?"
        })

    except Exception as e:
        print(f"Error during processing: {str(e)}")
        traceback.print_exc()
        return jsonify({'fulfillmentText': 'An error occurred.'}), 500

        
        if intent == 'CreateMealPlan':
            try:
                print("Starting CreateMealPlan intent")

                number_of_days = parameters.get('number_of_days')
                print(f"Received number_of_days: {number_of_days}")

                if not number_of_days:
                    return jsonify({'error': 'number_of_days is missing'}), 400

                try:
                    number_of_days = int(number_of_days)
                    print(f"Converted number_of_days to integer: {number_of_days}")
                except (ValueError, TypeError):
                    print("Invalid number_of_days format")
                    return jsonify({'error': 'Invalid number_of_days format. Must be a positive integer'}), 400

                favorite_ingredients = parameters.get('favorite_ingredients')
                allergies = parameters.get('allergies')
                cuisine_preferences = parameters.get('cuisine_preferences')
                dietary_preferences = parameters.get('dietary_preferences')
                portion_size = parameters.get('portion_size')
                meal_frequency = parameters.get('meal_frequency')
                budget_considerations = parameters.get('budget_considerations')

                print(f"Parameters received - favorite_ingredients: {favorite_ingredients}, allergies: {allergies}, "
                      f"cuisine_preferences: {cuisine_preferences}, dietary_preferences: {dietary_preferences}, "
                      f"portion_size: {portion_size}, meal_frequency: {meal_frequency}, budget_considerations: {budget_considerations}")

                prompt = (f"Create a {number_of_days}-day meal plan for a person who prefers {cuisine_preferences} cuisine, "
                          f"with favorite ingredients like {favorite_ingredients}, and avoiding {allergies}. "
                          f"The person follows a {dietary_preferences} diet, prefers {portion_size} portions, "
                          f"eats {meal_frequency} meals a day, and has a budget of {budget_considerations}.")
        
                print(f"Prompt sent to OpenAI: {prompt}")
                response_text = call_openai(prompt)
                print(f"OpenAI response: {response_text}")

                filename = "meal_plan.pdf"
                pdf_path = create_pdf_with_reportlab(response_text, filename)
                print(f"PDF generated at path: {pdf_path}")

                if pdf_path:
                    upload_response = upload_to_gcs_json_api("pdf-viewer-bucket", f"pdfs/{filename}", pdf_path)
                    print(f"GCS upload response: {upload_response}")

                    if upload_response:
                        download_url = upload_response.get("public_url", f"https://storage.googleapis.com/{upload_response['bucket']}/{upload_response['name']}")
                        print(f"Download URL: {download_url}")
                        return jsonify({
                            "fulfillmentText": "Great! Here is your meal plan. Click the link below to download it.",
                            "sessionInfo": {"parameters": {"download_url": download_url}}
                        })
                    else:
                        print("Error uploading the meal plan PDF.")
                        return jsonify({'fulfillmentText': 'Error uploading the meal plan PDF.'}), 500
                else:
                    print("Error creating the meal plan PDF.")
                    return jsonify({'fulfillmentText': 'Error creating the meal plan PDF.'}), 500

            except KeyError as e:
                print(f"KeyError: Missing key {e}")
                return jsonify({'error': f'Bad Request: Missing key {e}'}), 400
            except Exception as e:
                print(f"An error occurred in CreateMealPlan: {e}")
                traceback.print_exc()
                return jsonify({'error': 'Internal Server Error'}), 500

            

        elif intent == 'GenerateGroceryList':
            try:
                print("Starting GenerateGroceryList intent")

                recipe_preference = parameters.get('recipe_preference')
                dietary_restrictions = parameters.get('dietary_restrictions')
                portion_sizes = parameters.get('portion_sizes')

                print(f"Parameters received - recipe_preference: {recipe_preference}, dietary_restrictions: {dietary_restrictions}, "
                      f"portion_sizes: {portion_sizes}")

                if recipe_preference:
                    prompt = (f"Generate a grocery list for the following recipes: {recipe_preference}. "
                              f"Make sure the list fits a {dietary_restrictions} diet, serves {portion_sizes}.")
                    print(f"Prompt sent to OpenAI: {prompt}")
                    response_text = call_openai(prompt)
                    print(f"OpenAI response: {response_text}")
                else:
                    response_text = "Please provide recipes or create a meal plan first to generate your grocery list."
                    print(f"No recipe preference provided. Responding: {response_text}")

                filename = "grocery_list.pdf"
                pdf_path = create_pdf_with_reportlab(response_text, filename)
                print(f"PDF generated at path: {pdf_path}")

                if pdf_path:
                     upload_response = upload_to_gcs_json_api("pdf-viewer-bucket", f"pdfs/{filename}", pdf_path)
                     print(f"GCS upload response: {upload_response}")

                     if upload_response:
                         download_url = upload_response.get("public_url", f"https://storage.googleapis.com/{upload_response['bucket']}/{upload_response['name']}")
                         print(f"Download URL: {download_url}")
                         return jsonify({
                             "fulfillmentText": "Here is your grocery list. Click the link below to download it.",
                             "sessionInfo": {"parameters": {"download_url": download_url}}
                         })
                     else:
                         print("Error uploading the grocery list PDF.")
                         return jsonify({'fulfillmentText': 'Error uploading the grocery list PDF.'}), 500
                else:
                     print("Error creating the grocery list PDF.")
                     return jsonify({'fulfillmentText': 'Error creating the grocery list PDF.'}), 500

            except KeyError as e:
                 print(f"KeyError: Missing key {e}")
                 return jsonify({'error': f'Bad Request: Missing key {e}'}), 400
            except Exception as e:
                 print(f"An error occurred in GenerateGroceryList: {e}")
                 traceback.print_exc()
                 return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/download/<filename>')
def download_pdf(filename):
    try:
        file_path = os.path.join('/tmp', filename)
        print(f"Attempting to send file from: {file_path}")
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        print(f"Error sending file: {e}")
        return jsonify({'error': 'File not found.'}), 404

@app.route('/')
def home():
    return "Welcome to the Meal Planner Chatbot!"

if __name__ == '__main__':
    
    port = int(os.environ.get('PORT', 8080))  # Use PORT environment variable or default to 8080
    app.run(host='0.0.0.0', port=port)  # Ensure your app listens on all IPs
