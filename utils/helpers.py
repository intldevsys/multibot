import asyncio
import os
from typing import Dict, List
from datetime import datetime, timedelta
from config import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW, ADMINS, MAX_RESULTS_NON_ADMIN

async def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    return user_id in ADMINS

async def check_rate_limit(db, user_id: int, command: str) -> bool:
    """Check if user has exceeded rate limit"""
    if await is_admin(user_id):
        return True  # Admins have no rate limits
    
    return await db.check_rate_limit(user_id, command, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW)

async def record_command_usage(db, user_id: int, command: str):
    """Record command usage for rate limiting"""
    if not await is_admin(user_id):
        await db.record_request(user_id, command)

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"

def truncate_text(text: str, max_length: int = 4000) -> str:
    """Truncate text to fit Telegram message limits"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

async def create_results_file(content: str, filename: str = None) -> str:
    """Create a file with results content"""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results_{timestamp}.txt"
    
    filepath = os.path.join("downloads", filename)
    os.makedirs("downloads", exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return filepath

def get_max_results(user_id: int, user_specified: int = None) -> int:
    """Get maximum results based on user specification with 200 limit for all users"""
    if user_specified is not None:
        # User specified amount, but cap at 200
        return min(user_specified, 200)
    
    # Default amounts if not specified
    if user_id in ADMINS:
        return 50  # Admin default
    return MAX_RESULTS_NON_ADMIN  # Non-admin default (10)

def parse_search_terms(query: str) -> List[str]:
    """Parse comma-separated search terms"""
    return [term.strip() for term in query.split(',') if term.strip()]

def parse_search_command(command_text: str) -> tuple:
    """Parse search command to extract terms and optional result count
    
    Examples:
    - "/search bitcoin" -> (["bitcoin"], None)
    - "/search bitcoin,crypto" -> (["bitcoin", "crypto"], None) 
    - "/search bitcoin 50" -> (["bitcoin"], 50)
    - "/search bitcoin,crypto 100" -> (["bitcoin", "crypto"], 100)
    """
    try:
        # Remove command name
        parts = command_text.split(' ', 1)[1].strip()
        
        # Check if last part is a number
        words = parts.split()
        result_count = None
        
        if len(words) > 1 and words[-1].isdigit():
            result_count = int(words[-1])
            # Remove the number from the search terms
            search_query = ' '.join(words[:-1])
        else:
            search_query = parts
        
        # Parse search terms
        search_terms = parse_search_terms(search_query)
        
        return search_terms, result_count
        
    except (IndexError, ValueError):
        return [], None

def parse_usaid_command(command_text: str) -> tuple:
    """Parse usaid command to extract username, terms, and optional result count
    
    Examples:
    - "/usaid @john bitcoin" -> ("john", ["bitcoin"], None)
    - "/usaid @john bitcoin,crypto" -> ("john", ["bitcoin", "crypto"], None)
    - "/usaid @john bitcoin 50" -> ("john", ["bitcoin"], 50)
    - "/usaid @john bitcoin,crypto 100" -> ("john", ["bitcoin", "crypto"], 100)
    """
    try:
        # Remove command name
        args = command_text.split(' ', 1)[1].strip()
        
        # Split into username and rest
        if ' ' not in args:
            return None, [], None
        
        username, rest = args.split(' ', 1)
        
        # Check if last part is a number
        words = rest.split()
        result_count = None
        
        if len(words) > 1 and words[-1].isdigit():
            result_count = int(words[-1])
            # Remove the number from the search terms
            search_query = ' '.join(words[:-1])
        else:
            search_query = rest
        
        # Parse search terms
        search_terms = parse_search_terms(search_query)
        
        return username.lstrip('@'), search_terms, result_count
        
    except (IndexError, ValueError):
        return None, [], None

def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file creation"""
    import re
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit length
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:90] + ext
    return filename

async def send_long_message(client, chat_id: int, text: str, max_length: int = 4000):
    """Send long message by splitting it into chunks"""
    if len(text) <= max_length:
        await client.send_message(chat_id, text)
        return
    
    # Split text into chunks
    chunks = []
    current_chunk = ""
    
    for line in text.split('\n'):
        if len(current_chunk) + len(line) + 1 > max_length:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = line
        else:
            if current_chunk:
                current_chunk += '\n' + line
            else:
                current_chunk = line
    
    if current_chunk:
        chunks.append(current_chunk)
    
    # Send chunks
    for i, chunk in enumerate(chunks):
        if i > 0:
            await asyncio.sleep(1)  # Small delay between messages
        await client.send_message(chat_id, chunk)

class MessageTracker:
    """Track bot interactions in chats"""
    def __init__(self):
        self.interactions = {}  # chat_id -> {user_id: message_count}
        self.last_bot_message = {}  # chat_id -> timestamp
        self.message_counts = {}  # chat_id -> count since last bot message
    
    def record_user_message(self, chat_id: int, user_id: int):
        """Record a user message"""
        if chat_id not in self.interactions:
            self.interactions[chat_id] = {}
        
        self.interactions[chat_id][user_id] = self.interactions[chat_id].get(user_id, 0) + 1
        
        # Increment message count since last bot message
        self.message_counts[chat_id] = self.message_counts.get(chat_id, 0) + 1
    
    def record_bot_message(self, chat_id: int):
        """Record a bot message"""
        self.last_bot_message[chat_id] = datetime.now()
        self.message_counts[chat_id] = 0
        
        # Reset user interaction counts
        if chat_id in self.interactions:
            self.interactions[chat_id] = {}
    
    def get_user_interaction_count(self, chat_id: int, user_id: int) -> int:
        """Get user's message count in current interaction"""
        return self.interactions.get(chat_id, {}).get(user_id, 0)
    
    def get_messages_since_bot_reply(self, chat_id: int) -> int:
        """Get number of messages since last bot reply"""
        return self.message_counts.get(chat_id, 0)
    
    def should_reset_interaction(self, chat_id: int, user_id: int) -> bool:
        """Check if interaction should be reset (20 message limit)"""
        from config import MAX_INTERACTION_MESSAGES
        return self.get_user_interaction_count(chat_id, user_id) >= MAX_INTERACTION_MESSAGES

# Global message tracker instance
message_tracker = MessageTracker()