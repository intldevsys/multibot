import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from services.telegram_scanner import TelegramScanner
from utils.helpers import (
    check_rate_limit, record_command_usage, is_admin,
    get_max_results, parse_search_command, parse_usaid_command, create_results_file,
    truncate_text, send_long_message
)

scanner = TelegramScanner()

@Client.on_message(filters.command("search"))
async def search_current_chat(client: Client, message: Message):
    """Search current chat for specified terms"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Check rate limit
    if not await check_rate_limit(client.db, user_id, "search"):
        await message.reply_text(
            "⏰ You've reached your daily search limit (3 searches per day). "
            "Try again tomorrow or contact an admin for unlimited access."
        )
        return
    
    # Parse command
    search_terms, result_count = parse_search_command(message.text)
    
    if not search_terms:
        await message.reply_text(
            "❌ Please provide search terms.\n"
            "Usage: `/search term1,term2,term3 [count]`\n"
            "Examples:\n"
            "• `/search bitcoin,crypto,price`\n"
            "• `/search bitcoin 50` (limit to 50 results)\n"
            "• `/search bitcoin,crypto 100` (limit to 100 results)"
        )
        return
    
    # Record usage
    await record_command_usage(client.db, user_id, "search")
    
    # Send processing message
    processing_msg = await message.reply_text("🔍 Searching current chat...")
    
    try:
        # Search in current chat
        results = await scanner.search_in_chat(
            chat_id, 
            search_terms, 
            limit=1000
        )
        
        if not results:
            await processing_msg.edit_text(
                f"🔍 **Search Results**\n\n"
                f"No messages found containing: {', '.join(search_terms)}"
            )
            return
        
        # Get max results based on user specification
        max_results = get_max_results(user_id, result_count)
        
        # Sort results by date (most recent first) and limit to max_results
        results.sort(key=lambda x: x.get('date', ''), reverse=True)
        display_results = results[:max_results]
        
        # Format results
        result_text = f"🔍 **Search Results**\n\n"
        result_text += f"**Terms:** {', '.join(search_terms)}\n"
        result_text += f"**Found:** {len(results)} messages\n"
        result_text += f"**Showing:** {len(display_results)} results\n\n"
        
        for i, result in enumerate(display_results[:10], 1):
            username = result['username'] or result['first_name'] or 'Unknown'
            text_preview = result['text'][:100] + ('...' if len(result['text']) > 100 else '')
            
            result_text += f"{i}. **@{username}** ({result['date'][:10]})\n"
            result_text += f"   {text_preview}\n"
            result_text += f"   *Matched: {result['matched_term']}*\n\n"
        
        # If many results, create file
        if len(results) > 10 or await is_admin(user_id):
            search_data = {
                'results': results,
                'total_found': len(results),
                'searched_chats': 1,
                'chat_summary': {message.chat.title or 'Current Chat': {
                    'chat_id': chat_id,
                    'results_count': len(results)
                }}
            }
            
            filename = f"search_{chat_id}_{message.date.strftime('%Y%m%d_%H%M%S')}.txt"
            filepath = await scanner.export_results_to_file(search_data, filename)
            
            result_text += f"\n📎 **Full results attached as file** ({len(results)} total)"
            
            await processing_msg.delete()
            await message.reply_text(result_text)
            await message.reply_document(filepath, caption="Complete search results")
            
            # Clean up file
            try:
                os.remove(filepath)
            except:
                pass
        else:
            await processing_msg.edit_text(result_text)
        
        # Save search to database
        await client.db.save_search_result(
            user_id, 
            ' '.join(search_terms), 
            display_results[:50],  # Store limited results
            "chat_search"
        )
        
    except Exception as e:
        await processing_msg.edit_text(f"❌ Error during search: {str(e)}")

@Client.on_message(filters.command("searchall"))
async def search_all_chats(client: Client, message: Message):
    """Search all accessible chats for specified terms"""
    user_id = message.from_user.id
    
    # Check rate limit
    if not await check_rate_limit(client.db, user_id, "searchall"):
        await message.reply_text(
            "⏰ You've reached your daily search limit (3 searches per day). "
            "Try again tomorrow or contact an admin for unlimited access."
        )
        return
    
    # Parse command
    search_terms, result_count = parse_search_command(message.text)
    
    if not search_terms:
        await message.reply_text(
            "❌ Please provide search terms.\n"
            "Usage: `/searchall term1,term2,term3 [count]`\n"
            "Examples:\n"
            "• `/searchall bitcoin,crypto,ethereum`\n"
            "• `/searchall bitcoin 100` (limit to 100 results)"
        )
        return
    
    # Record usage
    await record_command_usage(client.db, user_id, "searchall")
    
    # Send processing message
    processing_msg = await message.reply_text(
        "🔍 Searching across all accessible chats...\n"
        "This may take a few minutes depending on the number of chats."
    )
    
    try:
        # Get max results with user specification
        max_results = get_max_results(user_id, result_count)
        
        # Search across all chats (get more than needed for sorting)
        search_data = await scanner.search_across_all_chats(search_terms, 200)
        
        results = search_data['results']
        
        # Sort results by date (most recent first) and limit to max_results
        results.sort(key=lambda x: x.get('date', ''), reverse=True)
        display_results = results[:max_results]
        
        if not results:
            await processing_msg.edit_text(
                f"🔍 **Global Search Results**\n\n"
                f"No messages found containing: {', '.join(search_terms)}\n"
                f"Searched {search_data['searched_chats']} chats"
            )
            return
        
        # Format summary
        result_text = f"🔍 **Global Search Results**\n\n"
        result_text += f"**Terms:** {', '.join(search_terms)}\n"
        result_text += f"**Found:** {search_data['total_found']} messages\n"
        result_text += f"**Searched:** {search_data['searched_chats']} chats\n"
        result_text += f"**Showing:** {min(len(display_results), 10)} results\n\n"
        
        # Show top results
        for i, result in enumerate(display_results[:10], 1):
            username = result['username'] or result['first_name'] or 'Unknown'
            text_preview = result['text'][:80] + ('...' if len(result['text']) > 80 else '')
            
            result_text += f"{i}. **@{username}** ({result['date'][:10]})\n"
            result_text += f"   {text_preview}\n"
            result_text += f"   *Matched: {result['matched_term']}*\n\n"
        
        # Chat summary
        if search_data['chat_summary']:
            result_text += "**📊 Chats with Results:**\n"
            for chat_name, info in list(search_data['chat_summary'].items())[:5]:
                result_text += f"• {chat_name}: {info['results_count']} matches\n"
        
        # Create detailed file with sorted results
        filename = f"global_search_{message.date.strftime('%Y%m%d_%H%M%S')}.txt"
        sorted_search_data = {
            'results': display_results,
            'total_found': search_data['total_found'],
            'searched_chats': search_data['searched_chats'],
            'chat_summary': search_data['chat_summary']
        }
        filepath = await scanner.export_results_to_file(sorted_search_data, filename)
        
        result_text += f"\n📎 **Complete results in attached file**"
        
        await processing_msg.delete()
        await message.reply_text(result_text)
        await message.reply_document(filepath, caption=f"Global search results for: {', '.join(search_terms)}")
        
        # Clean up file
        try:
            os.remove(filepath)
        except:
            pass
        
        # Save search to database
        await client.db.save_search_result(
            user_id, 
            ' '.join(search_terms), 
            display_results[:50],
            "global_search"
        )
        
    except Exception as e:
        await processing_msg.edit_text(f"❌ Error during global search: {str(e)}")

@Client.on_message(filters.command("usaid"))
async def search_user_messages(client: Client, message: Message):
    """Search for specific user's messages containing search terms"""
    user_id = message.from_user.id
    
    # Check rate limit
    if not await check_rate_limit(client.db, user_id, "usaid"):
        await message.reply_text(
            "⏰ You've reached your daily search limit (3 searches per day). "
            "Try again tomorrow or contact an admin for unlimited access."
        )
        return
    
    # Parse command
    username, search_terms, result_count = parse_usaid_command(message.text)
    
    if not username or not search_terms:
        await message.reply_text(
            "❌ Invalid format.\n"
            "Usage: `/usaid @username search,terms [count]`\n"
            "Examples:\n"
            "• `/usaid @john bitcoin,crypto,price`\n"
            "• `/usaid @john bitcoin 50` (limit to 50 results)"
        )
        return
    
    # Record usage
    await record_command_usage(client.db, user_id, "usaid")
    
    # Send processing message
    processing_msg = await message.reply_text(
        f"🔍 Searching for @{username.lstrip('@')}'s messages...\n"
        "This may take a few minutes."
    )
    
    try:
        # Get max results with user specification
        max_results = get_max_results(user_id, result_count)
        
        # Search for user's messages (get more for sorting)
        search_data = await scanner.search_user_in_chats(username, search_terms, 200)
        
        results = search_data['results']
        
        # Sort results by date (most recent first) and limit to max_results
        results.sort(key=lambda x: x.get('date', ''), reverse=True)
        display_results = results[:max_results]
        
        if not results:
            await processing_msg.edit_text(
                f"🔍 **User Search Results**\n\n"
                f"No messages found from @{search_data['target_username']} "
                f"containing: {', '.join(search_terms)}\n"
                f"Searched {search_data['searched_chats']} chats"
            )
            return
        
        # Format results
        result_text = f"🔍 **User Search Results**\n\n"
        result_text += f"**User:** @{search_data['target_username']}\n"
        result_text += f"**Terms:** {', '.join(search_terms)}\n"
        result_text += f"**Found:** {search_data['total_found']} messages\n"
        result_text += f"**Searched:** {search_data['searched_chats']} chats\n"
        result_text += f"**Showing:** {min(len(display_results), 10)} results\n\n"
        
        # Show results
        for i, result in enumerate(display_results[:10], 1):
            text_preview = result['text'][:100] + ('...' if len(result['text']) > 100 else '')
            
            result_text += f"{i}. **{result['date'][:10]}**\n"
            result_text += f"   {text_preview}\n"
            result_text += f"   *Matched: {result['matched_term']}*\n\n"
        
        # Create file for complete results
        if len(display_results) > 10:
            filename = f"user_search_{search_data['target_username']}_{message.date.strftime('%Y%m%d_%H%M%S')}.txt"
            sorted_search_data = {
                'results': display_results,
                'total_found': search_data['total_found'],
                'searched_chats': search_data['searched_chats'],
                'chat_summary': search_data['chat_summary'],
                'target_username': search_data['target_username']
            }
            filepath = await scanner.export_results_to_file(sorted_search_data, filename)
            
            result_text += f"\n📎 **Complete results in attached file**"
            
            await processing_msg.delete()
            await message.reply_text(result_text)
            await message.reply_document(
                filepath, 
                caption=f"@{search_data['target_username']}'s messages containing: {', '.join(search_terms)}"
            )
            
            # Clean up file
            try:
                os.remove(filepath)
            except:
                pass
        else:
            await processing_msg.edit_text(result_text)
        
        # Save search to database
        await client.db.save_search_result(
            user_id, 
            f"@{username} {' '.join(search_terms)}", 
            display_results[:50],
            "user_search"
        )
        
    except Exception as e:
        await processing_msg.edit_text(f"❌ Error during user search: {str(e)}")

