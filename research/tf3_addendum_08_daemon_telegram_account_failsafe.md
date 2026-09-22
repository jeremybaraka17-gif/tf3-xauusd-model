# TF3 Addendum 08 — unattended daily daemon: MT5 account fail-safe + Telegram signal push

## What was asked

Run TF3's live signal logic unattended while GFT trading happens in the background, push the daily target to Telegram, and add a fail-safe that confirms the terminal is logged into the correct account before anything is computed or sent.

## What exists now

Three new files in `live/`, added on top of the existing `tf3_challenge_live.py` / `tf3_risk_governor.py` (both reused unchanged, not duplicated):

- `mt5_interface.py` — a `RealMT5` class wrapping the `MetaTrader5` Python package (account info, open position, recent bars), and a `MockMT5` class that reproduces the same interface against this project's own historical CSV and a fake, configurable account, so everything except the real broker connection can be tested here.
- `telegram_notify.py` — sends a message to a Telegram chat via the Bot API's `sendMessage` endpoint, stdlib-only, with retry and a failure path that never throws away the local log entry.
- `tf3_daemon.py` — the orchestrator. Meant to run once per day, triggered by a scheduler (Windows Task Scheduler, since `MetaTrader5` only works alongside a Windows terminal on the same machine). Control flow: connect to MT5 → verify account login/server match `daemon_config.json` → if mismatch, send a CRITICAL alert and stop, **no signal computed** → read live equity and actual open position → reconcile the open lots back into TF3's internal 0–1 position fraction (reads reality every run, does not trust a cached state file) → pull recent bars, flag if stale → run the exact long-only EWMAC forecast + buffer + governor check via `tf3_challenge_live.py`'s own functions → send the result to Telegram, every day it runs successfully, whether or not the target changed (so silence never means "the scheduler died" and "nothing to do" look the same).

It never places an order. That stays consistent with this project's existing position (see `tf3_xauusd_live.py`'s own docstring) that live order execution is a separate, larger, unreviewed step — this addendum adds an unattended *alerting* layer on top of already-validated signal logic, which is a materially smaller and more reviewable change than unattended order placement would be, and the two are not conflated here.

## What was actually tested, and how

Everything **except** the real MT5 connection and real Telegram delivery, because neither can exist in this session: there is no Windows machine here to host an MT5 terminal, and no bot token/chat ID was available to send a real message with.

`python3 tf3_daemon.py --dry-run` runs the entire control flow against `MockMT5` (fed from this project's own `xauusd_D1.csv`) and prints exactly what would be sent to Telegram instead of sending it. Four scenarios were run and inspected:

1. **Normal** — account verified, signal computed, governor NORMAL, message correctly formatted, marked "dry-run, not sent."
2. **Wrong account** (`--simulate wrong-account`) — mock reports a different login/server than `daemon_config.json` expects. Result: CRITICAL alert fired, **no signal was computed at all** (confirmed by inspecting the code path, not just the message text) — this is the requested fail-safe, and it does what it says.
3. **Stale data** (`--simulate stale-data`) — mock drops the most recent 6 rows before answering. Result: the staleness warning fired correctly, and the signal was still computed and labeled as based on stale data, rather than either silently proceeding or halting outright — an intentional design choice, since a stale-but-present connection is a different failure mode than no connection at all and the person reading the Telegram message should be the one to judge it.
4. **Halt** (`--simulate halt`) — fake account equity set low enough to breach the governor's total-loss halt threshold. Result: governor state correctly showed HALT, no new entry was suggested, held position was reported as-is per the governor's own "no forced liquidation" rule.

This confirms the daemon's decision logic, message formatting, and failure handling are correct **given correct inputs from MT5**. It confirms nothing about whether `RealMT5` actually works against a live terminal, or whether `telegram_notify.send_message` actually delivers — those are the two things that can only be verified on your own machine, with your own credentials, which is a step you'll need to take before trusting this on a live challenge attempt.

## Credentials live in `.env`, not in JSON

Secrets and account-identifying values (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `EXPECTED_ACCOUNT_LOGIN`, `EXPECTED_ACCOUNT_SERVER`) load from a `.env` file in `live/`, parsed by a small dependency-free parser in `tf3_daemon.py` (no `python-dotenv` required). `daemon_config.json` holds only non-secret settings now (symbol, bar count, staleness threshold). `.env` is listed in `live/.gitignore` so it isn't committed by accident. `--dry-run` works even with no `.env` at all — it substitutes clearly-labeled placeholders and prints a note saying so, so the daemon's logic can be tested before any credential exists.

## Before running this for real

1. Set up a Telegram bot (`@BotFather` → `/newbot`) and get your chat ID (`@userinfobot`, or the bot's own `getUpdates` response) — instructions are in `telegram_notify.py`'s own docstring and in `.env.example`.
2. Copy `daemon_config.example.json` to `daemon_config.json` (non-secret settings only).
3. Copy `.env.example` to `.env` in the same `live/` folder and fill in the bot token, chat ID, `EXPECTED_ACCOUNT_LOGIN` (your MT5 account number), and `EXPECTED_ACCOUNT_SERVER` (the exact broker server string MT5 shows when logged in — this has to match character-for-character or the fail-safe will, correctly, refuse to run). Never share this file once it holds real values.
4. Install the `MetaTrader5` Python package on the same Windows machine your MT5 terminal runs on, with the terminal logged into the account you actually intend to trade.
5. Run `python3 tf3_daemon.py` manually once, by hand, and check both the console output and that a real Telegram message actually arrived, before scheduling it.
6. Only then set up the Windows Task Scheduler trigger described in `tf3_daemon.py`'s own docstring.
7. Deliberately log into the WRONG account (a demo account, say) once and confirm the CRITICAL alert actually fires before trusting the fail-safe on a real attempt — this addendum's dry-run scenario proves the logic is correct, not that your specific `EXPECTED_ACCOUNT_LOGIN`/`EXPECTED_ACCOUNT_SERVER` values are typed correctly.

## What this does not do

- Does not place, modify, or close any order.
- Does not implement the data-integrity/regime kill switches described qualitatively in `tf3_addendum_02...md` — the staleness check here is a narrower, simpler "is the last bar recent" check than that spec's fuller concept.
- Does not monitor its own uptime — if the scheduled task itself fails to fire, there is no separate alert for that; Windows Task Scheduler's own run history is the only record of that failure mode, and it should be checked periodically, not assumed reliable forever.
- Does not resolve the lot-rounding problem already disclosed in `tf3_addendum_04...md` — the daemon reports whatever `target_lots` comes out of the sizing formula, including a value that would round to zero lots at your broker's minimum increment; it does not flag that case specially, though it could be added if that turns out to matter in practice.
