from flask import Flask, request, jsonify, send_file, url_for
import requests
import os


OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

app = Flask(__name__)

# In-memory session storage
session_storage = {}

# Mock data store (replace with actual data store queries)
healthy_eating_guru_01 = {
    "chicken and rice": "Here is a simple recipe for chicken and rice...",
    "salmon": "Here is a simple recipe for salmon...",
    "grilled salmon": "Here is a recipe for grilled salmon..."
}

def call_openai(prompt):
    print(f"Calling OpenAI with prompt: {prompt}")  # Debugging
    headers = {'Authorization': f'Bearer {OPENAI_API_KEY}'}
    data = {'model': 'gpt-4', 'messages': [{'role': 'system', 'content': 'You are a helpful assistant.'}, {'role': 'user', 'content': prompt}], 'max_tokens': 1500}
    response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
    print(f"OpenAI response: {response.json()}")  # Debugging
    return response.json()['choices'][0]['message']['content'].strip()

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors

def create_pdf_with_reportlab(content, filename):
    # Create a PDF document with ReportLab
    save_path = os.path.join(os.path.expanduser("~"), "Downloads", filename)
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
    
    return save_path


def fallback_recipe_search(ingredients):
    for key in healthy_eating_guru_01:
        if all(item in key.lower() for item in ingredients):
            return healthy_eating_guru_01[key]
    return "Sorry, I couldn't find a predefined recipe. Please try again with different ingredients."

