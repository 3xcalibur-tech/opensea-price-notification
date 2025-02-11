OpenSea Price Tracker

A Python-based tool that monitors OpenSea NFT collection prices and sends updates to a Telegram channel when prices change.

Features
--------
- Real-time monitoring of OpenSea collection floor prices and best offers
- Automatic price change notifications via Telegram
- Price change indicators (+ for increase, - for decrease)
- Persistent price memory to track changes
- Configurable check intervals
- Robust error handling and retry mechanisms

Prerequisites
------------
- Python 3.9+
- A Telegram bot token (get from @BotFather)
- A Telegram channel where the bot is an administrator
- The collection slug from OpenSea URL (e.g., "hypio" from opensea.io/collection/hypio)

Installation
-----------
1. Clone the repository:
   git clone https://github.com/yourusername/opensea-price-tracker.git
   cd opensea-price-tracker

2. Create and activate a virtual environment:
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install dependencies:
   pip install -r requirements.txt

4. Create a .env file in the project root with your configuration:
   # OpenSea Configuration
   OPENSEA_COLLECTION_SLUG=hypio

   # Telegram Configuration
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHANNEL_ID=your_channel_id_here

   # Monitoring Configuration
   CHECK_INTERVAL=300  # Time in seconds between checks (5 minutes)

Usage
-----
1. Start the price monitor:
   python main.py

2. The bot will:
   - Check prices every 5 minutes (configurable)
   - Send notifications only when prices change
   - Show price movement indicators (+ for increase, - for decrease)
   - Store the last known prices in memory.json

Example notification:
HYPIO Update

Floor Price: 0.441 ETH +
Best Offer: 0.407 WETH -

Project Structure
----------------
- main.py - Main monitoring loop and price tracking logic
- opensea.py - OpenSea scraping service with retry mechanism
- telegram.py - Telegram notification service
- memory.json - Persistent storage for last known prices
- .env - Configuration file

Configuration
------------
Telegram Setup:
1. Create a new bot with @BotFather
2. Get the bot token
3. Create a channel and add the bot as administrator
4. Get the channel ID (forward a message to @userinfobot)

Environment Variables:
- OPENSEA_COLLECTION_SLUG: Collection identifier from OpenSea URL
- TELEGRAM_BOT_TOKEN: Your bot's API token
- TELEGRAM_CHANNEL_ID: Your channel's ID (usually starts with -100)
- CHECK_INTERVAL: Time between price checks in seconds

Error Handling
-------------
The tool includes:
- Automatic retries for failed requests
- Connection error handling
- Price validation
- Session management
- Comprehensive logging

Logging
-------
Logs are written to:
- Console output
- price_monitor.log file

Dependencies
-----------
pip install:
- aiogram
- python-dotenv
- playwright

Additional setup:
playwright install chromium

Contributing
-----------
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

License
-------
This project is licensed under the MIT License - see the LICENSE file for details.
