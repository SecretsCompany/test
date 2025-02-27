from decimal import Decimal, getcontext
from typing import Dict, Optional
import logging
from config import settings
from cex_client import CEXClient
from dex_client import DexPriceFetcher
from chainlink_verifier import ChainlinkPriceVerifier
from execution_predictor import ExecutionPredictor
from liquidity_analyzer import LiquidityAnalyzer
from telegram_notifier import send_telegram_message
from utils import format_decimal

getcontext().prec = 12

class ArbitrageEngine:
    def __init__(self):
        self.cex = CEXClient()
        self.dex = DexPriceFetcher()
        self.chainlink = ChainlinkPriceVerifier()
        self.liquidity = LiquidityAnalyzer()
        self.predictor = ExecutionPredictor()

    async def analyze_pair(self, symbol: str, address: str):
        if symbol == "USDT":
            return

        # Get DEX data
        dex_price = await self.dex.get_price_with_slippage(address, 1000)
        liquidity = await self.liquidity.get_liquidity(address)
        
        if liquidity < settings.MIN_LIQUIDITY:
            return

        # Get CEX data
        cex_prices = await self.cex.get_prices(f"{symbol}/USDT")
        
        for exchange, data in cex_prices.items():
            if not data['success']:
                continue
                
            # Price verification
            if not await self.chainlink.verify_price(data['price'], f"{symbol}/USD"):
                continue
                
            # Profit calculation
            spread = await self.calculate_spread(data['price'], dex_price)
            profit = await self.calculate_profit(data['price'], dex_price, 1000)
            
            if profit < settings.MIN_PROFIT_USD:
                continue
                
            # Execution time prediction
            exec_time = await self.predictor.predict(exchange, 1000)
            if exec_time > settings.MAX_EXECUTION_TIME:
                continue
                
            # Send notification
            message = self._prepare_message(
                symbol, exchange, data['price'], 
                dex_price, spread, profit, exec_time, liquidity
            )
            await send_telegram_message(message)

    async def calculate_spread(self, cex_price: Decimal, dex_price: Decimal) -> Decimal:
        return abs((cex_price - dex_price) / cex_price) * 100

    async def calculate_profit(self, cex_price: Decimal, dex_price: Decimal, amount: Decimal) -> Decimal:
        return abs(cex_price - dex_price) * amount

    def _prepare_message(self, symbol, exchange, cex_price, dex_price, spread, profit, exec_time, liquidity):
        return (
            f"🚀 *Arbitrage Opportunity* 🚀\n"
            f"• Pair: {symbol}/USDT\n"
            f"• Exchange: {exchange.upper()}\n"
            f"• CEX Price: ${format_decimal(cex_price, 6)}\n"
            f"• DEX Price: ${format_decimal(dex_price, 6)}\n"
            f"• Spread: {spread:.2f}%\n"
            f"• Est. Profit: ${format_decimal(profit)}\n"
            f"• Exec. Time: {exec_time:.1f}s\n"
            f"• Liquidity: ${format_decimal(liquidity)}"
        )