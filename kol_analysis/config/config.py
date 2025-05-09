"""
Configuration settings for the KOL analysis system.
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = BASE_DIR / 'data'
SRC_DIR = BASE_DIR / 'src'

# API endpoints
DEXSCREENER_API_BASE = "https://api.dexscreener.com/latest"
COINGECKO_API_BASE = "https://api.coingecko.com/api/v3"

# Time intervals for price analysis (in minutes)
TIME_INTERVALS = {
    '1h': 60,
    '6h': 360,
    '24h': 1440
}

# High-impact tweet thresholds (percentage change)
HIGH_IMPACT_THRESHOLDS = {
    '1h': 5.0,  # 5% change in 1 hour
    '6h': 10.0,  # 10% change in 6 hours
    '24h': 15.0  # 15% change in 24 hours
}

# Volume spike threshold (times normal volume)
VOLUME_SPIKE_THRESHOLD = 3.0

# File paths
TOKEN_LIST_PATH = DATA_DIR / 'token_list.json'
TWEETS_DATA_PATH = DATA_DIR / 'tweets_data.json'
RESULTS_PATH = DATA_DIR / 'results.csv'
GRAPHS_DIR = DATA_DIR / 'graphs'

# Create directories if they don't exist
for directory in [DATA_DIR, GRAPHS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Twitter API settings
TWITTER_API_BASE = "https://api.twitter.com/2"
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

# Default headers for API requests
DEFAULT_HEADERS = {
    'Accept': 'application/json',
    'User-Agent': 'KOLAnalysisBot/1.0'
} 