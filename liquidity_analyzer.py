from web3_client import web3_client
from config import settings
from decimal import Decimal
import logging
from cachetools import TTLCache

class LiquidityAnalyzer:
    def __init__(self):
        self.factory = web3_client.get_contract(
            settings.UNISWAP_FACTORY_ADDRESS,
            abi=settings.UNISWAP_FACTORY_ABI
        )
        self.liquidity_cache = TTLCache(maxsize=200, ttl=120)  # Cache for 2 minutes

    async def get_liquidity(self, token_address: str) -> Decimal:
        """Get the liquidity for a token/USDT pair"""
        cache_key = f"{token_address}:{settings.TOKENS['USDT']}"
        if cache_key in self.liquidity_cache:
            return self.liquidity_cache[cache_key]
            
        try:
            web3_client.reconnect_if_needed()
            
            # Get pair address
            pair_address = self.factory.functions.getPair(
                token_address,
                settings.TOKENS["USDT"]
            ).call()
            
            if pair_address == '0x' + '0'*40:
                return Decimal(0)
            
            # Get pair contract
            pair_contract = web3_client.get_contract(
                pair_address,
                abi=settings.UNISWAP_PAIR_ABI
            )
            
            # Get token order in the pair
            token0 = pair_contract.functions.token0().call()
            token1 = pair_contract.functions.token1().call()
            
            # Get reserves
            reserves = pair_contract.functions.getReserves().call()
            
            # Get token decimals
            token_decimals = 18  # Default
            usdt_decimals = 6    # USDT always has 6 decimals
            
            try:
                token_contract = web3_client.get_contract(
                    token_address,
                    abi=[{
                        "constant": True,
                        "inputs": [],
                        "name": "decimals",
                        "outputs": [{"name": "", "type": "uint8"}],
                        "type": "function"
                    }]
                )
                token_decimals = token_contract.functions.decimals().call()
            except Exception as e:
                logging.warning(f"Could not get token decimals, using default 18: {e}")
            
            # Determine which reserve is USDT
            if token0.lower() == settings.TOKENS["USDT"].lower():
                usdt_reserve = reserves[0]
                token_reserve = reserves[1]
            else:
                usdt_reserve = reserves[1]
                token_reserve = reserves[0]
            
            # Calculate USDT liquidity
            usdt_liquidity = Decimal(usdt_reserve) / 10**usdt_decimals
            
            # Cache the result
            self.liquidity_cache[cache_key] = usdt_liquidity
            
            return usdt_liquidity
        except Exception as e:
            logging.error(f"Liquidity analysis error for {token_address}: {e}")
            return Decimal(0)