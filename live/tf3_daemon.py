"""
tf3_daemon.py -- unattended daily run: verify the correct MT5 account is
logged in, compute TF3's long-only target position/lots from live data,
and push the result to Telegram. Designed to be triggered once per day
(after the daily close you're trading against) by a scheduler running ON
THE SAME MACHINE as the MT5 terminal -- Windows Task Scheduler is the
natural choice, since MetaTrader5's Python package only talks to a local
terminal process, not a remote one. See "Scheduling" at the bottom of
this docstring.

WHAT THIS DOES:
  1. Refuses to run twice in the same calendar day unless --force, so an
     accidental double-trigger doesn't double-alert.
  2. Connects to the local MT5 terminal. If it can't connect at all, that
     itself is a CRITICAL Telegram alert (best-effort) plus a local log
     entry -- no signal is computed.
  3. Reads which account is logged in (login + server) and compares it
     against EXPECTED_ACCOUNT_LOGIN / EXPECTED_ACCOUNT_SERVER in .env.
     THIS IS THE FAIL-SAFE THE MODEL WAS ASKED FOR:
     if they don't match, it sends a CRITICAL alert and stops -- it does
     NOT compute or send a signal for an unverified account. A signal
     silently computed against the wrong account (e.g. a demo account
     left open, or the 5k config accidentally pointed at the 10k
     account) is worse than no signal at all.
  4. Reads live account equity and the ACTUALLY open position (lots) for
     the traded symbol from MT5, and reconciles that into TF3's internal
     0..1 position-fraction convention -- it does NOT trust a locally
     cached "held position" file, so a manual override you made
     yesterday is picked up correctly today instead of silently
     overridden.
  5. Pulls recent daily bars from MT5, checks they're not stale (no bar
     for the last N days -- see stale_bar_max_age_days), and computes
     TF3's exact long-only EWMAC forecast + position-inertia buffer +
     risk-governor check, reusing tf3_challenge_live.py's own functions
     rather than reimplementing them.
  6. Formats and sends a Telegram message with the result, EVERY day the
     daemon successfully runs -- whether or not the target position
     changed -- so silence is never ambiguous between "nothing to do"
     and "the scheduled run silently died." A run that fails to reach
     Telegram still writes the same message to a local log file, so
     nothing is lost even if the alert itself doesn't arrive.
  7. NEVER places, modifies, or closes an order. This computes a target
     only, exactly like tf3_challenge_live.py. Wiring actual order
     execution is a separate, larger, unreviewed step this project has
     deliberately not taken (see tf3_xauusd_live.py's own docstring) --
     adding an unattended alerting layer on top of research-validated
     signal logic is a materially smaller, more reviewable change than
     adding unattended order placement would be, and this script does
     not conflate the two.

WHAT THIS DOES NOT DO, DISCLOSED PLAINLY:
  - It has never been run against a real MT5 terminal or a real GFT
    account. mt5_interface.py's RealMT5 class is documented, reasonable,
    standard MetaTrader5-package usage -- but untested here, because
    there is no Windows terminal in this sandbox to test it against.
    Run --dry-run first (works right now, see below), then validate
    RealMT5 against your own demo account before trusting it on a real
    challenge attempt.
  - It has never sent a real Telegram message. telegram_notify.py is
    tested for request construction and failure handling, not delivery.
  - It does not implement the data-integrity or regime kill switches
    described qualitatively in the deployment spec (tf3_addendum_02,
    item 4) -- the staleness check here is a narrower, simpler check
    (is the last bar recent) than what that spec envisioned.
  - It has no self-monitoring of its own uptime (e.g. "the scheduled
    task didn't fire at all today"). That has to be handled by whatever
    scheduler triggers this -- Windows Task Scheduler has its own
    history/logging you should check periodically, since this script
    can only alert about failures it's actually running to observe.

DRY-RUN (works right now, in any Python environment, no MT5/Telegram
needed -- exercises the full control flow against the mock interface and
this project's own historical CSV, printing what WOULD be sent):
    python3 tf3_daemon.py --dry-run
    python3 tf3_daemon.py --dry-run --simulate wrong-account
    python3 tf3_daemon.py --dry-run --simulate stale-data
    python3 tf3_daemon.py --dry-run --simulate halt

REAL RUN (only after RealMT5 has been validated on your own machine):
    python3 tf3_daemon.py
    python3 tf3_daemon.py --force   # re-run + re-alert even if already run today

SCHEDULING (Windows Task Scheduler, since MT5 runs on Windows):
  Create a Basic Task -> Trigger: Daily, shortly after your intended
  "day close" cutoff -> Action: "Start a program" ->
    Program: path to python.exe (the one with MetaTrader5 installed)
    Arguments: full path to this script
    Start in: this script's own directory (so challenge_config.json,
      daemon_config.json, .env, governor_state.json, daemon_state.json all
      resolve as relative paths correctly)
  Tick "Run whether user is logged on or not" only if the MT5 terminal
  itself is also configured to start without an interactive login --
  otherwise the terminal may not be running when the task fires, which
  this script will correctly report as a connection failure rather than
  silently doing nothing.
"""
import argparse
import json
import os
import sys
from datetime import date, datetime

