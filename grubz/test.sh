#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
test_binary=$(mktemp)
trap 'rm -f -- "$test_binary"' EXIT
cc -std=c99 -Wall -Wextra -Werror -fsanitize=undefined \
  tests/selection_fx_test.c -o "$test_binary"
"$test_binary"
git diff --check
