import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from services.news_service import NewsService
from utils.helpers import (
    check_rate_limit, record_command_usage, is_admin,
    get_max_results, create_results_file
)

news_service = NewsService()

@Client.on_message(filters.command("news"))
async def news_command(client: Client, message: Message):
    """Handle /news command"""
    user_id = message.from_user.id
    
    # Check rate limit
    if not await check_rate_limit(client.db, user_id, "news"):
        await message.reply_text(
            "⏰ You've reached your daily limit (3 info commands per day). "
            "Try again tomorrow or contact an admin for unlimited access."
        )
        return
    
    # Parse command
    try:
        query = message.text.split(' ', 1)[1]
    except IndexError:
        await message.reply_text(
            "❌ Please provide a search query.\n"
            "Usage: `/news your search query`\n\n"
            "Examples:\n"
            "• `/news bitcoin price`\n"
            "• `/news technology news`\n"
            "• `/news \"stock market\"`\n"
            "• `/news ethereum` (for crypto price + news)"
        )
        return
    
    # Record usage
    await record_command_usage(client.db, user_id, "news")
    
    # Send processing message
    processing_msg = await message.reply_text(
        f"📰 Searching for news about: **{query}**\n"
        "Please wait..."
    )
    
    try:
        # Initialize crypto_data to None for all queries
        crypto_data = None
        
        # Check if it's a crypto query
        if news_service.is_crypto_query(query):
            # Try to get crypto price first
            crypto_words = ['bitcoin', 'btc', 'ethereum', 'eth', 'dogecoin', 'doge', 
                          'litecoin', 'ltc', 'ripple', 'xrp', 'cardano', 'ada',
                          'solana', 'sol', 'binance', 'bnb', 'polygon', 'matic']
            
            crypto_symbol = None
            query_lower = query.lower()
            
            for word in crypto_words:
                if word in query_lower:
                    if word in ['bitcoin', 'btc']:
                        crypto_symbol = 'bitcoin'
                    elif word in ['ethereum', 'eth']:
                        crypto_symbol = 'ethereum'
                    elif word in ['dogecoin', 'doge']:
                        crypto_symbol = 'dogecoin'
                    elif word in ['litecoin', 'ltc']:
                        crypto_symbol = 'litecoin'
                    elif word in ['ripple', 'xrp']:
                        crypto_symbol = 'ripple'
                    elif word in ['cardano', 'ada']:
                        crypto_symbol = 'cardano'
                    elif word in ['solana', 'sol']:
                        crypto_symbol = 'solana'
                    elif word in ['binance', 'bnb']:
                        crypto_symbol = 'binancecoin'
                    elif word in ['polygon', 'matic']:
                        crypto_symbol = 'polygon'
                    break
            
            # Get crypto price if symbol found
            if crypto_symbol:
                crypto_data = await news_service.get_crypto_price(crypto_symbol)
        
        # Get max results
        max_results = get_max_results(user_id)
        
        # Search news
        articles = await news_service.search_all_news(query, max_results)
        
        if not articles and not crypto_data:
            await processing_msg.edit_text(
                f"📰 **News Search Results**\n\n"
                f"No news found for: **{query}**\n\n"
                "Try different keywords or check the spelling."
            )
            return
        
        # Format response
        response_text = f"📰 **News: {query}**\n\n"
        
        # Add crypto price if available
        if crypto_data:
            price = crypto_data['price']
            change = crypto_data['percent_change_24h']
            change_emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
            
            response_text += f"💰 **{crypto_data['name']} ({crypto_data['symbol']})**\n"
            response_text += f"Price: ${price:,.2f}\n"
            response_text += f"24h Change: {change_emoji} {change:.2f}%\n"
            
            if crypto_data.get('market_cap'):
                market_cap = crypto_data['market_cap']
                if market_cap > 1e9:
                    response_text += f"Market Cap: ${market_cap/1e9:.1f}B\n"
                elif market_cap > 1e6:
                    response_text += f"Market Cap: ${market_cap/1e6:.1f}M\n"
            
            response_text += "\n"
        
        # Add news articles
        if articles:
            summary, detailed = await news_service.format_news_results(articles, max_results)
            response_text += summary
            
            # Create file for detailed results if needed
            if len(articles) > 10 or await is_admin(user_id):
                timestamp = message.date.strftime("%Y%m%d_%H%M%S")
                filename = f"news_{query.replace(' ', '_')}_{timestamp}.txt"
                filepath = os.path.join("downloads", filename)
                os.makedirs("downloads", exist_ok=True)
                
                file_content = f"NEWS SEARCH RESULTS\n"
                file_content += f"Query: {query}\n"
                file_content += f"Search Date: {message.date.strftime('%Y-%m-%d %H:%M:%S')}\n"
                file_content += f"Total Articles: {len(articles)}\n\n"
                
                if crypto_data:
                    file_content += f"CRYPTOCURRENCY DATA\n"
                    file_content += f"Asset: {crypto_data['name']} ({crypto_data['symbol']})\n"
                    file_content += f"Price: ${crypto_data['price']:,.2f}\n"
                    file_content += f"24h Change: {crypto_data['percent_change_24h']:.2f}%\n"
                    if crypto_data.get('market_cap'):
                        file_content += f"Market Cap: ${crypto_data['market_cap']:,.0f}\n"
                    file_content += f"Last Updated: {crypto_data['last_updated']}\n\n"
                
                file_content += "ARTICLES\n"
                file_content += "=" * 50 + "\n\n"
                file_content += detailed
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(file_content)
                
                response_text += f"\n\n📎 **Detailed results attached**"
                
                await processing_msg.delete()
                await message.reply_text(response_text)
                await message.reply_document(
                    filepath, 
                    caption=f"Complete news results for: {query}"
                )
                
                # Clean up file
                try:
                    os.remove(filepath)
                except:
                    pass
            else:
                await processing_msg.edit_text(response_text)
        else:
            await processing_msg.edit_text(response_text)
        
        # Save search to database
        search_data = {
            'query': query,
            'articles': articles[:20] if articles else [],
            'crypto_data': crypto_data
        }
        
        await client.db.save_search_result(
            user_id, 
            query, 
            [search_data],
            "news_search"
        )
        
    except Exception as e:
        await processing_msg.edit_text(f"❌ Error searching news: {str(e)}")
    finally:
        # Don't close session here, let it be reused
        pass