import numpy as np
import pandas as pd

import mt5_interface
import telegram_notify
import tf3_challenge_live as tcl
import tf3_risk_governor as gov

HERE = os.path.dirname(os.path.abspath(__file__))
DAEMON_CONFIG_PATH = os.path.join(HERE, 'daemon_config.json')
ENV_PATH = os.path.join(HERE, '.env')
DAEMON_STATE_PATH = os.path.join(HERE, 'daemon_state.json')
LOG_PATH = os.path.join(HERE, 'daemon_log.txt')
DEFAULT_MIN_BARS = 400          # covers the slowest EWMAC pair (256) + vol window (60) with margin
DEFAULT_STALE_DAYS = 3          # flag if the newest bar is older than this many calendar days

_REQUIRED_ENV_KEYS = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'EXPECTED_ACCOUNT_LOGIN', 'EXPECTED_ACCOUNT_SERVER']


def _load_env_file(path):
    """Minimal, dependency-free .env parser -- no python-dotenv required,
    so this works on a fresh machine with nothing but pandas/numpy
    installed. Supports KEY=VALUE lines, blank lines, and '#' comments.
    Does not support multi-line values or quoting beyond stripping a
    single layer of matching quotes -- this project's .env only ever
    holds single-line secrets, so that's deliberately all this does."""
    env = {}
    if not os.path.exists(path):
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, val = line.partition('=')
            key, val = key.strip(), val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                val = val[1:-1]
            env[key] = val
    return env


def _load_daemon_config(dry_run=False):
    if not os.path.exists(DAEMON_CONFIG_PATH):
        raise RuntimeError(
            f"No daemon_config.json at {DAEMON_CONFIG_PATH}. Copy "
            f"daemon_config.example.json to daemon_config.json first."
        )
    with open(DAEMON_CONFIG_PATH) as f:
        cfg = json.load(f)

    env = _load_env_file(ENV_PATH)
    # Real OS environment variables win over .env -- lets a scheduler inject
    # secrets via its own environment instead of a file, if you'd rather.
    for key in _REQUIRED_ENV_KEYS:
        if os.environ.get(key):
            env[key] = os.environ[key]

    missing = [k for k in _REQUIRED_ENV_KEYS if not env.get(k) or 'PASTE_YOUR' in env.get(k, '')]
    if missing and not dry_run:
        raise RuntimeError(
            f"Missing or unfilled .env value(s): {', '.join(missing)}. Copy "
            f".env.example to .env in this same folder (not the example file "
            f"itself) and fill in every PASTE_YOUR_* placeholder before "
            f"running for real."
        )
    if missing and dry_run:
        # --dry-run works with no real .env at all -- the mock account check
        # still exercises the same code path, it just won't mean anything
        # about a real account until you fill .env in for real.
        print(f"[dry-run: no real .env values for {', '.join(missing)} -- using placeholders; "
              f"this exercises the daemon's logic, not a real account or a real Telegram send]")
        for k in missing:
            env.setdefault(k, '0' if k == 'EXPECTED_ACCOUNT_LOGIN' else f'dry-run-placeholder-{k.lower()}')

    cfg['telegram_bot_token'] = env['TELEGRAM_BOT_TOKEN']
    cfg['telegram_chat_id'] = env['TELEGRAM_CHAT_ID']
    cfg['expected_account_login'] = env['EXPECTED_ACCOUNT_LOGIN']
    cfg['expected_account_server'] = env['EXPECTED_ACCOUNT_SERVER']
    return cfg


def _load_daemon_state():
    if os.path.exists(DAEMON_STATE_PATH):
        with open(DAEMON_STATE_PATH) as f:
            return json.load(f)
    return {}


def _save_daemon_state(state):
    with open(DAEMON_STATE_PATH, 'w') as f:
        json.dump(state, f, indent=2)


def _log(text):
    stamp = datetime.now().isoformat(timespec='seconds')
    with open(LOG_PATH, 'a') as f:
        f.write(f"\n{'='*70}\n[{stamp}]\n{text}\n")
    print(text)


