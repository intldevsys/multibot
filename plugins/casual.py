import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from services.llm_service import LLMService
from utils.helpers import (
    is_admin, message_tracker, check_rate_limit, 
    record_command_usage
)
from config import CHAT_HISTORY_DAYS

llm_service = LLMService()

# Store casual mode settings per chat
casual_mode_chats = {}  # chat_id -> {'enabled': bool, 'style': str, 'model': str}

@Client.on_message(filters.command("casual"))
async def toggle_casual_mode(client: Client, message: Message):
    """Toggle casual chat mode for the current chat"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Only admins can enable casual mode in groups
    if message.chat.type not in ["private", "bot"]:
        try:
            chat_member = await client.get_chat_member(chat_id, user_id)
            if chat_member.status not in ["administrator", "creator"] and not await is_admin(user_id):
                await message.reply_text(
                    "❌ Only group administrators can enable casual mode."
                )
                return
        except Exception as e:
            print(f"Error checking admin status: {e}")
            # If we can't check admin status, allow it (might be a private group)
            pass
    
    # Toggle casual mode
    if chat_id not in casual_mode_chats:
        casual_mode_chats[chat_id] = {'enabled': False, 'style': None, 'model': 'qwen'}
    
    current_mode = casual_mode_chats[chat_id]['enabled']
    
    if current_mode:
        # Disable casual mode
        casual_mode_chats[chat_id]['enabled'] = False
        await message.reply_text(
            "💤 **Casual mode disabled**\n\n"
            "I'll no longer participate in conversations automatically."
        )
    else:
        # Enable casual mode
        processing_msg = await message.reply_text(
            "🔄 **Analyzing chat history...**\n\n"
            f"Reading the last {CHAT_HISTORY_DAYS} days of messages to understand the conversational style."
        )
        
        try:
            # Get chat history for analysis
            chat_history = await client.db.get_chat_history(chat_id, CHAT_HISTORY_DAYS)
            
            if not chat_history:
                await processing_msg.edit_text(
                    "⚠️ **No chat history found**\n\n"
                    "I need some message history to analyze the chat style. "
                    "Send a few messages and try again, or I'll use a default friendly style."
                )
                style_analysis = "casual and friendly"
            else:
                # Analyze chat style
                style_analysis = await llm_service.analyze_chat_style(chat_history)
            
            # Enable casual mode
            casual_mode_chats[chat_id] = {
                'enabled': True, 
                'style': style_analysis,
                'model': 'qwen'
            }
            
            # Get user's preferred model
            user_model = 'qwen'
            
            await processing_msg.edit_text(
                "🤖 **Casual mode enabled!**\n\n"
                f"📊 **Chat Analysis:**\n{style_analysis[:200]}{'...' if len(style_analysis) > 200 else ''}\n\n"
                f"🧠 **AI Model:** {user_model}\n\n"
                "**How it works:**\n"
                "• Mention me with @gdsys_bot to start a conversation\n"
                "• I'll respond naturally for up to 20 messages\n"
                "• I'll occasionally join conversations based on context\n"
            )
            
        except Exception as e:
            await processing_msg.edit_text(
                f"❌ Error setting up casual mode: {str(e)}\n\n"
                "Using default settings."
            )
            casual_mode_chats[chat_id] = {
                'enabled': True, 
                'style': "casual and friendly",
                'model': 'qwen'
            }

@Client.on_message(filters.text & ~filters.command(['casual', 'start', 'help', 'search', 'searchall', 'usaid', 'news', 'tweets', 'llm', 'stats', 'ping', 'dialogs']))
async def handle_casual_chat(client: Client, message: Message):
    """Handle casual chat interactions"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # Skip if casual mode not enabled
    if chat_id not in casual_mode_chats or not casual_mode_chats[chat_id]['enabled']:
        # Still save chat history for potential future analysis
        if message.text and message.from_user:
            await client.db.save_chat_message(
                chat_id, 
                user_id, 
                message.text, 
                message.from_user.username
            )
        return
    
    # Save message to chat history
    if message.text and message.from_user:
        await client.db.save_chat_message(
            chat_id, 
            user_id, 
            message.text, 
            message.from_user.username
        )
    
    # Track user messages
    message_tracker.record_user_message(chat_id, user_id)
    
    # Check if bot is mentioned
    bot_mentioned = False
    if message.text:
        bot_mentions = ["@gdsys_bot", "gdsys", "bot"]
        bot_mentioned = any(mention.lower() in message.text.lower() for mention in bot_mentions)
    
    # Determine if bot should respond
    should_respond = False
    
    if bot_mentioned:
        should_respond = True
    else:
        # Check interaction limits
        if message_tracker.should_reset_interaction(chat_id, user_id):
            # User has reached 20 message limit, reset
            message_tracker.record_bot_message(chat_id)
            return
        
        # Random response based on chat activity
        messages_since_bot = message_tracker.get_messages_since_bot_reply(chat_id)
        activity_level = "high" if messages_since_bot < 5 else "normal" if messages_since_bot < 15 else "low"
        
        should_respond = await llm_service.should_respond(
            message.text or "", 
            False, 
            messages_since_bot,
            activity_level
        )
    
    if should_respond:
        try:
            # Get recent context
            recent_messages = await client.db.get_chat_history(chat_id, days=1)
            recent_context = recent_messages[-20:] if recent_messages else []
            
            # Get chat settings
            chat_settings = casual_mode_chats[chat_id]
            
            # Generate response
            response = await llm_service.generate_casual_response(
                message.text or "📷 [Media]",
                chat_settings['style'],
                recent_context,
                chat_settings['model']
            )
            
            if response:
                # Send response
                await message.reply_text(response)
                
                # Record bot message
                message_tracker.record_bot_message(chat_id)
                await client.db.save_chat_message(
                    chat_id, 
                    client.me.id, 
                    response, 
                    "gdsys_bot"
                )
        
        except Exception as e:
            print(f"Error in casual chat: {e}")
            # Don't send error messages in casual mode to avoid spam

