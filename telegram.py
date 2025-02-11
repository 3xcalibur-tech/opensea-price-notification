import asyncio
import logging
from typing import Optional, Dict
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import os
from dotenv import load_dotenv


class TelegramService:
    def __init__(self, logger=None):
        """Initialize Telegram service"""
        self.logger = logger or self._setup_default_logger()

        # Load environment variables
        load_dotenv()

        # Get credentials from environment
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.channel_id = os.getenv('TELEGRAM_CHANNEL_ID')

        if not self.bot_token or not self.channel_id:
            raise ValueError("Missing required environment variables")

        # Initialize bot with default properties
        self.bot = Bot(
            token=self.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.dp = Dispatcher()

    async def send_message(self, text: str) -> bool:
        """
        Send message to the channel

        Args:
            text: Message text (can include HTML formatting)

        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        try:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=text
            )
            self.logger.info(
                f"Message sent successfully to channel {self.channel_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send message: {str(e)}")
            return False

        finally:
            await self.close()

    async def send_price_update(self, collection: str,
                                floor_price: str,
                                best_offer: str,
                                old_prices: Optional[Dict[str, str]] = None) -> bool:
        """
        Send formatted price update message with change indicators

        Args:
            collection: Collection name/slug
            floor_price: Floor price with currency (e.g., "0.441 ETH")
            best_offer: Best offer with currency (e.g., "0.407 WETH")
            old_prices: Previous prices for comparison
        """
        def format_change(new_price: str, old_price: str) -> str:
            if not old_price or new_price == old_price:
                return f"<b>{new_price}</b>"  # No change

            # Extract numeric values for comparison
            new_val = float(new_price.split()[0])
            old_val = float(old_price.split()[0])

            # Return bold price with change indicator
            if new_val > old_val:
                return f"<b>{new_price}</b> +"  # Price increased
            else:
                return f"<b>{new_price}</b> -"  # Price decreased

        # Format prices with change indicators if old prices provided
        floor_display = (format_change(floor_price, old_prices['floor_price'])
                         if old_prices else f"<b>{floor_price}</b>")
        best_offer_display = (format_change(best_offer, old_prices['best_offer'])
                              if old_prices else f"<b>{best_offer}</b>")

        message = (
            f"<b>{collection.upper()}</b> Update\n\n"
            f"Floor Price: {floor_display}\n"
            f"Best Offer: {best_offer_display}"
        )

        return await self.send_message(message)

    async def close(self):
        """Close bot session"""
        try:
            await self.bot.session.close()
        except Exception as e:
            self.logger.error(f"Error closing bot session: {str(e)}")

    def _setup_default_logger(self) -> logging.Logger:
        """Create default logger if none provided"""
        logger = logging.getLogger('telegram_service')
        logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(console_handler)

        return logger


async def _send_message_async(text: str) -> bool:
    """Async helper for sending messages"""
    service = TelegramService()
    try:
        return await service.send_message(text)
    finally:
        await service.close()


async def _send_price_update_async(collection: str,
                                   floor_price: str,
                                   best_offer: str,
                                   old_prices: Optional[Dict[str, str]] = None) -> bool:
    """Async helper for sending price updates"""
    service = TelegramService()
    try:
        return await service.send_price_update(
            collection, floor_price, best_offer, old_prices)
    finally:
        await service.close()


# Helper function for sending messages without dealing with asyncio
def send_telegram_message(text: str) -> bool:
    """Synchronous wrapper for sending messages"""
    return asyncio.get_event_loop().run_until_complete(_send_message_async(text))


# Helper function for sending price updates
def send_price_update(collection: str,
                      floor_price: str,
                      best_offer: str,
                      old_prices: Optional[Dict[str, str]] = None) -> bool:
    """
    Synchronous wrapper for sending price updates with change indicators
    """
    return asyncio.get_event_loop().run_until_complete(
        _send_price_update_async(collection, floor_price, best_offer, old_prices))
