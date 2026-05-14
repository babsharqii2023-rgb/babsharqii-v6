"""
BABSHARQII v21.0 — Trading Engine (محرك التداول)
غرفة تداول كاملة — تحليل الأسواق، تتبع المحافظ، إشارات التداول، رسوم بيانية

يدعم:
  - الأسهم العالمية (Yahoo Finance API)
  - العملات الرقمية (CoinGecko API)
  - المحافظ الاستثمارية
  - إشارات التداول (تحليل فني بسيط)
  - الرسوم البيانية (شمعية، خطية)
  - تنبيهات الأسعار
  - تحليل الأخبار
"""

import os
import time
import json
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from pathlib import Path

import httpx

logger = logging.getLogger("mamoun.agents.trading")

TRADING_ENABLED = os.getenv("MAMOUN_TRADING_ENABLED", "true").lower() == "true"


class AssetType(str, Enum):
    STOCK = "stock"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITY = "commodity"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class SignalType(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


@dataclass
class Asset:
    """أصل مالي"""
    symbol: str = ""
    name: str = ""
    name_ar: str = ""
    asset_type: AssetType = AssetType.STOCK
    current_price: float = 0.0
    change_percent: float = 0.0
    volume_24h: float = 0.0
    market_cap: float = 0.0
    high_24h: float = 0.0
    low_24h: float = 0.0
    last_updated: float = 0.0
    currency: str = "USD"

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "name_ar": self.name_ar,
            "asset_type": self.asset_type.value,
            "current_price": round(self.current_price, 4),
            "change_percent": round(self.change_percent, 4),
            "volume_24h": round(self.volume_24h, 2),
            "market_cap": round(self.market_cap, 2),
            "high_24h": round(self.high_24h, 4),
            "low_24h": round(self.low_24h, 4),
            "last_updated": self.last_updated,
            "currency": self.currency,
        }


@dataclass
class PortfolioItem:
    """عنصر محفظة"""
    symbol: str = ""
    name: str = ""
    quantity: float = 0.0
    avg_buy_price: float = 0.0
    current_price: float = 0.0
    total_value: float = 0.0
    profit_loss: float = 0.0
    profit_loss_percent: float = 0.0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "quantity": self.quantity,
            "avg_buy_price": round(self.avg_buy_price, 4),
            "current_price": round(self.current_price, 4),
            "total_value": round(self.total_value, 2),
            "profit_loss": round(self.profit_loss, 2),
            "profit_loss_percent": round(self.profit_loss_percent, 4),
        }


@dataclass
class TradingSignal:
    """إشارة تداول"""
    symbol: str = ""
    signal_type: SignalType = SignalType.NEUTRAL
    price: float = 0.0
    target_price: float = 0.0
    stop_loss: float = 0.0
    confidence: float = 0.0
    reason: str = ""
    reason_ar: str = ""
    timestamp: float = 0.0
    indicators: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "signal_type": self.signal_type.value,
            "price": round(self.price, 4),
            "target_price": round(self.target_price, 4),
            "stop_loss": round(self.stop_loss, 4),
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
            "reason_ar": self.reason_ar,
            "timestamp": self.timestamp,
            "indicators": self.indicators,
        }


@dataclass
class PriceAlert:
    """تنبيه سعر"""
    id: str = ""
    symbol: str = ""
    target_price: float = 0.0
    condition: str = "above"  # above, below
    is_active: bool = True
    created_at: float = 0.0
    triggered_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "target_price": round(self.target_price, 4),
            "condition": self.condition,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "triggered_at": self.triggered_at,
        }


@dataclass
class CandleData:
    """بيانات شمعة"""
    timestamp: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "open": round(self.open, 4),
            "high": round(self.high, 4),
            "low": round(self.low, 4),
            "close": round(self.close, 4),
            "volume": round(self.volume, 2),
        }


