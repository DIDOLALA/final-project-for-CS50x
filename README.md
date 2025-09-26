# START YOUR CHINESE TRAVEL
#### Video Demo:  <[URL HERE](https://youtu.be/pKDJsybttCY)>
#### Description:

# Project Background
With the implementation of China's visa-free policy, more and more foreigners now have greater opportunities to travel to China. However, the most challenging part of planning a trip lies in the initial stage—especially selecting a destination—particularly for many foreigners who have little to no knowledge about China.

# Project Overview
This project is a Flask-based web application designed to generate personalized China travel recommendations for foreign tourists through a series of engaging interactive questionnaires. Users can answer a set of questions to receive AI-generated travel destination recommendations and detailed itinerary plans. The ultimate goal is to inspire users' interest in (or "plant a seed of desire for") China's tourist destinations.

# Technology Stack
*   **Backend Framework**: Flask
*   **Database**: SQLite
*   **Frontend Templating**: Jinja2
*   **Multilingual Support**: Custom JSON dictionary mapping
*   **AI Service**: DeepSeek API
*   **User Authentication**: Flask Session Management

# Core Features
## 1. Multilingual Support
*   Supports both Chinese and English, with dynamic interface language switching based on user selection.
*   Implements text mapping through JSON dictionaries in `translations.py`.
## 2. User Authentication System
*   Allows users to register, log in, and log out.
*   Unauthenticated users can experience the questionnaire once; logged-in users enjoy unlimited access.
## 3. Questionnaire
*   **Information Collection**: Gathers users' basic information (name, gender, nationality, age, occupation, etc.).
*   **Travel Preferences**: Captures users' travel personality, travel purposes, destination preferences, and dietary tastes.
*   **Practical Constraints**: Collects information about users' travel duration, travel pace, and budget.
## 4. AI Recommendations
*   Integrates the DeepSeek API to generate recommendations based on user information.
*   Uses carefully designed prompts to ensure the recommended content adheres to specified format requirements.
*   Supports generating two types of results: "Dream Destination Recommendations" and "Detailed Itinerary Plans".
## 5. Result Display
*   Formats the text returned by AI using HTML tags to enhance readability.

# Database Design
*   **User**: Stores users' basic information (username, password hash, personal details, etc.).
*   **Preference**: Stores users' travel preferences.
*   **Limitation**: Stores users' practical travel constraints.
*   **Itinerary**: Stores the generated travel plans.

# AI Integration
*   Calls the DeepSeek API via HTTP requests.
*   Designs different prompt templates for different stages (recommendation generation and itinerary planning).
*   Handles API timeouts and errors to ensure a smooth user experience.

# Project Structure
project/
├── app.py                 # Main application file
├── database.py            # Database models
├── create_db.py           # Database initialization script
├── translations.py        # Multilingual dictionaries
├── requirements.txt       # Dependencies list
├── templates/             # Jinja2 templates
│   ├── base.html
│   ├── index.html
│   ├── information.html
│   ├── preferences.html
│   ├── result.html
│   ├── limitations.html
│   ├── itinerary.html
│   ├── layout.html
│   ├── login.html
│   └── register.html
└── instance/
  └── project.db 