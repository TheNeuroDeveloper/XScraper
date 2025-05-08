# X (Twitter) Scraper

A Python script to scrape tweets from X (formerly Twitter) using their web API. This script uses GraphQL endpoints and session cookies for authentication.

## Features

- Fetch tweets from any public Twitter account
- Get pinned tweets
- Save tweets to JSON file
- Configurable number of tweets to fetch
- Uses GraphQL API for better reliability

## Requirements

- Python 3.7+
- Required packages (install via `pip install -r requirements.txt`):
  - requests
  - python-dotenv

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/XScraperBot.git
cd XScraperBot
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your Twitter session cookies:
```
X_AUTH_TOKEN=your_auth_token_here
X_CT0=your_ct0_here
```

To get these tokens:
1. Log into Twitter in your browser
2. Open Developer Tools (F12)
3. Go to Application tab
4. Look for Cookies under Storage
5. Find and copy the `auth_token` and `ct0` values

## Usage

1. First, get the latest GraphQL hashes:
```bash
python get_hashes.py
```

2. Then fetch tweets:
```bash
python scraper.py username [--count NUMBER]
```

Example:
```bash
python scraper.py elonmusk --count 5
```

This will:
- Fetch 5 tweets from @elonmusk
- Display them in the console
- Save them to `elonmusk_tweets.json`

## Notes

- The script uses Twitter's web API, so it's subject to their rate limits
- Make sure to keep your session tokens secure and never commit them to version control
- The GraphQL hashes need to be updated periodically as Twitter updates their web client

## License

MIT License - feel free to use this code for any purpose.

## Disclaimer

This tool is for educational purposes only. Make sure to comply with Twitter's terms of service and rate limits when using this script. 