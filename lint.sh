#!/usr/bin/env bash
# Format Markdown files in place using rumdl. Respects .rumdl.toml and .gitignore.
# For a non-mutating check (e.g. CI), use `rumdl fmt --check .`.
set -euo pipefail
rumdl fmt .