def _alert(cfg, text, dry_run):
    """Log locally always; also try Telegram. Returns the send result so
    the caller can decide on an exit code, but a failed Telegram send is
    never allowed to hide the local log entry above it."""
    _log(text)
    if dry_run:
        print("[dry-run: Telegram send skipped -- message above is what would have been sent]")
        return True, "dry-run, not sent"
    ok, detail = telegram_notify.send_message(cfg['telegram_bot_token'], cfg['telegram_chat_id'], text)
    if not ok:
        _log(f"TELEGRAM SEND FAILED ({detail}). The message above was NOT delivered to Telegram, "
             f"only written to this log. Check .env's TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID and connectivity.")
    return ok, detail


def get_interface(dry_run, simulate, price_csv):
    if dry_run:
        if simulate == 'wrong-account':
            return mt5_interface.MockMT5(price_csv, fake_login=11111111, fake_server='WrongServer-Demo')
        if simulate == 'stale-data':
            return mt5_interface.MockMT5(price_csv, fake_open_volume=0.05, fake_bar_offset_days=6)
        if simulate == 'halt':
            # fake_equity set low relative to challenge_config's account_equity so the
            # governor's own daily/total loss math pushes it into HALT
            return mt5_interface.MockMT5(price_csv, fake_open_volume=0.05, fake_equity=1.0)
        return mt5_interface.MockMT5(price_csv, fake_open_volume=0.05, fake_equity=10000.0)
    return mt5_interface.RealMT5()


def build_message(*, account_mismatch=False, info=None, cfg=None, challenge_name=None,
                   equity=None, gstate=None, diag=None, challenge_passed=None,
                   held_position=None, held_position_note=None, target=None,
                   new_position=None, traded=None, target_lots=None,
                   last_price=None, last_bar_date=None, stale=False, stale_note=None,
                   exposure_mult=None):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    lines = [f"<b>TF3 XAUUSD -- {challenge_name} -- {ts}</b>"]

    if account_mismatch:
        lines.append(f"\U0001F534 <b>CRITICAL: WRONG ACCOUNT LOGGED IN</b>")
        lines.append(f"Connected: login {info['login']} / server {info['server']}")
        lines.append(f"Expected:  login {cfg['expected_account_login']} / server {cfg['expected_account_server']}")
        lines.append("NO SIGNAL GENERATED -- refusing to compute a target for an unverified account.")
        return "\n".join(lines)

    icon = "\U0001F7E2" if gstate == gov.GovernorState.NORMAL else ("\U0001F7E1" if gstate == gov.GovernorState.WARNING else "\U0001F534")
    lines.append(f"{icon} Governor: <b>{gstate.value.upper()}</b>")
    if stale:
        lines.append(f"⚠️ {stale_note}")
    if held_position_note:
        lines.append(f"⚠️ {held_position_note}")

    lines.append(f"\nAccount equity: {equity:,.2f}")
    lines.append(f"Daily loss: {diag['daily_loss_pct']*100:.2f}% (limit {diag['daily_limit']*100:.0f}%)")
    lines.append(f"Total loss: {diag['total_loss_pct']*100:.2f}% (limit {diag['total_limit']*100:.0f}%)")
    lines.append(f"Phase: {diag['phase_name']} -- gain {diag['phase_gain_pct']*100:.2f}% "
                 f"(target {diag['phase_target']*100:.0f}%), {diag['trading_days_this_phase']} trading days so far")
    if challenge_passed:
        lines.append("\U0001F3C6 <b>CHALLENGE PASSED</b>")

    lines.append(f"\nXAUUSD close ({last_bar_date}): {last_price:,.2f}")
    lines.append(f"Raw target (0..1, long-only): {target:.4f}")
    lines.append(f"Reconciled held position: {held_position:.4f}")
    lines.append(f"New position to hold: <b>{new_position:.4f}</b>  (trade fires: {traded})")
    if gstate == gov.GovernorState.HALT:
        lines.append("HALT -- no new entries suggested. Existing position may remain per your own judgment.")
    lines.append(f"effective_exposure_mult: {exposure_mult}  (see challenge_config.json)")
    lines.append(f"Target lots: <b>{target_lots:.4f}</b>")
    lines.append("\n<b>MANUAL EXECUTION REQUIRED -- this does not place orders.</b>")
    return "\n".join(lines)


