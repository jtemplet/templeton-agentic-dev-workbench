<!--
Expected: overall PASS, score 100/100, band Excellent.
All four content sections pass, structure 5/5 canonical, size Target. No cap applies.
-->
Title: Rate-limit failed login attempts
Type: task

## Why (Computational)

Credential-stuffing bots hammer the login endpoint unthrottled, so a leaked password list
can be tested against every account overnight. The security team flagged this after an
incident; the account-takeover dashboard depends on this defense existing.

## How (Algorithmic)

Add a fixed-window counter keyed on source IP in the existing Redis instance, checked in the
sessions controller before the password comparison. Chosen over a token bucket because the
threshold only needs per-minute granularity and the fixed window is one INCR plus one EXPIRE.
The limit is read from config so it can change without a redeploy.

## Done when (Acceptance)

- Repeated failed logins from one source are throttled before the password check runs.
- The threshold is configurable without a redeploy.

## Acceptance Criteria

1. Given 5 failed logins in 60s from one IP, when a 6th is attempted, then the response status is 429.
2. Given the RATE_LIMIT config value changes, when config reloads, then the new limit applies without a process restart.
3. Given a successful login, when the rolling window elapses, then the failure counter for that IP resets to 0.

## Estimated size

2 files, ~90 LOC, band: Target.
