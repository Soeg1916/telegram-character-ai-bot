"""
This file contains functions for handling data storage and retrieval.
For simplicity, we're using JSON files for storage, but in a production environment,
you might want to use a proper database.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def ensure_data_directory_exists() -> None:
    """Ensure that the data directory exists"""
    if not os.path.exists("data"):
        os.makedirs("data")

def load_json_file(file_path: str, default_value: Any = None) -> Any:
    """Load data from a JSON file"""
    if default_value is None:
        default_value = {}
    
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return default_value
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON file {file_path}: {e}")
        return default_value
    except Exception as e:
        logger.error(f"Error loading file {file_path}: {e}")
        return default_value

def save_json_file(file_path: str, data: Any) -> bool:
    """Save data to a JSON file"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving file {file_path}: {e}")
        return False

def get_user_data(user_id: int) -> Dict[str, Any]:
    """Get data for a specific user"""
    ensure_data_directory_exists()
    
    user_data_file = f"data/user_{user_id}.json"
    return load_json_file(user_data_file, {"selected_character": None, "custom_characters": []})

def save_user_data(user_id: int, data: Dict[str, Any]) -> bool:
    """Save data for a specific user"""
    ensure_data_directory_exists()
    
    user_data_file = f"data/user_{user_id}.json"
    return save_json_file(user_data_file, data)

def get_custom_characters() -> Dict[str, Dict[str, Any]]:
    """Get all custom characters"""
    ensure_data_directory_exists()
    
    custom_characters_file = "data/custom_characters.json"
    return load_json_file(custom_characters_file)

def save_custom_characters(custom_characters: Dict[str, Dict[str, Any]]) -> bool:
    """Save all custom characters"""
    ensure_data_directory_exists()
    
    custom_characters_file = "data/custom_characters.json"
    return save_json_file(custom_characters_file, custom_characters)
