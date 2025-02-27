from typing import Optional
from web3_client import web3_client
from config import settings
from decimal import Decimal
import time
import logging
import asyncio
from cachetools import TTLCache

class ChainlinkPriceVerifier:
    def __init__(self):
        self.feeds = {}
        self.decimals_cache = {}
        self.price_cache = TTLCache(maxsize=100, ttl=60)  # Cache prices for 60 seconds
        self._init_feeds()

    def _init_feeds(self):
        """Initialize all chainlink price feeds"""
        for pair, address in settings.CHAINLINK_FEEDS.items():
            try:
                self.feeds[pair] = web3_client.get_contract(
                    address,
                    abi=settings.CHAINLINK_AGGREGATOR_ABI
                )
                # Cache the decimals to avoid repeated calls
                self.decimals_cache[pair] = self.feeds[pair].functions.decimals().call()
                logging.info(f"Initialized Chainlink feed for {pair}")
            except Exception as e:
                logging.error(f"Failed to initialize Chainlink feed for {pair}: {e}")

    async def get_price(self, pair: str) -> Optional[Decimal]:
        """Get price from Chainlink oracle with caching"""
        # Check cache first
        if pair in self.price_cache:
            return self.price_cache[pair]
            
        try:
            web3_client.reconnect_if_needed()
            
            contract = self.feeds.get(pair)
            if not contract:
                logging.warning(f"No Chainlink feed available for {pair}")
                return None
                
            round_data = contract.functions.latestRoundData().call()
            decimals = self.decimals_cache.get(pair, 8)  # Default to 8 decimals
            price = Decimal(round_data[1]) / (10 ** decimals)
            
            # Check if data is stale (older than 15 minutes)
            if (time.time() - round_data[3]) > 900:
                logging.warning(f"Stale Chainlink data for {pair}, last updated {time.time() - round_data[3]} seconds ago")
                return None
            
            # Cache the price
            self.price_cache[pair] = price
            return price
        except Exception as e:
            logging.error(f"Chainlink error for {pair}: {e}")
            return None

    async def verify_price(self, market_price: Decimal, pair: str) -> bool:
        """Verify a market price against Chainlink oracle data"""
        try:
            chainlink_price = await self.get_price(pair)
            if not chainlink_price:
                logging.info(f"No Chainlink price available for {pair}, skipping verification")
                return True  # Skip verification if no price available
                
            deviation = abs(market_price - chainlink_price) / chainlink_price
            is_valid = deviation <= settings.MAX_PRICE_DEVIATION
            
            if not is_valid:
                logging.warning(f"Price verification failed for {pair}. Market: {market_price}, Chainlink: {chainlink_price}, Deviation: {deviation*100:.2f}%")
                
            return is_valid
        except Exception as e:
            logging.error(f"Error during price verification for {pair}: {e}")
            return False  # Fail closed on errors