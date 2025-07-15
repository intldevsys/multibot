import aiohttp
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from config import (
    NEWS_API_KEY, NEWSDATA_API_KEY, GNEWS_API_KEY, GUARDIAN_API_KEY,
    COINMARKETCAP_API_KEY, COINGECKO_API_KEY,
    TWITTER_BEARER_TOKEN, TWITTER_API_KEY, TWITTER_API_SECRET
)

class NewsService:
    def __init__(self):
        self.session = None

    async def get_session(self):
        """Get or create aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()

    async def search_news_api(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search news using NewsAPI"""
        if not NEWS_API_KEY:
            return []

        session = await self.get_session()
        url = "https://newsapi.org/v2/everything"
        
        params = {
            'q': query,
            'apiKey': NEWS_API_KEY,
            'sortBy': 'publishedAt',
            'pageSize': max_results,
            'language': 'en'
        }

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = []
                    
                    for article in data.get('articles', []):
                        articles.append({
                            'title': article.get('title', ''),
                            'description': article.get('description', ''),
                            'url': article.get('url', ''),
                            'source': article.get('source', {}).get('name', 'NewsAPI'),
                            'published_at': article.get('publishedAt', ''),
                            'image_url': article.get('urlToImage', '')
                        })
                    
                    return articles
        except Exception as e:
            print(f"Error fetching from NewsAPI: {e}")
        
        return []

    async def search_newsdata_api(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search news using NewsData.io API"""
        if not NEWSDATA_API_KEY:
            return []

        session = await self.get_session()
        url = "https://newsdata.io/api/1/news"
        
        params = {
            'apikey': NEWSDATA_API_KEY,
            'q': query,
            'language': 'en',
            'size': max_results
        }

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = []
                    
                    for article in data.get('results', []):
                        articles.append({
                            'title': article.get('title', ''),
                            'description': article.get('description', ''),
                            'url': article.get('link', ''),
                            'source': article.get('source_id', 'NewsData'),
                            'published_at': article.get('pubDate', ''),
                            'image_url': article.get('image_url', '')
                        })
                    
                    return articles
        except Exception as e:
            print(f"Error fetching from NewsData: {e}")
        
        return []

    async def search_gnews_api(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search news using GNews API"""
        if not GNEWS_API_KEY:
            return []

        session = await self.get_session()
        url = "https://gnews.io/api/v4/search"
        
        params = {
            'q': query,
            'token': GNEWS_API_KEY,
            'lang': 'en',
            'max': max_results
        }

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = []
                    
                    for article in data.get('articles', []):
                        articles.append({
                            'title': article.get('title', ''),
                            'description': article.get('description', ''),
                            'url': article.get('url', ''),
                            'source': article.get('source', {}).get('name', 'GNews'),
                            'published_at': article.get('publishedAt', ''),
                            'image_url': article.get('image', '')
                        })
                    
                    return articles
        except Exception as e:
            print(f"Error fetching from GNews: {e}")
        
        return []

    async def search_guardian_api(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search news using The Guardian API"""
        if not GUARDIAN_API_KEY:
            return []

        session = await self.get_session()
        url = "https://content.guardianapis.com/search"
        
        params = {
            'q': query,
            'api-key': GUARDIAN_API_KEY,
            'page-size': max_results,
            'show-fields': 'headline,trailText,thumbnail,shortUrl',
            'order-by': 'newest'
        }

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = []
                    
                    results = data.get('response', {}).get('results', [])
                    for article in results:
                        fields = article.get('fields', {})
                        articles.append({
                            'title': fields.get('headline', article.get('webTitle', '')),
                            'description': fields.get('trailText', ''),
                            'url': fields.get('shortUrl', article.get('webUrl', '')),
                            'source': 'The Guardian',
                            'published_at': article.get('webPublicationDate', ''),
                            'image_url': fields.get('thumbnail', '')
                        })
                    
                    return articles
        except Exception as e:
            print(f"Error fetching from Guardian API: {e}")
        
        return []

    async def get_crypto_price(self, symbol: str) -> Optional[Dict]:
        """Get cryptocurrency price from CoinMarketCap"""
        if not COINMARKETCAP_API_KEY:
            return await self.get_crypto_price_coingecko(symbol)

        session = await self.get_session()
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        
        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY,
        }
        
        params = {
            'symbol': symbol.upper(),
            'convert': 'USD'
        }

        try:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    crypto_data = data.get('data', {}).get(symbol.upper(), {})
                    
                    if crypto_data:
                        quote = crypto_data.get('quote', {}).get('USD', {})
                        return {
                            'symbol': symbol.upper(),
                            'name': crypto_data.get('name', ''),
                            'price': quote.get('price', 0),
                            'percent_change_24h': quote.get('percent_change_24h', 0),
                            'market_cap': quote.get('market_cap', 0),
                            'volume_24h': quote.get('volume_24h', 0),
                            'last_updated': quote.get('last_updated', '')
                        }
        except Exception as e:
            print(f"Error fetching crypto price from CMC: {e}")
        
        return await self.get_crypto_price_coingecko(symbol)

    async def get_crypto_price_coingecko(self, symbol: str) -> Optional[Dict]:
        """Get cryptocurrency price from CoinGecko (fallback)"""
        session = await self.get_session()
        url = f"https://api.coingecko.com/api/v3/simple/price"
        
        params = {
            'ids': symbol.lower(),
            'vs_currencies': 'usd',
            'include_24hr_change': 'true',
            'include_market_cap': 'true',
            'include_24hr_vol': 'true'
        }

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if symbol.lower() in data:
                        crypto_data = data[symbol.lower()]
                        return {
                            'symbol': symbol.upper(),
                            'name': symbol.capitalize(),
                            'price': crypto_data.get('usd', 0),
                            'percent_change_24h': crypto_data.get('usd_24h_change', 0),
                            'market_cap': crypto_data.get('usd_market_cap', 0),
                            'volume_24h': crypto_data.get('usd_24h_vol', 0),
                            'last_updated': datetime.now().isoformat()
                        }
        except Exception as e:
            print(f"Error fetching crypto price from CoinGecko: {e}")
        
        return None

    async def search_all_news(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search news from all available sources"""
        tasks = []
        
        # Calculate results per API (divide by 4 since we have 4 APIs now)
        results_per_api = max(1, max_results // 4)
        
        # Create tasks for all APIs
        if NEWS_API_KEY:
            tasks.append(self.search_news_api(query, results_per_api))
        if NEWSDATA_API_KEY:
            tasks.append(self.search_newsdata_api(query, results_per_api))
        if GNEWS_API_KEY:
            tasks.append(self.search_gnews_api(query, results_per_api))
        if GUARDIAN_API_KEY:
            tasks.append(self.search_guardian_api(query, results_per_api))

        # Execute all tasks concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results and remove duplicates
            all_articles = []
            seen_urls = set()
            
            for result in results:
                if isinstance(result, list):
                    for article in result:
                        url = article.get('url', '')
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_articles.append(article)
            
            # Sort by publication date (newest first)
            all_articles.sort(
                key=lambda x: x.get('published_at', ''), 
                reverse=True
            )
            
            return all_articles[:max_results]
        
        return []

    def is_crypto_query(self, query: str) -> bool:
        """Check if query is related to cryptocurrency"""
        crypto_keywords = [
            'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency',
            'coin', 'price', 'dogecoin', 'doge', 'litecoin', 'ltc',
            'ripple', 'xrp', 'cardano', 'ada', 'solana', 'sol',
            'binance', 'bnb', 'polygon', 'matic', 'avalanche', 'avax'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in crypto_keywords)

    async def format_news_results(self, articles: List[Dict], max_lines: int = 10) -> tuple:
        """Format news results for display"""
        if not articles:
            return "No news found for your query.", None
        
        summary_lines = []
        detailed_content = []
        
        for i, article in enumerate(articles[:max_lines], 1):
            title = article.get('title', 'No title')
            url = article.get('url', '')
            source = article.get('source', 'Unknown')
            
            # Summary line
            summary_line = f"{i}. {title}"
            if url:
                summary_line += f" - [Link]({url})"
            summary_lines.append(summary_line)
            
            # Detailed content for file
            detailed_content.append(f"{i}. {title}")
            detailed_content.append(f"   Source: {source}")
            detailed_content.append(f"   Description: {article.get('description', 'No description')}")
            detailed_content.append(f"   URL: {url}")
            detailed_content.append(f"   Published: {article.get('published_at', 'Unknown')}")
            detailed_content.append("-" * 50)
        
        summary = "\n".join(summary_lines)
        detailed = "\n".join(detailed_content)
        
        return summary, detailed


class TwitterService:
    def __init__(self):
        self.session = None
        self.bearer_token = TWITTER_BEARER_TOKEN

    async def get_session(self):
        """Get or create aiohttp session"""
        if not self.session:
            headers = {}
            if self.bearer_token:
                headers['Authorization'] = f'Bearer {self.bearer_token}'
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session

    async def close(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()

    async def search_tweets(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search tweets using Twitter API v2"""
        if not self.bearer_token:
            return []

        session = await self.get_session()
        url = "https://api.twitter.com/2/tweets/search/recent"
        
        params = {
            'query': query,
            'max_results': min(max_results, 100),
            'tweet.fields': 'created_at,author_id,public_metrics,context_annotations',
            'user.fields': 'username,name,verified',
            'expansions': 'author_id'
        }

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    tweets = []
                    users = {user['id']: user for user in data.get('includes', {}).get('users', [])}
                    
                    for tweet in data.get('data', []):
                        author_id = tweet.get('author_id', '')
                        author = users.get(author_id, {})
                        
                        tweets.append({
                            'id': tweet.get('id', ''),
                            'text': tweet.get('text', ''),
                            'created_at': tweet.get('created_at', ''),
                            'author_username': author.get('username', ''),
                            'author_name': author.get('name', ''),
                            'author_verified': author.get('verified', False),
                            'metrics': tweet.get('public_metrics', {}),
                            'url': f"https://twitter.com/{author.get('username', 'unknown')}/status/{tweet.get('id', '')}"
                        })
                    
                    return tweets
                else:
                    print(f"Twitter API error: {response.status}")
        except Exception as e:
            print(f"Error searching tweets: {e}")
        
        return []

    async def get_user_tweets(self, username: str, max_results: int = 5) -> List[Dict]:
        """Get recent tweets from a specific user"""
        if not self.bearer_token:
            return []

        # First, get user ID by username
        session = await self.get_session()
        user_url = f"https://api.twitter.com/2/users/by/username/{username}"
        
        try:
            async with session.get(user_url) as response:
                if response.status == 200:
                    user_data = await response.json()
                    user_id = user_data.get('data', {}).get('id')
                    
                    if user_id:
                        # Get user's tweets
                        tweets_url = f"https://api.twitter.com/2/users/{user_id}/tweets"
                        params = {
                            'max_results': min(max_results, 100),
                            'tweet.fields': 'created_at,public_metrics',
                            'exclude': 'retweets,replies'
                        }
                        
                        async with session.get(tweets_url, params=params) as tweets_response:
                            if tweets_response.status == 200:
                                tweets_data = await tweets_response.json()
                                
                                tweets = []
                                for tweet in tweets_data.get('data', []):
                                    tweets.append({
                                        'id': tweet.get('id', ''),
                                        'text': tweet.get('text', ''),
                                        'created_at': tweet.get('created_at', ''),
                                        'author_username': username,
                                        'metrics': tweet.get('public_metrics', {}),
                                        'url': f"https://twitter.com/{username}/status/{tweet.get('id', '')}"
                                    })
                                
                                return tweets
        except Exception as e:
            print(f"Error getting user tweets: {e}")
        
        return []

    async def format_tweet_results(self, tweets: List[Dict]) -> str:
        """Format tweet results for display"""
        if not tweets:
            return "No tweets found for your query."
        
        formatted_tweets = []
        for i, tweet in enumerate(tweets, 1):
            text = tweet.get('text', '')[:200] + ('...' if len(tweet.get('text', '')) > 200 else '')
            username = tweet.get('author_username', 'unknown')
            url = tweet.get('url', '')
            metrics = tweet.get('metrics', {})
            
            tweet_line = f"{i}. @{username}: {text}"
            if url:
                tweet_line += f"\n   [Link]({url})"
            
            likes = metrics.get('like_count', 0)
            retweets = metrics.get('retweet_count', 0)
            if likes or retweets:
                tweet_line += f"\n   ❤️ {likes} | 🔄 {retweets}"
            
            formatted_tweets.append(tweet_line)
        
        return "\n\n".join(formatted_tweets)