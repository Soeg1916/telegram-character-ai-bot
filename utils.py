import logging
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from character_manager import CharacterManager

logger = logging.getLogger(__name__)

# Define conversation states
SELECTING_NAME = 1
ENTERING_DESCRIPTION = 2
SELECTING_TRAITS = 3

async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Send a message to the user
    if update and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, something went wrong. Please try again later."
        )

async def list_characters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all available characters"""
    character_manager = CharacterManager()
    
    # Get all characters
    all_characters = character_manager.get_all_characters()
    
    # Get the user's custom characters
    user_id = update.effective_user.id
    user_custom_characters = character_manager.get_user_characters(user_id)
    
    # Create inline keyboard for character selection
    keyboard = []
    
    # Add preset characters
    keyboard.append([InlineKeyboardButton("--- Preset Characters ---", callback_data="preset_header")])
    for char_id, char in all_characters.items():
        if not char_id.startswith("custom_"):
            keyboard.append([InlineKeyboardButton(char["name"], callback_data=f"select_character:{char_id}")])
    
    # Add custom characters
    if user_custom_characters:
        keyboard.append([InlineKeyboardButton("--- Your Custom Characters ---", callback_data="custom_header")])
        for char_id in user_custom_characters:
            if char_id in all_characters:
                keyboard.append([InlineKeyboardButton(
                    all_characters[char_id]["name"], 
                    callback_data=f"select_character:{char_id}"
                )])
    
    # Add button to create a new character
    keyboard.append([InlineKeyboardButton("Create New Character", callback_data="create_character")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Choose a character to chat with:",
        reply_markup=reply_markup
    )

async def show_current_character(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the user's currently selected character"""
    character_manager = CharacterManager()
    
    # Get the user's selected character
    user_id = update.effective_user.id
    selected_character_id = context.user_data.get("selected_character") or character_manager.get_user_selected_character(user_id)
    
    if not selected_character_id:
        keyboard = [
            [InlineKeyboardButton("Choose a Character", callback_data="show_characters")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "You haven't selected a character yet! Use /characters to choose one, or tap the button below:",
            reply_markup=reply_markup
        )
        return
    
    # Get the character
    character = character_manager.get_character(selected_character_id)
    if not character:
        await update.message.reply_text(
            "The selected character no longer exists. Please choose another one with /characters."
        )
        return
    
    # Get the character stats
    character_stats = character_manager.get_character_stats(user_id, selected_character_id)
    
    # Create message
    message = f"You are currently chatting with *{character['name']}*\n\n"
    message += f"{character['description']}\n\n"
    
    if character_stats:
        mood_description = _get_mood_description(character_stats["mood"])
        message += f"Current mood: {mood_description}\n"
        message += f"Conversations: {character_stats['conversation_count']}\n\n"
    
    message += "Use /stats to see more detailed personality stats."
    
    # Create buttons
    keyboard = [
        [InlineKeyboardButton("Reset Conversation", callback_data=f"reset:{selected_character_id}")],
        [InlineKeyboardButton("Choose Different Character", callback_data="show_characters")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def reset_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset the conversation with the current character"""
    character_manager = CharacterManager()
    
    # Get the user's selected character
    user_id = update.effective_user.id
    selected_character_id = context.user_data.get("selected_character") or character_manager.get_user_selected_character(user_id)
    
    if not selected_character_id:
        await update.message.reply_text(
            "You haven't selected a character yet! Use /characters to choose one."
        )
        return
    
    # Get the character
    character = character_manager.get_character(selected_character_id)
    if not character:
        await update.message.reply_text(
            "The selected character no longer exists. Please choose another one with /characters."
        )
        return
    
    # Reset the conversation
    character_manager.reset_conversation(user_id, selected_character_id)
    
    await update.message.reply_text(
        f"Conversation with {character['name']} has been reset! Start chatting again."
    )

async def show_character_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detailed stats for the current character"""
    character_manager = CharacterManager()
    
    # Get the user's selected character
    user_id = update.effective_user.id
    selected_character_id = context.user_data.get("selected_character") or character_manager.get_user_selected_character(user_id)
    
    if not selected_character_id:
        await update.message.reply_text(
            "You haven't selected a character yet! Use /characters to choose one."
        )
        return
    
    # Get the character
    character = character_manager.get_character(selected_character_id)
    if not character:
        await update.message.reply_text(
            "The selected character no longer exists. Please choose another one with /characters."
        )
        return
    
    # Get the character stats
    character_stats = character_manager.get_character_stats(user_id, selected_character_id)
    
    if not character_stats:
        await update.message.reply_text(
            f"No stats available for {character['name']} yet. Start chatting to build up stats!"
        )
        return
    
    # Create message
    message = f"📊 *{character['name']} Stats* 📊\n\n"
    
    # Add mood
    mood_description = _get_mood_description(character_stats["mood"])
    mood_bar = _create_stat_bar(character_stats["mood"], 10)
    message += f"*Current Mood:* {mood_description}\n{mood_bar}\n\n"
    
    # Add conversation count
    message += f"*Conversations:* {character_stats['conversation_count']}\n\n"
    
    # Add personality traits
    message += "*Personality Traits:*\n"
    
    # Use character's defined traits if available, otherwise use the generic ones
    if "traits" in character:
        traits = character["traits"]
    else:
        traits = character_stats["personality_stats"]
    
    for trait, value in traits.items():
        trait_bar = _create_stat_bar(value, 10)
        message += f"*{trait.capitalize()}:* {trait_bar} ({value}/10)\n"
    
    await update.message.reply_text(
        message,
        parse_mode="Markdown"
    )

async def create_character_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the character creation process"""
    # Initialize character creation state
    context.user_data["character_creation"] = {"step": "name"}
    
    await update.message.reply_text(
        "Let's create a custom character! 🎭\n\n"
        "First, what's the name of your character?\n"
        "Send me the name or use /cancel to stop the creation process."
    )
    
    return SELECTING_NAME

async def process_character_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process character creation steps"""
    user_input = update.message.text
    
    if "character_creation" not in context.user_data:
        context.user_data["character_creation"] = {"step": "name"}
    
    current_step = context.user_data["character_creation"]["step"]
    
    if current_step == "name":
        # Save the name
        context.user_data["character_creation"]["name"] = user_input
        context.user_data["character_creation"]["step"] = "description"
        
        await update.message.reply_text(
            f"Great! Your character will be named *{user_input}*.\n\n"
            "Now, write a brief description of your character. Include their personality, background, and any important traits:",
            parse_mode="Markdown"
        )
        return ENTERING_DESCRIPTION
        
    elif current_step == "description":
        # Save the description
        context.user_data["character_creation"]["description"] = user_input
        context.user_data["character_creation"]["step"] = "traits"
        
        await update.message.reply_text(
            "Excellent description! Now, let's set some personality traits for your character.\n\n"
            "Rate each trait on a scale from 1-10, separated by commas:\n"
            "friendliness, humor, intelligence, empathy, energy\n\n"
            "For example: `7, 5, 9, 6, 8`"
        )
        return SELECTING_TRAITS
        
    elif current_step == "traits":
        # Parse and save the traits
        try:
            trait_values = [int(t.strip()) for t in user_input.split(",")]
            if len(trait_values) != 5:
                await update.message.reply_text(
                    "Please provide exactly 5 numbers separated by commas. Try again:"
                )
                return SELECTING_TRAITS
            
            for val in trait_values:
                if val < 1 or val > 10:
                    await update.message.reply_text(
                        "All values must be between 1 and 10. Try again:"
                    )
                    return SELECTING_TRAITS
            
            # Save the traits
            traits = {
                "friendliness": trait_values[0],
                "humor": trait_values[1],
                "intelligence": trait_values[2],
                "empathy": trait_values[3],
                "energy": trait_values[4]
            }
            context.user_data["character_creation"]["traits"] = traits
            
            # Create the character
            character_manager = CharacterManager()
            
            # Create a system prompt based on the character information
            system_prompt = (
                f"You are {context.user_data['character_creation']['name']}. "
                f"{context.user_data['character_creation']['description']}\n\n"
                "Respond as this character would, maintaining their personality and speech patterns."
            )
            
            character_id = character_manager.create_custom_character(
                update.effective_user.id,
                context.user_data["character_creation"]["name"],
                context.user_data["character_creation"]["description"],
                traits,
                system_prompt
            )
            
            # Select the new character for the user
            character_manager.set_user_selected_character(update.effective_user.id, character_id)
            context.user_data["selected_character"] = character_id
            
            # Clear the character creation data
            del context.user_data["character_creation"]
            
            await update.message.reply_text(
                f"🎉 Character *{context.user_data['character_creation']['name']}* created successfully!\n\n"
                "You are now chatting with your new character. Say hello!",
                parse_mode="Markdown"
            )
            
            # End the conversation
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text(
                "Please provide numbers only, separated by commas. Try again:"
            )
            return SELECTING_TRAITS
    
    # Default fallback
    await update.message.reply_text("Something went wrong. Please try again or use /cancel.")
    return ConversationHandler.END

async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel character creation"""
    if "character_creation" in context.user_data:
        del context.user_data["character_creation"]
    
    await update.message.reply_text(
        "Character creation cancelled. Use /characters to choose from existing characters."
    )
    
    return ConversationHandler.END

async def delete_character(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a custom character"""
    character_manager = CharacterManager()
    
    # Get the user's custom characters
    user_id = update.effective_user.id
    user_custom_characters = character_manager.get_user_characters(user_id)
    
    if not user_custom_characters:
        await update.message.reply_text(
            "You don't have any custom characters to delete. Use /create to make one!"
        )
        return
    
    # Create inline keyboard for character selection
    keyboard = []
    all_characters = character_manager.get_all_characters()
    
    for char_id in user_custom_characters:
        if char_id in all_characters:
            keyboard.append([InlineKeyboardButton(
                all_characters[char_id]["name"], 
                callback_data=f"delete_character:{char_id}"
            )])
    
    keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel_delete")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Select a custom character to delete:",
        reply_markup=reply_markup
    )

def _get_mood_description(mood_value: int) -> str:
    """Convert a numeric mood value to a text description"""
    if mood_value >= 9:
        return "Ecstatic 😄"
    elif mood_value >= 8:
        return "Very happy 😊"
    elif mood_value >= 7:
        return "Happy 🙂"
    elif mood_value >= 6:
        return "Content 😌"
    elif mood_value == 5:
        return "Neutral 😐"
    elif mood_value >= 4:
        return "Slightly annoyed 😕"
    elif mood_value >= 3:
        return "Frustrated 😒"
    elif mood_value >= 2:
        return "Upset 😠"
    else:
        return "Angry 😡"

def _create_stat_bar(value: int, max_value: int) -> str:
    """Create a visual bar representation of a stat"""
    filled = "█" * value
    empty = "░" * (max_value - value)
    return filled + empty
