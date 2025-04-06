import os
import json
import logging
from typing import Dict, List, Optional, Any
from preset_characters import PRESET_CHARACTERS

logger = logging.getLogger(__name__)

class CharacterManager:
    """
    Manages character profiles, including preset and custom characters.
    Handles character selection, creation, deletion, and stats tracking.
    """
    def __init__(self):
        self.data_dir = "data"
        self.custom_characters_file = os.path.join(self.data_dir, "custom_characters.json")
        self.user_data_file = os.path.join(self.data_dir, "user_data.json")
        self.preset_characters = PRESET_CHARACTERS
        
        # Create data directory if it doesn't exist
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        # Load custom characters and user data
        self.custom_characters = self._load_custom_characters()
        self.user_data = self._load_user_data()
    
    def _load_custom_characters(self) -> Dict[str, Dict]:
        """Load custom characters from file or create empty dict if file doesn't exist"""
        if os.path.exists(self.custom_characters_file):
            try:
                with open(self.custom_characters_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error("Error decoding custom characters file. Creating new file.")
                return {}
        return {}
    
    def _load_user_data(self) -> Dict[str, Dict]:
        """Load user data from file or create empty dict if file doesn't exist"""
        if os.path.exists(self.user_data_file):
            try:
                with open(self.user_data_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error("Error decoding user data file. Creating new file.")
                return {}
        return {}
    
    def _save_custom_characters(self) -> None:
        """Save custom characters to file"""
        with open(self.custom_characters_file, 'w') as f:
            json.dump(self.custom_characters, f, indent=2)
    
    def _save_user_data(self) -> None:
        """Save user data to file"""
        with open(self.user_data_file, 'w') as f:
            json.dump(self.user_data, f, indent=2)
    
    def get_all_characters(self) -> Dict[str, Dict]:
        """Get all characters (preset + custom)"""
        all_characters = self.preset_characters.copy()
        all_characters.update(self.custom_characters)
        return all_characters
    
    def get_character(self, character_id: str) -> Optional[Dict]:
        """Get a character by ID"""
        all_characters = self.get_all_characters()
        return all_characters.get(character_id)
    
    def get_user_characters(self, user_id: int) -> List[str]:
        """Get the custom characters created by a user"""
        if str(user_id) not in self.user_data:
            self.user_data[str(user_id)] = {"custom_characters": []}
            self._save_user_data()
        
        return self.user_data[str(user_id)].get("custom_characters", [])
    
    def get_user_selected_character(self, user_id: int) -> Optional[str]:
        """Get the currently selected character for a user"""
        if str(user_id) not in self.user_data:
            self.user_data[str(user_id)] = {"selected_character": None}
            self._save_user_data()
        
        return self.user_data[str(user_id)].get("selected_character")
    
    def set_user_selected_character(self, user_id: int, character_id: str) -> None:
        """Set the currently selected character for a user"""
        if str(user_id) not in self.user_data:
            self.user_data[str(user_id)] = {}
        
        self.user_data[str(user_id)]["selected_character"] = character_id
        # Initialize character stats if they don't exist
        if "character_stats" not in self.user_data[str(user_id)]:
            self.user_data[str(user_id)]["character_stats"] = {}
        
        if character_id not in self.user_data[str(user_id)]["character_stats"]:
            character = self.get_character(character_id)
            if character:
                # Initialize stats
                self.user_data[str(user_id)]["character_stats"][character_id] = {
                    "mood": 5,  # Scale of 1-10
                    "conversation_count": 0,
                    "personality_stats": {
                        "friendliness": 5,
                        "humor": 5,
                        "intelligence": 5,
                        "empathy": 5,
                        "energy": 5
                    }
                }
        
        self._save_user_data()
    
    def create_custom_character(self, user_id: int, name: str, description: str, 
                                traits: Dict[str, int], system_prompt: str, nsfw: bool = False) -> str:
        """Create a custom character and return its ID"""
        # Generate a unique ID for the character
        character_id = f"custom_{name.lower().replace(' ', '_')}_{user_id}"
        
        # Create the character
        character = {
            "name": name,
            "description": description,
            "traits": traits,
            "system_prompt": system_prompt,
            "creator_id": user_id,
            "nsfw": nsfw
        }
        
        # Add the character to custom characters
        self.custom_characters[character_id] = character
        self._save_custom_characters()
        
        # Add the character to the user's custom characters
        if str(user_id) not in self.user_data:
            self.user_data[str(user_id)] = {"custom_characters": []}
        
        if "custom_characters" not in self.user_data[str(user_id)]:
            self.user_data[str(user_id)]["custom_characters"] = []
        
        self.user_data[str(user_id)]["custom_characters"].append(character_id)
        self._save_user_data()
        
        return character_id
    
    def delete_custom_character(self, user_id: int, character_id: str) -> bool:
        """Delete a custom character if it belongs to the user"""
        if character_id in self.custom_characters and self.custom_characters[character_id]["creator_id"] == user_id:
            # Remove from custom characters
            del self.custom_characters[character_id]
            self._save_custom_characters()
            
            # Remove from user's custom characters
            if str(user_id) in self.user_data and "custom_characters" in self.user_data[str(user_id)]:
                if character_id in self.user_data[str(user_id)]["custom_characters"]:
                    self.user_data[str(user_id)]["custom_characters"].remove(character_id)
                
                # If this was the user's selected character, deselect it
                if self.user_data[str(user_id)].get("selected_character") == character_id:
                    self.user_data[str(user_id)]["selected_character"] = None
                
                self._save_user_data()
            
            return True
        
        return False
    
    def get_character_stats(self, user_id: int, character_id: str) -> Optional[Dict]:
        """Get the stats for a character for a specific user"""
        if str(user_id) in self.user_data and "character_stats" in self.user_data[str(user_id)]:
            return self.user_data[str(user_id)]["character_stats"].get(character_id)
        
        return None
    
    def update_character_stats(self, user_id: int, character_id: str, stats_update: Dict[str, Any]) -> None:
        """Update the stats for a character for a specific user"""
        if str(user_id) not in self.user_data:
            self.user_data[str(user_id)] = {"character_stats": {}}
        
        if "character_stats" not in self.user_data[str(user_id)]:
            self.user_data[str(user_id)]["character_stats"] = {}
        
        if character_id not in self.user_data[str(user_id)]["character_stats"]:
            self.user_data[str(user_id)]["character_stats"][character_id] = {
                "mood": 5,
                "conversation_count": 0,
                "personality_stats": {
                    "friendliness": 5,
                    "humor": 5,
                    "intelligence": 5,
                    "empathy": 5,
                    "energy": 5
                }
            }
        
        # Update the stats
        character_stats = self.user_data[str(user_id)]["character_stats"][character_id]
        
        if "mood" in stats_update:
            character_stats["mood"] = max(1, min(10, stats_update["mood"]))
        
        if "conversation_count" in stats_update:
            character_stats["conversation_count"] = stats_update["conversation_count"]
        
        if "personality_stats" in stats_update:
            for trait, value in stats_update["personality_stats"].items():
                if trait in character_stats["personality_stats"]:
                    character_stats["personality_stats"][trait] = max(1, min(10, value))
        
        self._save_user_data()
    
    def reset_conversation(self, user_id: int, character_id: str) -> None:
        """Reset the conversation with a character"""
        if str(user_id) in self.user_data and "conversation_history" in self.user_data[str(user_id)]:
            if character_id in self.user_data[str(user_id)]["conversation_history"]:
                self.user_data[str(user_id)]["conversation_history"][character_id] = []
                self._save_user_data()
    
    def get_conversation_history(self, user_id: int, character_id: str) -> List[Dict]:
        """Get the conversation history with a character"""
        if str(user_id) not in self.user_data:
            self.user_data[str(user_id)] = {"conversation_history": {}}
        
        if "conversation_history" not in self.user_data[str(user_id)]:
            self.user_data[str(user_id)]["conversation_history"] = {}
        
        if character_id not in self.user_data[str(user_id)]["conversation_history"]:
            self.user_data[str(user_id)]["conversation_history"][character_id] = []
        
        return self.user_data[str(user_id)]["conversation_history"][character_id]
    
    def add_to_conversation_history(self, user_id: int, character_id: str, role: str, content: str) -> None:
        """Add a message to the conversation history"""
        if str(user_id) not in self.user_data:
            self.user_data[str(user_id)] = {"conversation_history": {}}
        
        if "conversation_history" not in self.user_data[str(user_id)]:
            self.user_data[str(user_id)]["conversation_history"] = {}
        
        if character_id not in self.user_data[str(user_id)]["conversation_history"]:
            self.user_data[str(user_id)]["conversation_history"][character_id] = []
        
        # Add the message to the conversation history
        self.user_data[str(user_id)]["conversation_history"][character_id].append({
            "role": role,
            "content": content
        })
        
        # Limit the conversation history to the last 30 messages for better memory while avoiding context length issues
        if len(self.user_data[str(user_id)]["conversation_history"][character_id]) > 30:
            self.user_data[str(user_id)]["conversation_history"][character_id] = \
                self.user_data[str(user_id)]["conversation_history"][character_id][-30:]
        
        self._save_user_data()
