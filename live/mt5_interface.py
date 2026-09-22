"""
mt5_interface.py -- thin wrapper around the MetaTrader5 Python package,
used ONLY for (a) verifying which account the local terminal is logged
into before any signal is generated -- this project's requested
fail-safe, (b) reading live account equity, (c) reading the ACTUAL open
position for the traded symbol (so the daemon reconciles against reality
every run instead of trusting a locally-cached state file that could
drift after a manual intervention), and (d) pulling recent daily bars.
It never places, modifies, or closes an order -- that stays a manual,
human step, consistent with this project's existing "not wired to a
broker for execution" stance (see tf3_xauusd_live.py's own docstring).

This module requires the `MetaTrader5` package AND a running MT5
terminal on the SAME machine, logged into the account you intend to
check. That package only works on Windows (it talks to a local terminal
process, not a remote API), and only while the terminal is running and
logged in. It CANNOT be exercised from this research sandbox -- there is
no Windows terminal here, and this was never tested end-to-end against a
real account. That is exactly why MockMT5 exists below: it reproduces
the same interface against a static CSV and a fake, configurable
account, purely so the REST of the daemon's logic (account-check control
flow, signal computation, message formatting) can be exercised and
verified without a live terminal. Swapping MockMT5 for RealMT5 is a
one-line change in tf3_daemon.py's get_interface().
"""
import pandas as pd

try:
    import MetaTrader5 as mt5
    _HAS_MT5 = True
except ImportError:
    _HAS_MT5 = False


class MT5ConnectionError(Exception):
    pass


class RealMT5:
    """Live wrapper. Only usable on Windows, with the MetaTrader5 package
    installed and a running, logged-in terminal on this same machine.
    UNTESTED in this project -- no Windows terminal or real account was
    available to verify this against. Treat it as a documented starting
    point to validate on your own machine before trusting it, not as a
    proven integration."""

    def __init__(self):
        if not _HAS_MT5:
            raise MT5ConnectionError(
                "MetaTrader5 package is not installed. It only works on Windows, "
                "alongside a running MT5 terminal. `pip install MetaTrader5` on "
                "the machine where the terminal runs -- not in a cloud research "
                "sandbox, which cannot host a live terminal at all."
            )

    def connect(self):
        if not mt5.initialize():
            raise MT5ConnectionError(f"mt5.initialize() failed: {mt5.last_error()}")

    def shutdown(self):
        mt5.shutdown()

    def account_info(self):
        info = mt5.account_info()
        if info is None:
            raise MT5ConnectionError(f"mt5.account_info() returned None: {mt5.last_error()}")
        return {"login": info.login, "server": info.server, "equity": info.equity,
                "balance": info.balance, "currency": info.currency}

    def open_volume(self, symbol):
        """Net open volume in lots for `symbol`, positive = net long,
        negative = net short. Sums across all open positions on that
        symbol -- if you ever hold split/hedged positions on the same
        symbol, this collapses them to a net figure, which is what the
        long-only position-fraction reconciliation below needs."""
        positions = mt5.positions_get(symbol=symbol)
        if positions is None:
            return 0.0
        net = 0.0
        for p in positions:
            # MT5 POSITION_TYPE_BUY=0, POSITION_TYPE_SELL=1
            net += p.volume if p.type == 0 else -p.volume
        return net

    def recent_daily_bars(self, symbol, n_bars):
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, n_bars)
        if rates is None or len(rates) == 0:
            raise MT5ConnectionError(f"copy_rates_from_pos returned no data for {symbol}: {mt5.last_error()}")
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df = df.set_index('time')
        return df[['close', 'high', 'low', 'spread']]


class MockMT5:
    """Reproduces RealMT5's interface against a static CSV and a
    configurable fake account, so the REST of the daemon (account-check
    control flow, signal math, message formatting) can be tested without
    a live terminal. This validates the daemon's logic ONLY -- it proves
    nothing about a real MT5 connection, a real GFT account, or real
    Telegram delivery."""

    def __init__(self, price_csv, fake_login=99999999, fake_server='MockServer-Demo',
                 fake_equity=10000.0, fake_open_volume=0.0, fake_bar_offset_days=0):
        self.price_csv = price_csv
        self.fake_login = fake_login
        self.fake_server = fake_server
        self.fake_equity = fake_equity
        self.fake_open_volume = fake_open_volume
        self.fake_bar_offset_days = fake_bar_offset_days  # simulate stale data by dropping recent rows
        self._connected = False

    def connect(self):
        self._connected = True

    def shutdown(self):
        self._connected = False

    def account_info(self):
        if not self._connected:
            raise MT5ConnectionError("MockMT5 not connected -- call connect() first.")
        return {"login": self.fake_login, "server": self.fake_server, "equity": self.fake_equity,
                "balance": self.fake_equity, "currency": "USD"}

    def open_volume(self, symbol):
        return self.fake_open_volume

    def recent_daily_bars(self, symbol, n_bars):
        d = pd.read_csv(self.price_csv, parse_dates=['time']).set_index('time')
        d = d[['close', 'high', 'low', 'spread']]
        if self.fake_bar_offset_days > 0:
            d = d.iloc[:-self.fake_bar_offset_days]
        return d.tail(n_bars)


def verify_account(iface, expected_login, expected_server):
    """Returns (ok: bool, info: dict). Never raises on a mismatch -- a
    mismatch is an expected, handled outcome (wrong account logged in,
    or the demo account left open instead of the funded one), not a bug
    in this script. Raises MT5ConnectionError only if the terminal
    itself can't be reached at all, which is a separate failure mode."""
    info = iface.account_info()
    ok = (int(info["login"]) == int(expected_login)) and (str(info["server"]) == str(expected_server))
    return ok, info
