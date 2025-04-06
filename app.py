import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# use SQLite for simplicity in development
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///character_bot.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# initialize the app with the extension
db.init_app(app)

# Import character manager for displaying data
from character_manager import CharacterManager

@app.route('/')
def index():
    """Home page"""
    # Get character data for display
    character_manager = CharacterManager()
    preset_characters = {}
    
    # Separate preset characters from custom ones
    all_characters = character_manager.get_all_characters()
    for char_id, char in all_characters.items():
        if not char_id.startswith("custom_"):
            preset_characters[char_id] = char
    
    return render_template('index.html', 
                          preset_characters=preset_characters,
                          bot_name="Character Chat Bot")

@app.route('/characters')
def characters():
    """Display all available characters"""
    character_manager = CharacterManager()
    
    # Get all characters
    all_characters = character_manager.get_all_characters()
    
    # Separate preset and custom characters
    preset_characters = {}
    custom_characters = {}
    
    for char_id, char in all_characters.items():
        if not char_id.startswith("custom_"):
            preset_characters[char_id] = char
        else:
            custom_characters[char_id] = char
            
    return render_template('characters.html', 
                          preset_characters=preset_characters,
                          custom_characters=custom_characters,
                          all_characters=all_characters)

@app.route('/character/<character_id>')
def character_details(character_id):
    """Display details for a specific character"""
    character_manager = CharacterManager()
    
    # Get the character
    character = character_manager.get_character(character_id)
    
    if not character:
        flash("Character not found", "danger")
        return redirect(url_for('characters'))
    
    return render_template('character_details.html', 
                          character=character,
                          character_id=character_id)

@app.route('/api/characters')
def api_characters():
    """API endpoint to get all characters"""
    character_manager = CharacterManager()
    all_characters = character_manager.get_all_characters()
    return jsonify(all_characters)

@app.route('/api/character/<character_id>')
def api_character(character_id):
    """API endpoint to get a specific character"""
    character_manager = CharacterManager()
    character = character_manager.get_character(character_id)
    
    if not character:
        return jsonify({"error": "Character not found"}), 404
        
    return jsonify(character)

@app.route('/docs')
def docs():
    """Documentation page"""
    return render_template('docs.html')

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

# Create all database tables
with app.app_context():
    import models  # Import models to register them with SQLAlchemy
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)