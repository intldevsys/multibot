import asyncio
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import ChannelPrivate, ChatAdminRequired, UsernameNotOccupied
import aiofiles
from config import API_ID, API_HASH, DOWNLOADS_PATH

class TelegramScanner:
    def __init__(self, session_name: str = "scanner_session"):
        self.client = Client(
            session_name,
            api_id=API_ID,
            api_hash=API_HASH
        )
        self.is_connected = False

    async def connect(self):
        """Connect to Telegram"""
        if not self.is_connected:
            await self.client.start()
            self.is_connected = True

    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.is_connected:
            await self.client.stop()
            self.is_connected = False

    async def get_dialogs(self) -> List[Dict]:
        """Get all available chats/channels/groups"""
        await self.connect()
        dialogs = []
        
        async for dialog in self.client.get_dialogs():
            chat_info = {
                "id": dialog.chat.id,
                "title": dialog.chat.title or dialog.chat.first_name or "Unknown",
                "type": dialog.chat.type.value,
                "username": dialog.chat.username,
                "member_count": getattr(dialog.chat, 'members_count', 0)
            }
            dialogs.append(chat_info)
        
        return dialogs

    async def search_in_chat(self, chat_id: int, search_terms: List[str], limit: int = 1000) -> List[Dict]:
        """Search for messages containing specific terms in a chat"""
        await self.connect()
        results = []
        
        try:
            # Compile regex patterns for each search term
            patterns = [re.compile(term, re.IGNORECASE) for term in search_terms]
            
            message_count = 0
            async for message in self.client.get_chat_history(chat_id, limit=limit):
                if message_count >= limit:
                    break
                    
                message_count += 1
                
                if message.text:
                    # Check if any search term matches
                    for i, pattern in enumerate(patterns):
                        if pattern.search(message.text):
                            result = {
                                "message_id": message.id,
                                "chat_id": chat_id,
                                "user_id": message.from_user.id if message.from_user else None,
                                "username": message.from_user.username if message.from_user else None,
                                "first_name": message.from_user.first_name if message.from_user else None,
                                "text": message.text,
                                "date": message.date.isoformat(),
                                "matched_term": search_terms[i],
                                "message_link": f"https://t.me/c/{str(chat_id)[4:]}/{message.id}" if chat_id < 0 else None
                            }
                            results.append(result)
                            break  # Don't duplicate results for multiple matches in same message
                            
        except ChannelPrivate:
            raise Exception(f"Chat {chat_id} is private or bot doesn't have access")
        except ChatAdminRequired:
            raise Exception(f"Admin rights required for chat {chat_id}")
        except Exception as e:
            raise Exception(f"Error searching in chat {chat_id}: {str(e)}")
        
        return results

    async def search_across_all_chats(self, search_terms: List[str], max_results: int = 100) -> Dict:
        """Search for terms across all accessible chats"""
        await self.connect()
        all_results = []
        chat_summary = {}
        
        dialogs = await self.get_dialogs()
        
        for dialog in dialogs:
            try:
                chat_results = await self.search_in_chat(
                    dialog["id"], 
                    search_terms, 
                    limit=200  # Limit per chat to avoid overwhelming
                )
                
                if chat_results:
                    chat_summary[dialog["title"]] = {
                        "chat_id": dialog["id"],
                        "chat_type": dialog["type"],
                        "results_count": len(chat_results),
                        "username": dialog["username"]
                    }
                    all_results.extend(chat_results)
                    
                    # Break if we have enough results
                    if len(all_results) >= max_results:
                        break
                        
            except Exception as e:
                # Log error but continue with other chats
                print(f"Error searching in {dialog['title']}: {str(e)}")
                continue
        
        # Sort results by date (newest first)
        all_results.sort(key=lambda x: x["date"], reverse=True)
        
        return {
            "results": all_results[:max_results],
            "total_found": len(all_results),
            "searched_chats": len(dialogs),
            "chat_summary": chat_summary
        }

    async def search_user_in_chats(self, username: str, search_terms: List[str], max_results: int = 100) -> Dict:
        """Search for specific user's messages containing search terms"""
        await self.connect()
        all_results = []
        chat_summary = {}
        
        # Remove @ if present
        username = username.lstrip('@')
        
        dialogs = await self.get_dialogs()
        
        for dialog in dialogs:
            try:
                chat_results = await self.search_in_chat(dialog["id"], search_terms, limit=500)
                
                # Filter results by username
                user_results = [
                    result for result in chat_results 
                    if result["username"] and result["username"].lower() == username.lower()
                ]
                
                if user_results:
                    chat_summary[dialog["title"]] = {
                        "chat_id": dialog["id"],
                        "chat_type": dialog["type"],
                        "results_count": len(user_results),
                        "username": dialog["username"]
                    }
                    all_results.extend(user_results)
                    
                    if len(all_results) >= max_results:
                        break
                        
            except Exception as e:
                continue
        
        all_results.sort(key=lambda x: x["date"], reverse=True)
        
        return {
            "results": all_results[:max_results],
            "total_found": len(all_results),
            "searched_chats": len(dialogs),
            "chat_summary": chat_summary,
            "target_username": username
        }

    async def export_results_to_file(self, results: Dict, filename: str = None) -> str:
        """Export search results to a text file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"search_results_{timestamp}.txt"
        
        filepath = os.path.join(DOWNLOADS_PATH, filename)
        
        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write("TELEGRAM SEARCH RESULTS\n")
            await f.write("=" * 50 + "\n\n")
            
            if "target_username" in results:
                await f.write(f"Searched for user: @{results['target_username']}\n")
            
            await f.write(f"Search completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            await f.write(f"Total results found: {results['total_found']}\n")
            await f.write(f"Chats searched: {results['searched_chats']}\n\n")
            
            # Chat summary
            if results['chat_summary']:
                await f.write("CHAT SUMMARY:\n")
                await f.write("-" * 30 + "\n")
                for chat_title, info in results['chat_summary'].items():
                    await f.write(f"📁 {chat_title}: {info['results_count']} results\n")
                await f.write("\n")
            
            # Detailed results
            await f.write("DETAILED RESULTS:\n")
            await f.write("-" * 30 + "\n")
            
            for i, result in enumerate(results['results'], 1):
                await f.write(f"\n{i}. Message ID: {result['message_id']}\n")
                await f.write(f"   Date: {result['date']}\n")
                await f.write(f"   User: {result['first_name'] or 'Unknown'}")
                if result['username']:
                    await f.write(f" (@{result['username']})")
                await f.write(f"\n   Matched term: {result['matched_term']}\n")
                await f.write(f"   Text: {result['text'][:500]}{'...' if len(result['text']) > 500 else ''}\n")
                if result['message_link']:
                    await f.write(f"   Link: {result['message_link']}\n")
                await f.write("-" * 50 + "\n")
        
        return filepath

    async def get_chat_members(self, chat_id: int, limit: int = 1000) -> List[Dict]:
        """Get members of a chat/channel"""
        await self.connect()
        members = []
        
        try:
            async for member in self.client.get_chat_members(chat_id, limit=limit):
                member_info = {
                    "user_id": member.user.id,
                    "username": member.user.username,
                    "first_name": member.user.first_name,
                    "last_name": member.user.last_name,
                    "status": member.status.value if member.status else "unknown"
                }
                members.append(member_info)
        except Exception as e:
            raise Exception(f"Error getting members for chat {chat_id}: {str(e)}")
        
        return members