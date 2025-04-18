import logging
import re
from telegram import Update
from telegram.ext import ContextTypes
from character_manager import CharacterManager
from mistral_integration import generate_response

logger = logging.getLogger(__name__)

def format_emotional_expressions(text):
    """
    Format emotional expressions like *sigh*, *hmph*, etc. with monospace formatting
    Also handles expressions like "ahh", "umm", "hmm", etc.
    Properly escapes special characters for Telegram's MarkdownV2
    """
    # First, we'll collect all the sections we want to format as monospace
    monospace_sections = []
    
    # Pattern for expressions in asterisks like *sigh* or *blushes*
    asterisk_pattern = r'\*(.*?)\*'
    for match in re.finditer(asterisk_pattern, text):
        monospace_sections.append((match.start(), match.end(), match.group(1)))
    
    # Pattern for common emotional expressions like "ahh", "umm", "hmm", etc.
    # These are usually at the beginning of a sentence or standalone
    emotional_sounds = [
        r'\b(a+h+)\b', r'\b(u+m+)\b', r'\b(h+m+)\b', r'\b(o+h+)\b', 
        r'\b(w+o+w+)\b', r'\b(h+u+h+)\b', r'\b(e+h+)\b', r'\b(u+h+)\b',
        r'\b(h+a+h+a+)\b', r'\b(h+e+h+e+)\b', r'\b(t+s+k+)\b', r'\b(s+i+g+h+)\b',
        r'\b(a+w+w+)\b', r'\b(o+o+p+s+)\b', r'\b(y+a+y+)\b', r'\b(w+h+e+w+)\b',
        r'\b(p+f+f+t+)\b', r'\b(e+e+k+)\b', r'\b(a+c+k+)\b', r'\b(h+m+p+h+)\b',
        r'\b(e+r+m+)\b', r'\b(w+e+l+l+)\b'
    ]
    
    for pattern in emotional_sounds:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            monospace_sections.append((match.start(), match.end(), match.group(1)))
    
    # Sort the sections by start position
    monospace_sections.sort(key=lambda x: x[0])
    
    # If no sections were found, return the original text
    if not monospace_sections:
        return text
    
    # Now we need to escape special characters required by MarkdownV2
    # The characters that need escaping are: _*[]()~`>#+-=|{}.!
    special_chars = r'_*[]()~`>#+-=|{}.!'
    escape_chars = lambda s: ''.join([f'\\{c}' if c in special_chars else c for c in s])
    
    # Build the resulting text with proper escaping and formatting
    result = ""
    last_end = 0
    
    for start, end, content in monospace_sections:
        # Add escaped text before this monospace section
        result += escape_chars(text[last_end:start])
        
        # Add the monospace section without escaping inside the backticks
        # For MarkdownV2, backticks themselves don't need to be escaped when they're used for code formatting
        result += f'`{content}`'
        
        last_end = end
    
    # Add any remaining text after the last monospace section
    if last_end < len(text):
        result += escape_chars(text[last_end:])
    
    return result

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle normal messages and generate a response from the character"""
    user_message = update.message.text
    user_id = update.effective_user.id
    
    # Check if user is in character creation mode
    # If the user is in the character creation process, don't process this message
    # The ConversationHandler should handle it instead
    if "character_creation" in context.user_data:
        logger.info(f"User {user_id} is in character creation mode, ignoring message in general handler")
        # Don't respond with character since the user is in creation mode
        return
    
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
        
        # Format emotional expressions in the response
        formatted_response = format_emotional_expressions(response)
        
        # Check if message is too long (Telegram limit is 4096 characters)
        if len(formatted_response) > 4000:  # Use 4000 as a safe limit
            # Split message into chunks of about 4000 characters
            # Try to split at sentence boundaries when possible
            chunks = []
            current_chunk = ""
            
            # First try to split at paragraph boundaries
            paragraphs = formatted_response.split('\n\n')
            for paragraph in paragraphs:
                if len(current_chunk) + len(paragraph) + 2 <= 4000:
                    if current_chunk:
                        current_chunk += '\n\n'
                    current_chunk += paragraph
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = paragraph
            
            if current_chunk:
                chunks.append(current_chunk)
            
            # Send each chunk
            for i, chunk in enumerate(chunks):
                try:
                    if formatted_response != response:
                        # Add a continuation indicator for multi-part messages
                        if i < len(chunks) - 1:
                            chunk += "\n\n\\.\\.\\."  # Escaped dots for MarkdownV2
                        if i > 0:
                            chunk = "\\.\\.\\.\n\n" + chunk  # Escaped dots for MarkdownV2
                        
                        await update.message.reply_text(chunk, parse_mode="MarkdownV2")
                    else:
                        # Add a continuation indicator for multi-part messages
                        if i < len(chunks) - 1:
                            chunk += "\n\n..."
                        if i > 0:
                            chunk = "...\n\n" + chunk
                            
                        await update.message.reply_text(chunk)
                except Exception as chunk_error:
                    logger.error(f"Error sending message chunk: {str(chunk_error)}")
                    # Try without markdown as fallback
                    try:
                        await update.message.reply_text(chunk.replace('`', ''))
                    except:
                        pass
        else:
            # Send the response with MarkdownV2 parsing mode if formatting was applied
            if formatted_response != response:
                try:
                    # Use Markdown for the formatted response
                    await update.message.reply_text(formatted_response, parse_mode="MarkdownV2")
                except Exception as markdown_error:
                    logger.error(f"Error sending formatted message: {str(markdown_error)}")
                    # Fallback to plain text if Markdown fails
                    await update.message.reply_text(response)
            else:
                # Send as plain text if no formatting was applied
                await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        await update.message.reply_text(
            f"Sorry, I couldn't generate a response from {character['name']} right now. Please try again later."
        )
