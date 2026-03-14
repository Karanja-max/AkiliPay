"""
Currency conversion service using a forex API.
Stores amounts in KES (M-Pesa base); converts to USD, JPY, GBP, EUR, ZAR on request.
Set FOREX_API_KEY in .env to enable live rates (e.g. from exchangerate-api.com).
"""
import os
from typing import Any, Dict

import requests
from dotenv import load_dotenv

load_dotenv()

FOREX_API_KEY = os.getenv("FOREX_API_KEY")
FOREX_API_BASE_URL = os.getenv(
    "FOREX_API_BASE_URL",
    "https://v6.exchangerate-api.com/v6/{api_key}/latest/KES",
)
BASE_CURRENCY = os.getenv("BASE_CURRENCY", "KES")

# Supported target currencies (standard codes)
SUPPORTED_CURRENCIES = {"KES", "USD", "JPY", "GBP", "EUR", "ZAR"}

# Optional: map friendly names to codes for query params
CURRENCY_ALIASES = {
    "pounds": "GBP",
    "euros": "EUR",
    "rands": "ZAR",
    "yen": "JPY",
    "dollars": "USD",
    "usd": "USD",
    "jpy": "JPY",
    "gbp": "GBP",
    "eur": "EUR",
    "zar": "ZAR",
    "kes": "KES",
}


def _normalize_currency(currency: str) -> str:
    """Return standard 3-letter code; default to BASE_CURRENCY if unknown."""
    if not currency:
        return BASE_CURRENCY
    key = currency.strip().lower()
    return CURRENCY_ALIASES.get(key, key.upper() if len(key) == 3 else BASE_CURRENCY)


def _fetch_rates() -> Dict[str, float]:
    """
    Fetch conversion rates from KES to supported currencies.
    Uses FOREX_API_KEY. Returns empty dict on failure; callers fall back to no conversion.
    """
    # #region agent log
    import json as _json
    _debug_log_path = __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))), "debug-eec1d2.log")
    def _dlog(msg, data, hid):
        try:
            with open(_debug_log_path, "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"sessionId": "eec1d2", "runId": "run1", "hypothesisId": hid, "location": "forex_service.py", "message": msg, "data": data, "timestamp": __import__("time").time() * 1000}) + "\n")
        except Exception:
            pass
    _dlog("_fetch_rates", {"has_key": bool(FOREX_API_KEY)}, "H5")
    # #endregion
    if not FOREX_API_KEY:
        return {}

    url = FOREX_API_BASE_URL.format(api_key=FOREX_API_KEY)
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data: Dict[str, Any] = response.json()
        if data.get("result") != "success":
            # #region agent log
            _dlog("_fetch_rates result not success", {"result": data.get("result")}, "H5")
            # #endregion
            return {}
        rates = data.get("conversion_rates") or {}
        out = {k: float(v) for k, v in rates.items() if isinstance(v, (int, float))}
        # #region agent log
        _dlog("_fetch_rates success", {"rates_count": len(out)}, "H5")
        # #endregion
        return out
    except Exception as e:
        # #region agent log
        _dlog("_fetch_rates exception", {"error": str(type(e).__name__)}, "H5")
        # #endregion
        return {}


# In-memory cache: rates and a simple "valid for a while" check
_cached_rates: Dict[str, float] = {}
_cache_time: float = 0
_CACHE_SECONDS = 300  # 5 minutes


def get_rate_to_target(target_currency: str) -> float:
    """
    Get FX rate from BASE_CURRENCY (KES) to target_currency.
    Returns 1.0 for KES or if API is unavailable so existing flow does not break.
    """
    target = _normalize_currency(target_currency)
    if target == BASE_CURRENCY:
        return 1.0

    global _cached_rates, _cache_time
    import time
    now = time.time()
    if (now - _cache_time) > _CACHE_SECONDS or not _cached_rates:
        _cached_rates = _fetch_rates()
        _cache_time = now

    rate = _cached_rates.get(target)
    if rate is None:
        return 1.0
    return float(rate)


def convert_from_base(amount_in_base: float, target_currency: str) -> float:
    """Convert amount from BASE_CURRENCY (KES) to target currency using live/cached FX."""
    rate = get_rate_to_target(target_currency)
    return round(amount_in_base * rate, 2)


def normalize_currency_param(currency: str) -> str:
    """Normalize user input (e.g. 'pounds', 'euros') to standard code (GBP, EUR)."""
    return _normalize_currency(currency)
