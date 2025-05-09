"""
Main script for running KOL impact analysis.
"""

import argparse
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
import json
import os

from .match_tokens import TokenMatcher
from .analyze_price import PriceAnalyzer
from .report_generator import ReportGenerator
from ..config.config import TWEETS_DATA_PATH, RESULTS_PATH

logger = logging.getLogger(__name__)

def load_tweets(handles: list[str], days: int = 1) -> dict:
    """
    Load tweets from the tweets data file.
    
    Args:
        handles: List of Twitter handles to analyze
        days: Number of days of tweets to analyze
    
    Returns:
        Dict mapping handles to lists of tweets
    """
    try:
        with open(TWEETS_DATA_PATH, 'r') as f:
            all_tweets = json.load(f)
        
        # Filter tweets by handle and date
        # For testing purposes, we'll use a future cutoff date
        cutoff_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        filtered_tweets = {}
        
        for handle in handles:
            if handle in all_tweets:
                filtered_tweets[handle] = [
                    tweet for tweet in all_tweets[handle]
                    if datetime.fromisoformat(tweet['timestamp'].replace('Z', '+00:00')) > cutoff_time
                ]
                logger.info(f"Loaded {len(filtered_tweets[handle])} tweets from @{handle}")
            else:
                logger.warning(f"No tweets found for @{handle}")
        
        return filtered_tweets
    except FileNotFoundError:
        logger.error(f"Tweets data file not found at {TWEETS_DATA_PATH}")
        return {}
    except json.JSONDecodeError:
        logger.error("Invalid tweets data JSON format")
        return {}

async def analyze_kol_impact(handles: list[str], days: int, output_dir: Path) -> None:
    """
    Analyze the impact of KOL tweets on token prices.
    
    Args:
        handles: List of Twitter handles to analyze
        days: Number of days of tweets to analyze
        output_dir: Directory to save reports
    """
    try:
        # Load and process tweets
        tweets = load_tweets(handles, days)
        if not tweets:
            logger.error("No tweets to analyze")
            return
        
        # Find token mentions
        token_matcher = TokenMatcher()
        tweets_with_tokens = await token_matcher.process_tweets(tweets)
        logger.info(f"Found {len(tweets_with_tokens)} tweets with token mentions")
        
        if not tweets_with_tokens:
            logger.warning("No tweets with token mentions found")
            return
        
        # Analyze price impact
        async with PriceAnalyzer() as price_analyzer:
            results = []
            for tweet in tweets_with_tokens:
                result = await price_analyzer.analyze_tweet_impact(tweet)
                results.append(result)
            
            # Save results
            price_analyzer.save_results(results)
        
        # Generate report
        report_generator = ReportGenerator(RESULTS_PATH)
        report_generator.generate_report(output_dir)
        logger.info(f"Generated report in {output_dir}")
        
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        raise

def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Analyze KOL impact on token prices")
    parser.add_argument(
        "--handles",
        nargs="+",
        required=True,
        help="Twitter handles to analyze"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of days to analyze (default: 1)"
    )
    parser.add_argument(
        "--output",
        default="reports",
        help="Output directory for reports (default: reports)"
    )
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if 'LOG_LEVEL' in os.environ else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run analysis
    asyncio.run(analyze_kol_impact(
        handles=args.handles,
        days=args.days,
        output_dir=Path(args.output)
    ))

if __name__ == '__main__':
    main() 