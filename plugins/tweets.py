import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from services.news_service import TwitterService
from utils.helpers import (
    check_rate_limit, record_command_usage, is_admin,
    get_max_results, create_results_file
)

twitter_service = TwitterService()

@Client.on_message(filters.command("tweets"))
async def tweets_command(client: Client, message: Message):
    """Handle /tweets command"""
    user_id = message.from_user.id
    
    # Check rate limit
    if not await check_rate_limit(client.db, user_id, "tweets"):
        await message.reply_text(
            "⏰ You've reached your daily limit (3 info commands per day). "
            "Try again tomorrow or contact an admin for unlimited access."
        )
        return
    
    # Parse command
    try:
        query = message.text.split(' ', 1)[1].strip()
    except IndexError:
        await message.reply_text(
            "❌ Please provide a search query or username.\n"
            "Usage: `/tweets search_query` or `/tweets @username`\n\n"
            "Examples:\n"
            "• `/tweets artificial intelligence`\n"
            "• `/tweets @elonmusk`\n"
            "• `/tweets bitcoin price`\n"
            "• `/tweets \"machine learning\"`"
        )
        return
    
    # Record usage
    await record_command_usage(client.db, user_id, "tweets")
    
    # Check if it's a username or search query
    is_username = query.startswith('@')
    if is_username:
        username = query[1:]  # Remove @ symbol
        search_type = "user tweets"
        processing_msg = await message.reply_text(
            f"🐦 Getting recent tweets from @{username}...\n"
            "Please wait..."
        )
    else:
        search_type = "tweet search"
        processing_msg = await message.reply_text(
            f"🐦 Searching tweets for: **{query}**\n"
            "Please wait..."
        )
    
    try:
        # Get tweets based on type
        if is_username:
            tweets = await twitter_service.get_user_tweets(username, max_results=5)
        else:
            tweets = await twitter_service.search_tweets(query, max_results=5)
        
        if not tweets:
            await processing_msg.edit_text(
                f"🐦 **{search_type.title()} Results**\n\n"
                f"No tweets found for: **{query}**\n\n"
                "Try different keywords or check the username."
            )
            return
        
        # Format response
        response_text = f"🐦 **{search_type.title()}: {query}**\n\n"
        
        # Format tweets
        formatted_tweets = await twitter_service.format_tweet_results(tweets)
        response_text += formatted_tweets
        
        # Check if admin wants detailed file
        if await is_admin(user_id) and len(tweets) > 0:
            timestamp = message.date.strftime("%Y%m%d_%H%M%S")
            filename = f"tweets_{query.replace(' ', '_').replace('@', '')}_{timestamp}.txt"
            filepath = os.path.join("downloads", filename)
            os.makedirs("downloads", exist_ok=True)
            
            file_content = f"TWITTER SEARCH RESULTS\n"
            file_content += f"Query: {query}\n"
            file_content += f"Search Type: {search_type}\n"
            file_content += f"Search Date: {message.date.strftime('%Y-%m-%d %H:%M:%S')}\n"
            file_content += f"Total Tweets: {len(tweets)}\n\n"
            
            file_content += "TWEETS\n"
            file_content += "=" * 50 + "\n\n"
            
            for i, tweet in enumerate(tweets, 1):
                file_content += f"{i}. Tweet ID: {tweet.get('id', 'N/A')}\n"
                file_content += f"   Author: @{tweet.get('author_username', 'unknown')}"
                if tweet.get('author_name'):
                    file_content += f" ({tweet.get('author_name', '')})"
                if tweet.get('author_verified'):
                    file_content += " ✓"
                file_content += "\n"
                file_content += f"   Text: {tweet.get('text', '')}\n"
                file_content += f"   Created: {tweet.get('created_at', 'N/A')}\n"
                file_content += f"   URL: {tweet.get('url', 'N/A')}\n"
                
                metrics = tweet.get('metrics', {})
                if metrics:
                    file_content += f"   Likes: {metrics.get('like_count', 0)}\n"
                    file_content += f"   Retweets: {metrics.get('retweet_count', 0)}\n"
                    file_content += f"   Replies: {metrics.get('reply_count', 0)}\n"
                
                file_content += "-" * 50 + "\n\n"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(file_content)
            
            response_text += f"\n\n📎 **Detailed results attached**"
            
            await processing_msg.delete()
            await message.reply_text(response_text)
            await message.reply_document(
                filepath, 
                caption=f"Complete tweet results for: {query}"
            )
            
            # Clean up file
            try:
                os.remove(filepath)
            except:
                pass
        else:
            await processing_msg.edit_text(response_text)
        
        # Save search to database
        search_data = {
            'query': query,
            'search_type': search_type,
            'tweets': tweets[:10],  # Save first 10 tweets
            'total_found': len(tweets)
        }
        
        await client.db.save_search_result(
            user_id, 
            query, 
            [search_data],
            "twitter_search"
        )
        
    except Exception as e:
        await processing_msg.edit_text(f"❌ Error searching tweets: {str(e)}")
    finally:
        # Don't close session here, let it be reused
        pass

# Close twitter service when bot shuts down
@Client.on_message(filters.command("shutdown") & filters.user([]))  # No users can run this
async def cleanup_twitter_service(client: Client, message: Message):
    """Cleanup twitter service on shutdown"""
    await twitter_service.close()