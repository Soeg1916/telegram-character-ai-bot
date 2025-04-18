import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)

from character_manager import CharacterManager
from conversation_handler import handle_message
from utils import (
    handle_error, list_characters, show_current_character, 
    reset_conversation, show_character_stats, create_character_start,
    process_character_creation, delete_character, cancel_creation,
    toggle_nsfw, SELECTING_NAME, ENTERING_DESCRIPTION, SELECTING_TRAITS
)

logger = logging.getLogger(__name__)

def setup_bot(token: str) -> Application:
    """Set up the Telegram bot with all handlers"""
    # Initialize the character manager
    character_manager = CharacterManager()
    
    # Create the Application instance
    application = Application.builder().token(token).build()
    
    # Add conversation handler for character creation
    creation_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("create", create_character_start)],
        states={
            SELECTING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_character_creation)],
            ENTERING_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_character_creation)],
            SELECTING_TRAITS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_character_creation)],
        },
        fallbacks=[CommandHandler("cancel", cancel_creation)],
    )
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("characters", list_characters))
    application.add_handler(CommandHandler("character", show_current_character))
    application.add_handler(CommandHandler("reset", reset_conversation))
    application.add_handler(CommandHandler("stats", show_character_stats))
    application.add_handler(CommandHandler("delete", delete_character))
    application.add_handler(CommandHandler("nsfw", toggle_nsfw))
    
    # Add conversation handler for character creation
    application.add_handler(creation_conv_handler)
    
    # Register callback query handler for inline buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Register message handler for general messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Register error handler
    application.add_error_handler(handle_error)
    
    return application

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message when the command /start is issued."""
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("Choose a Character", callback_data="show_characters")],
        [InlineKeyboardButton("Create Custom Character", callback_data="create_character")],
        [InlineKeyboardButton("Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Hello {user.first_name}! I'm a character-based chat bot powered by Mistral AI.\n\n"
        "I can take on the personality of various fictional characters and chat with you as them!\n\n"
        "Use /help to see all available commands, or tap a button below to get started:",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message when the command /help is issued."""
    help_text = (
        "🤖 *Character Chat Bot Help* 🤖\n\n"
        "*Available Commands:*\n"
        "/characters - List all available characters\n"
        "/character - Show your current character\n"
        "/create - Create a custom character\n"
        "/delete - Delete a custom character\n"
        "/reset - Reset conversation with current character\n"
        "/stats - Show character's mood and personality stats\n"
        "/nsfw - Toggle NSFW mode for current character\n"
        "/help - Show this help message\n\n"
        "*How to use:*\n"
        "1. Select a character using /characters\n"
        "2. Start chatting with them!\n"
        "3. The character will respond based on their personality.\n"
        "4. Their mood might change based on your conversation.\n\n"
        "*Custom Characters:*\n"
        "Create your own characters with /create\n"
        "You can set their name, background, and personality traits.\n\n"
        "*NSFW Mode:*\n"
        "Use /nsfw to toggle NSFW mode for your current character.\n"
        "NSFW mode allows more mature and adult-themed conversations."
    )
    
    keyboard = [
        [InlineKeyboardButton("Choose a Character", callback_data="show_characters")],
        [InlineKeyboardButton("Create Custom Character", callback_data="create_character")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callback queries"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "show_characters":
        # Create a new message instead of trying to update
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
                nsfw_mode = char.get("nsfw", False)
                button_text = f"{char['name']} {'🔞' if nsfw_mode else ''}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"select_character:{char_id}")])
        
        # Add custom characters
        if user_custom_characters:
            keyboard.append([InlineKeyboardButton("--- Your Custom Characters ---", callback_data="custom_header")])
            for char_id in user_custom_characters:
                if char_id in all_characters:
                    nsfw_mode = all_characters[char_id].get("nsfw", False)
                    button_text = f"{all_characters[char_id]['name']} {'🔞' if nsfw_mode else ''}"
                    keyboard.append([InlineKeyboardButton(
                        button_text, 
                        callback_data=f"select_character:{char_id}"
                    )])
        
        # Add button to create a new character
        keyboard.append([InlineKeyboardButton("Create New Character", callback_data="create_character")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Choose a character to chat with:",
            reply_markup=reply_markup
        )
    elif query.data == "create_character":
        # Send a new message to start character creation
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Let's create a custom character! 🎭\n\n"
            "First, what's the name of your character?\n"
            "Send me the name or use /cancel to stop the creation process."
        )
        
        # Initialize character creation state
        context.user_data["character_creation"] = {"step": "name"}
        
        # Set conversation state
        context.user_data["state"] = SELECTING_NAME
    elif query.data == "help":
        help_text = (
            "🤖 *Character Chat Bot Help* 🤖\n\n"
            "*Available Commands:*\n"
            "/characters - List all available characters\n"
            "/character - Show your current character\n"
            "/create - Create a custom character\n"
            "/delete - Delete a custom character\n"
            "/reset - Reset conversation with current character\n"
            "/stats - Show character's mood and personality stats\n"
            "/nsfw - Toggle NSFW mode for current character\n"
            "/help - Show this help message\n\n"
            "*How to use:*\n"
            "1. Select a character using /characters\n"
            "2. Start chatting with them!\n"
            "3. The character will respond based on their personality.\n"
            "4. Their mood might change based on your conversation.\n\n"
            "*Custom Characters:*\n"
            "Create your own characters with /create\n"
            "You can set their name, background, and personality traits.\n\n"
            "*NSFW Mode:*\n"
            "Use /nsfw to toggle NSFW mode for your current character.\n"
            "NSFW mode allows more mature and adult-themed conversations."
        )
        
        keyboard = [
            [InlineKeyboardButton("Choose a Character", callback_data="show_characters")],
            [InlineKeyboardButton("Create Custom Character", callback_data="create_character")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=help_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    elif query.data.startswith("select_character:"):
        character_id = query.data.split(":")[1]
        # Set the selected character for the user
        if not context.user_data.get("selected_character"):
            context.user_data["selected_character"] = {}
        context.user_data["selected_character"] = character_id
        
        # Get character details from character manager
        character_manager = CharacterManager()
        character = character_manager.get_character(character_id)
        character_manager.set_user_selected_character(update.effective_user.id, character_id)
        
        # Show NSFW status
        nsfw_mode = character.get("nsfw", False)
        
        await query.edit_message_text(
            f"You are now chatting with *{character['name']}*!\n\n"
            f"{character['description']}\n\n"
            f"NSFW mode: {'Enabled' if nsfw_mode else 'Disabled'}\n\n"
            "Start chatting now! You can reset the conversation anytime with /reset",
            parse_mode="Markdown"
        )
