#!/usr/bin/env bash
find . -name "*.md" -type f -print0 | xargs -0 rumdl fmt --fix
