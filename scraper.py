import requests
import json
import os
import argparse
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# === CONFIGURATION ===
USERNAME = "elonmusk"  # Can be changed as needed
AUTH_TOKEN = os.getenv('X_AUTH_TOKEN')
CT0 = os.getenv('X_CT0')
BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

def load_graphql_hashes():
    """Load GraphQL operation hashes from JSON file"""
    try:
        with open("graphql_hashes.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("GraphQL hashes file not found. Please run get_hashes.py first")
        return None
    except json.JSONDecodeError:
        logger.error("Invalid GraphQL hashes file")
        return None

# Load GraphQL hashes
GRAPHQL_HASHES = load_graphql_hashes()
if not GRAPHQL_HASHES:
    raise ValueError("Could not load GraphQL hashes")

# Required features for the API
FEATURES = {
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
}

def get_headers():
    return {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "X-Csrf-Token": CT0,
        "X-Twitter-Active-User": "yes",
        "X-Twitter-Client-Language": "en",
        "X-Twitter-Auth-Type": "OAuth2Session",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cookie": f"auth_token={AUTH_TOKEN}; ct0={CT0};",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"'
    }

def get_user_id(username):
    """Get user ID from username"""
    if "UserByScreenName" not in GRAPHQL_HASHES:
        logger.error("UserByScreenName operation not found in GraphQL hashes")
        return None
        
    url = f"https://twitter.com/i/api/graphql/{GRAPHQL_HASHES['UserByScreenName']}/UserByScreenName"
    variables = {
        "screen_name": username,
        "withSafetyModeUserFields": True
    }
    params = {
        "variables": json.dumps(variables),
        "features": json.dumps(FEATURES)
    }
    
    response = requests.get(url, params=params, headers=get_headers())
    
    if response.status_code == 200:
        data = response.json()
        user_id = data.get('data', {}).get('user', {}).get('result', {}).get('rest_id')
        if user_id:
            return user_id
        else:
            logger.error("Could not find user ID in response")
            return None
    else:
        logger.error(f"Failed to get user ID: {response.status_code}")
        return None

def fetch_tweets(username, count=10):
    """Fetch tweets for a given username"""
    # First get the user ID
    user_id = get_user_id(username)
    if not user_id:
        return []
    
    # Now fetch tweets using the user ID
    if "UserTweets" not in GRAPHQL_HASHES:
        logger.error("UserTweets operation not found in GraphQL hashes")
        return None
        
    url = f"https://twitter.com/i/api/graphql/{GRAPHQL_HASHES['UserTweets']}/UserTweets"
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
    
    params = {
        "variables": json.dumps(variables),
        "features": json.dumps(FEATURES)
    }
    
    try:
        response = requests.get(url, params=params, headers=get_headers())
        
        if response.status_code == 200:
            data = response.json()
            
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
            
            tweets = []
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
                                'id': tweet.get('rest_id'),
                                'text': tweet['legacy'].get('full_text'),
                                'created_at': tweet['legacy'].get('created_at'),
                                'retweet_count': tweet['legacy'].get('retweet_count', 0),
                                'favorite_count': tweet['legacy'].get('favorite_count', 0),
                                'user': username,
                                'pinned': True
                            }
                            tweets.append(tweet_data)
                            print(f"\n📌 {tweet_data['text']}")
                
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
                                'id': tweet.get('rest_id'),
                                'text': tweet['legacy'].get('full_text'),
                                'created_at': tweet['legacy'].get('created_at'),
                                'retweet_count': tweet['legacy'].get('retweet_count', 0),
                                'favorite_count': tweet['legacy'].get('favorite_count', 0),
                                'user': username
                            }
                            tweets.append(tweet_data)
                            print(f"\n{tweet_data['text']}")
                            
                            # Stop if we have enough tweets
                            if len(tweets) >= count:
                                break
                
                # Stop if we have enough tweets
                if len(tweets) >= count:
                    break
            
            return tweets
            
        else:
            logger.error(f"Request failed: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"Error fetching tweets: {str(e)}")
        return []

def main():
    parser = argparse.ArgumentParser(description='Fetch tweets from a Twitter user')
    parser.add_argument('username', help='Twitter username to fetch tweets from')
    parser.add_argument('--count', type=int, default=10, help='Number of tweets to fetch (default: 10)')
    args = parser.parse_args()
    
    if not AUTH_TOKEN or not CT0:
        logger.error("X_AUTH_TOKEN and X_CT0 must be set in environment variables")
        return
        
    tweets = fetch_tweets(args.username, args.count)
    
    if tweets:
        # Save to JSON file
        filename = f"{args.username}_tweets.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(tweets, f, ensure_ascii=False, indent=2)
        print(f"\nSaved {len(tweets)} tweets to {filename}")

if __name__ == "__main__":
    main() 