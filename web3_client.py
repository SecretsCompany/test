from web3 import Web3
from web3.middleware import geth_poa_middleware
from config import settings
import json
import os
import logging
from typing import Optional, Any, Dict, List
import time

current_dir = os.path.dirname(os.path.abspath(__file__))
abi_path = os.path.join(current_dir, "load.json")

class Web3Client:
    def __init__(self):
        self.w3: Optional[Web3] = None
        self.uniswap_router = None
        self.providers = [
            f"https://mainnet.infura.io/v3/{settings.INFURA_PROJECT_ID}",
            "https://eth.llamarpc.com",
            "https://rpc.ankr.com/eth"
        ]
        self.contract_cache = {}
        self._connect()
        self._init_contracts()

    def _connect(self):
        for provider_url in self.providers:
            try:
                self.w3 = Web3(Web3.HTTPProvider(provider_url))
                if self.w3.is_connected():
                    logging.info(f"Connected to {provider_url}")
                    self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                    return
            except Exception as e:
                logging.warning(f"Connection failed to {provider_url}: {str(e)}")
        
        raise ConnectionError("Could not connect to any Ethereum node")

    def _init_contracts(self):
        try:
            # Load the Uniswap Router ABI
            with open(abi_path, "r") as f:
                uniswap_abi = json.load(f)
            
            # Initialize the Uniswap Router contract
            self.uniswap_router = self.w3.eth.contract(
                address=settings.UNISWAP_ROUTER_ADDRESS,
                abi=uniswap_abi
            )
            logging.info("Uniswap router contract initialized")
            
            # Initialize factory contract
            self.uniswap_factory = self.w3.eth.contract(
                address=settings.UNISWAP_FACTORY_ADDRESS,
                abi=settings.UNISWAP_FACTORY_ABI
            )
            logging.info("Uniswap factory contract initialized")
        except Exception as e:
            logging.error(f"Contract initialization failed: {e}")
            raise

    def get_contract(self, address: str, abi: List[Dict[str, Any]] = None) -> Any:
        """Get a contract instance, using cache if available"""
        cache_key = f"{address}:{hash(str(abi)) if abi else 'default'}"
        
        if cache_key in self.contract_cache:
            return self.contract_cache[cache_key]
            
        contract = self.w3.eth.contract(
            address=address,
            abi=abi or self.uniswap_router.abi
        )
        
        self.contract_cache[cache_key] = contract
        return contract
    
    def reconnect_if_needed(self):
        """Check connection and reconnect if needed"""
        try:
            if not self.w3.is_connected():
                logging.warning("Web3 connection lost, reconnecting...")
                self._connect()
                self._init_contracts()
        except Exception as e:
            logging.error(f"Reconnection failed: {e}")
            
    def is_address(self, address: str) -> bool:
        """Validate if the given string is a valid Ethereum address"""
        return self.w3.is_address(address)
        
    def convert_to_checksum_address(self, address: str) -> str:
        """Convert address to checksum format"""
        return self.w3.to_checksum_address(address)

# Initialize Web3 client
try:
    web3_client = Web3Client()
except Exception as e:
    logging.critical(f"Web3 client initialization failed: {e}")
    exit(1)