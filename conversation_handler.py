import logging
from telegram import Update
from telegram.ext import ContextTypes
from character_manager import CharacterManager
from mistral_integration import generate_response

logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle normal messages and generate a response from the character"""
    user_message = update.message.text
    user_id = update.effective_user.id
    
    # Get the character manager
    character_manager = CharacterManager()
    
    # Get the user's selected character
    selected_character_id = context.user_data.get("selected_character") or character_manager.get_user_selected_character(user_id)
    
    # If no character is selected, ask the user to select one
    if not selected_character_id:
        keyboard = [
            [{"text": "Choose a Character", "callback_data": "show_characters"}]
        ]
        await update.message.reply_text(
            "You haven't selected a character yet! Use /characters to choose one, or tap the button below:",
            reply_markup={"inline_keyboard": keyboard}
        )
        return
    
    # Get the character
    character = character_manager.get_character(selected_character_id)
    if not character:
        await update.message.reply_text(
            "The selected character no longer exists. Please choose another one with /characters."
        )
        return
    
    # Send a "typing" action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Add the user message to the conversation history
    character_manager.add_to_conversation_history(user_id, selected_character_id, "user", user_message)
    
    # Get the conversation history
    conversation_history = character_manager.get_conversation_history(user_id, selected_character_id)
    
    # Get the character stats
    character_stats = character_manager.get_character_stats(user_id, selected_character_id)
    
    # If the character stats don't exist, initialize them
    if not character_stats:
        character_stats = {
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
    
    # Update conversation count
    character_stats["conversation_count"] += 1
    
    # Generate a response from the character using Mistral AI
    try:
        response, mood_change = await generate_response(
            character,
            conversation_history,
            character_stats
        )
        
        # Update the character's mood based on the response
        new_mood = max(1, min(10, character_stats["mood"] + mood_change))
        character_stats["mood"] = new_mood
        
        # Update character stats
        character_manager.update_character_stats(user_id, selected_character_id, character_stats)
        
        # Add the response to the conversation history
        character_manager.add_to_conversation_history(user_id, selected_character_id, "assistant", response)
        
        # Send the response
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        await update.message.reply_text(
            f"Sorry, I couldn't generate a response from {character['name']} right now. Please try again later."
        )
