"""
tf3_risk_governor.py -- tracks a TF3/XAUUSD prop-challenge account's state
against ITS OWN challenge's daily-loss, total-loss, and phase-profit-target
rules, and produces a governor state (NORMAL / WARNING / HALT) exactly
following the pattern your existing GFT prop-firm system already uses
(`risk_governor.py`, this project's other live construction): HALT means
"stop suggesting NEW entries," never "force-liquidate open positions" --
that lesson was already learned the hard way once in this project family
and is not being re-learned here.

This is a GENERIC governor, parametrized by CHALLENGE_CONFIG (see the
sibling `challenge_config.json` in this folder) rather than hardcoded to
one specific challenge's numbers, since this project now runs two
different challenge configs (5k 2-Step, 10k 1-Step) side by side.

WARNING/HALT buffers below are set at 70%/90% of the challenge's actual
hard limits -- the SAME buffer convention the existing risk_governor.py
already uses, reused rather than re-derived, for the same reason: leaves
real margin for daily-snapshot timing mismatches (this script approximates
"day start" as first-run-of-the-calendar-day, not any specific broker
cutoff time) and for the fact these are checked once a day, not
continuously.

State is persisted to governor_state.json in this same folder. Day-start
equity resets daily; the TOTAL-loss floor is against the ORIGINAL initial
balance and does not reset between phases (per this challenge family's
"static" total-loss description) unless CHALLENGE_CONFIG explicitly says
otherwise for a specific challenge.
"""
import json
import os
from datetime import date
from enum import Enum

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(HERE, "governor_state.json")
CONFIG_PATH = os.path.join(HERE, "challenge_config.json")

WARNING_FRACTION = 0.70   # matches the existing project's risk_governor.py convention
HALT_FRACTION = 0.90


class GovernorState(Enum):
    NORMAL = "normal"
    WARNING = "warning"
    HALT = "halt"


def _load_config():
    if not os.path.exists(CONFIG_PATH):
        raise RuntimeError(
            f"No challenge_config.json found at {CONFIG_PATH}. This governor is "
            f"generic and needs a challenge config (account_equity, daily_loss_limit, "
            f"total_loss_limit, phase targets) to know what it's guarding against."
        )
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return None


def _save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def initialize_challenge(force: bool = False):
    """Run ONCE, manually, at the start of a challenge attempt (or a new
    phase, if your config wants phase-level total-loss resets -- this
    generic version defaults to NOT resetting between phases, matching
    the "static, from initial balance" description confirmed for both
    the 5k and 10k challenges this project currently simulates)."""
    cfg = _load_config()
    existing = _load_state()
    if existing and not force:
        raise RuntimeError(
            f"Governor state already initialized (initial_balance="
            f"{existing['initial_balance']}, started {existing['challenge_start_date']}). "
            f"Pass force=True if you're deliberately starting a NEW challenge attempt."
        )
    state = {
        "initial_balance": cfg["account_equity"],
        "challenge_start_date": date.today().isoformat(),
        "day_start_balance": cfg["account_equity"],
        "last_recorded_date": date.today().isoformat(),
        "high_water_mark": cfg["account_equity"],
        "phase_index": 0,
        "phase_start_balance": cfg["account_equity"],
        "trading_days_this_phase": 0,
    }
    _save_state(state)
    return state


def evaluate(current_equity: float):
    """Call this once per day before suggesting any new entry. Returns
    (GovernorState, dict of diagnostics, phase_passed: bool)."""
    cfg = _load_config()
    state = _load_state()
    if state is None:
        raise RuntimeError(
            "Governor not initialized. Run tf3_risk_governor.initialize_challenge() "
            "once before using this."
        )

    today = date.today().isoformat()
    if state["last_recorded_date"] != today:
        state["day_start_balance"] = current_equity  # new day: reset the daily-loss reference
        state["trading_days_this_phase"] += 1
        state["last_recorded_date"] = today

    state["high_water_mark"] = max(state["high_water_mark"], current_equity)

    daily_loss_pct = max(0.0, (state["day_start_balance"] - current_equity) / state["day_start_balance"])
    total_loss_pct = max(0.0, (state["initial_balance"] - current_equity) / state["initial_balance"])

    daily_limit = cfg["daily_loss_limit"]
    total_limit = cfg["total_loss_limit"]

    if daily_loss_pct >= HALT_FRACTION * daily_limit or total_loss_pct >= HALT_FRACTION * total_limit:
        gstate = GovernorState.HALT
    elif daily_loss_pct >= WARNING_FRACTION * daily_limit or total_loss_pct >= WARNING_FRACTION * total_limit:
        gstate = GovernorState.WARNING
    else:
        gstate = GovernorState.NORMAL

    phase = cfg["phases"][state["phase_index"]]
    phase_gain_pct = (current_equity - state["phase_start_balance"]) / state["phase_start_balance"]
    phase_passed = (phase_gain_pct >= phase["target"]
                     and state["trading_days_this_phase"] >= cfg.get("min_trading_days", 3))

    if phase_passed and state["phase_index"] < len(cfg["phases"]) - 1:
        state["phase_index"] += 1
        state["phase_start_balance"] = current_equity
        state["trading_days_this_phase"] = 0
        phase_passed = False  # only the FINAL phase passing counts as challenge-passed

    challenge_passed = phase_passed and state["phase_index"] == len(cfg["phases"]) - 1

    _save_state(state)

    diagnostics = {
        "daily_loss_pct": daily_loss_pct, "daily_limit": daily_limit,
        "total_loss_pct": total_loss_pct, "total_limit": total_limit,
        "phase_name": phase["name"], "phase_gain_pct": phase_gain_pct, "phase_target": phase["target"],
        "phase_index": state["phase_index"], "trading_days_this_phase": state["trading_days_this_phase"],
    }
    return gstate, diagnostics, challenge_passed


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        s = initialize_challenge(force="--force" in sys.argv)
        print(f"Initialized: {s}")
    elif len(sys.argv) > 2 and sys.argv[1] == "check":
        equity = float(sys.argv[2])
        gstate, diag, passed = evaluate(equity)
        print(f"State: {gstate.value}")
        print(f"Diagnostics: {diag}")
        print(f"Challenge passed: {passed}")
    else:
        print("Usage:\n  python3 tf3_risk_governor.py init [--force]\n"
              "  python3 tf3_risk_governor.py check <current_equity>")
