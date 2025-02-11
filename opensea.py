from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout
import time
import logging
from typing import Dict, Optional, Tuple


class OpenSeaService:
    def __init__(self, logger=None):
        """Initialize OpenSea service with optional logger"""
        self.logger = logger or self._setup_default_logger()
        self._base_url = "https://opensea.io/collection"
        self._user_agent = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                            'AppleWebKit/537.36 (KHTML, like Gecko) '
                            'Chrome/132.0.0.0 Safari/537.36')

        # Updated selectors based on the current HTML structure
        self._selectors = {
            'floor_price': 'a[data-testid="collection-stats-floor-price"] div.flex.items-center',
            'best_offer': 'a[data-testid="collection-stats-best-offer"] div.flex.items-center'
        }

        # Timeout and retry settings
        self._config = {
            'max_retries': 5,
            'timeout': 10000,  # 10 seconds
            'retry_delay': 2,  # seconds between retries
        }

    def get_collection_prices(self, collection_slug: str) -> Optional[Dict[str, Tuple[float, str]]]:
        """Main method to get prices with retry mechanism"""
        last_error = None

        for attempt in range(self._config['max_retries']):
            try:
                result = self._try_get_prices(collection_slug)
                if not result:
                    continue

                # Validate the result - if either price is UNKNOWN, consider it a failure
                floor_price, floor_currency = result['floor_price']
                best_offer, best_currency = result['best_offer']

                if "UNKNOWN" in [floor_currency, best_currency]:
                    self.logger.warning(
                        f"Attempt {attempt + 1}: Got UNKNOWN currency, retrying...")
                    time.sleep(self._config['retry_delay'])
                    continue

                if floor_price == 0.0 or best_offer == 0.0:
                    self.logger.warning(
                        f"Attempt {attempt + 1}: Got zero price, retrying...")
                    time.sleep(self._config['retry_delay'])
                    continue

                return result

            except Exception as e:
                last_error = str(e)
                self.logger.warning(
                    f"Attempt {attempt + 1}/{self._config['max_retries']} failed: {last_error}")
                if attempt < self._config['max_retries'] - 1:
                    time.sleep(self._config['retry_delay'])
                    continue

        self.logger.error(
            f"All {self._config['max_retries']} attempts failed. Last error: {last_error}")
        return None

    def _try_get_prices(self, collection_slug: str) -> Optional[Dict[str, Tuple[float, str]]]:
        """Single attempt to get prices"""
        with sync_playwright() as p:
            try:
                # Setup browser with additional options
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self._user_agent,
                    viewport={'width': 1920, 'height': 1080}
                )
                page = context.new_page()

                # Get the data with timeout
                raw_data = self._scrape_price_data_with_timeout(
                    page, collection_slug)
                if not raw_data:
                    return None

                # Parse the results
                return {
                    'floor_price': self._parse_price_string(raw_data['floor_price']),
                    'best_offer': self._parse_price_string(raw_data['best_offer'])
                }

            finally:
                browser.close()

    def _scrape_price_data_with_timeout(self, page: Page, collection_slug: str) -> Optional[Dict[str, str]]:
        """Scrape data with strict timeout control"""
        try:
            # Navigate to collection
            url = f"{self._base_url}/{collection_slug}"
            self.logger.info(f"Accessing {url}")

            # Set strict timeout for navigation
            page.set_default_navigation_timeout(self._config['timeout'])
            page.goto(url)

            # Quick check for page load
            page.wait_for_load_state("domcontentloaded",
                                     timeout=self._config['timeout'])

            # Wait for elements with timeout
            for name, selector in self._selectors.items():
                try:
                    page.wait_for_selector(
                        selector,
                        state="visible",
                        timeout=self._config['timeout']
                    )
                except PlaywrightTimeout:
                    self.logger.warning(f"Timeout waiting for {name} element")
                    raise

            # Extract prices quickly
            floor_price = self._get_element_text(
                page, self._selectors['floor_price']).strip()
            best_offer = self._get_element_text(
                page, self._selectors['best_offer']).strip()

            # Validate extracted data
            if floor_price == "N/A" or best_offer == "N/A":
                raise Exception("Failed to extract valid prices")

            return {
                'floor_price': floor_price,
                'best_offer': best_offer
            }

        except Exception as e:
            self.logger.error(f"Error in scraping attempt: {str(e)}")
            raise

    def _scrape_price_data(self, page: Page, collection_slug: str) -> Optional[Dict[str, str]]:
        """Scrape raw price data from the collection page"""
        try:
            # Navigate to collection
            url = f"{self._base_url}/{collection_slug}"
            self.logger.info(f"Accessing {url}")
            page.goto(url)

            # Wait for page load with increased timeout
            page.wait_for_load_state("networkidle", timeout=60000)
            time.sleep(5)  # Additional wait for dynamic content

            # Wait for elements with increased timeout
            for selector in self._selectors.values():
                page.wait_for_selector(
                    selector, state="visible", timeout=60000)

            # Extract prices with text content cleanup
            floor_price = self._get_element_text(
                page, self._selectors['floor_price']).strip()
            best_offer = self._get_element_text(
                page, self._selectors['best_offer']).strip()

            return {
                'floor_price': floor_price,
                'best_offer': best_offer
            }

        except Exception as e:
            self.logger.error(f"Error scraping data: {str(e)}")
            return None

    def _get_element_text(self, page: Page, selector: str) -> str:
        """Safely extract text from a page element"""
        try:
            element = page.locator(selector)
            if element.is_visible():
                # Get text and clean up any extra whitespace
                text = element.inner_text()
                return ' '.join(text.split())  # Normalize whitespace
            return "N/A"
        except Exception:
            return "N/A"

    def _parse_price_string(self, price_string: str) -> Tuple[float, str]:
        """
        Parse price string into numeric value and currency

        Args:
            price_string: String like "0.4399 ETH" or "0.41 WETH"

        Returns:
            Tuple of (price as float, currency as string)
        """
        try:
            if price_string == "N/A":
                return (0.0, "UNKNOWN")

            # Split into price and currency
            parts = price_string.split()
            if len(parts) != 2:
                return (0.0, "UNKNOWN")

            # Convert price string to float (handling both . and , as decimal separator)
            price_str = parts[0].replace(',', '.')
            price = float(price_str)

            return (price, parts[1])

        except (ValueError, IndexError) as e:
            self.logger.error(
                f"Error parsing price string '{price_string}': {str(e)}")
            return (0.0, "UNKNOWN")

    def _setup_default_logger(self) -> logging.Logger:
        """Create default logger if none provided"""
        logger = logging.getLogger('opensea_service')
        logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(console_handler)

        return logger
