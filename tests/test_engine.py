import unittest
from decimal import Decimal

from tradeapp.engine import Exchange, TradeError


class ExchangeTest(unittest.TestCase):
    def test_buy_and_sell(self):
        ex = Exchange(cash="1000")
        ex.trade("buy", "TBILL", "2")
        self.assertEqual(ex.account.cash, Decimal("800.00"))
        ex.trade("sell", "tbill", "1")
        self.assertEqual(ex.account.holdings["TBILL"], Decimal("1"))
        self.assertEqual(ex.account.cash, Decimal("900.00"))

    def test_errors(self):
        ex = Exchange(cash="10")
        for args in [("buy", "GOLD", "1"), ("sell", "GOLD", "1"), ("buy", "NOPE", "1"),
                     ("hold", "GOLD", "1"), ("buy", "GOLD", "-1"), ("buy", "GOLD", "abc"),
                     ("buy", "GOLD", "nan")]:
            with self.assertRaises(TradeError):
                ex.trade(*args)


if __name__ == "__main__":
    unittest.main()
