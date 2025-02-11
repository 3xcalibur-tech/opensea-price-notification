import json
import logging
import os
import time
from typing import Dict, Optional
from dotenv import load_dotenv

from opensea import OpenSeaService
from telegram import send_price_update


class PriceMonitor:
    def __init__(self):
        self.logger = self._setup_logging()
        self._load_config()

        self.opensea = OpenSeaService(self.logger)
        self.memory_file = "memory.json"
        self.last_prices = self._load_memory()

    def _setup_logging(self) -> logging.Logger:
        """Configure logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('price_monitor.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger('price_monitor')

    def _load_config(self):
        """Load configuration from .env"""
        load_dotenv()
        self.collection_slug = os.getenv('OPENSEA_COLLECTION_SLUG', 'hypio')
        self.check_interval = int(
            os.getenv('CHECK_INTERVAL', 300))  # 5 minutes default

    def _load_memory(self) -> Dict[str, str]:
        """Load last known prices from memory file"""
        try:
            with open(self.memory_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"floor_price": "0 ETH", "best_offer": "0 ETH"}

    def _save_memory(self, prices: Dict[str, str]):
        """Save current prices to memory file"""
        with open(self.memory_file, 'w') as f:
            json.dump(prices, f, indent=4)

    def _format_price(self, price_tuple) -> str:
        """Format price tuple into string"""
        price, currency = price_tuple
        return f"{price} {currency}"

    def _prices_changed(self, new_prices: Dict[str, str]) -> bool:
        """Check if prices have changed from last known values"""
        return (new_prices['floor_price'] != self.last_prices['floor_price'] or
                new_prices['best_offer'] != self.last_prices['best_offer'])

    def check_prices(self) -> Optional[Dict[str, str]]:
        """Get current prices from OpenSea"""
        try:
            result = self.opensea.get_collection_prices(self.collection_slug)
            if not result:
                return None

            # Format prices
            return {
                'floor_price': f"{result['floor_price'][0]} {result['floor_price'][1]}",
                'best_offer': f"{result['best_offer'][0]} {result['best_offer'][1]}"
            }
        except Exception as e:
            self.logger.error(f"Error checking prices: {str(e)}")
            return None

    def run(self):
        """Main monitoring loop"""
        self.logger.info(f"Starting price monitor for {self.collection_slug}")
        self.logger.info(f"Check interval: {self.check_interval} seconds")
        self.logger.info(f"Last known prices: {self.last_prices}")

        while True:
            try:
                # Get current prices
                current_prices = self.check_prices()

                if not current_prices:
                    self.logger.warning(
                        "Failed to get current prices, will retry next interval")
                    time.sleep(self.check_interval)
                    continue

                # Check if prices changed
                if self._prices_changed(current_prices):
                    self.logger.info("Price change detected!")
                    self.logger.info(f"Old prices: {self.last_prices}")
                    self.logger.info(f"New prices: {current_prices}")

                    # Send notification with old prices for comparison
                    if send_price_update(
                        collection=self.collection_slug,
                        floor_price=current_prices['floor_price'],
                        best_offer=current_prices['best_offer'],
                        old_prices=self.last_prices  # Pass old prices for comparison
                    ):
                        self.logger.info("Notification sent successfully")
                        # Update memory only after successful notification
                        self._save_memory(current_prices)
                        self.last_prices = current_prices
                    else:
                        self.logger.error("Failed to send notification")
                else:
                    self.logger.info("No price changes detected")

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")

            # Wait for next check
            self.logger.info(
                f"Waiting {self.check_interval} seconds until next check...")
            time.sleep(self.check_interval)


def main():
    monitor = PriceMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