@Client.on_message(filters.command("dialogs"))
async def list_dialogs(client: Client, message: Message):
    """List all accessible chats/channels (admin only)"""
    user_id = message.from_user.id
    
    if not await is_admin(user_id):
        await message.reply_text("❌ This command is only available to administrators.")
        return
    
    processing_msg = await message.reply_text("📋 Getting list of accessible chats...")
    
    try:
        dialogs = await scanner.get_dialogs()
        
        if not dialogs:
            await processing_msg.edit_text("No accessible chats found.")
            return
        
        # Group dialogs by type
        groups = [d for d in dialogs if d['type'] in ['group', 'supergroup']]
        channels = [d for d in dialogs if d['type'] == 'channel']
        private_chats = [d for d in dialogs if d['type'] == 'private']
        
        result_text = f"📋 **Accessible Chats** ({len(dialogs)} total)\n\n"
        
        if groups:
            result_text += f"👥 **Groups ({len(groups)}):**\n"
            for group in groups[:10]:
                members = f" ({group['member_count']} members)" if group['member_count'] else ""
                result_text += f"• {group['title']}{members}\n"
            if len(groups) > 10:
                result_text += f"  ... and {len(groups) - 10} more\n"
            result_text += "\n"
        
        if channels:
            result_text += f"📢 **Channels ({len(channels)}):**\n"
            for channel in channels[:10]:
                username = f" (@{channel['username']})" if channel['username'] else ""
                result_text += f"• {channel['title']}{username}\n"
            if len(channels) > 10:
                result_text += f"  ... and {len(channels) - 10} more\n"
            result_text += "\n"
        
        result_text += f"💬 **Private Chats:** {len(private_chats)}\n"
        
        await processing_msg.edit_text(result_text)
        
    except Exception as e:
        await processing_msg.edit_text(f"❌ Error getting dialogs: {str(e)}")