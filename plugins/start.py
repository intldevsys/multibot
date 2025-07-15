from pyrogram import Client, filters
from pyrogram.types import Message
from database.database import Database
from utils.helpers import is_admin

@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Add user to database
    await client.db.add_user(user_id, username, first_name)
    
    if message.chat.type == "private":
        # Private chat - detailed welcome message
        welcome_text = f"""
🤖 **Welcome to GdSys Bot, {first_name}!**

I'm your advanced Telegram assistant with the following capabilities:

📡 **Search & Crawl:**
• Scan rooms/channels for specific terms
• Export results to files

💬 **Casual Chat:**
• `/casual` - Turn on conversational mode
• I'll analyze chat history and match the group's style

🔍 **User Search:**
• `/usaid @username search,terms` - Find user's messages

📰 **News & Information:**
• `/news query` - Get latest news headlines
• Crypto prices and market data

🐦 **Social Media:**
• `/tweets @username` or `/tweets keyword` - X/Twitter search

⚙️ **Admin Commands:**
• `/llm list` - View available AI models
• `/llm set model_name` - Choose AI model

**Rate Limits:**
- Non-admins: 3 searches per day
- Admins: Unlimited access

Type `/help` for detailed command information!
"""
    else:
        # Group chat - brief introduction
        welcome_text = f"""
👋 **Hi! I'm GdSys Bot**

I'm now active in this group with these features:

🔍 **Search**: `/search term` - Find messages in chat
💬 **AI Chat**: `/casual` - Enable conversational mode  
📰 **News**: `/news query` - Get news articles
📊 **Crypto**: `/crypto BTC` - Get crypto prices
🐦 **Tweets**: `/tweets @user` - Get Twitter content

Use `/help` for the complete command list.

**Admin note:** Use `/casual` to enable AI chat mode where I'll participate in conversations naturally.
"""
    
    await message.reply_text(welcome_text)

@Client.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    """Handle /help command"""
    help_text = """
🆘 **GdSys Bot - Command Help**

**🔍 Search Commands:**
• `/search terms,here` - Search current chat for terms
• `/searchall terms,here` - Search all accessible chats
• `/usaid @username term1,term2` - Search user's messages

**📰 News Commands:**
• `/news bitcoin` - Get Bitcoin-related news
• `/news "stock market"` - Get stock market news
• `/news ethereum price` - Crypto price + news

**🐦 Social Media:**
• `/tweets @elonmusk` - Get user's recent tweets  
• `/tweets bitcoin` - Search tweets about Bitcoin

**💬 Chat Features:**
• `/casual` - Enable conversational AI mode
• Bot analyzes 20 days of chat history
• Responds naturally for 20 messages when mentioned

**⚙️ Settings (Admins only):**
• `/llm list` - Show available AI models
• `/llm set claude` - Set AI model (claude/gpt/cohere/gemini)
• `/stats` - Show bot statistics

**📊 Rate Limits:**
- Regular users: 3 info commands per day
- Admins: Unlimited access
- All results over 10 lines saved as text files

**💡 Tips:**
- Use quotes for multi-word searches
- Separate multiple terms with commas
- Results are automatically saved for large datasets
- Bot works in groups and private chats
"""
    
    await message.reply_text(help_text)

@Client.on_message(filters.command("stats"))
async def stats_command(client: Client, message: Message):
    """Handle /stats command (admin only)"""
    user_id = message.from_user.id
    
    if not await is_admin(user_id):
        await message.reply_text("❌ This command is only available to administrators.")
        return
    
    try:
        # Get database statistics
        total_users = len(await client.db.get_all_users())
        
        # Get recent activity
        from datetime import datetime, timedelta
        recent_searches = await client.db.search_results.count_documents({
            "timestamp": {"$gte": datetime.utcnow() - timedelta(days=7)}
        })
        
        stats_text = f"""
📊 **Bot Statistics**

👥 **Users:** {total_users} total users
🔍 **Activity:** {recent_searches} searches this week

**Database Collections:**
• Users: {total_users}
• Rate Limits: Active tracking
• Chat History: Stored for casual mode
• Search Results: Cached for performance

**Features Status:**
✅ Telegram Scanning
✅ News APIs 
✅ Twitter Integration
✅ LLM Chat Mode
✅ Rate Limiting
✅ File Export

**Uptime:** Since bot restart
"""
        
        await message.reply_text(stats_text)
        
    except Exception as e:
        await message.reply_text(f"❌ Error getting statistics: {str(e)}")

@Client.on_message(filters.command("ping"))
async def ping_command(client: Client, message: Message):
    """Handle /ping command"""
    await message.reply_text("🏓 Pong! Bot is running normally.")

@Client.on_message(filters.private & ~filters.command(['start', 'help', 'stats', 'ping', 'casual', 'casual_status', 'casual_reset', 'search', 'searchall', 'usaid', 'dialogs', 'news', 'crypto', 'tweets', 'llm']))
async def handle_private_message(client: Client, message: Message):
    """Handle private messages that aren't commands"""
    await message.reply_text(
        "👋 Hello! I'm GdSys Bot. Use /start to see my capabilities or /help for command details."
    )