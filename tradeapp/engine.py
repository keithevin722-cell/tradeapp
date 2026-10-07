"""Simulated trading engine for tokenized real-world assets (RWAs)."""
import threading
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")
UNIT = Decimal("0.000001")


class TradeError(ValueError):
    pass


@dataclass
class Asset:
    symbol: str
    name: str
    category: str
    price: Decimal


def default_assets():
    return [
        Asset("TBILL", "Tokenized US Treasury Bill", "Treasuries", Decimal("100.00")),
        Asset("REIT1", "Manhattan Office Building Token", "Real Estate", Decimal("52.50")),
        Asset("GOLD", "Tokenized Gold (1 oz fractions)", "Commodities", Decimal("2350.00")),
        Asset("ART1", "Fine Art Collection Token", "Collectibles", Decimal("18.75")),
        Asset("CRED1", "Private Credit Pool Token", "Private Credit", Decimal("10.20")),
    ]


@dataclass
class Account:
    cash: Decimal
    holdings: dict = field(default_factory=dict)
    trades: list = field(default_factory=list)


def _dec(value, name):
    try:
        d = Decimal(str(value))
    except Exception:
        raise TradeError(f"invalid {name}")
    if not d.is_finite():
        raise TradeError(f"invalid {name}")
    return d


class Exchange:
    def __init__(self, assets=None, cash="100000"):
        self.assets = {a.symbol: a for a in (assets or default_assets())}
        self.account = Account(cash=Decimal(cash))
        self._lock = threading.RLock()

    def quote(self, symbol):
        try:
            return self.assets[symbol.upper()]
        except (KeyError, AttributeError):
            raise TradeError("unknown asset")

    def set_price(self, symbol, price):
        price = _dec(price, "price")
        if price <= 0:
            raise TradeError("price must be positive")
        with self._lock:
            self.quote(symbol).price = price.quantize(CENT, ROUND_HALF_UP)

    def trade(self, side, symbol, quantity):
        """Execute a market order at the current price."""
        side = str(side).lower()
        if side not in ("buy", "sell"):
            raise TradeError("side must be buy or sell")
        qty = _dec(quantity, "quantity").quantize(UNIT, ROUND_HALF_UP)
        if qty <= 0:
            raise TradeError("quantity must be positive")
        with self._lock:
            asset = self.quote(symbol)
            total = (asset.price * qty).quantize(CENT, ROUND_HALF_UP)
            acct = self.account
            held = acct.holdings.get(asset.symbol, Decimal(0))
            if side == "buy":
                if total > acct.cash:
                    raise TradeError("insufficient cash")
                acct.cash -= total
                acct.holdings[asset.symbol] = held + qty
            else:
                if qty > held:
                    raise TradeError("insufficient holdings")
                acct.cash += total
                if held - qty == 0:
                    del acct.holdings[asset.symbol]
                else:
                    acct.holdings[asset.symbol] = held - qty
            rec = {"side": side, "symbol": asset.symbol, "quantity": str(qty),
                   "price": str(asset.price), "total": str(total)}
            acct.trades.append(rec)
            return rec

    def snapshot(self):
        with self._lock:
            acct = self.account
            positions = []
            equity = acct.cash
            for sym, qty in acct.holdings.items():
                value = (self.assets[sym].price * qty).quantize(CENT, ROUND_HALF_UP)
                equity += value
                positions.append({"symbol": sym, "quantity": str(qty), "value": str(value)})
            return {
                "assets": [{"symbol": a.symbol, "name": a.name, "category": a.category,
                            "price": str(a.price)} for a in self.assets.values()],
                "cash": str(acct.cash),
                "equity": str(equity),
                "positions": positions,
                "trades": acct.trades[-50:][::-1],
            }
