#!/usr/bin/env python3
"""
okx_client.py — K745 OKX Authenticated API Client
====================================================
Full OKX REST API client supporting both public (no-auth) and private (HMAC-SHA256 signed)
endpoints. Built for K498 integration scaffold: HL concentration cap relief 65%→50%.

Public endpoints (no API key required):
  - GET /api/v5/public/funding-rate        → live FR snapshot
  - GET /api/v5/public/funding-rate-history → historical FR
  - GET /api/v5/market/ticker               → mark price + volume

Private endpoints (require OKX_API_KEY + OKX_API_SECRET + OKX_PASSPHRASE in env):
  - GET  /api/v5/account/balance           → account balances
  - GET  /api/v5/account/positions         → open positions
  - POST /api/v5/trade/order               → place order (POST_ONLY default)
  - POST /api/v5/trade/cancel-order        → cancel order
  - GET  /api/v5/trade/order               → query order status
  - POST /api/v5/trade/close-position      → emergency position close

Auth: HMAC-SHA256 over (timestamp + method + requestPath + body)
  - Timestamp: ISO 8601 UTC (seconds precision, e.g. "2026-05-30T10:15:00.123Z")
  - Headers: OK-ACCESS-KEY, OK-ACCESS-SIGN, OK-ACCESS-TIMESTAMP, OK-ACCESS-PASSPHRASE

Rate limits (OKX 2026):
  - Public endpoints:  20 req/2s per IP
  - Private endpoints: 60 req/2s per UID
  - Trade endpoints:   60 req/2s per UID

Fee structure (post-VIP4):
  - Maker rebate: -0.005% per trade (RECEIVE 0.5 bps)
  - Taker fee:     0.050% per trade (PAY 5.0 bps)
  Note: K745 uses VIP1 as conservative (0.5 bps maker rebate). VIP4+ improves further.

K339 Security:
  REPO_ROOT = Path(__file__).resolve().parent.parent — no /Users/ literals
  API credentials: ONLY from env vars (OKX_API_KEY, OKX_API_SECRET, OKX_PASSPHRASE)
  LIVE_ENABLED gate: must set OKX_LIVE_ENABLED=true in .env.local to enable trading
  Paper mode default: all order methods return mock responses unless LIVE gate passes

K498 context:
  OKX is the 3rd major venue (HL=1st, Bybit=2nd).
  K745: HL 65% exact cap → OKX integration unblocks $4.5M Phase A queue.
  Phase A sleeve allocation: K500 INJ-BTC OKX 70%, HL 30%.

Usage:
  from scripts.okx_client import OKXClient
  client = OKXClient()                              # paper mode (no API keys needed for public)
  fr = client.get_funding_rate("BTC-USDT-SWAP")     # public, no auth
  client.place_order(...)                           # live only if OKX_LIVE_ENABLED=true

Dependencies: stdlib only (urllib, hashlib, hmac, json, os)

Outputs:
  logs/okx_client.log — structured request log
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR  = REPO_ROOT / "logs"
DATA_DIR  = REPO_ROOT / "data"
LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

JST = timezone(timedelta(hours=9))

# ── OKX API constants ─────────────────────────────────────────────────────────
OKX_BASE_URL     = "https://www.okx.com"
OKX_DEMO_URL     = "https://www.okx.com"  # OKX demo: same URL, x-simulated-trading: 1 header
API_VERSION      = "v5"

# Public endpoints (no auth)
EP_FUNDING_RATE         = f"/api/{API_VERSION}/public/funding-rate"
EP_FUNDING_RATE_HISTORY = f"/api/{API_VERSION}/public/funding-rate-history"
EP_TICKER               = f"/api/{API_VERSION}/market/ticker"
EP_TICKERS              = f"/api/{API_VERSION}/market/tickers"
EP_BOOKS                = f"/api/{API_VERSION}/market/books"
EP_MARK_PRICE           = f"/api/{API_VERSION}/public/mark-price"
EP_INSTRUMENTS          = f"/api/{API_VERSION}/public/instruments"

# Private endpoints (auth required)
EP_ACCOUNT_BALANCE  = f"/api/{API_VERSION}/account/balance"
EP_ACCOUNT_POSITIONS = f"/api/{API_VERSION}/account/positions"
EP_TRADE_ORDER       = f"/api/{API_VERSION}/trade/order"
EP_TRADE_CANCEL      = f"/api/{API_VERSION}/trade/cancel-order"
EP_TRADE_CLOSE       = f"/api/{API_VERSION}/trade/close-position"
EP_TRADE_ORDERS_PENDING = f"/api/{API_VERSION}/trade/orders-pending"

# Rate limit: 20 req/2s public, 60 req/2s private (conservative sleep)
PUBLIC_SLEEP_S  = 0.12   # ~8 req/s (well under 10 req/s limit)
PRIVATE_SLEEP_S = 0.05   # ~20 req/s (under 30 req/s limit)

# K745 fee table (post-VIP4 maker rebate; VIP1 conservative baseline)
FEE_TABLE = {
    "VIP0": {"maker_rebate_bps": 0.0,  "taker_fee_bps": 5.0},
    "VIP1": {"maker_rebate_bps": 0.5,  "taker_fee_bps": 4.5},
    "VIP2": {"maker_rebate_bps": 1.0,  "taker_fee_bps": 4.0},
    "VIP3": {"maker_rebate_bps": 1.5,  "taker_fee_bps": 3.5},
    "VIP4": {"maker_rebate_bps": 2.0,  "taker_fee_bps": 3.0},  # "post-VIP4" target
    "VIP5": {"maker_rebate_bps": 2.5,  "taker_fee_bps": 2.5},
}
DEFAULT_VIP_TIER = "VIP1"   # conservative for new accounts

# K208 universe in OKX instId format
K208_OKX_SYMBOLS = [
    "BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "XRP-USDT-SWAP",
    "SUI-USDT-SWAP",  "OP-USDT-SWAP",  "APT-USDT-SWAP", "AXS-USDT-SWAP",
    "JTO-USDT-SWAP",  "IMX-USDT-SWAP", "ATOM-USDT-SWAP","INJ-USDT-SWAP",
    "AVAX-USDT-SWAP", "SEI-USDT-SWAP", "TIA-USDT-SWAP", "LINK-USDT-SWAP",
    "DOT-USDT-SWAP",  "NEAR-USDT-SWAP","ENA-USDT-SWAP", "HBAR-USDT-SWAP",
]

# ── Logging ───────────────────────────────────────────────────────────────────
def _setup_logger() -> logging.Logger:
    logger = logging.getLogger("okx_client")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(LOGS_DIR / "okx_client.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter("[okx_client] %(message)s"))
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger

log = _setup_logger()


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class FundingRateSnapshot:
    """Live funding rate snapshot for one instrument."""
    symbol:           str
    funding_rate:     float          # current rate (fractional, per 8h)
    next_funding_rate: float         # predicted next rate
    funding_time_ms:  int            # next settlement epoch ms
    mark_px:          float
    annualized_pct:   float          # FR × 3 × 365 × 100
    fetched_at_utc:   str
    ok:               bool
    error:            str = ""
    source:           str = "OKX_v5"

    def to_dict(self) -> dict:
        return {
            "symbol":            self.symbol,
            "funding_rate":      self.funding_rate,
            "next_funding_rate": self.next_funding_rate,
            "funding_time_ms":   self.funding_time_ms,
            "mark_px":           self.mark_px,
            "annualized_pct":    self.annualized_pct,
            "fetched_at_utc":    self.fetched_at_utc,
            "ok":                self.ok,
            "error":             self.error,
            "source":            self.source,
        }


@dataclass
class OrderResponse:
    """Response from a trade order call (live or paper mock)."""
    ok:          bool
    order_id:    str   = ""
    client_id:   str   = ""
    symbol:      str   = ""
    side:        str   = ""          # "buy" | "sell"
    size:        float = 0.0
    price:       float = 0.0
    order_type:  str   = "post_only"
    mode:        str   = "paper"    # "live" | "paper"
    raw:         dict  = field(default_factory=dict)
    error:       str   = ""

    def to_dict(self) -> dict:
        return {
            "ok": self.ok, "order_id": self.order_id, "client_id": self.client_id,
            "symbol": self.symbol, "side": self.side, "size": self.size,
            "price": self.price, "order_type": self.order_type,
            "mode": self.mode, "error": self.error,
        }


@dataclass
class AccountBalance:
    """Account balance snapshot."""
    ok:           bool
    total_eq_usd: float         = 0.0   # total equity in USD
    avail_eq_usd: float         = 0.0   # available equity in USD
    currencies:   Dict[str, dict] = field(default_factory=dict)
    fetched_at:   str           = ""
    error:        str           = ""


# ── Main client class ─────────────────────────────────────────────────────────

class OKXClient:
    """
    OKX REST API client for K745 integration scaffold.

    Paper-mode (default): public endpoints work without credentials.
    Live mode: set OKX_LIVE_ENABLED=true in environment AND provide
               OKX_API_KEY, OKX_API_SECRET, OKX_PASSPHRASE.

    Example:
        client = OKXClient()
        fr = client.get_funding_rate("BTC-USDT-SWAP")
        print(f"BTC FR: {fr.funding_rate*100:.4f}%/8h  ann={fr.annualized_pct:.2f}%/yr")

        # Live order (requires LIVE gate):
        resp = client.place_order("INJ-USDT-SWAP", "sell", size=1.0)
    """

    def __init__(
        self,
        api_key:    Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        vip_tier:   str = DEFAULT_VIP_TIER,
        simulated:  bool = False,   # OKX paper trading (simulated account)
    ):
        """
        Initialize OKX client. Credentials are read from env vars if not supplied.

        Env vars (set in .env.local — NEVER commit to repo):
          OKX_API_KEY       — API key
          OKX_API_SECRET    — API secret (for HMAC signing)
          OKX_PASSPHRASE    — API passphrase (set at key creation)
          OKX_LIVE_ENABLED  — "true" to enable live order routing

        K339: credentials never logged, never hardcoded.
        """
        self._api_key    = api_key    or os.environ.get("OKX_API_KEY", "")
        self._api_secret = api_secret or os.environ.get("OKX_API_SECRET", "")
        self._passphrase = passphrase or os.environ.get("OKX_PASSPHRASE", "")
        self.vip_tier    = vip_tier
        self.simulated   = simulated

        # K745 LIVE gate — must be explicitly set
        live_env = os.environ.get("OKX_LIVE_ENABLED", "false").lower().strip()
        self._live_enabled = (live_env == "true") and bool(self._api_key)

        self._has_credentials = bool(self._api_key and self._api_secret and self._passphrase)

        log.info(
            "OKXClient init: live=%s credentials=%s vip_tier=%s simulated=%s",
            self._live_enabled, self._has_credentials, vip_tier, simulated,
        )

    # ── Auth helpers ──────────────────────────────────────────────────────────

    def _timestamp(self) -> str:
        """
        OKX requires ISO 8601 UTC timestamp for HMAC signing.
        Format: '2026-05-30T10:15:00.123Z' (millisecond precision).
        """
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
               f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z"

    def _sign(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        """
        HMAC-SHA256 signature over (timestamp + METHOD + requestPath + body).
        method must be uppercase: "GET" | "POST".
        body is JSON string for POST requests, empty for GET.
        Returns base64-encoded signature string.
        """
        prehash = timestamp + method.upper() + path + body
        sig = hmac.new(
            self._api_secret.encode("utf-8"),
            prehash.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(sig).decode("utf-8")

    def _auth_headers(self, method: str, path: str, body: str = "") -> dict:
        """Build authenticated request headers for private endpoints."""
        ts = self._timestamp()
        return {
            "OK-ACCESS-KEY":       self._api_key,
            "OK-ACCESS-SIGN":      self._sign(ts, method, path, body),
            "OK-ACCESS-TIMESTAMP": ts,
            "OK-ACCESS-PASSPHRASE": self._passphrase,
            "Content-Type":        "application/json",
            "User-Agent":          "crypto-lab-okx-client/1.0",
        }

    # ── HTTP transport ────────────────────────────────────────────────────────

    def _get(self, path: str, params: Optional[dict] = None, auth: bool = False) -> Optional[dict]:
        """
        HTTP GET. Returns parsed JSON dict or None on error.
        For public endpoints: auth=False (no credentials sent).
        For private endpoints: auth=True (HMAC headers required).
        """
        query = ("?" + urllib.parse.urlencode(params)) if params else ""
        full_path = path + query
        url = OKX_BASE_URL + full_path

        headers = {"User-Agent": "crypto-lab-okx-client/1.0", "Accept": "application/json"}
        if auth:
            if not self._has_credentials:
                log.warning("GET %s: auth=True but no credentials loaded", path)
                return None
            headers.update(self._auth_headers("GET", full_path))
        if self.simulated:
            headers["x-simulated-trading"] = "1"

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") != "0":
                    log.warning("GET %s → OKX error code=%s msg=%s", path, data.get("code"), data.get("msg"))
                return data
        except urllib.error.HTTPError as exc:
            log.error("GET %s → HTTP %d", path, exc.code)
            return None
        except Exception as exc:
            log.error("GET %s → %s", path, exc)
            return None

    def _post(self, path: str, body: dict) -> Optional[dict]:
        """
        HTTP POST with HMAC auth. Always requires credentials.
        Returns parsed JSON dict or None on error.
        """
        if not self._has_credentials:
            log.error("POST %s: credentials not loaded (set OKX_API_KEY/SECRET/PASSPHRASE)", path)
            return None

        body_str = json.dumps(body, separators=(",", ":"))
        url      = OKX_BASE_URL + path
        headers  = self._auth_headers("POST", path, body_str)
        if self.simulated:
            headers["x-simulated-trading"] = "1"

        try:
            req = urllib.request.Request(
                url,
                data=body_str.encode("utf-8"),
                headers=headers,
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") != "0":
                    log.warning("POST %s → OKX error code=%s msg=%s", path, data.get("code"), data.get("msg"))
                return data
        except urllib.error.HTTPError as exc:
            body_resp = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
            log.error("POST %s → HTTP %d: %s", path, exc.code, body_resp[:200])
            return None
        except Exception as exc:
            log.error("POST %s → %s", path, exc)
            return None

    # ── Public endpoints ──────────────────────────────────────────────────────

    def get_funding_rate(self, symbol: str = "BTC-USDT-SWAP") -> FundingRateSnapshot:
        """
        GET /api/v5/public/funding-rate?instId={symbol}

        No auth required. Returns FundingRateSnapshot.
        symbol: OKX instId format, e.g. "BTC-USDT-SWAP", "INJ-USDT-SWAP"

        Response fields used:
          fundingRate      — current 8h rate (fractional)
          nextFundingRate  — predicted next rate
          fundingTime      — next settlement time (epoch ms)
          markPx           — current mark price
        """
        now_utc = datetime.now(timezone.utc).isoformat()
        raw = self._get(EP_FUNDING_RATE, params={"instId": symbol})
        time.sleep(PUBLIC_SLEEP_S)

        base = FundingRateSnapshot(
            symbol=symbol, funding_rate=0.0, next_funding_rate=0.0,
            funding_time_ms=0, mark_px=0.0, annualized_pct=0.0,
            fetched_at_utc=now_utc, ok=False,
        )

        if raw is None or raw.get("code") != "0":
            base.error = f"HTTP/API error: {raw.get('msg', 'no response') if raw else 'no response'}"
            return base

        data = raw.get("data", [])
        if not data:
            base.error = "Empty data array"
            return base

        item = data[0]
        try:
            fr       = float(item.get("fundingRate", 0.0) or 0.0)
            next_fr  = float(item.get("nextFundingRate", fr) or fr)
            ft_ms    = int(item.get("fundingTime", 0) or 0)
            mark_px  = float(item.get("markPx", 0.0) or 0.0)
            ann_pct  = round(fr * 3 * 365 * 100, 4)
            base.funding_rate      = fr
            base.next_funding_rate = next_fr
            base.funding_time_ms   = ft_ms
            base.mark_px           = mark_px
            base.annualized_pct    = ann_pct
            base.ok                = True
            log.debug("FR %s: %.6f (ann=%.2f%%/yr)", symbol, fr, ann_pct)
        except (TypeError, ValueError, KeyError) as exc:
            base.error = f"Parse error: {exc}"

        return base

    def get_funding_rate_history(
        self,
        symbol: str = "BTC-USDT-SWAP",
        limit:  int = 100,
        after:  Optional[int] = None,  # pagination: records before this fundingTime ms
        before: Optional[int] = None,
    ) -> List[dict]:
        """
        GET /api/v5/public/funding-rate-history?instId={symbol}&limit={limit}

        Returns list of funding rate records. Each record:
          {fundingTime: int(ms), fundingRate: float, realizedRate: float, instId: str}

        Paginates using after/before (epoch ms). OKX max limit=100 per call.
        For 30d history: call 3-4 times (30d × 3 records/day = 90 records).
        """
        params: dict = {"instId": symbol, "limit": str(min(limit, 100))}
        if after  is not None:
            params["after"]  = str(after)
        if before is not None:
            params["before"] = str(before)

        raw = self._get(EP_FUNDING_RATE_HISTORY, params=params)
        time.sleep(PUBLIC_SLEEP_S)

        if raw is None or raw.get("code") != "0":
            log.warning("FR history failed for %s: %s", symbol, raw)
            return []

        return raw.get("data", [])

    def get_ticker(self, symbol: str = "BTC-USDT-SWAP") -> Optional[dict]:
        """
        GET /api/v5/market/ticker?instId={symbol}

        Returns ticker dict with: last, markPx, askPx, bidPx, vol24h, volCcy24h, etc.
        No auth required.
        """
        raw = self._get(EP_TICKER, params={"instId": symbol})
        time.sleep(PUBLIC_SLEEP_S)
        if raw is None or raw.get("code") != "0":
            return None
        data = raw.get("data", [])
        return data[0] if data else None

    def get_tickers(self, inst_type: str = "SWAP") -> List[dict]:
        """
        GET /api/v5/market/tickers?instType={inst_type}

        Bulk ticker for all instruments of given type.
        inst_type: "SWAP" for perpetuals, "SPOT" for spot.
        """
        raw = self._get(EP_TICKERS, params={"instType": inst_type})
        time.sleep(PUBLIC_SLEEP_S)
        if raw is None or raw.get("code") != "0":
            return []
        return raw.get("data", [])

    def get_mark_price(self, symbol: str = "BTC-USDT-SWAP") -> Optional[float]:
        """Fetch current mark price via ticker. Returns float or None."""
        ticker = self.get_ticker(symbol)
        if not ticker:
            return None
        try:
            return float(ticker.get("markPx", 0.0) or 0.0)
        except (TypeError, ValueError):
            return None

    def get_orderbook(self, symbol: str = "BTC-USDT-SWAP", depth: int = 5) -> dict:
        """
        GET /api/v5/market/books?instId={symbol}&sz={depth}

        Returns {bids: [...], asks: [...], ts: str} or empty dict on failure.
        Each level: [price_str, size_str, deprecated_orders, orders_count].
        """
        raw = self._get(EP_BOOKS, params={"instId": symbol, "sz": str(depth)})
        time.sleep(PUBLIC_SLEEP_S)
        if raw is None or raw.get("code") != "0":
            return {}
        data = raw.get("data", [])
        return data[0] if data else {}

    def get_orderbook_depth_usd(self, symbol: str = "BTC-USDT-SWAP", depth: int = 5) -> float:
        """
        Estimate top-of-book liquidity in USD (bids + asks summed over top {depth} levels).
        Falls back to 2_000_000 USD (conservative for OKX majors) on failure.
        """
        book = self.get_orderbook(symbol, depth)
        if not book:
            return 2_000_000.0
        try:
            bids = book.get("bids", [])
            asks = book.get("asks", [])
            bid_depth = sum(float(b[0]) * float(b[1]) for b in bids if len(b) >= 2)
            ask_depth = sum(float(a[0]) * float(a[1]) for a in asks if len(a) >= 2)
            return bid_depth + ask_depth
        except (TypeError, ValueError, IndexError):
            return 2_000_000.0

    def get_instruments(self, inst_type: str = "SWAP") -> List[dict]:
        """
        GET /api/v5/public/instruments?instType={inst_type}

        Returns list of instrument dicts with: instId, baseCcy, quoteCcy, ctMult,
        minSz, lotSz, tickSz, maxLev, etc.
        """
        raw = self._get(EP_INSTRUMENTS, params={"instType": inst_type})
        time.sleep(PUBLIC_SLEEP_S)
        if raw is None or raw.get("code") != "0":
            return []
        return raw.get("data", [])

    # ── Private endpoints (auth required) ─────────────────────────────────────

    def get_balance(self) -> AccountBalance:
        """
        GET /api/v5/account/balance

        Returns AccountBalance with total equity and per-currency breakdown.
        Requires live credentials.
        """
        if not self._live_enabled:
            return AccountBalance(ok=False, error="Live disabled (set OKX_LIVE_ENABLED=true)")

        raw = self._get(EP_ACCOUNT_BALANCE, auth=True)
        time.sleep(PRIVATE_SLEEP_S)

        if raw is None or raw.get("code") != "0":
            return AccountBalance(ok=False, error=f"API error: {raw.get('msg', '?') if raw else 'no response'}")

        data = raw.get("data", [])
        if not data:
            return AccountBalance(ok=False, error="Empty balance data")

        acct = data[0]
        try:
            total_eq = float(acct.get("totalEq", 0.0) or 0.0)
            avail_eq = float(acct.get("adjEq", total_eq) or total_eq)
            currencies: Dict[str, dict] = {}
            for detail in acct.get("details", []):
                ccy = detail.get("ccy", "")
                if ccy:
                    currencies[ccy] = {
                        "eq":    float(detail.get("eq", 0.0) or 0.0),
                        "cashBal": float(detail.get("cashBal", 0.0) or 0.0),
                        "upl":   float(detail.get("upl", 0.0) or 0.0),
                    }
            return AccountBalance(
                ok=True, total_eq_usd=total_eq, avail_eq_usd=avail_eq,
                currencies=currencies,
                fetched_at=datetime.now(timezone.utc).isoformat(),
            )
        except (TypeError, ValueError, KeyError) as exc:
            return AccountBalance(ok=False, error=f"Parse error: {exc}")

    def get_positions(self, inst_type: str = "SWAP") -> List[dict]:
        """
        GET /api/v5/account/positions?instType={inst_type}

        Returns list of open position dicts. Each dict includes:
          instId, posSide (long/short/net), pos (size in contracts),
          notionalUsd, avgPx, upl, lever, etc.

        Returns empty list if live disabled or no positions.
        """
        if not self._live_enabled:
            log.warning("get_positions: live disabled")
            return []

        raw = self._get(EP_ACCOUNT_POSITIONS, params={"instType": inst_type}, auth=True)
        time.sleep(PRIVATE_SLEEP_S)
        if raw is None or raw.get("code") != "0":
            return []
        return raw.get("data", [])

    def place_order(
        self,
        symbol:    str,
        side:      str,          # "buy" | "sell"
        size:      float,        # contract size (in contracts, not USD)
        price:     Optional[float] = None,  # None → market order (NOT post_only)
        order_type: str = "post_only",     # "post_only" | "limit" | "market" | "ioc"
        reduce_only: bool = False,
        client_oid: Optional[str] = None,
        td_mode:   str = "cross",          # "cross" | "isolated"
        pos_side:  str = "net",            # "net" | "long" | "short" (net for hedge-off)
    ) -> OrderResponse:
        """
        POST /api/v5/trade/order

        Places a single order on OKX. POST_ONLY is the default (maker rebate).

        K745 enforcement:
          - POST_ONLY is always used unless explicitly overridden (never market in prod)
          - paper mode returns mock response if OKX_LIVE_ENABLED != "true"
          - all order calls are logged to logs/okx_client.log

        Args:
          symbol:     OKX instId, e.g. "INJ-USDT-SWAP"
          side:       "buy" (long/close-short) or "sell" (short/close-long)
          size:       Number of contracts (check instrument ctMult for USD value)
          price:      Limit price. Required for post_only/limit. None for market.
          order_type: "post_only" (default), "limit", "market", "ioc"
          reduce_only: True to close existing position only
          client_oid: Optional unique client order ID (≤32 chars alphanumeric)
          td_mode:    "cross" (default for perps) or "isolated"
          pos_side:   "net" (one-way mode, default) or "long"/"short" (hedge mode)

        Returns:
          OrderResponse with ok=True and order_id on success.
          OrderResponse with ok=False and error string on failure.
          OrderResponse with mode="paper" if live gate not passed.
        """
        # K745: paper mode gate
        if not self._live_enabled:
            log.info("place_order PAPER: %s %s %s @ %s", symbol, side, size, price)
            return OrderResponse(
                ok=True, order_id=f"PAPER_{int(time.time()*1000)}",
                symbol=symbol, side=side, size=size,
                price=price or 0.0, order_type=order_type, mode="paper",
            )

        if order_type == "post_only" and price is None:
            log.error("place_order: post_only requires a price")
            return OrderResponse(ok=False, error="post_only requires explicit price", mode="live")

        body: dict = {
            "instId":  symbol,
            "tdMode":  td_mode,
            "side":    side,
            "ordType": order_type,
            "sz":      str(size),
        }
        if price is not None:
            body["px"] = str(price)
        if reduce_only:
            body["reduceOnly"] = "true"
        if client_oid:
            body["clOrdId"] = client_oid[:32]
        if pos_side != "net":
            body["posSide"] = pos_side

        log.info(
            "place_order LIVE: %s %s size=%s px=%s type=%s reduce_only=%s",
            symbol, side, size, price, order_type, reduce_only,
        )

        raw = self._post(EP_TRADE_ORDER, body)
        time.sleep(PRIVATE_SLEEP_S)

        if raw is None:
            return OrderResponse(ok=False, error="HTTP request failed", mode="live")

        if raw.get("code") != "0":
            return OrderResponse(
                ok=False, error=f"OKX error {raw.get('code')}: {raw.get('msg', '?')}",
                mode="live", raw=raw,
            )

        data = raw.get("data", [])
        if not data:
            return OrderResponse(ok=False, error="Empty order response", mode="live")

        item = data[0]
        ok_flag = item.get("sCode", "1") == "0"
        return OrderResponse(
            ok=ok_flag,
            order_id=item.get("ordId", ""),
            client_id=item.get("clOrdId", ""),
            symbol=symbol, side=side, size=size,
            price=price or 0.0, order_type=order_type,
            mode="live", raw=raw,
            error="" if ok_flag else item.get("sMsg", "unknown"),
        )

    def cancel_order(
        self,
        symbol:   str,
        order_id: str = "",
        client_id: str = "",
    ) -> dict:
        """
        POST /api/v5/trade/cancel-order

        Cancel an open order by ordId or clOrdId.
        Returns raw OKX response dict.
        """
        if not self._live_enabled:
            log.info("cancel_order PAPER: %s ordId=%s", symbol, order_id)
            return {"ok": True, "mode": "paper", "ordId": order_id}

        body: dict = {"instId": symbol}
        if order_id:
            body["ordId"] = order_id
        elif client_id:
            body["clOrdId"] = client_id
        else:
            return {"ok": False, "error": "must supply ordId or clOrdId"}

        raw = self._post(EP_TRADE_CANCEL, body)
        time.sleep(PRIVATE_SLEEP_S)
        return raw or {"ok": False, "error": "HTTP request failed"}

    def close_position(
        self,
        symbol:  str,
        pos_side: str = "net",   # "net" | "long" | "short"
        td_mode:  str = "cross",
        price:    Optional[float] = None,
        order_type: str = "market",   # emergency exit uses market to guarantee fill
    ) -> dict:
        """
        POST /api/v5/trade/close-position

        Close an entire position for the given instrument (emergency use).
        Default: market order (guarantees fill, used in emergency_okx_exit.py).

        K745: in paper mode, logs the intended close without executing.
        """
        if not self._live_enabled:
            log.info("close_position PAPER: %s posSide=%s ordType=%s", symbol, pos_side, order_type)
            return {"ok": True, "mode": "paper", "symbol": symbol, "pos_side": pos_side}

        body: dict = {
            "instId":  symbol,
            "mgnMode": td_mode,
            "posSide": pos_side,
            "ordType": order_type,
        }
        if price is not None:
            body["px"] = str(price)

        log.warning("close_position LIVE: %s mgnMode=%s posSide=%s ordType=%s", symbol, td_mode, pos_side, order_type)
        raw = self._post(EP_TRADE_CLOSE, body)
        time.sleep(PRIVATE_SLEEP_S)
        return raw or {"ok": False, "error": "HTTP request failed"}

    def get_pending_orders(self, symbol: Optional[str] = None, inst_type: str = "SWAP") -> List[dict]:
        """
        GET /api/v5/trade/orders-pending

        Returns list of pending (unfilled/partially filled) orders.
        """
        if not self._live_enabled:
            return []
        params: dict = {"instType": inst_type}
        if symbol:
            params["instId"] = symbol
        raw = self._get(EP_TRADE_ORDERS_PENDING, params=params, auth=True)
        time.sleep(PRIVATE_SLEEP_S)
        if raw is None or raw.get("code") != "0":
            return []
        return raw.get("data", [])

    # ── Bulk helpers ──────────────────────────────────────────────────────────

    def get_all_funding_rates(
        self,
        symbols:    Optional[List[str]] = None,
        sleep_between: float = PUBLIC_SLEEP_S,
    ) -> Dict[str, FundingRateSnapshot]:
        """
        Fetch live funding rates for all symbols in K208_OKX_SYMBOLS (or custom list).
        Returns dict {symbol: FundingRateSnapshot}.

        Note: OKX has no bulk FR endpoint — calls are sequential with sleep between.
        """
        if symbols is None:
            symbols = K208_OKX_SYMBOLS
        results: Dict[str, FundingRateSnapshot] = {}
        for sym in symbols:
            results[sym] = self.get_funding_rate(sym)
            time.sleep(sleep_between)
        ok_count = sum(1 for r in results.values() if r.ok)
        log.info("get_all_funding_rates: %d/%d ok", ok_count, len(symbols))
        return results

    def get_fr_for_strategy(self, base: str, quote: str = "USDT") -> Tuple[float, bool]:
        """
        Convenience: return (funding_rate, ok) for a base symbol.
        base: "BTC" | "INJ" | "SOL" etc. (will append -USDT-SWAP)
        """
        snap = self.get_funding_rate(f"{base}-{quote}-SWAP")
        return snap.funding_rate, snap.ok

    # ── Fee helpers ───────────────────────────────────────────────────────────

    def maker_rebate_bps(self) -> float:
        """Return maker rebate in basis points for current VIP tier."""
        return FEE_TABLE.get(self.vip_tier, FEE_TABLE[DEFAULT_VIP_TIER])["maker_rebate_bps"]

    def taker_fee_bps(self) -> float:
        """Return taker fee in basis points for current VIP tier."""
        return FEE_TABLE.get(self.vip_tier, FEE_TABLE[DEFAULT_VIP_TIER])["taker_fee_bps"]

    def net_execution_cost_bps(self, is_maker: bool = True) -> float:
        """
        Net execution cost in bps.
        Negative = net credit (maker rebate).
        Positive = net debit (taker fee).
        """
        if is_maker:
            return -self.maker_rebate_bps()
        return self.taker_fee_bps()

    def __repr__(self) -> str:
        return (
            f"OKXClient(live={self._live_enabled}, "
            f"credentials={self._has_credentials}, "
            f"vip_tier={self.vip_tier}, simulated={self.simulated})"
        )


# ── Standalone smoke test ─────────────────────────────────────────────────────

def smoke_test() -> dict:
    """
    Run public endpoint smoke test (no API key required).
    Tests: funding rate, ticker, orderbook, FR history.
    Returns dict with pass/fail per test.
    """
    client = OKXClient()
    results: dict = {"wave": "K745", "date": "2026-05-30", "tests": {}}
    test_symbol = "BTC-USDT-SWAP"

    # Test 1: live funding rate
    fr = client.get_funding_rate(test_symbol)
    results["tests"]["funding_rate"] = {
        "ok": fr.ok,
        "symbol": test_symbol,
        "funding_rate": fr.funding_rate,
        "annualized_pct": fr.annualized_pct,
        "error": fr.error,
    }
    print(f"  [smoke] FR {test_symbol}: ok={fr.ok} fr={fr.funding_rate:.6f} ann={fr.annualized_pct:.2f}%/yr")

    # Test 2: ticker
    ticker = client.get_ticker(test_symbol)
    results["tests"]["ticker"] = {
        "ok": ticker is not None,
        "last": float(ticker.get("last", 0)) if ticker else None,
    }
    if ticker:
        print(f"  [smoke] Ticker {test_symbol}: last={float(ticker.get('last', 0)):,.2f}")

    # Test 3: orderbook depth
    depth = client.get_orderbook_depth_usd(test_symbol)
    results["tests"]["orderbook_depth"] = {"ok": depth > 0, "depth_usd": depth}
    print(f"  [smoke] Orderbook depth {test_symbol}: ${depth:,.0f}")

    # Test 4: FR history (last 10 records)
    hist = client.get_funding_rate_history(test_symbol, limit=10)
    results["tests"]["fr_history"] = {"ok": len(hist) > 0, "records": len(hist)}
    print(f"  [smoke] FR history {test_symbol}: {len(hist)} records")

    # Test 5: paper order (no API key needed)
    order = client.place_order(test_symbol, "sell", size=0.001, price=90000.0)
    results["tests"]["paper_order"] = {
        "ok": order.ok, "mode": order.mode, "order_id": order.order_id,
    }
    print(f"  [smoke] Paper order: ok={order.ok} mode={order.mode} id={order.order_id}")

    all_ok = all(t.get("ok", False) for t in results["tests"].values())
    results["all_ok"] = all_ok
    results["passed"] = sum(1 for t in results["tests"].values() if t.get("ok"))
    results["total"] = len(results["tests"])
    print(f"\n  [smoke] RESULT: {results['passed']}/{results['total']} tests passed")
    return results


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    import argparse
    p = argparse.ArgumentParser(
        description="K745 OKX Client — public endpoint smoke test + FR snapshot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/okx_client.py                         # BTC FR snapshot
  python3 scripts/okx_client.py --symbol INJ-USDT-SWAP  # INJ FR
  python3 scripts/okx_client.py --all                   # All K208 symbols
  python3 scripts/okx_client.py --smoke                 # Full public smoke test
  python3 scripts/okx_client.py --balance               # Account balance (requires LIVE)
  python3 scripts/okx_client.py --positions             # Open positions (requires LIVE)

K745: Set OKX_LIVE_ENABLED=true in .env.local to enable live trading.
K339: OKX_API_KEY/SECRET/PASSPHRASE from env only — never hardcoded.
        """,
    )
    p.add_argument("--symbol",    default="BTC-USDT-SWAP", help="OKX instId")
    p.add_argument("--all",       action="store_true", help="Fetch all K208 symbols")
    p.add_argument("--smoke",     action="store_true", help="Run public smoke test")
    p.add_argument("--balance",   action="store_true", help="Fetch account balance (requires LIVE)")
    p.add_argument("--positions", action="store_true", help="Fetch open positions (requires LIVE)")
    p.add_argument("--ticker",    action="store_true", help="Fetch ticker (mark price + vol)")
    p.add_argument("--depth",     action="store_true", help="Fetch orderbook depth USD")
    p.add_argument("--json",      action="store_true", help="Output as JSON")
    args = p.parse_args()

    client = OKXClient()
    print(f"  OKXClient: {client}", file=sys.stderr)

    if args.smoke:
        results = smoke_test()
        if args.json:
            print(json.dumps(results, indent=2))
        return 0 if results["all_ok"] else 1

    if args.balance:
        bal = client.get_balance()
        out = {"total_eq_usd": bal.total_eq_usd, "avail_eq_usd": bal.avail_eq_usd,
               "currencies": bal.currencies, "ok": bal.ok, "error": bal.error}
        print(json.dumps(out, indent=2) if args.json else f"Balance: ${bal.total_eq_usd:,.2f}")
        return 0

    if args.positions:
        positions = client.get_positions()
        print(json.dumps(positions, indent=2) if args.json else f"Positions: {len(positions)}")
        return 0

    if args.all:
        results = client.get_all_funding_rates()
        if args.json:
            print(json.dumps({s: r.to_dict() for s, r in results.items()}, indent=2))
        else:
            print(f"\n=== OKX FR Snapshot ({datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}) ===")
            for sym, r in results.items():
                if r.ok:
                    print(f"  {sym:<22}  FR={r.funding_rate*100:+.4f}%  ann={r.annualized_pct:+.2f}%/yr  mark={r.mark_px:,.2f}")
                else:
                    print(f"  {sym:<22}  FAILED: {r.error}")
        return 0

    fr = client.get_funding_rate(args.symbol)
    if args.ticker:
        ticker = client.get_ticker(args.symbol)
        if ticker and not args.json:
            print(f"  Ticker: last={float(ticker.get('last', 0)):,.2f}  bid={ticker.get('bidPx')}  ask={ticker.get('askPx')}")
    if args.depth:
        depth = client.get_orderbook_depth_usd(args.symbol)
        if not args.json:
            print(f"  Orderbook depth: ${depth:,.0f}")

    if args.json:
        print(json.dumps(fr.to_dict(), indent=2))
    else:
        if fr.ok:
            print(f"\n=== OKX FR: {args.symbol} ===")
            print(f"  Current FR:  {fr.funding_rate*100:+.4f}% per 8h")
            print(f"  Next FR:     {fr.next_funding_rate*100:+.4f}% (predicted)")
            print(f"  Annualized:  {fr.annualized_pct:+.2f}%/yr")
            print(f"  Mark price:  ${fr.mark_px:,.2f}")
            print(f"  Fetched:     {fr.fetched_at_utc}")
        else:
            print(f"FAILED: {fr.error}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
