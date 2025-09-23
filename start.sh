#!/bin/bash

# Set Flask environment variables
export FLASK_APP=app.py
export FLASK_ENV=development

# Run Flask application
flask run --host=0.0.0.0 --port=5006
