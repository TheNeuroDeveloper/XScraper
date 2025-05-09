"""
Token matching module for detecting cryptocurrency mentions in tweets.
"""

import json
import re
from pathlib import Path
import logging
from typing import Dict, List, Set, Optional
import asyncio
import aiohttp
from datetime import datetime, timedelta

from ..config.config import TOKEN_LIST_PATH, DEXSCREENER_API_BASE

logger = logging.getLogger(__name__)

class TokenMatcher:
    def __init__(self):
        """Initialize token matcher with token list."""
        self.tokens = {}
        self.token_patterns = {}
        self.alias_patterns = {}
        self.load_tokens()
        
    def load_tokens(self):
        """Load token list and compile regex patterns."""
        try:
            with open(TOKEN_LIST_PATH, 'r') as f:
                self.tokens = json.load(f)
            
            # Compile regex patterns for token symbols ($SYMBOL)
            self.token_patterns = {
                symbol: re.compile(rf'\${symbol}\b', re.IGNORECASE)
                for symbol in self.tokens.keys()
            }
            
            # Compile regex patterns for token names and aliases
            self.alias_patterns = {}
            for symbol, data in self.tokens.items():
                patterns = []
                if 'name' in data:
                    patterns.append(rf'\b{re.escape(data["name"])}\b')
                if 'aliases' in data:
                    patterns.extend(rf'\b{re.escape(alias)}\b' for alias in data['aliases'])
                if patterns:
                    self.alias_patterns[symbol] = re.compile('|'.join(patterns), re.IGNORECASE)
            
            logger.info(f"Loaded {len(self.tokens)} tokens")
            logger.debug(f"Token patterns: {self.token_patterns}")
            logger.debug(f"Alias patterns: {self.alias_patterns}")
            
        except Exception as e:
            logger.error(f"Error loading token list: {e}")
            raise
    
    def find_mentions(self, text: str) -> Set[str]:
        """Find token mentions in tweet text."""
        mentions = set()
        
        # First check for token symbols ($SYMBOL)
        for symbol, pattern in self.token_patterns.items():
            if pattern.search(text):
                mentions.add(symbol)
                logger.debug(f"Found token symbol mention: ${symbol}")
        
        # Then check for token names and aliases
        for symbol, pattern in self.alias_patterns.items():
            if pattern.search(text):
                mentions.add(symbol)
                logger.debug(f"Found token name/alias mention: {symbol}")
        
        # Look for potential new tokens ($SYMBOL format)
        new_token_matches = re.finditer(r'\$([A-Za-z0-9]+)\b', text)
        for match in new_token_matches:
            symbol = match.group(1).upper()
            if symbol not in self.tokens:
                logger.debug(f"Potential new token found: ${symbol}")
        
        return mentions
    
    async def add_new_token(self, symbol: str, name: Optional[str] = None, aliases: Optional[List[str]] = None):
        """Add a new token to the list."""
        symbol = symbol.upper()
        if symbol not in self.tokens:
            self.tokens[symbol] = {
                'name': name or symbol,
                'aliases': aliases or []
            }
            
            # Update patterns
            self.token_patterns[symbol] = re.compile(rf'\${symbol}\b', re.IGNORECASE)
            
            patterns = []
            if name:
                patterns.append(rf'\b{re.escape(name)}\b')
            if aliases:
                patterns.extend(rf'\b{re.escape(alias)}\b' for alias in aliases)
            if patterns:
                self.alias_patterns[symbol] = re.compile('|'.join(patterns), re.IGNORECASE)
            
            # Save updated token list
            with open(TOKEN_LIST_PATH, 'w') as f:
                json.dump(self.tokens, f, indent=2)
            
            logger.info(f"Added new token: {symbol}")
    
    async def fetch_token_info(self, symbol: str) -> Optional[Dict]:
        """Fetch token information from DexScreener API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{DEXSCREENER_API_BASE}/tokens/{symbol}") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
        except Exception as e:
            logger.error(f"Error fetching token info for {symbol}: {e}")
        return None
    
    async def process_tweets(self, tweets: Dict[str, List[Dict]]) -> List[Dict]:
        """Process tweets and find token mentions."""
        results = []
        
        for handle, handle_tweets in tweets.items():
            logger.debug(f"Processing tweets from @{handle}")
            for tweet in handle_tweets:
                text = tweet.get('text', '')
                logger.debug(f"Analyzing tweet text: {text}")
                
                mentions = self.find_mentions(text)
                if mentions:
                    logger.debug(f"Found mentions in tweet: {mentions}")
                    results.append({
                        'handle': handle,
                        'tweet_id': tweet.get('id'),
                        'text': text,
                        'timestamp': tweet.get('timestamp'),
                        'matched_tokens': list(mentions)
                    })
                    
                    # Check for new tokens
                    for symbol in mentions:
                        if symbol not in self.tokens:
                            token_info = await self.fetch_token_info(symbol)
                            if token_info:
                                await self.add_new_token(
                                    symbol,
                                    name=token_info.get('name'),
                                    aliases=token_info.get('aliases', [])
                                )
        
        logger.info(f"Found {len(results)} tweets with token mentions")
        return results

def main():
    """Example usage."""
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Sample tweets
    sample_tweets = {
        'elonmusk': [
            {
                'id': '1',
                'text': 'Just bought some $BTC and $ETH!',
                'timestamp': datetime.now().isoformat()
            }
        ]
    }
    
    # Process tweets
    matcher = TokenMatcher()
    results = asyncio.run(matcher.process_tweets(sample_tweets))
    
    # Print results
    for result in results:
        print(f"\nHandle: @{result['handle']}")
        print(f"Tweet: {result['text']}")
        print(f"Timestamp: {result['timestamp']}")
        print(f"Matched tokens: {', '.join(result['matched_tokens'])}")

if __name__ == '__main__':
    main() 