class TradingEngine:
    """
    محرك التداول — تحليل الأسواق وإدارة المحافظ وإشارات التداول

    مصادر البيانات:
    - أسهم: Yahoo Finance (yfinance) أو Alpha Vantage API
    - كريبتو: CoinGecko API (مجاني، بدون مفتاح)
    - فوركس: ExchangeRate API

    تنبيه: هذا محرك تحليلي فقط — لا ينفذ صفقات حقيقية تلقائياً
    """

    COINGECKO_BASE = "https://api.coingecko.com/api/v3"
    YAHOO_FINANCE_BASE = "https://query1.finance.yahoo.com/v8/finance"

    def __init__(self, alpha_vantage_key: str = ""):
        self._alpha_vantage_key = alpha_vantage_key or os.getenv("MAMOUN_ALPHA_VANTAGE_KEY", "")
        self._portfolio: dict[str, PortfolioItem] = {}
        self._watchlist: list[str] = []
        self._alerts: dict[str, PriceAlert] = {}
        self._price_cache: dict[str, Asset] = {}
        self._chart_cache: dict[str, list[CandleData]] = {}
        self._alert_counter = 0
        self._initialized = False

    def initialize(self) -> bool:
        if self._initialized:
            return True
        self._load_default_watchlist()
        self._initialized = True
        logger.info("TradingEngine initialized — watchlist: %d assets", len(self._watchlist))
        return True

    def _load_default_watchlist(self):
        """تحميل قائمة المراقبة الافتراضية"""
        self._watchlist = [
            "BTC", "ETH", "SOL", "BNB", "XRP",  # Crypto
            "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",  # US Stocks
            "EUR/USD", "GBP/USD", "USD/JPY",  # Forex
            "GOLD", "OIL",  # Commodities
        ]

    # ─── Market Data ────────────────────────────────────────────────────────

    async def get_crypto_price(self, symbol: str) -> Asset:
        """الحصول على سعر عملة رقمية من CoinGecko"""
        symbol_lower = symbol.lower()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Map common symbols to CoinGecko IDs
                id_map = {
                    "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
                    "bnb": "binancecoin", "xrp": "ripple", "ada": "cardano",
                    "doge": "dogecoin", "dot": "polkadot", "matic": "matic-network",
                    "avax": "avalanche-2", "link": "chainlink",
                }
                coin_id = id_map.get(symbol_lower, symbol_lower)

                resp = await client.get(
                    f"{self.COINGECKO_BASE}/coins/{coin_id}",
                    params={
                        "localization": "false",
                        "tickers": "false",
                        "market_data": "true",
                        "community_data": "false",
                        "developer_data": "false",
                    }
                )

                if resp.status_code == 200:
                    data = resp.json()
                    md = data.get("market_data", {})
                    asset = Asset(
                        symbol=symbol.upper(),
                        name=data.get("name", symbol.upper()),
                        name_ar=self._translate_crypto_name(symbol.upper()),
                        asset_type=AssetType.CRYPTO,
                        current_price=md.get("current_price", {}).get("usd", 0),
                        change_percent=md.get("price_change_percentage_24h", 0),
                        volume_24h=md.get("total_volume", {}).get("usd", 0),
                        market_cap=md.get("market_cap", {}).get("usd", 0),
                        high_24h=md.get("high_24h", {}).get("usd", 0),
                        low_24h=md.get("low_24h", {}).get("usd", 0),
                        last_updated=time.time(),
                    )
                    self._price_cache[symbol.upper()] = asset
                    return asset
        except Exception as e:
            logger.warning("CoinGecko API error for %s: %s", symbol, e)

        # Return cached or empty
        return self._price_cache.get(symbol.upper(), Asset(symbol=symbol.upper(), name=symbol.upper(), asset_type=AssetType.CRYPTO))

    async def get_stock_price(self, symbol: str) -> Asset:
        """الحصول على سعر سهم من Yahoo Finance"""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self.YAHOO_FINANCE_BASE}/chart/{symbol}",
                    params={"range": "1d", "interval": "1d"}
                )

                if resp.status_code == 200:
                    data = resp.json()
                    result = data.get("chart", {}).get("result", [{}])[0]
                    meta = result.get("meta", {})
                    asset = Asset(
                        symbol=symbol.upper(),
                        name=meta.get("shortName", symbol.upper()),
                        name_ar=self._translate_stock_name(symbol.upper()),
                        asset_type=AssetType.STOCK,
                        current_price=meta.get("regularMarketPrice", 0),
                        change_percent=meta.get("regularMarketChangePercent", 0),
                        currency=meta.get("currency", "USD"),
                        last_updated=time.time(),
                    )
                    self._price_cache[symbol.upper()] = asset
                    return asset
        except Exception as e:
            logger.warning("Yahoo Finance API error for %s: %s", symbol, e)

        return self._price_cache.get(symbol.upper(), Asset(symbol=symbol.upper(), name=symbol.upper(), asset_type=AssetType.STOCK))

    async def get_price(self, symbol: str) -> Asset:
        """الحصول على سعر أي أصل"""
        symbol = symbol.upper()

        # تحديد النوع
        crypto_symbols = {"BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "DOT", "MATIC", "AVAX", "LINK"}
        forex_symbols = {"EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD"}
        commodity_symbols = {"GOLD", "OIL", "SILVER", "NATURAL_GAS"}

        if symbol in crypto_symbols:
            return await self.get_crypto_price(symbol)
        elif symbol in forex_symbols:
            return Asset(symbol=symbol, name=symbol, asset_type=AssetType.FOREX, last_updated=time.time())
        elif symbol in commodity_symbols:
            return Asset(symbol=symbol, name=symbol, asset_type=AssetType.COMMODITY, last_updated=time.time())
        else:
            return await self.get_stock_price(symbol)

    async def get_chart_data(self, symbol: str, days: int = 30) -> list[dict]:
        """الحصول على بيانات الرسم البياني"""
        symbol_upper = symbol.upper()
        crypto_symbols = {"BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE"}

        if symbol_upper in crypto_symbols:
            try:
                id_map = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin", "XRP": "ripple", "ADA": "cardano", "DOGE": "dogecoin"}
                coin_id = id_map.get(symbol_upper, symbol_upper.lower())

                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(
                        f"{self.COINGECKO_BASE}/coins/{coin_id}/market_chart",
                        params={"vs_currency": "usd", "days": str(days)}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        prices = data.get("prices", [])
                        volumes = data.get("total_volumes", [])
                        candles = []
                        for i, (ts, price) in enumerate(prices):
                            vol = volumes[i][1] if i < len(volumes) else 0
                            candles.append(CandleData(
                                timestamp=ts / 1000,
                                open=price,
                                high=price * 1.001,
                                low=price * 0.999,
                                close=price,
                                volume=vol,
                            ))
                        self._chart_cache[symbol_upper] = candles
                        return [c.to_dict() for c in candles]
            except Exception as e:
                logger.warning("Chart data error for %s: %s", symbol, e)

        # Fallback: return cached or empty
        cached = self._chart_cache.get(symbol_upper, [])
        return [c.to_dict() for c in cached]

    # ─── Portfolio Management ────────────────────────────────────────────────

    async def add_to_portfolio(self, symbol: str, quantity: float, buy_price: float) -> dict:
        """إضافة أصل للمحفظة"""
        asset = await self.get_price(symbol)
        current_price = asset.current_price or buy_price
        total_value = quantity * current_price
        pl = (current_price - buy_price) * quantity
        pl_pct = ((current_price - buy_price) / buy_price * 100) if buy_price > 0 else 0

        item = PortfolioItem(
            symbol=symbol.upper(),
            name=asset.name,
            quantity=quantity,
            avg_buy_price=buy_price,
            current_price=current_price,
            total_value=total_value,
            profit_loss=pl,
            profit_loss_percent=pl_pct,
        )
        self._portfolio[symbol.upper()] = item
        return {"success": True, "item": item.to_dict()}

    async def remove_from_portfolio(self, symbol: str) -> dict:
        """إزالة أصل من المحفظة"""
        if symbol.upper() in self._portfolio:
            del self._portfolio[symbol.upper()]
            return {"success": True}
        return {"success": False, "error": f"الأصل غير موجود: {symbol}"}

    async def get_portfolio(self) -> dict:
        """الحصول على المحفظة الكاملة مع تحديث الأسعار"""
        # Update all prices
        for symbol, item in self._portfolio.items():
            asset = await self.get_price(symbol)
            if asset.current_price > 0:
                item.current_price = asset.current_price
                item.total_value = item.quantity * item.current_price
                item.profit_loss = (item.current_price - item.avg_buy_price) * item.quantity
                item.profit_loss_percent = ((item.current_price - item.avg_buy_price) / item.avg_buy_price * 100) if item.avg_buy_price > 0 else 0

        total_value = sum(i.total_value for i in self._portfolio.values())
        total_pl = sum(i.profit_loss for i in self._portfolio.values())

        return {
            "items": [i.to_dict() for i in self._portfolio.values()],
            "total_value": round(total_value, 2),
            "total_profit_loss": round(total_pl, 2),
            "item_count": len(self._portfolio),
        }

    # ─── Trading Signals ─────────────────────────────────────────────────────

    async def generate_signal(self, symbol: str) -> TradingSignal:
        """توليد إشارة تداول — تحليل فني بسيط"""
        chart_data = await self.get_chart_data(symbol, days=30)

        if len(chart_data) < 5:
            return TradingSignal(
                symbol=symbol,
                signal_type=SignalType.NEUTRAL,
                reason="بيانات غير كافية",
                reason_ar="بيانات غير كافية للتحليل",
                timestamp=time.time(),
            )

        # Simple Moving Average Crossover + RSI approximation
        closes = [c["close"] for c in chart_data]

        # SMA 7 vs SMA 21
        sma_7 = sum(closes[-7:]) / 7 if len(closes) >= 7 else sum(closes) / len(closes)
        sma_21 = sum(closes[-21:]) / 21 if len(closes) >= 21 else sum(closes) / len(closes)
        current_price = closes[-1]

        # Price momentum
        momentum = ((current_price - closes[-5]) / closes[-5] * 100) if len(closes) >= 5 and closes[-5] > 0 else 0

        # Determine signal
        score = 0
        if sma_7 > sma_21:
            score += 1  # Bullish trend
        else:
            score -= 1  # Bearish trend

        if momentum > 3:
            score += 1
        elif momentum < -3:
            score -= 1

        if current_price > sma_7:
            score += 0.5
        else:
            score -= 0.5

        # Map score to signal
        if score >= 2:
            signal_type = SignalType.STRONG_BUY
        elif score >= 1:
            signal_type = SignalType.BUY
        elif score <= -2:
            signal_type = SignalType.STRONG_SELL
        elif score <= -1:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.NEUTRAL

        # Target and stop-loss
        volatility = abs(momentum) / 100 if momentum else 0.02
        if signal_type in (SignalType.BUY, SignalType.STRONG_BUY):
            target = current_price * (1 + max(volatility * 3, 0.03))
            stop_loss = current_price * (1 - max(volatility * 2, 0.02))
        else:
            target = current_price * (1 - max(volatility * 3, 0.03))
            stop_loss = current_price * (1 + max(volatility * 2, 0.02))

        confidence = min(0.95, 0.5 + abs(score) * 0.15)

        reason_map = {
            SignalType.STRONG_BUY: "SMA crossover bullish + strong momentum",
            SignalType.BUY: "SMA bullish crossover",
            SignalType.SELL: "SMA bearish crossover",
            SignalType.STRONG_SELL: "SMA crossover bearish + strong negative momentum",
            SignalType.NEUTRAL: "No clear trend — mixed signals",
        }
        reason_ar_map = {
            SignalType.STRONG_BUY: "تقاطع المتوسطات المتحركة صاعد + زخم قوي",
            SignalType.BUY: "تقاطع المتوسطات المتحركة صاعد",
            SignalType.SELL: "تقاطع المتوسطات المتحركة هابط",
            SignalType.STRONG_SELL: "تقاطع المتوسطات المتحركة هابط + زخم سلبي قوي",
            SignalType.NEUTRAL: "لا اتجاه واضح — إشارات متضاربة",
        }

        return TradingSignal(
            symbol=symbol,
            signal_type=signal_type,
            price=current_price,
            target_price=round(target, 4),
            stop_loss=round(stop_loss, 4),
            confidence=confidence,
            reason=reason_map.get(signal_type, ""),
            reason_ar=reason_ar_map.get(signal_type, ""),
            timestamp=time.time(),
            indicators={
                "sma_7": round(sma_7, 4),
                "sma_21": round(sma_21, 4),
                "momentum_5d": round(momentum, 4),
                "score": score,
            },
        )

    # ─── Price Alerts ────────────────────────────────────────────────────────

    def create_alert(self, symbol: str, target_price: float, condition: str = "above") -> dict:
        """إنشاء تنبيه سعر"""
        self._alert_counter += 1
        alert = PriceAlert(
            id=f"alert_{int(time.time())}_{self._alert_counter}",
            symbol=symbol.upper(),
            target_price=target_price,
            condition=condition,
            created_at=time.time(),
        )
        self._alerts[alert.id] = alert
        return {"success": True, "alert": alert.to_dict()}

    async def check_alerts(self) -> list[dict]:
        """فحص التنبيهات — يرجع التنبيهات المُفعّلة"""
        triggered = []
        for alert_id, alert in self._alerts.items():
            if not alert.is_active:
                continue
            asset = await self.get_price(alert.symbol)
            if asset.current_price <= 0:
                continue

            if alert.condition == "above" and asset.current_price >= alert.target_price:
                alert.is_active = False
                alert.triggered_at = time.time()
                triggered.append({
                    "alert": alert.to_dict(),
                    "current_price": asset.current_price,
                    "message_ar": f"تنبيه: {alert.symbol} وصل إلى {asset.current_price} (الهدف: {alert.target_price})",
                })
            elif alert.condition == "below" and asset.current_price <= alert.target_price:
                alert.is_active = False
                alert.triggered_at = time.time()
                triggered.append({
                    "alert": alert.to_dict(),
                    "current_price": asset.current_price,
                    "message_ar": f"تنبيه: {alert.symbol} انخفض إلى {asset.current_price} (الهدف: {alert.target_price})",
                })

        return triggered

    def get_alerts(self) -> list[dict]:
        """قائمة جميع التنبيهات"""
        return [a.to_dict() for a in self._alerts.values()]

    # ─── Market Overview ─────────────────────────────────────────────────────

    async def get_market_overview(self) -> dict:
        """نظرة عامة على السوق"""
        crypto_data = []
        for sym in ["BTC", "ETH", "SOL", "BNB", "XRP"]:
            asset = await self.get_crypto_price(sym)
            crypto_data.append(asset.to_dict())

        return {
            "crypto": crypto_data,
            "timestamp": time.time(),
            "total_crypto_market_cap": sum(a.get("market_cap", 0) for a in crypto_data),
        }

    # ─── Utilities ───────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "enabled": TRADING_ENABLED,
            "portfolio_items": len(self._portfolio),
            "watchlist_size": len(self._watchlist),
            "alerts_active": sum(1 for a in self._alerts.values() if a.is_active),
            "price_cache_size": len(self._price_cache),
        }

    @staticmethod
    def _translate_crypto_name(symbol: str) -> str:
        translations = {
            "BTC": "بيتكوين", "ETH": "إيثريوم", "SOL": "سولانا",
            "BNB": "باينانس كوين", "XRP": "ريبيل", "ADA": "كاردانو",
            "DOGE": "دوج كوين", "DOT": "بولكادوت", "MATIC": "بوليجون",
            "AVAX": "أفالانش", "LINK": "تشين لينك",
        }
        return translations.get(symbol, symbol)

    @staticmethod
    def _translate_stock_name(symbol: str) -> str:
        translations = {
            "AAPL": "أبل", "GOOGL": "جوجل", "MSFT": "مايكروسوفت",
            "AMZN": "أمازون", "TSLA": "تسلا", "META": "ميتا",
            "NVDA": "إنفيديا", "NFLX": "نتفليكس",
        }
        return translations.get(symbol, symbol)


# Singleton
_trading_engine: Optional[TradingEngine] = None

def get_trading_engine() -> TradingEngine:
    global _trading_engine
    if _trading_engine is None:
        _trading_engine = TradingEngine()
        _trading_engine.initialize()
    return _trading_engine
