import os
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class XScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Twitter-Active-User': 'yes',
            'X-Twitter-Client-Language': 'en'
        })
        self._load_cookies()
        
    def _load_cookies(self):
        """Load cookies from environment variables"""
        load_dotenv()
        auth_token = os.getenv('X_AUTH_TOKEN')
        ct0 = os.getenv('X_CT0')
        
        if not auth_token:
            raise ValueError("X_AUTH_TOKEN not found in environment variables")
            
        self.session.cookies.set('auth_token', auth_token, domain='.x.com')
        if ct0:
            self.session.cookies.set('ct0', ct0, domain='.x.com')
            
    def get_user_tweets(self, username, count=20):
        """Fetch tweets from a specific user"""
        try:
            url = f"https://x.com/i/api/2/timeline/profile/{username}.json"
            params = {
                'count': count,
                'include_entities': 'true',
                'include_rts': 'true'
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            tweets = []
            
            for tweet in data.get('globalObjects', {}).get('tweets', {}).values():
                tweet_data = {
                    'id': tweet.get('id_str'),
                    'text': tweet.get('full_text'),
                    'created_at': tweet.get('created_at'),
                    'retweet_count': tweet.get('retweet_count'),
                    'favorite_count': tweet.get('favorite_count'),
                    'user': tweet.get('user', {}).get('screen_name')
                }
                tweets.append(tweet_data)
                
            return tweets
            
        except Exception as e:
            logger.error(f"Error fetching tweets for user {username}: {str(e)}")
            return []
            
    def search_tweets(self, query, count=20):
        """Search tweets by keywords"""
        try:
            url = "https://x.com/i/api/2/search/adaptive.json"
            params = {
                'q': query,
                'count': count,
                'include_entities': 'true'
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            tweets = []
            
            for tweet in data.get('globalObjects', {}).get('tweets', {}).values():
                tweet_data = {
                    'id': tweet.get('id_str'),
                    'text': tweet.get('full_text'),
                    'created_at': tweet.get('created_at'),
                    'retweet_count': tweet.get('retweet_count'),
                    'favorite_count': tweet.get('favorite_count'),
                    'user': tweet.get('user', {}).get('screen_name')
                }
                tweets.append(tweet_data)
                
            return tweets
            
        except Exception as e:
            logger.error(f"Error searching tweets for query {query}: {str(e)}")
            return []
            
    def save_to_json(self, tweets, filename=None):
        """Save tweets to a JSON file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'tweets_{timestamp}.json'
            
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(tweets, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(tweets)} tweets to {filename}")
        except Exception as e:
            logger.error(f"Error saving tweets to {filename}: {str(e)}")

def main():
    scraper = XScraper()
    
    # Example: Fetch tweets from a user
    username = "elonmusk"  # Example username
    tweets = scraper.get_user_tweets(username, count=10)
    scraper.save_to_json(tweets, f"{username}_tweets.json")
    
    # Example: Search tweets
    query = "python programming"
    search_results = scraper.search_tweets(query, count=10)
    scraper.save_to_json(search_results, f"search_{query.replace(' ', '_')}.json")

if __name__ == "__main__":
    main() 