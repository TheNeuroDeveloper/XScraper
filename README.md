# X Scraper Bot

A Python-based scraper for X (formerly Twitter) using the official API.

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the root directory with your X API credentials:
```
X_API_KEY=your_api_key
X_API_SECRET=your_api_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_TOKEN_SECRET=your_access_token_secret
```

3. Run the scraper:
```bash
python scraper.py
```

## Features

- Fetch tweets from specific users
- Search tweets by keywords
- Save results to CSV files
- Rate limit handling
- Error handling and logging

## Note

Make sure to comply with X's API terms of service and rate limits when using this scraper. 