@app.route('/dialogflowWebhook', methods=['POST'])
def dialogflow_webhook():
    try:
        req_data = request.get_json()

        # Log the full request data for debugging
        print(f"Request Data: {req_data}")

        # Ensure 'queryResult' and 'sessionInfo' are present
        if 'queryResult' not in req_data or 'sessionInfo' not in req_data:
            print("Error: 'queryResult' or 'sessionInfo' is missing in the request.")
            return jsonify({'error': 'Bad Request: Missing queryResult or sessionInfo'}), 400

        # Retrieve session parameters
        session_info = req_data.get('sessionInfo', {})
        session_parameters = session_info.get('parameters', {})
               
        # Extract intent and queryResult parameters

        query_result = req_data.get('queryResult', {})
        intent = query_result.get('intent', {}).get('displayName', '')
        query_result_parameters = query_result.get('parameters', {})

        print(f"Session Parameters: {session_parameters}")
        print(f"Query Result Parameters: {query_result_parameters}")
        print(f"Intent: {intent}")

        response_text = ''
        filename = ''
        
        if intent == 'CreateMealPlan':
            # Extract parameters from queryResult if sessionInfo does not include them
            query_result_parameters = req_data['queryResult'].get('parameters', {})

            # Log session and query result parameters to troubleshoot
            print(f"Raw session parameters: {session_parameters}")
            print(f"Raw query result parameters: {query_result_parameters}")

            # Retrieve number_of_days from the query result
            number_of_days = query_result_parameters.get('number_of_days')

            # Ensure number_of_days is valid
            if number_of_days is None:
                print("number_of_days is missing from the request.")
                return jsonify({'error': 'number_of_days is missing'}), 400

            if isinstance(number_of_days, str):
                print("number_of_days is a string, converting to int")

            try:
                number_of_days = int(number_of_days)  # Cast to integer
                if number_of_days <= 0:
                    return jsonify({'error': 'Invalid number_of_days'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid number_of_days format. Must be a positive integer'}), 400

            # Retrieve other parameters from queryResult
            allergies = query_result_parameters.get('allergies')
            favorite_ingredients = query_result_parameters.get('favorite_ingredients')
            avoided_ingredients = query_result_parameters.get('avoided_ingredients')
            portion_size = query_result_parameters.get('portion_size')
            cuisine_preferences = query_result_parameters.get('cuisine_preferences')
            dietary_preferences = query_result_parameters.get('dietary_preferences')
            meal_types = query_result_parameters.get('meal_types')
            meal_frequency = query_result_parameters.get('meal_frequency')
            calorie_goals = query_result_parameters.get('calorie_goals')
            budget_considerations = query_result_parameters.get('budget_considerations')
            time_constraints = query_result_parameters.get('time_constraints')

            # Create the OpenAI prompt dynamically with the extracted values
            prompt = (f"Create a {number_of_days}-day meal plan for a person who prefers {cuisine_preferences} cuisine, "
                      f"with favorite ingredients like {favorite_ingredients}, and avoiding {avoided_ingredients}. "
                      f"The person follows a {dietary_preferences} diet, prefers {portion_size} portions, "
                      f"eats {meal_frequency} meals a day, and has a budget of {budget_considerations}.")

            # Log the prompt for debugging
            print(f"Calling OpenAI with prompt: {prompt}")

            # Call OpenAI and handle the response
            response_text = call_openai(prompt)
            filename = "meal_plan.pdf"
            pdf_path = create_pdf_with_reportlab(response_text, filename)
            pdf_url = url_for('download_pdf', filename=filename, _external=True)

            return jsonify({
                'fulfillmentText': "Great! Here is your meal plan. Click the link below to download it.",
                'pdf_url': pdf_url
            })

        elif intent == 'GenerateGroceryList':
            # Extract parameters from the query result
            recipe_preference = query_result_parameters.get('recipe_preference')
            dietary_restrictions = query_result_parameters.get('dietary_restrictions')
            portion_sizes = query_result_parameters.get('portion_sizes')
            staples_and_essentials = query_result_parameters.get('staples_and_essentials')
            preferred_stores = query_result_parameters.get('preferred_stores')
            budget_considerations = query_result_parameters.get('budget_considerations')

            # Check if the user has a previously created meal plan
            meal_plan_ingredients = session_storage.get(session_info.get('session'), {}).get('meal_plan_ingredients', [])
            
            # If meal plan ingredients are found, include them in the grocery list
            if meal_plan_ingredients:
                response_text = f"Here is your grocery list based on the meal plan: {', '.join(meal_plan_ingredients)}"
            else:
                # If no meal plan, create a grocery list based on the recipes the user provided
                if recipe_preference:
                    try:
                        # Create OpenAI prompt to extract ingredients for the specified recipes
                        prompt = (f"Generate a grocery list for the following recipes: {recipe_preference}. "
                                  f"Make sure the list fits a {dietary_restrictions} diet, serves {portion_sizes}, "
                                  f"and includes staples like {staples_and_essentials}. The budget is {budget_considerations} "
                                  f"and shopping will be done at {preferred_stores}.")
                        response_text = call_openai(prompt)
                    except Exception as e:
                        print(f"OpenAI API error: {e}")
                        response_text = "Sorry, I couldn't generate the grocery list based on the provided recipes."
                else:
                    # If no recipes provided and no previous meal plan, fallback to a default response
                    response_text = "Please provide recipes or create a meal plan first to generate your grocery list."
            
            # Create a PDF of the grocery list
            filename = "grocery_list.pdf"
            pdf_path = create_pdf_with_reportlab(response_text, filename)

            # Generate the URL for downloading the PDF
            pdf_url = url_for('download_pdf', filename=filename, _external=True)

            return jsonify({
                'fulfillmentText': "Here is your grocery list. Click the link below to download it.",
                'pdf_url': pdf_url
            })


        # Handling the GetRecipes intent
        elif intent == 'GetRecipes':
            query_result_parameters = req_data['queryResult'].get('parameters', {})  # Retrieves parameters from the request
            ingredients_preference = query_result_parameters.get('ingredients_preference')
            dietary_restrictions = query_result_parameters.get('dietary_restrictions')
            cuisine_preference = query_result_parameters.get('cuisine_preference')
            meal_type = query_result_parameters.get('meal_type')
            cooking_time = query_result_parameters.get('cooking_time')
            serving_size = query_result_parameters.get('serving_size')
            skill_level = query_result_parameters.get('skill_level')
            special_occasions = query_result_parameters.get('special_occasions')

            # Log the ingredients for debugging
            print(f"Ingredients preference received: {ingredients_preference}")

            # Ensure it calls OpenAI before datastore
            if ingredients_preference:
                try:
                    # Create recipe using OpenAI
                    prompt = (f"Create a detailed recipe for a meal using the following ingredients: {ingredients_preference}. "
                              f"It should be a {cuisine_preference} cuisine, suitable for {dietary_restrictions} diet. "
                              f"The recipe should take {cooking_time}, serve {serving_size} people, and be suitable for a {skill_level} chef. "
                              f"It should be appropriate for {special_occasions}.")
                    response_text = call_openai(prompt)
                except Exception as e:
                    # If OpenAI fails, log it and fall back to predefined recipes
                    print(f"OpenAI API error: {e}")
                    response_text = fallback_recipe_search(ingredients_preference)
            else:
                response_text = "No ingredients provided. Please specify some ingredients."

            filename = "recipe.pdf"
            pdf_path = create_pdf_with_reportlab(response_text, filename)

            # Generate the URL for downloading the PDF
            pdf_url = url_for('download_pdf', filename=filename, _external=True)

            # Send the response with the download link
            return jsonify({
                'fulfillmentText': f"Here is your recipe. Click the link below to download it.",
                'pdf_url': pdf_url
            })

        else:
            return jsonify({'fulfillmentText': "I'm not sure how to handle that intent."})

    except KeyError as e:
        print(f'Bad Request: Missing key {e}')
        return jsonify({'error': f'Bad Request: Missing key {e}'}), 400
    except Exception as e:
        print(f'Error handling request: {e}')
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/download/<filename>')
def download_pdf(filename):
    return send_file(os.path.join(os.path.expanduser("~"), "Downloads", filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)






















