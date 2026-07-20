<!--
Expected: overall REFORMAT, raw score 90/100, band Great (structure cap).
All four content sections pass, but every one sits under a non-canonical heading/label,
so structure is 0/4 canonical = 0 of 10 structure points. Raw 90 would band Excellent;
the REFORMAT (structure) cap pulls it to Great. Fixable mechanically, no new content.
-->
Title: Cache the project settings lookup
Type: task

WHY: Every request re-reads the settings row from Postgres, and the settings page hits it
in a loop rendering the sidebar, so a single page load fires a dozen identical queries. The
performance budget for that page depends on removing them.

HOW: Memoize the lookup per-request in the existing request-store middleware, keyed on
project id. Chosen over a global cache because settings change mid-session and a request-
scoped memo avoids any invalidation logic.

Done when:

- The settings page issues at most one settings query per request.
- A settings change is visible on the next request, not stale.

AC:

1. Given the settings page renders, when the query log is inspected, then exactly one settings SELECT appears.
2. Given a user updates a setting, when they reload, then the new value shows on the next request.

Size: 1 file, ~40 LOC, band: Target.
