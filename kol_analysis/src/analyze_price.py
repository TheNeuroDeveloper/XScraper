"""
Analyze price movements of cryptocurrencies mentioned in tweets.
"""

import json
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from pytz import UTC
import os
from dotenv import load_dotenv
import time

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PriceAnalyzer:
    def __init__(self):
        """Initialize price analyzer."""
        self.dex_url = "https://api.dexscreener.com/latest/dex"
        self.cmc_url = "https://pro-api.coinmarketcap.com/v1"
        self.cmc_api_key = os.getenv('CMC_API_KEY')
        if not self.cmc_api_key:
            logger.warning("CMC_API_KEY not found in environment variables")
            
        self.timeframes = {
            'first_mention': timedelta(minutes=0),  # At first mention
            'post_24h': timedelta(hours=24),        # 24 hours after
            'post_7d': timedelta(days=7),          # 7 days after
            'post_30d': timedelta(days=30)         # 30 days after
        }
        # Cache to store historical price data
        self.price_cache = {}
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum seconds between requests

    async def rate_limit(self):
        """Implement rate limiting for API requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last_request)
        self.last_request_time = time.time()

    async def get_cmc_headers(self) -> Dict[str, str]:
        """Get headers for CoinMarketCap API requests."""
        return {
            'X-CMC_PRO_API_KEY': self.cmc_api_key,
            'Accept': 'application/json'
        }

    async def search_cmc_token(self, token_symbol: str) -> Optional[Dict]:
        """Search for token on CoinMarketCap."""
        if not self.cmc_api_key:
            logger.error("CMC_API_KEY not found")
            return None
            
        await self.rate_limit()
        url = f"{self.cmc_url}/cryptocurrency/map"
        params = {'symbol': token_symbol}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=await self.get_cmc_headers(), params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('data'):
                            return data['data'][0]  # Return first match
                    logger.error(f"Failed to search CMC for token {token_symbol}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error searching CMC for token {token_symbol}: {e}")
            return None

    async def get_cmc_historical_price(self, token_id: int, timestamp: datetime) -> Optional[Dict]:
        """Get historical price data from CoinMarketCap."""
        if not self.cmc_api_key:
            logger.error("CMC_API_KEY not found")
            return None
            
        await self.rate_limit()
        # Convert timestamp to Unix timestamp in seconds
        unix_timestamp = int(timestamp.timestamp())
        
        url = f"{self.cmc_url}/cryptocurrency/ohlcv/historical"
        params = {
            'id': token_id,
            'time_start': unix_timestamp,
            'time_end': unix_timestamp,
            'convert': 'USD',
            'interval': '1d'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=await self.get_cmc_headers(), params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('data', {}).get(str(token_id)):
                            quote = data['data'][str(token_id)]['quotes'][0]
                            return {
                                'price_usd': quote.get('close'),
                                'volume_24h': quote.get('volume'),
                                'market_cap': quote.get('market_cap'),
                                'timestamp': timestamp.isoformat(),
                                'data_source': 'coinmarketcap'
                            }
                    logger.error(f"Failed to get CMC historical price: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting CMC historical price: {e}")
            return None

    async def get_cmc_current_price(self, token_id: int) -> Optional[Dict]:
        """Get current price data from CoinMarketCap."""
        if not self.cmc_api_key:
            logger.error("CMC_API_KEY not found")
            return None
            
        await self.rate_limit()
        url = f"{self.cmc_url}/cryptocurrency/quotes/latest"
        params = {
            'id': token_id,
            'convert': 'USD'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=await self.get_cmc_headers(), params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('data', {}).get(str(token_id)):
                            quote = data['data'][str(token_id)]['quote']['USD']
                            return {
                                'price_usd': quote.get('price'),
                                'volume_24h': quote.get('volume_24h'),
                                'market_cap': quote.get('market_cap'),
                                'timestamp': datetime.now(UTC).isoformat(),
                                'data_source': 'coinmarketcap'
                            }
                    logger.error(f"Failed to get CMC current price: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting CMC current price: {e}")
            return None

    async def search_token(self, token_symbol: str) -> List[Dict]:
        """Search for token pairs on DEXScreener."""
        url = f"{self.dex_url}/search"
        params = {'q': token_symbol}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('pairs'):
                            # Sort pairs by liquidity
                            pairs = sorted(
                                data['pairs'], 
                                key=lambda x: float(x.get('liquidity', {}).get('usd', 0) or 0), 
                                reverse=True
                            )
                            return pairs
                    logger.error(f"Failed to search for token {token_symbol}: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error searching for token {token_symbol}: {e}")
            return []

    def get_cache_key(self, token: str, pair_address: str, timeframe: str) -> str:
        """Generate a unique cache key for a token-pair-timeframe combination."""
        return f"{token}_{pair_address}_{timeframe}"

    def store_price_data(self, token: str, pair_address: str, timeframe: str, price_data: Dict):
        """Store price data in cache."""
        cache_key = self.get_cache_key(token, pair_address, timeframe)
        self.price_cache[cache_key] = price_data

    def get_cached_price_data(self, token: str, pair_address: str, timeframe: str) -> Optional[Dict]:
        """Retrieve cached price data."""
        cache_key = self.get_cache_key(token, pair_address, timeframe)
        return self.price_cache.get(cache_key)

    async def get_best_token_pair(self, token_symbol: str, tweet_time: datetime) -> Optional[Dict]:
        """Get the best matching token pair based on liquidity and creation time."""
        pairs = await self.search_token(token_symbol)
        
        if not pairs:
            logger.warning(f"No pairs found for token {token_symbol}")
            return None
            
        # Filter pairs created before or around tweet time
        valid_pairs = []
        for pair in pairs:
            # Convert pair creation timestamp from milliseconds to datetime
            if 'pairCreatedAt' in pair:
                created_at = datetime.fromtimestamp(int(pair['pairCreatedAt']) / 1000, UTC)
                # Allow some flexibility (1 hour) for timestamp comparison
                if created_at <= tweet_time + timedelta(hours=1):
                    valid_pairs.append(pair)
        
        if not valid_pairs:
            # If no valid pairs found, use the oldest pair as fallback
            valid_pairs = sorted(
                pairs,
                key=lambda x: int(x.get('pairCreatedAt', 0)),
                reverse=False
            )
        
        # Get the pair with highest liquidity among valid pairs
        best_pair = max(
            valid_pairs,
            key=lambda x: float(x.get('liquidity', {}).get('usd', 0) or 0)
        )
        
        return best_pair

    def extract_tokens_from_tweets(self, tweets: List[Dict]) -> List[str]:
        """Extract unique token mentions from tweets."""
        tokens = set()
        # Common non-crypto tokens to exclude
        exclude_tokens = {'BTC', 'ETH', 'USDT', 'USD', 'USDC', 'BINANCE', 'GATEIO', 'INTERMILAN', 'CHAMPIONSLEAGUE'}
        
        for tweet in tweets:
            text = tweet['text']
            # Look for $SYMBOL or #SYMBOL patterns
            words = text.split()
            for word in words:
                if word.startswith('$') or word.startswith('#'):
                    token = word.strip('$#').upper().strip(',')  # Also strip commas
                    # Filter out non-crypto tokens and numbers
                    if (token and len(token) > 1 and  # Ignore single-character tokens
                        token not in exclude_tokens and  # Ignore common non-crypto tokens
                        not any(c.isdigit() for c in token) and  # Ignore tokens with numbers
                        not token.endswith('M') and  # Ignore tokens ending with M (million)
                        not token.endswith('B')):  # Ignore tokens ending with B (billion)
                        tokens.add(token)
        return list(tokens)

    async def get_price_at_time(self, pair_data: Dict, target_time: datetime, token_symbol: str) -> Dict:
        """Get price data for a specific time using CoinMarketCap if available."""
        logger.info(f"\nRequesting price for {token_symbol} at {target_time.isoformat()}")
        
        current_time = datetime.now(UTC)
        if target_time > current_time:
            return {
                'price_usd': None,
                'price_native': None,
                'liquidity_usd': None,
                'volume_24h': None,
                'timestamp': target_time.isoformat(),
                'data_source': 'future_date'
            }
        
        # First try to get data from CoinMarketCap
        try:
            cmc_token = await self.search_cmc_token(token_symbol)
            if cmc_token:
                cmc_id = cmc_token.get('id')
                if cmc_id:
                    logger.info(f"Attempting to get historical price from CMC for {token_symbol} at {target_time}")
                    historical_data = await self.get_cmc_historical_price(cmc_id, target_time)
                    if historical_data:
                        logger.info(f"Found historical price data for {token_symbol} on CoinMarketCap")
                        return historical_data
        except Exception as e:
            logger.debug(f"Could not get CMC data for {token_symbol}: {e}")
        
        # If we can't get CMC data, use DEXScreener data
        logger.info(f"Using DEXScreener data for {token_symbol}")
        
        # For DEXScreener, we need to get the price at the specific time
        pair_address = pair_data.get('pairAddress')
        chain_id = pair_data.get('chainId')
        
        if pair_address and chain_id:
            # Get historical price data from DEXScreener
            # First try the candles endpoint for more precise historical data
            candles_url = f"{self.dex_url}/pairs/{chain_id}/{pair_address}/candles"
            try:
                params = {
                    'from': int((target_time - timedelta(hours=12)).timestamp() * 1000),
                    'to': int((target_time + timedelta(hours=12)).timestamp() * 1000),
                    'res': '1H'  # 1-hour candles
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(candles_url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get('data'):
                                # Find the closest candle to our target time
                                closest_candle = None
                                min_time_diff = float('inf')
                                
                                for candle in data['data']:
                                    candle_time = datetime.fromtimestamp(int(candle['timestamp']) / 1000, UTC)
                                    time_diff = abs((candle_time - target_time).total_seconds())
                                    
                                    if time_diff < min_time_diff:
                                        min_time_diff = time_diff
                                        closest_candle = candle
                                
                                if closest_candle and min_time_diff <= 43200:  # Within 12 hours
                                    return {
                                        'price_usd': closest_candle.get('close'),
                                        'price_native': closest_candle.get('close'),  # DEXScreener candles are in USD
                                        'liquidity_usd': pair_data.get('liquidity', {}).get('usd'),
                                        'volume_24h': pair_data.get('volume', {}).get('h24'),
                                        'timestamp': datetime.fromtimestamp(int(closest_candle['timestamp']) / 1000, UTC).isoformat(),
                                        'data_source': 'dexscreener_candles'
                                    }
            
            except Exception as e:
                logger.error(f"Error getting candle data from DEXScreener: {e}")
            
            # If candles didn't work, try the price history endpoint
            history_url = f"{self.dex_url}/pairs/{chain_id}/{pair_address}/history"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(history_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get('data'):
                                # Find the closest price to our target time
                                closest_price = None
                                min_time_diff = float('inf')
                                
                                for price_point in data['data']:
                                    price_time = datetime.fromtimestamp(int(price_point['timestamp']) / 1000, UTC)
                                    time_diff = abs((price_time - target_time).total_seconds())
                                    
                                    if time_diff < min_time_diff:
                                        min_time_diff = time_diff
                                        closest_price = price_point
                                
                                if closest_price and min_time_diff <= 43200:  # Within 12 hours
                                    return {
                                        'price_usd': closest_price.get('priceUsd'),
                                        'price_native': closest_price.get('priceNative'),
                                        'liquidity_usd': closest_price.get('liquidityUsd'),
                                        'volume_24h': closest_price.get('volumeUsd'),
                                        'timestamp': datetime.fromtimestamp(int(closest_price['timestamp']) / 1000, UTC).isoformat(),
                                        'data_source': 'dexscreener_historical'
                                    }
            
            except Exception as e:
                logger.error(f"Error getting historical price from DEXScreener: {e}")
        
        # If we can't get historical data, use current price data
        return {
            'price_usd': pair_data.get('priceUsd'),
            'price_native': pair_data.get('priceNative'),
            'liquidity_usd': pair_data.get('liquidity', {}).get('usd'),
            'volume_24h': pair_data.get('volume', {}).get('h24'),
            'timestamp': target_time.isoformat(),
            'data_source': 'dexscreener_current'
        }

    async def analyze_tweet_impact(self, tweet: Dict, token: str) -> Dict:
        """Analyze price impact of a tweet for a specific token."""
        # Convert tweet timestamp to UTC datetime
        tweet_time = datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S %z %Y')
        tweet_time = tweet_time.astimezone(UTC)
        current_time = datetime.now(UTC)
        
        logger.info(f"\nAnalyzing tweet impact for {token}")
        logger.info(f"Tweet time: {tweet_time.isoformat()}")
        
        # Get best matching token pair
        pair_data = await self.get_best_token_pair(token, tweet_time)
        
        if not pair_data:
            return {
                'token': token,
                'tweet_id': tweet['id'],
                'tweet_time': tweet_time.isoformat(),
                'tweet_text': tweet['text'],
                'error': 'No price data available'
            }

        # Calculate target times for price checks
        first_mention_time = tweet_time + self.timeframes['first_mention']
        post_24h_time = tweet_time + self.timeframes['post_24h']
        post_7d_time = tweet_time + self.timeframes['post_7d']
        post_30d_time = tweet_time + self.timeframes['post_30d']
        
        logger.info(f"\nTimeframes for {token}:")
        logger.info(f"First mention: {first_mention_time.isoformat()}")
        logger.info(f"24h after: {post_24h_time.isoformat()}")
        logger.info(f"7d after: {post_7d_time.isoformat()}")
        logger.info(f"30d after: {post_30d_time.isoformat()}")
        
        # Get price data for each timeframe
        first_mention_data = await self.get_price_at_time(pair_data, first_mention_time, token)
        
        # Only get historical prices if the target time is not in the future
        post_24h_data = (
            {'price_usd': None, 'timestamp': post_24h_time.isoformat(), 'data_source': 'future_date'}
            if post_24h_time > current_time
            else await self.get_price_at_time(pair_data, post_24h_time, token)
        )
        
        post_7d_data = (
            {'price_usd': None, 'timestamp': post_7d_time.isoformat(), 'data_source': 'future_date'}
            if post_7d_time > current_time
            else await self.get_price_at_time(pair_data, post_7d_time, token)
        )
        
        post_30d_data = (
            {'price_usd': None, 'timestamp': post_30d_time.isoformat(), 'data_source': 'future_date'}
            if post_30d_time > current_time
            else await self.get_price_at_time(pair_data, post_30d_time, token)
        )
        
        # Log price data sources and timestamps
        logger.info(f"\nPrice data for {token}:")
        logger.info(f"First mention: ${first_mention_data['price_usd']} from {first_mention_data['data_source']} at {first_mention_data['timestamp']}")
        logger.info(f"24h after: ${post_24h_data['price_usd']} from {post_24h_data['data_source']} at {post_24h_data['timestamp']}")
        logger.info(f"7d after: ${post_7d_data['price_usd']} from {post_7d_data['data_source']} at {post_7d_data['timestamp']}")
        logger.info(f"30d after: ${post_30d_data['price_usd']} from {post_30d_data['data_source']} at {post_30d_data['timestamp']}")
        
        # Calculate price changes only if we have valid prices
        first_price = float(first_mention_data['price_usd'] or 0)
        post_24h_price = float(post_24h_data['price_usd'] or 0)
        post_7d_price = float(post_7d_data['price_usd'] or 0)
        post_30d_price = float(post_30d_data['price_usd'] or 0)
        
        price_change_24h = ((post_24h_price - first_price) / first_price * 100) if first_price > 0 and post_24h_price > 0 and post_24h_data['data_source'] != 'future_date' else None
        price_change_7d = ((post_7d_price - first_price) / first_price * 100) if first_price > 0 and post_7d_price > 0 and post_7d_data['data_source'] != 'future_date' else None
        price_change_30d = ((post_30d_price - first_price) / first_price * 100) if first_price > 0 and post_30d_price > 0 and post_30d_data['data_source'] != 'future_date' else None
        
        # Log price changes
        logger.info(f"\nPrice changes for {token}:")
        logger.info(f"24h change: {price_change_24h:.2f}% (${first_price} -> ${post_24h_price})" if price_change_24h is not None else "24h change: N/A")
        logger.info(f"7d change: {price_change_7d:.2f}% (${first_price} -> ${post_7d_price})" if price_change_7d is not None else "7d change: N/A")
        logger.info(f"30d change: {price_change_30d:.2f}% (${first_price} -> ${post_30d_price})" if price_change_30d is not None else "30d change: N/A")

        # Extract token info and return data
        base_token = pair_data.get('baseToken', {})
        
        return {
            'token': token,
            'token_name': base_token.get('name'),
            'token_address': base_token.get('address'),
            'tweet_id': tweet['id'],
            'tweet_time': tweet_time.isoformat(),
            'tweet_text': tweet['text'],
            # First mention price data
            'first_mention_price_usd': first_mention_data['price_usd'],
            'first_mention_price_native': first_mention_data.get('price_native'),
            'first_mention_liquidity_usd': first_mention_data.get('liquidity_usd'),
            'first_mention_volume_24h': first_mention_data.get('volume_24h'),
            'first_mention_timestamp': first_mention_data['timestamp'],
            'first_mention_data_source': first_mention_data.get('data_source', 'unknown'),
            # 24h post-tweet price data
            'post_24h_price_usd': post_24h_data['price_usd'],
            'post_24h_price_native': post_24h_data.get('price_native'),
            'post_24h_liquidity_usd': post_24h_data.get('liquidity_usd'),
            'post_24h_volume_24h': post_24h_data.get('volume_24h'),
            'post_24h_timestamp': post_24h_data['timestamp'],
            'post_24h_data_source': post_24h_data.get('data_source', 'unknown'),
            # 7d post-tweet price data
            'post_7d_price_usd': post_7d_data['price_usd'],
            'post_7d_price_native': post_7d_data.get('price_native'),
            'post_7d_liquidity_usd': post_7d_data.get('liquidity_usd'),
            'post_7d_volume_24h': post_7d_data.get('volume_24h'),
            'post_7d_timestamp': post_7d_data['timestamp'],
            'post_7d_data_source': post_7d_data.get('data_source', 'unknown'),
            # 30d post-tweet price data
            'post_30d_price_usd': post_30d_data['price_usd'],
            'post_30d_price_native': post_30d_data.get('price_native'),
            'post_30d_liquidity_usd': post_30d_data.get('liquidity_usd'),
            'post_30d_volume_24h': post_30d_data.get('volume_24h'),
            'post_30d_timestamp': post_30d_data['timestamp'],
            'post_30d_data_source': post_30d_data.get('data_source', 'unknown'),
            # Calculated price changes
            'price_change_24h': price_change_24h,
            'price_change_7d': price_change_7d,
            'price_change_30d': price_change_30d,
            # Additional metrics
            'market_cap': pair_data.get('marketCap'),
            'fdv': pair_data.get('fdv'),
            'pair_address': pair_data.get('pairAddress'),
            'pair_url': pair_data.get('url'),
            'dex_id': pair_data.get('dexId'),
            'chain_id': pair_data.get('chainId'),
            'created_at': datetime.fromtimestamp(int(pair_data.get('pairCreatedAt', 0)) / 1000, UTC).isoformat()
        }

    async def analyze_all_tweets(self, tweets_file: Path) -> List[Dict]:
        """Analyze all tweets in the file."""
        try:
            logger.debug(f"Reading tweets from {tweets_file}")
            with open(tweets_file, 'r') as f:
                tweets = json.load(f)
            
            tokens = self.extract_tokens_from_tweets(tweets)
            logger.info(f"Found {len(tokens)} unique tokens: {tokens}")
            
            results = []
            for tweet in tweets:
                for token in tokens:
                    if f"${token}" in tweet['text'] or f"#{token}" in tweet['text']:
                        analysis = await self.analyze_tweet_impact(tweet, token)
                        results.append(analysis)
                        logger.debug(f"Analyzed {token} in tweet {tweet['id']}")
            
            return results
        except Exception as e:
            logger.error(f"Error analyzing tweets: {e}")
            return []

    def save_analysis(self, results: List[Dict], output_path: Path):
        """Save analysis results to JSON file."""
        try:
            # Save full analysis
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Saved analysis to {output_path}")
            
            # Save summary CSV
            summary_path = output_path.parent / 'price_analysis_summary.csv'
            with open(summary_path, 'w') as f:
                f.write("Token,First Price,24h Price,7d Price,30d Price,24h Change,7d Change,30d Change,Market Cap,Liquidity,DEX,Chain\n")
                for result in results:
                    if 'error' in result:
                        f.write(f"{result['token']},Error: {result['error']}\n")
                        continue
                        
                    f.write(f"{result['token']},"
                           f"{result.get('first_mention_price_usd', 'N/A')},"
                           f"{result.get('post_24h_price_usd', 'N/A')},"
                           f"{result.get('post_7d_price_usd', 'N/A')},"
                           f"{result.get('post_30d_price_usd', 'N/A')},"
                           f"{result.get('price_change_24h', 'N/A')},"
                           f"{result.get('price_change_7d', 'N/A')},"
                           f"{result.get('price_change_30d', 'N/A')},"
                           f"{result.get('market_cap', 'N/A')},"
                           f"{result.get('first_mention_liquidity_usd', 'N/A')},"
                           f"{result.get('dex_id', 'N/A')},"
                           f"{result.get('chain_id', 'N/A')}\n")
            logger.info(f"Saved summary to {summary_path}")
            
        except Exception as e:
            logger.error(f"Error saving analysis: {e}")

    def print_analysis_summary(self, results: List[Dict]):
        """Print a formatted summary of the analysis results."""
        print("\n=== Token Price Analysis Summary ===\n")
        
        for result in results:
            if 'error' in result:
                print(f"\nToken: ${result['token']}")
                print(f"Error: {result['error']}")
                continue
                
            print(f"\nToken: ${result['token']}")
            if result.get('token_name'):
                print(f"Token Name: {result['token_name']}")
            if result.get('token_address'):
                print(f"Contract Address: {result['token_address']}")
            if result.get('chain_id'):
                print(f"Chain: {result['chain_id']}")
            
            print(f"\nTweet Time: {result['tweet_time']}")
            
            # Calculate and display timeframes
            tweet_time = datetime.fromisoformat(result['tweet_time'].replace('Z', '+00:00'))
            current_time = datetime.now(UTC)
            first_mention_time = tweet_time + self.timeframes['first_mention']
            post_24h_time = tweet_time + self.timeframes['post_24h']
            post_7d_time = tweet_time + self.timeframes['post_7d']
            post_30d_time = tweet_time + self.timeframes['post_30d']
            
            print("\nPrice Data:")
            if result.get('first_mention_price_usd'):
                print(f"First Mention (Target: {first_mention_time.isoformat()}): ${result['first_mention_price_usd']} ({result.get('first_mention_data_source', 'unknown')})")
                print(f"Checked at: {result.get('first_mention_timestamp', 'unknown')}")
            
            # Calculate and display price changes
            first_price = float(result.get('first_mention_price_usd') or 0)
            
            # 24h price change
            if post_24h_time <= current_time and result.get('post_24h_price_usd') is not None:
                post_24h_price = float(result['post_24h_price_usd'])
                price_change_24h = ((post_24h_price - first_price) / first_price * 100) if first_price > 0 else 0
                print(f"\n24h After (Target: {post_24h_time.isoformat()}): ${post_24h_price:.6f} ({price_change_24h:+.2f}%)")
                print(f"Checked at: {result.get('post_24h_timestamp', 'unknown')}")
            else:
                print(f"\n24h After (Target: {post_24h_time.isoformat()}): N/A (Future date)")
            
            # 7d price change
            if post_7d_time <= current_time and result.get('post_7d_price_usd') is not None:
                post_7d_price = float(result['post_7d_price_usd'])
                price_change_7d = ((post_7d_price - first_price) / first_price * 100) if first_price > 0 else 0
                print(f"7d After (Target: {post_7d_time.isoformat()}): ${post_7d_price:.6f} ({price_change_7d:+.2f}%)")
                print(f"Checked at: {result.get('post_7d_timestamp', 'unknown')}")
            else:
                print(f"7d After (Target: {post_7d_time.isoformat()}): N/A (Future date)")
            
            # 30d price change
            if post_30d_time <= current_time and result.get('post_30d_price_usd') is not None:
                post_30d_price = float(result['post_30d_price_usd'])
                price_change_30d = ((post_30d_price - first_price) / first_price * 100) if first_price > 0 else 0
                print(f"30d After (Target: {post_30d_time.isoformat()}): ${post_30d_price:.6f} ({price_change_30d:+.2f}%)")
                print(f"Checked at: {result.get('post_30d_timestamp', 'unknown')}")
            else:
                print(f"30d After (Target: {post_30d_time.isoformat()}): N/A (Future date)")
            
            if result.get('dex_id'):
                print(f"\nDEX: {result['dex_id']}")
            if result.get('pair_url'):
                print(f"Pair URL: {result['pair_url']}")
            print("-" * 80)

async def main():
    """Example usage of PriceAnalyzer."""
    analyzer = PriceAnalyzer()
    
    # Get absolute paths
    workspace_dir = Path(os.getcwd())
    tweets_file = workspace_dir / 'kol_analysis' / 'data' / 'tweets_data.json'
    output_path = workspace_dir / 'kol_analysis' / 'data' / 'price_analysis.json'
    
    logger.debug(f"Workspace directory: {workspace_dir}")
    logger.debug(f"Tweets file path: {tweets_file}")
    logger.debug(f"Output path: {output_path}")
    
    results = await analyzer.analyze_all_tweets(tweets_file)
    
    if results:
        analyzer.save_analysis(results, output_path)
        analyzer.print_analysis_summary(results)
        print(f"\nAnalyzed {len(results)} tweet-token pairs")
        print(f"Results saved to:")
        print(f"- JSON: {output_path}")
        print(f"- Summary: {output_path.parent / 'price_analysis_summary.csv'}")
    else:
        print("No analysis results")

if __name__ == '__main__':
    asyncio.run(main()) 