def run(dry_run=False, force=False, simulate=None, price_csv=None):
    cfg = _load_daemon_config(dry_run=dry_run)
    challenge_cfg = tcl._load_config()
    n_steps = len(challenge_cfg.get('phases', [1]))
    challenge_name = f"GFT ${challenge_cfg.get('account_equity', 0):,.0f} {n_steps}-Step"

    today = date.today().isoformat()
    dstate = _load_daemon_state()
    if dstate.get('last_run_date') == today and not force:
        print(f"Already ran today ({today}). Pass --force to re-run and re-alert anyway.")
        return 0

    if dry_run and price_csv is None:
        price_csv = os.path.join(HERE, '..', 'data', 'xauusd_D1.csv')

    iface = get_interface(dry_run, simulate, price_csv)

    try:
        iface.connect()
    except mt5_interface.MT5ConnectionError as e:
        text = (f"\U0001F534 CRITICAL: TF3 daemon ({challenge_name}) could not connect to MT5.\n{e}\n"
                f"NO SIGNAL GENERATED.")
        _alert(cfg, text, dry_run)
        return 2

    try:
        ok, info = mt5_interface.verify_account(iface, cfg['expected_account_login'], cfg['expected_account_server'])
        if not ok:
            text = build_message(account_mismatch=True, info=info, cfg=cfg, challenge_name=challenge_name)
            _alert(cfg, text, dry_run)
            return 2

        equity = info['equity']
        n_bars = cfg.get('min_bars_required', DEFAULT_MIN_BARS)
        bars = iface.recent_daily_bars(cfg['mt5_symbol'], n_bars)
        if len(bars) < n_bars:
            _log(f"WARNING: only got {len(bars)} bars, wanted {n_bars} -- EWMAC scalar calibration "
                 f"and the 256-day pair may be under-supported this early in a fresh data source.")

        last_bar_date = bars.index[-1]
        age_days = (pd.Timestamp(datetime.now().date()) - pd.Timestamp(last_bar_date.date())).days
        stale = age_days > cfg.get('stale_bar_max_age_days', DEFAULT_STALE_DAYS)
        stale_note = (f"Last bar is {age_days} day(s) old ({last_bar_date.date()}) -- feed may be stale. "
                      f"Signal below still computed from it, treat with more caution than usual.") if stale else None

        open_volume = iface.open_volume(cfg['mt5_symbol'])
        last_price = float(bars['close'].iloc[-1])
        exposure_mult = challenge_cfg['effective_exposure_mult']
        contract_size = tcl.CONTRACT_SIZE
        denom = exposure_mult * equity
        held_position = (open_volume * contract_size * last_price) / denom if denom else 0.0
        held_position_note = None
        if held_position < -0.05 or held_position > 1.05:
            held_position_note = (f"Reconciled held position ({held_position:.3f}) is outside the expected "
                                   f"[0,1] long-only range -- check for a manual override, a short position "
                                   f"left open, or a mismatched effective_exposure_mult before trusting this "
                                   f"run's target.")
            held_position = float(np.clip(held_position, 0.0, 1.0))

        gstate, diag, challenge_passed = gov.evaluate(equity)

        dev_scalars = tcl.compute_dev_scalars_from_df(bars)
        cf_today = tcl.combined_forecast_today(bars['close'], dev_scalars)
        target = float(np.clip(cf_today / 20.0, 0, 1))

        if gstate == gov.GovernorState.HALT:
            new_position, traded = held_position, False
        else:
            new_position, traded = tcl.apply_buffer_single_step(target, held_position)

        notional = new_position * exposure_mult * equity
        target_lots = notional / (contract_size * last_price) if last_price else 0.0

        text = build_message(
            challenge_name=challenge_name, equity=equity, gstate=gstate, diag=diag,
            challenge_passed=challenge_passed, held_position=held_position,
            held_position_note=held_position_note, target=target, new_position=new_position,
            traded=traded, target_lots=target_lots, last_price=last_price,
            last_bar_date=last_bar_date.date(), stale=stale, stale_note=stale_note,
            exposure_mult=exposure_mult,
        )
        _alert(cfg, text, dry_run)

        _save_daemon_state({'last_run_date': today, 'gstate': gstate.value,
                             'new_position': new_position, 'target_lots': target_lots})
        return 0
    finally:
        iface.shutdown()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dry-run', action='store_true', help='Use MockMT5 + local CSV instead of a real MT5 terminal; skips real Telegram send.')
    ap.add_argument('--force', action='store_true', help='Re-run and re-alert even if already run today.')
    ap.add_argument('--simulate', choices=['normal', 'wrong-account', 'stale-data', 'halt'], default='normal',
                     help='Only with --dry-run: which scenario MockMT5 should reproduce.')
    ap.add_argument('--price-csv', default=None, help='Only with --dry-run: CSV to feed MockMT5. Defaults to ../data/xauusd_D1.csv.')
    args = ap.parse_args()
    sys.exit(run(dry_run=args.dry_run, force=args.force, simulate=args.simulate, price_csv=args.price_csv))


if __name__ == '__main__':
    main()
