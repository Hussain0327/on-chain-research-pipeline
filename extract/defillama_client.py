"""
DeFiLlama API client with retry logic, rate limiting, and in-memory caching.
"""

import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (
    DEFILLAMA_BASE_URL,
    DEFILLAMA_STABLECOINS_URL,
    DEFAULT_CACHE_TTL,
    DEFAULT_RATE_LIMIT,
    DEFAULT_RETRIES,
)


class DeFiLlamaClient:
    def __init__(self, cache_ttl=DEFAULT_CACHE_TTL, rate_limit=DEFAULT_RATE_LIMIT):
        self.base_url = DEFILLAMA_BASE_URL
        self.stablecoins_url = DEFILLAMA_STABLECOINS_URL
        self.cache_ttl = cache_ttl
        self.rate_limit = rate_limit
        self._cache = {}
        self._last_request_time = 0

        self.session = requests.Session()
        retry_strategy = Retry(
            total=DEFAULT_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _rate_limit_wait(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)

    def _get(self, url):
        now = time.time()
        if url in self._cache:
            cached_data, cached_time = self._cache[url]
            if now - cached_time < self.cache_ttl:
                return cached_data

        self._rate_limit_wait()
        response = self.session.get(url, timeout=(10, 120))
        response.raise_for_status()
        self._last_request_time = time.time()

        data = response.json()
        self._cache[url] = (data, time.time())
        return data

    # --- Protocol endpoints ---

    def get_protocols(self):
        return self._get(f"{self.base_url}/protocols")

    def get_protocol(self, slug):
        return self._get(f"{self.base_url}/protocol/{slug}")

    def get_protocol_tvl(self, slug):
        return self._get(f"{self.base_url}/tvl/{slug}")

    # --- TVL endpoints ---

    def get_chains(self):
        return self._get(f"{self.base_url}/v2/chains")

    def get_chain_tvl(self, chain):
        return self._get(f"{self.base_url}/v2/historicalChainTvl/{chain}")

    # --- Fees & Revenue endpoints ---

    def get_fees_overview(self):
        return self._get(f"{self.base_url}/overview/fees")

    def get_protocol_fees(self, slug):
        return self._get(f"{self.base_url}/summary/fees/{slug}")

    # --- DEX endpoints ---

    def get_dex_overview(self):
        return self._get(f"{self.base_url}/overview/dexs")

    def get_dex_volume(self, slug):
        return self._get(f"{self.base_url}/summary/dexs/{slug}")

    # --- Stablecoin endpoints ---

    def get_stablecoins(self):
        return self._get(f"{self.stablecoins_url}/stablecoins?includePrices=true")

    def get_stablecoin(self, asset_id):
        return self._get(f"{self.stablecoins_url}/stablecoin/{asset_id}")

    def get_stablecoin_chains(self):
        return self._get(f"{self.stablecoins_url}/stablecoinchains")

    def get_stablecoin_prices(self):
        return self._get(f"{self.stablecoins_url}/stablecoinprices")

    # --- Yields endpoints ---

    def get_pools(self):
        return self._get(f"{self.base_url}/pools")
