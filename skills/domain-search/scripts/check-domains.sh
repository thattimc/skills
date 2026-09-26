#!/usr/bin/env bash
# check-domains.sh: check domain registration at the registries (RDAP, WHOIS fallback).
# Thin wrapper around check_domains.py (Python 3, standard library only); see --help.
#
#   check-domains.sh acme.com acme.ai foo.io
#   check-domains.sh --tlds com,ai,io acme foo bar
#   check-domains.sh --json --tlds com,ai acme foo
set -eu
if ! command -v python3 >/dev/null 2>&1; then
  echo "error: check-domains.sh needs python3" >&2
  exit 1
fi
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/check_domains.py" "$@"
