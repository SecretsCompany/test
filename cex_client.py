import aiohttp
import hmac
import hashlib
import time
from typing import Dict, Optional, Any
from config import settings
from decimal import Decimal
import logging
from cachetools import TTLCache
import json

class CEXClient:
    def __init__(self):
        self.session = None
        self.cache = TTLCache(maxsize=1000, ttl=10)
        self.rate_limits = {exchange: {'last_request': 0, 'limit': settings.EXCHANGES[exchange].get('rate_limit', 10)} 
                           for exchange in settings.EXCHANGES}

    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def get_prices(self, pair: str) -> Dict:
        await self._ensure_session()
        results = {}
        for exchange in settings.EXCHANGES:
            if self._check_rate_limit(exchange):
                try:
                    price = await self._fetch_price(exchange, pair)
                    results[exchange] = {'success': True, 'price': price}
                except Exception as e:
                    logging.error(f"Error fetching {pair} price from {exchange}: {e}")
                    results[exchange] = {'success': False, 'error': str(e)}
            else:
                results[exchange] = {'success': False, 'error': 'Rate limited'}
        return results

    def _check_rate_limit(self, exchange: str) -> bool:
        """Check if we're within rate limits for the exchange"""
        now = time.time()
        rate_info = self.rate_limits.get(exchange, {'last_request': 0, 'limit': 10})
        
        if now - rate_info['last_request'] < (1.0 / rate_info['limit']):
            return False
            
        self.rate_limits[exchange]['last_request'] = now
        return True

    async def _fetch_price(self, exchange: str, pair: str) -> Decimal:
        """Fetch price from specific exchange"""
        cache_key = f"{exchange}:{pair}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        exchange_config = settings.EXCHANGES.get(exchange, {})
        if not exchange_config:
            raise ValueError(f"Exchange {exchange} not configured")
            
        url = exchange_config.get('url')
        if not url:
            raise ValueError(f"URL not configured for exchange {exchange}")
            
        # Replace placeholder with actual pair
        url = url.replace("{pair}", pair.replace("/", ""))
        
        # Add authentication if needed
        headers = {}
        if 'auth_required' in exchange_config and exchange_config['auth_required']:
            timestamp = str(int(time.time() * 1000))
            signature = self._generate_signature(exchange, timestamp, pair)
            headers.update({
                'API-Key': exchange_config.get('api_key', ''),
                'API-Timestamp': timestamp,
                'API-Signature': signature
            })
        
        async with self.session.get(url, headers=headers) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Error {response.status}: {text}")
                
            data = await response.json()
            price = self._extract_price(exchange, data)
            self.cache[cache_key] = price
            return price
    
    def _generate_signature(self, exchange: str, timestamp: str, pair: str) -> str:
        """Generate signature for authenticated exchanges"""
        exchange_config = settings.EXCHANGES.get(exchange, {})
        secret = exchange_config.get('api_secret', '')
        
        if exchange == 'binance':
            message = f"symbol={pair.replace('/', '')}&timestamp={timestamp}"
            return hmac.new(
                secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
        elif exchange == 'kucoin':
            message = f"{timestamp}{pair}"
            return hmac.new(
                secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
        
        # Default signature method
        return hmac.new(
            secret.encode('utf-8'),
            f"{timestamp}{pair}".encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _extract_price(self, exchange: str, data: Dict[str, Any]) -> Decimal:
        """Extract price from exchange response based on their specific format"""
        if exchange == 'binance':
            return Decimal(str(data.get('price', 0)))
        elif exchange == 'kucoin':
            return Decimal(str(data.get('data', {}).get('price', 0)))
        elif exchange == 'kraken':
            # Example: {"result":{"XXBTZUSD":{"a":["29326.10000","1","1.000"]}}}
            pair_data = list(data.get('result', {}).values())[0]
            return Decimal(str(pair_data.get('a', [[0]])[0][0]))
        elif exchange == 'coinbase':
            return Decimal(str(data.get('data', {}).get('amount', 0)))
        
        # Default fallback - attempt to find a price field
        if 'price' in data:
            return Decimal(str(data['price']))
        elif 'last' in data:
            return Decimal(str(data['last']))
        
        raise ValueError(f"Could not extract price from {exchange} response: {data}")
    
    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()