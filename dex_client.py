from web3_client import web3_client
from config import settings
from decimal import Decimal
import logging
from cachetools import TTLCache
import asyncio
from typing import Optional, Tuple

class DexPriceFetcher:
    def __init__(self):
        self.router = web3_client.uniswap_router
        self.decimals_cache = TTLCache(maxsize=500, ttl=3600)
        self.pair_cache = TTLCache(maxsize=500, ttl=300)  # Cache pair addresses for 5 minutes

    async def _get_decimals(self, token_address: str) -> int:
        """Get token decimals with caching"""
        if token_address in self.decimals_cache:
            return self.decimals_cache[token_address]
        
        try:
            token_contract = web3_client.get_contract(
                token_address,
                abi=[
                    {
                        "constant": True,
                        "inputs": [],
                        "name": "decimals",
                        "outputs": [{"name": "", "type": "uint8"}],
                        "type": "function"
                    }
                ]
            )
            decimals = token_contract.functions.decimals().call()
            self.decimals_cache[token_address] = decimals
            return decimals
        except Exception as e:
            logging.error(f"Error fetching decimals for token {token_address}: {e}")
            return 18  # Default to 18 decimals

    async def _get_pair_address(self, token_address: str, usdt_address: str) -> Optional[str]:
        """Get the pair address for a token/USDT pair with caching"""
        cache_key = f"{token_address}:{usdt_address}"
        if cache_key in self.pair_cache:
            return self.pair_cache[cache_key]
            
        try:
            # Ensure addresses are checksum format
            token_address = web3_client.convert_to_checksum_address(token_address)
            usdt_address = web3_client.convert_to_checksum_address(usdt_address)
            
            factory = web3_client.uniswap_factory
            pair_address = factory.functions.getPair(token_address, usdt_address).call()
            
            if pair_address == '0x' + '0'*40:
                return None
                
            self.pair_cache[cache_key] = pair_address
            return pair_address
        except Exception as e:
            logging.error(f"Error getting pair address: {e}")
            return None

    async def get_price_with_slippage(self, token_address: str, amount_usd: Decimal) -> Optional[Decimal]:
        """Get price for a token with slippage applied"""
        try:
            web3_client.reconnect_if_needed()
            
            # Get token information
            token_decimals = await self._get_decimals(token_address)
            usdt_address = settings.TOKENS["USDT"]
            usdt_decimals = 6  # USDT always has 6 decimals
            
            # Calculate the amount in token's smallest unit
            amount_in_wei = int(amount_usd * 10**token_decimals)
            
            try:
                # Try direct price query first
                amounts = self.router.functions.getAmountsOut(
                    amount_in_wei,
                    [token_address, usdt_address]
                ).call()
                
                price = Decimal(amounts[1]) / 10**usdt_decimals
                return price * (1 - settings.MAX_SLIPPAGE)
            except Exception as e:
                logging.warning(f"Direct price query failed: {e}")
                
                # Fallback to reserves calculation
                pair_address = await self._get_pair_address(token_address, usdt_address)
                if not pair_address:
                    logging.error(f"No liquidity pair found for {token_address} and USDT")
                    return None
                    
                pair_contract = web3_client.get_contract(
                    pair_address,
                    abi=settings.UNISWAP_PAIR_ABI
                )
                
                # Get token order in the pair
                token0 = pair_contract.functions.token0().call()
                token1 = pair_contract.functions.token1().call()
                
                # Get reserves
                reserves = pair_contract.functions.getReserves().call()
                
                # Determine which reserve belongs to which token
                if token0.lower() == token_address.lower():
                    token_reserve = reserves[0]
                    usdt_reserve = reserves[1]
                else:
                    token_reserve = reserves[1]
                    usdt_reserve = reserves[0]
                
                # Calculate price based on reserves (with slippage)
                if token_reserve == 0:
                    return None
                    
                price = (Decimal(usdt_reserve) / 10**usdt_decimals) / (Decimal(token_reserve) / 10**token_decimals)
                return price * (1 - settings.MAX_SLIPPAGE)
                
        except Exception as e:
            logging.error(f"DEX price error: {e}")
            return None