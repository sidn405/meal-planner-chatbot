#!/bin/bash

# Start the Meal Planner Chatbot
gunicorn -w 2 -k gthread -t 120 -b 0.0.0.0:$PORT app:app
