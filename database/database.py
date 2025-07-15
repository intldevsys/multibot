import motor.motor_asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from config import DATABASE_URI, DATABASE_NAME

class Database:
    def __init__(self):
        self.client = None
        self.db = None

    async def connect(self):
        """Connect to MongoDB database"""
        self.client = motor.motor_asyncio.AsyncIOMotorClient(DATABASE_URI)
        self.db = self.client[DATABASE_NAME]
        
        # Create indexes
        await self.db.users.create_index("user_id", unique=True)
        await self.db.rate_limits.create_index([("user_id", 1), ("command", 1)])
        await self.db.chat_history.create_index([("chat_id", 1), ("timestamp", 1)])
        
    async def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()

    # User Management
    async def add_user(self, user_id: int, username: str = None, first_name: str = None):
        """Add a new user to the database"""
        user_data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "joined_date": datetime.utcnow(),
            "is_active": True
        }
        try:
            await self.db.users.insert_one(user_data)
        except:
            # User already exists, update info
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": {"username": username, "first_name": first_name, "is_active": True}}
            )

    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user information"""
        return await self.db.users.find_one({"user_id": user_id})

    async def is_user_exists(self, user_id: int) -> bool:
        """Check if user exists in database"""
        user = await self.db.users.find_one({"user_id": user_id})
        return user is not None

    async def get_all_users(self) -> List[Dict]:
        """Get all users from database"""
        users = []
        async for user in self.db.users.find({"is_active": True}):
            users.append(user)
        return users

    # Rate Limiting
    async def check_rate_limit(self, user_id: int, command: str, limit: int, window: int) -> bool:
        """Check if user has exceeded rate limit"""
        cutoff_time = datetime.utcnow() - timedelta(seconds=window)
        
        # Count recent requests
        count = await self.db.rate_limits.count_documents({
            "user_id": user_id,
            "command": command,
            "timestamp": {"$gte": cutoff_time}
        })
        
        return count < limit

    async def record_request(self, user_id: int, command: str):
        """Record a new request for rate limiting"""
        await self.db.rate_limits.insert_one({
            "user_id": user_id,
            "command": command,
            "timestamp": datetime.utcnow()
        })

    async def cleanup_old_rate_limits(self, hours: int = 24):
        """Clean up old rate limit records"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        await self.db.rate_limits.delete_many({"timestamp": {"$lt": cutoff_time}})

    # Chat History
    async def save_chat_message(self, chat_id: int, user_id: int, message_text: str, username: str = None):
        """Save chat message for analysis"""
        await self.db.chat_history.insert_one({
            "chat_id": chat_id,
            "user_id": user_id,
            "username": username,
            "message_text": message_text,
            "timestamp": datetime.utcnow()
        })

    async def get_chat_history(self, chat_id: int, days: int = 20) -> List[Dict]:
        """Get chat history for the specified number of days"""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        messages = []
        
        async for message in self.db.chat_history.find({
            "chat_id": chat_id,
            "timestamp": {"$gte": cutoff_time}
        }).sort("timestamp", 1):
            messages.append(message)
        
        return messages

    async def cleanup_old_chat_history(self, days: int = 30):
        """Clean up old chat history"""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        await self.db.chat_history.delete_many({"timestamp": {"$lt": cutoff_time}})

    # Search Results Storage
    async def save_search_result(self, user_id: int, query: str, results: List[Dict], search_type: str):
        """Save search results"""
        await self.db.search_results.insert_one({
            "user_id": user_id,
            "query": query,
            "results": results,
            "search_type": search_type,
            "timestamp": datetime.utcnow()
        })

    async def get_search_history(self, user_id: int, search_type: str = None) -> List[Dict]:
        """Get user's search history"""
        query = {"user_id": user_id}
        if search_type:
            query["search_type"] = search_type
            
        searches = []
        async for search in self.db.search_results.find(query).sort("timestamp", -1).limit(10):
            searches.append(search)
        
        return searches

    # LLM Settings
    async def set_user_llm_model(self, user_id: int, model: str):
        """Set user's preferred LLM model"""
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"preferred_llm": model}}
        )

    async def get_user_llm_model(self, user_id: int) -> str:
        """Get user's preferred LLM model"""
        user = await self.db.users.find_one({"user_id": user_id})
        return user.get("preferred_llm", "qwen") if user else "qwen"