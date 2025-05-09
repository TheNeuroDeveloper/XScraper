"""
Tweet fetching module for KOL analysis using X's GraphQL API.
"""

import os
import json
import logging
import aiohttp
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables from kol_analysis/.env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Configure logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

class TweetFetcher:
    def __init__(self):
        """Initialize tweet fetcher with auth tokens from env."""
        self.auth_token = os.getenv('auth_token')
        self.ct0 = os.getenv('ct0')
        if not self.auth_token or not self.ct0:
            logger.error(f"Environment variables not found in {env_path}")
            raise ValueError("auth_token and ct0 environment variables must be set")
            
        self.base_url = "https://twitter.com/i/api/graphql"
        # Load GraphQL hashes from kol_analysis folder
        hashes_path = Path(__file__).parent.parent / 'graphql_hashes.json'
        try:
            with open(hashes_path, 'r') as f:
                hashes = json.load(f)
                self.user_by_screen_name_query_id = hashes.get('UserByScreenName')
                self.user_tweets_query_id = hashes.get('UserTweets')
                if not self.user_by_screen_name_query_id or not self.user_tweets_query_id:
                    raise ValueError("Required GraphQL hashes not found")
                logger.debug(f"Loaded GraphQL hashes from {hashes_path}")
        except Exception as e:
            logger.error(f"Error loading GraphQL hashes from {hashes_path}: {e}")
            raise

    def get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'cookie': f'auth_token={self.auth_token}; ct0={self.ct0}',
            'x-csrf-token': self.ct0,
            'x-twitter-active-user': 'yes',
            'x-twitter-auth-type': 'OAuth2Session',
            'x-twitter-client-language': 'en',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'connection': 'keep-alive',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"'
        }

    async def get_user_id(self, username: str, session: aiohttp.ClientSession) -> Optional[str]:
        """Get user ID from username."""
        variables = {
            "screen_name": username,
            "withSafetyModeUserFields": True
        }
        
        url = f"{self.base_url}/{self.user_by_screen_name_query_id}/UserByScreenName"
        params = {
            'variables': json.dumps(variables),
            'features': json.dumps({
                "responsive_web_enhance_cards_enabled": False,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "communities_web_enable_tweet_community_results_fetch": True,
                "longform_notetweets_inline_media_enabled": True,
                "responsive_web_jetfuel_frame": False,
                "responsive_web_grok_show_grok_translated_post": False,
                "responsive_web_edit_tweet_api_enabled": True,
                "responsive_web_grok_analysis_button_from_backend": False,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_grok_share_attachment_enabled": False,
                "responsive_web_grok_image_annotation_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "rweb_tipjar_consumption_enabled": True,
                "premium_content_api_read_enabled": False,
                "tweet_awards_web_tipping_enabled": False,
                "responsive_web_twitter_article_tweet_consumption_enabled": True,
                "creator_subscriptions_quote_tweet_preview_enabled": False,
                "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "view_counts_everywhere_api_enabled": True,
                "responsive_web_grok_analyze_post_followups_enabled": False,
                "articles_preview_enabled": False,
                "standardized_nudges_misinfo": True,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "profile_label_improvements_pcf_label_in_post_enabled": False,
                "verified_phone_label_enabled": False,
                "longform_notetweets_rich_text_read_enabled": True,
                "rweb_video_screen_enabled": False,
                "subscriptions_verification_info_is_identity_verified_enabled": False,
                "subscriptions_verification_info_verified_since_enabled": False,
                "responsive_web_twitter_article_notes_tab_enabled": False,
                "hidden_profile_subscriptions_enabled": False,
                "highlights_tweets_tab_ui_enabled": False,
                "subscriptions_feature_can_gift_premium": False
            })
        }
        
        try:
            logger.debug(f"Fetching user ID for @{username}")
            logger.debug(f"Request URL: {url}")
            logger.debug(f"Request params: {params}")
            
            async with session.get(url, headers=self.get_headers(), params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Response data: {json.dumps(data, indent=2)}")
                    return data['data']['user']['result']['rest_id']
                else:
                    response_text = await response.text()
                    logger.error(f"Failed to get user ID for {username}: {response.status}")
                    logger.error(f"Response: {response_text}")
                    return None
        except Exception as e:
            logger.error(f"Error getting user ID for {username}: {e}")
            return None
            
    async def fetch_user_tweets(self, username: str, count: int = 10) -> List[Dict]:
        """
        Fetch recent tweets from a user.
        
        Args:
            username: Twitter handle without @
            count: Number of tweets to fetch
            
        Returns:
            List of tweet dictionaries
        """
        async with aiohttp.ClientSession() as session:
            user_id = await self.get_user_id(username, session)
            if not user_id:
                return []
                
            variables = {
                "userId": user_id,
                "count": count,
                "includePromotedContent": False,
                "withQuickPromoteEligibilityTweetFields": True,
                "withSuperFollowsUserFields": True,
                "withDownvotePerspective": False,
                "withReactionsMetadata": False,
                "withReactionsPerspective": False,
                "withSuperFollowsTweetFields": True,
                "withVoice": True,
                "withV2Timeline": True
            }
            
            url = f"{self.base_url}/{self.user_tweets_query_id}/UserTweets"
            params = {
                'variables': json.dumps(variables),
                'features': json.dumps({
                    "responsive_web_enhance_cards_enabled": False,
                    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                    "communities_web_enable_tweet_community_results_fetch": True,
                    "longform_notetweets_inline_media_enabled": True,
                    "responsive_web_jetfuel_frame": False,
                    "responsive_web_grok_show_grok_translated_post": False,
                    "responsive_web_edit_tweet_api_enabled": True,
                    "responsive_web_grok_analysis_button_from_backend": False,
                    "creator_subscriptions_tweet_preview_api_enabled": True,
                    "responsive_web_grok_share_attachment_enabled": False,
                    "responsive_web_grok_image_annotation_enabled": False,
                    "freedom_of_speech_not_reach_fetch_enabled": True,
                    "rweb_tipjar_consumption_enabled": True,
                    "premium_content_api_read_enabled": False,
                    "tweet_awards_web_tipping_enabled": False,
                    "responsive_web_twitter_article_tweet_consumption_enabled": True,
                    "creator_subscriptions_quote_tweet_preview_enabled": False,
                    "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
                    "responsive_web_graphql_timeline_navigation_enabled": True,
                    "longform_notetweets_consumption_enabled": True,
                    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                    "view_counts_everywhere_api_enabled": True,
                    "responsive_web_grok_analyze_post_followups_enabled": False,
                    "articles_preview_enabled": False,
                    "standardized_nudges_misinfo": True,
                    "c9s_tweet_anatomy_moderator_badge_enabled": True,
                    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                    "profile_label_improvements_pcf_label_in_post_enabled": False,
                    "verified_phone_label_enabled": False,
                    "longform_notetweets_rich_text_read_enabled": True,
                    "rweb_video_screen_enabled": False,
                    "subscriptions_verification_info_is_identity_verified_enabled": False,
                    "subscriptions_verification_info_verified_since_enabled": False,
                    "responsive_web_twitter_article_notes_tab_enabled": False,
                    "hidden_profile_subscriptions_enabled": False,
                    "highlights_tweets_tab_ui_enabled": False,
                    "subscriptions_feature_can_gift_premium": False
                })
            }
            
            try:
                logger.debug(f"Fetching tweets for @{username}")
                logger.debug(f"Request URL: {url}")
                logger.debug(f"Request params: {params}")
                
                async with session.get(url, headers=self.get_headers(), params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"Response data: {json.dumps(data, indent=2)}")
                        tweets = []
                        
                        # Get the timeline entries
                        user_data = data.get('data', {}).get('user', {}).get('result', {})
                        if not user_data:
                            logger.error("No user data found in response")
                            return []
                            
                        timeline = user_data.get('timeline', {})
                        if not timeline:
                            logger.error("No timeline found in response")
                            return []
                            
                        instructions = timeline.get('timeline', {}).get('instructions', [])
                        if not instructions:
                            logger.error("No instructions found in timeline")
                            return []
                        
                        for instruction in instructions:
                            # Skip non-tweet instructions
                            if instruction.get('type') not in ['TimelinePinEntry', 'TimelineAddEntries']:
                                continue
                                
                            # Handle pinned tweet
                            if instruction.get('type') == 'TimelinePinEntry':
                                entry = instruction.get('entry', {})
                                if entry and entry.get('content', {}).get('itemContent', {}).get('tweet_results'):
                                    tweet = entry['content']['itemContent']['tweet_results'].get('result', {})
                                    if tweet and 'legacy' in tweet:
                                        tweet_data = {
                                            'tweet_id': tweet.get('rest_id'),
                                            'text': tweet['legacy'].get('full_text'),
                                            'timestamp': tweet['legacy'].get('created_at'),
                                            'handle': username,
                                            'retweet_count': tweet['legacy'].get('retweet_count', 0),
                                            'favorite_count': tweet['legacy'].get('favorite_count', 0),
                                            'reply_count': tweet['legacy'].get('reply_count', 0),
                                            'quote_count': tweet['legacy'].get('quote_count', 0),
                                            'pinned': True
                                        }
                                        tweets.append(tweet_data)
                                        logger.info(f"Found pinned tweet: {tweet_data['text'][:100]}...")
                            
                            # Handle regular tweets
                            elif instruction.get('type') == 'TimelineAddEntries':
                                entries = instruction.get('entries', [])
                                for entry in entries:
                                    # Skip if not a tweet entry
                                    if not entry.get('content', {}).get('itemContent', {}).get('tweet_results'):
                                        continue
                                        
                                    tweet = entry['content']['itemContent']['tweet_results'].get('result', {})
                                    if tweet and 'legacy' in tweet:
                                        tweet_data = {
                                            'tweet_id': tweet.get('rest_id'),
                                            'text': tweet['legacy'].get('full_text'),
                                            'timestamp': tweet['legacy'].get('created_at'),
                                            'handle': username,
                                            'retweet_count': tweet['legacy'].get('retweet_count', 0),
                                            'favorite_count': tweet['legacy'].get('favorite_count', 0),
                                            'reply_count': tweet['legacy'].get('reply_count', 0),
                                            'quote_count': tweet['legacy'].get('quote_count', 0)
                                        }
                                        tweets.append(tweet_data)
                                        logger.info(f"Found tweet: {tweet_data['text'][:100]}...")
                                        
                                        # Stop if we have enough tweets
                                        if len(tweets) >= count:
                                            break
                            
                            # Stop if we have enough tweets
                            if len(tweets) >= count:
                                break
                        
                        return tweets
                    else:
                        response_text = await response.text()
                        logger.error(f"Failed to fetch tweets: {response.status}")
                        logger.error(f"Response: {response_text}")
                        return []
            except Exception as e:
                logger.error(f"Error fetching tweets: {e}")
                return []
                
    async def save_tweets(self, tweets: List[Dict], output_path: Path):
        """Save tweets to JSON file."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(tweets, f, indent=2)
            logger.info(f"Saved {len(tweets)} tweets to {output_path}")
        except Exception as e:
            logger.error(f"Error saving tweets: {e}")

async def main():
    """Example usage of TweetFetcher."""
    fetcher = TweetFetcher()
    
    # Get absolute paths
    workspace_dir = Path(os.getcwd())
    output_path = workspace_dir / 'kol_analysis' / 'data' / 'tweets_data.json'
    
    logger.debug(f"Workspace directory: {workspace_dir}")
    logger.debug(f"Output path: {output_path}")
    
    # Fetch tweets from @deanbulla
    tweets = await fetcher.fetch_user_tweets('deanbulla', count=20)
    
    if tweets:
        fetcher.save_tweets(tweets, output_path)
        print(f"\nFetched {len(tweets)} tweets from @deanbulla")
        print(f"Results saved to: {output_path}")
    else:
        print("No tweets fetched")

if __name__ == '__main__':
    asyncio.run(main()) 