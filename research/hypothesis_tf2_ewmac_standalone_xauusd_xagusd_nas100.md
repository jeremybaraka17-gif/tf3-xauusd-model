# Hypothesis TF2 — Pre-Registration: multi-scale EWMAC forecast framework, developed standalone per-instrument for XAUUSD, XAGUSD, NAS100

Status: PRE-REGISTERED, not yet run.

## Why this is a genuinely different test from TF1, not a repeat

TF1 tested the same construction blended across an 8-instrument (GOAT-8: FX+WTI+NAS100) or 16-instrument (equity+index) portfolio via inverse-vol weighting, and failed on both. Blending is itself a risk-reduction mechanism — it can mask or dilute a real single-instrument signal exactly the way this project's own FD4/FD7/FD10 overlay family had to be developed and validated standalone per-instrument before any of them worked; blended tests of similar overlays (FD8, FD9, FD12) failed precisely because diversification had already done the work the overlay was trying to do. XAUUSD and XAGUSD were never tested under TF1 at all (GOAT-8 has no metals). NAS100 was only ever tested as one-eighth of a blend, never standalone. This is new ground, not a re-run.

## Construction (identical to TF1, unchanged — reused exactly, not re-tuned)

Same 6-pair EWMAC forecast (2/8, 4/16, 8/32, 16/64, 32/128, 64/256), vol-normalized (60-day, native calendar), scalar calibrated to average absolute forecast of 10 on the DEV window only per pair per instrument, capped ±20, combined by simple average across pairs. Position = combined_forecast/20 (range -1 to +1), applied as the FULL position size for that single instrument (no cross-instrument IV-blending needed or applied — there's only one instrument per test). Stage 2 layers the identical acceleration-sizing (`1 + 0.5*sign(accel)*sign(forecast)`, clipped 0.5-1.5x) and volatility-spike cut (21d vol > 1.5x 252d trailing average → 50% position) used in TF1.

## Universe and data

XAUUSD, XAGUSD, NAS100 — all three sourced from `h4_uploads` (single FX-broker calendar, no cross-calendar gap risk, the native-calendar fix is applied anyway for consistency and safety).

## Dev / OOS split

Unchanged: 2025-04-02 dev cutoff, 2025-04-03 to 2026-07-03 OOS — same boundary used throughout this project.

## Benchmark and verdict rule

Buy-and-hold on that same single instrument — matching EV1's own benchmark convention for a directional signal replacing a default exposure, not FD4/FD7/FD10's convention of a de-risk overlay on an existing signal (there is no existing directional signal on gold/silver in this project to overlay onto; NAS100 only has FD10's de-risk overlay, not a directional entry, so buy-and-hold is the correct comparison here too).

**Primary**: Stage 1 (raw forecast) and Stage 1+2 (with acceleration/vol-cut) are BOTH reported against buy-and-hold, per instrument — Sharpe comparison, both windows.
**Secondary**: floor-breach episode count (-6%), both windows.
**Verdict**: PASS requires primary in both windows for a given stage; PARTIAL if one window holds or both are individually positive; FAIL otherwise — identical rubric to every EV/TF hypothesis so far, reused rather than picked fresh per instrument.

## What "develop" means here, concretely

If a given instrument's construction (Stage 1 or Stage 1+2) reaches PASS or a strong PARTIAL, the next step is writing a deployable model spec for that instrument specifically — matching this project's `model_spec_fd4_gold_derisk_overlay_v1.md` / `model_spec_fd10_copper_nas100_derisk_overlay_v1.md` convention (exact formula, parameters, position-sizing recipe, net-of-cost check, disclosed caveats) — not just a pass/fail addendum. If it fails, the addendum reports that plainly and no spec is written, consistent with this project never writing a spec for anything that didn't pass.

## Discipline

Each instrument gets ONE evaluation of the full framework (Stage 1 and Stage 1+2 together count as one look, not two separate gated attempts, since Stage 2 is an integral, already-specified part of what's being developed, not a contingent follow-up). No per-instrument re-tuning after seeing results — the same frozen construction runs on all three, exactly as specified above, and whatever it produces is reported.