@Client.on_message(filters.command("crypto"))
async def crypto_command(client: Client, message: Message):
    """Handle /crypto command for cryptocurrency prices"""
    user_id = message.from_user.id
    
    # Check rate limit
    if not await check_rate_limit(client.db, user_id, "crypto"):
        await message.reply_text(
            "⏰ You've reached your daily limit (3 info commands per day). "
            "Try again tomorrow or contact an admin for unlimited access."
        )
        return
    
    # Parse command
    try:
        symbol = message.text.split(' ', 1)[1].strip()
    except IndexError:
        await message.reply_text(
            "❌ Please provide a cryptocurrency symbol.\n"
            "Usage: `/crypto symbol`\n\n"
            "Examples:\n"
            "• `/crypto bitcoin`\n"
            "• `/crypto ethereum`\n"
            "• `/crypto btc`\n"
            "• `/crypto eth`"
        )
        return
    
    # Record usage
    await record_command_usage(client.db, user_id, "crypto")
    
    # Send processing message
    processing_msg = await message.reply_text(f"💰 Getting {symbol.upper()} price data...")
    
    try:
        # Get crypto price
        crypto_data = await news_service.get_crypto_price(symbol)
        
        if not crypto_data:
            await processing_msg.edit_text(
                f"❌ Could not find cryptocurrency: **{symbol}**\n\n"
                "Please check the symbol and try again."
            )
            return
        
        # Format response
        price = crypto_data['price']
        change = crypto_data['percent_change_24h']
        change_emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        
        response_text = f"💰 **{crypto_data['name']} ({crypto_data['symbol']})**\n\n"
        response_text += f"**Price:** ${price:,.2f}\n"
        response_text += f"**24h Change:** {change_emoji} {change:.2f}%\n"
        
        if crypto_data.get('market_cap'):
            market_cap = crypto_data['market_cap']
            if market_cap > 1e9:
                response_text += f"**Market Cap:** ${market_cap/1e9:.1f}B\n"
            elif market_cap > 1e6:
                response_text += f"**Market Cap:** ${market_cap/1e6:.1f}M\n"
        
        if crypto_data.get('volume_24h'):
            volume = crypto_data['volume_24h']
            if volume > 1e9:
                response_text += f"**24h Volume:** ${volume/1e9:.1f}B\n"
            elif volume > 1e6:
                response_text += f"**24h Volume:** ${volume/1e6:.1f}M\n"
        
        response_text += f"\n🕐 Last updated: {crypto_data['last_updated'][:19].replace('T', ' ')}"
        
        await processing_msg.edit_text(response_text)
        
        # Save to database
        await client.db.save_search_result(
            user_id, 
            f"crypto_{symbol}", 
            [crypto_data],
            "crypto_price"
        )
        
    except Exception as e:
        await processing_msg.edit_text(f"❌ Error getting crypto price: {str(e)}")

# Close news service when bot shuts down
@Client.on_message(filters.command("shutdown") & filters.user([]))  # No users can run this
async def cleanup_news_service(client: Client, message: Message):
    """Cleanup news service on shutdown"""
    await news_service.close()