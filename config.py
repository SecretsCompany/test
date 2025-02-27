from pydantic_settings import BaseSettings, SettingsConfigDict
from decimal import Decimal
from typing import Dict, List, Any
import os
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

class Settings(BaseSettings):
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: str
    
    # Blockchain
    INFURA_PROJECT_ID: str
    UNISWAP_ROUTER_ADDRESS: str = '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'
    UNISWAP_FACTORY_ADDRESS: str = '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f'
    CHAINLINK_FEEDS: Dict[str, str] = {
        "ETH/USD": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
        "BTC/USD": "0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c"
    }
    
    # Chainlink ABI
    CHAINLINK_AGGREGATOR_ABI: List[Dict[str, Any]] = [
        {
            "inputs": [],
            "name": "decimals",
            "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [],
            "name": "latestRoundData",
            "outputs": [
                {"internalType": "uint80", "name": "roundId", "type": "uint80"},
                {"internalType": "int256", "name": "answer", "type": "int256"},
                {"internalType": "uint256", "name": "startedAt", "type": "uint256"},
                {"internalType": "uint256", "name": "updatedAt", "type": "uint256"},
                {"internalType": "uint80", "name": "answeredInRound", "type": "uint80"}
            ],
            "stateMutability": "view",
            "type": "function"
        }
    ]
    
    # Uniswap Factory ABI
    UNISWAP_FACTORY_ABI: List[Dict[str, Any]] = [
        {
            "inputs": [
                {"internalType": "address", "name": "tokenA", "type": "address"},
                {"internalType": "address", "name": "tokenB", "type": "address"}
            ],
            "name": "getPair",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function"
        }
    ]
    
    # Uniswap Pair ABI
    UNISWAP_PAIR_ABI: List[Dict[str, Any]] = [
        {
            "inputs": [],
            "name": "getReserves",
            "outputs": [
                {"internalType": "uint112", "name": "reserve0", "type": "uint112"},
                {"internalType": "uint112", "name": "reserve1", "type": "uint112"},
                {"internalType": "uint32", "name": "blockTimestampLast", "type": "uint32"}
            ],
            "stateMutability": "view",
            "type": "function"
        }
    ]
    
    # Exchanges
    EXCHANGES: Dict[str, Dict[str, Any]] = {}
    
    # Tokens
    TOKENS: Dict[str, str] = {
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7"  # Пример адреса USDT
    }
    
    # Commissions
    DEX_COMMISSION: Decimal = Decimal('0.003')
    MAX_SLIPPAGE: Decimal = Decimal('0.01')
    
    # ML
    ML_MODEL_PATH: str = 'models/execution_model.pkl'
    MAX_EXECUTION_TIME: int = 3
    
    # Risk Management
    MIN_PROFIT_USD: Decimal = Decimal('50')
    MAX_PRICE_DEVIATION: Decimal = Decimal('0.05')
    MIN_LIQUIDITY: Decimal = Decimal('10000')

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()