import os
import json
import logging
import random
from typing import Dict, List, Tuple
import aiohttp

logger = logging.getLogger(__name__)

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

async def generate_response(
    character: Dict, 
    conversation_history: List[Dict], 
    character_stats: Dict
) -> Tuple[str, float]:
    """
    Generate a response from the character using Mistral AI
    
    Args:
        character: The character data
        conversation_history: The conversation history
        character_stats: The character's mood and personality stats
    
    Returns:
        Tuple of (response text, mood change)
    """
    # Get the Mistral API key from environment variable
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY environment variable not set!")
    
    # Prepare the system prompt with character info and current stats
    system_prompt = _prepare_system_prompt(character, character_stats)
    
    # Prepare the messages for the Mistral API
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add the conversation history
    for message in conversation_history:
        messages.append({"role": message["role"], "content": message["content"]})
    
    # Prepare the request payload
    payload = {
        "model": "mistral-medium",  # Using Mistral Medium model
        "messages": messages,
        "temperature": 0.7,  # A moderate temperature for good creativity but consistent responses
        "max_tokens": 1000,  # Limit response length
        "top_p": 0.9,
        "safe_prompt": True
    }
    
    # Make the API call
    async with aiohttp.ClientSession() as session:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        async with session.post(MISTRAL_API_URL, json=payload, headers=headers) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Mistral API error: {error_text}")
                raise Exception(f"Mistral API error: {response.status}")
            
            response_data = await response.json()
            
            # Extract the response text
            response_text = response_data["choices"][0]["message"]["content"]
            
            # Calculate a random mood change based on the conversation
            # This is a simple implementation - in a more advanced system, this would
            # use sentiment analysis or more complex logic
            mood_change = random.uniform(-0.5, 0.5)
            
            return response_text, mood_change

def _prepare_system_prompt(character: Dict, character_stats: Dict) -> str:
    """
    Prepare the system prompt for the Mistral API, including character info and current stats
    
    Args:
        character: The character data
        character_stats: The character's mood and personality stats
    
    Returns:
        The system prompt
    """
    # Use the character's system prompt if available, otherwise create one
    if "system_prompt" in character and character["system_prompt"]:
        base_prompt = character["system_prompt"]
    else:
        base_prompt = (
            f"You are {character['name']}. {character['description']}\n\n"
            f"Respond as this character would, maintaining their personality and speech patterns."
        )
    
    # Add current mood and personality traits
    mood_description = _get_mood_description(character_stats["mood"])
    
    traits_info = "Personality traits:\n"
    if "traits" in character:
        for trait, value in character["traits"].items():
            traits_info += f"- {trait.capitalize()}: {value}/10\n"
    else:
        traits_info += (
            f"- Friendliness: {character_stats['personality_stats']['friendliness']}/10\n"
            f"- Humor: {character_stats['personality_stats']['humor']}/10\n"
            f"- Intelligence: {character_stats['personality_stats']['intelligence']}/10\n"
            f"- Empathy: {character_stats['personality_stats']['empathy']}/10\n"
            f"- Energy: {character_stats['personality_stats']['energy']}/10\n"
        )
    
    current_state = (
        f"\nCurrent state:\n"
        f"- Mood: {mood_description}\n"
        f"- Conversation count: {character_stats['conversation_count']}\n"
    )
    
    # Add guidelines for response structure
    guidelines = (
        "\nGuidelines:\n"
        "1. Stay in character at all times\n"
        "2. Keep responses concise but meaningful\n"
        "3. Express emotions and reactions consistent with the character\n"
        "4. If asked about being an AI, maintain the character illusion\n"
        "5. Base responses on the character's knowledge, not modern information they wouldn't know\n"
    )
    
    return f"{base_prompt}\n\n{traits_info}{current_state}{guidelines}"

def _get_mood_description(mood_value: int) -> str:
    """Convert a numeric mood value to a text description"""
    if mood_value >= 9:
        return "Ecstatic"
    elif mood_value >= 8:
        return "Very happy"
    elif mood_value >= 7:
        return "Happy"
    elif mood_value >= 6:
        return "Content"
    elif mood_value == 5:
        return "Neutral"
    elif mood_value >= 4:
        return "Slightly annoyed"
    elif mood_value >= 3:
        return "Frustrated"
    elif mood_value >= 2:
        return "Upset"
    else:
        return "Angry"