@Client.on_message(filters.command("casual_status"))
async def casual_status(client: Client, message: Message):
    """Show casual mode status for current chat"""
    chat_id = message.chat.id
    
    if chat_id not in casual_mode_chats or not casual_mode_chats[chat_id]['enabled']:
        await message.reply_text("❌ Casual mode is currently disabled in this chat.")
        return
    
    settings = casual_mode_chats[chat_id]
    user_id = message.from_user.id
    
    # Get interaction stats
    interaction_count = message_tracker.get_user_interaction_count(chat_id, user_id)
    messages_since_bot = message_tracker.get_messages_since_bot_reply(chat_id)
    
    status_text = f"""
🤖 **Casual Mode Status**

✅ **Enabled** in this chat

🧠 **AI Model:** {settings['model']}
📊 **Your interactions:** {interaction_count}/20
💬 **Messages since my last reply:** {messages_since_bot}

**Style Analysis:**
{settings['style'][:300]}{'...' if len(settings['style']) > 300 else ''}

**Tip:** Mention @gdsys_bot to guarantee a response!
"""
    
    await message.reply_text(status_text)

@Client.on_message(filters.command("casual_reset"))
async def casual_reset(client: Client, message: Message):
    """Reset casual mode interactions (admin only)"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Check permissions
    if message.chat.type not in ["private", "bot"]:
        try:
            chat_member = await client.get_chat_member(chat_id, user_id)
            if chat_member.status not in ["administrator", "creator"] and not await is_admin(user_id):
                await message.reply_text("❌ Only administrators can reset casual mode.")
                return
        except Exception as e:
            print(f"Error checking admin status: {e}")
            # If we can't check admin status, allow it (might be a private group)
            pass
    
    # Reset interaction counters
    message_tracker.record_bot_message(chat_id)
    
    await message.reply_text(
        "🔄 **Casual mode interactions reset**\n\n"
        "All user interaction counters have been cleared."
    )