#!/usr/bin/env bash
# check-domains.sh — check domain registration/availability via RDAP (authoritative).
#
# RDAP (RFC 9082/9083) is the official successor to WHOIS. rdap.org is a router that
# redirects each query to the responsible registry's RDAP server.
#   HTTP 404 => no registration record  => AVAILABLE
#   HTTP 200 => registration exists      => TAKEN
#   other    => TLD has no RDAP / rate-limited / network => UNKNOWN (verify manually)
#
# Transient failures (429, 5xx, network) are retried up to 3x with backoff before UNKNOWN,
# and queries are throttled (RDAP_THROTTLE seconds, default 0.2) since rdap.org limits bursts.
#
# Usage:
#   check-domains.sh acme.com acme.ai foo.io          # explicit FQDNs
#   check-domains.sh --tlds com,ai,io acme foo bar     # names x TLDs
#   check-domains.sh --json --tlds com,ai acme foo      # machine-readable output
#
# Notes:
# - Not every TLD publishes RDAP. Known gaps: .io historically lacked RDAP (now improving),
#   .co, some ccTLDs. UNKNOWN means "couldn't determine", NOT "available".
# - "Available via RDAP" means unregistered; it does not price premium/reserved names.
#   Confirm final price + purchase at a registrar (Cloudflare Registrar, Porkbun, etc.).

set -u

JSON=0
TLDS=""
THROTTLE="${RDAP_THROTTLE:-0.2}"   # pause between domains; rdap.org throttles bursts
ARGS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --json) JSON=1; shift ;;
    --tlds) TLDS="$2"; shift 2 ;;
    --tlds=*) TLDS="${1#*=}"; shift ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done

if [ "${#ARGS[@]}" -eq 0 ]; then
  echo "error: no names/domains given. See --help." >&2
  exit 1
fi

# Build the final list of FQDNs to check.
DOMAINS=()
if [ -n "$TLDS" ]; then
  IFS=',' read -ra TLD_ARR <<< "$TLDS"
  for name in "${ARGS[@]}"; do
    for tld in "${TLD_ARR[@]}"; do
      tld="${tld#.}"                      # tolerate ".com" or "com"
      DOMAINS+=("${name}.${tld}")
    done
  done
else
  DOMAINS=("${ARGS[@]}")                  # treat args as full FQDNs
fi

rdap_status() {
  # echoes: AVAILABLE | TAKEN | UNKNOWN
  # rdap.org rate-limits bursts; a transient 429/5xx/timeout must not be reported as UNKNOWN,
  # because UNKNOWN reads as "verify manually" and silently hides real answers in a batch.
  local d="$1" code attempt
  for attempt in 1 2 3; do
    code=$(curl -sL --max-time 12 -o /dev/null -w "%{http_code}" "https://rdap.org/domain/${d}" 2>/dev/null)
    case "$code" in
      404)          echo "AVAILABLE"; return ;;
      200)          echo "TAKEN"; return ;;
      429|5*|000)   sleep $((attempt * 2)) ;;   # rate-limited / server error / network: back off
      *)            break ;;                    # genuine "no RDAP for this TLD": stop early
    esac
  done
  echo "UNKNOWN"
}

if [ "$JSON" -eq 1 ]; then
  printf '['
  first=1
  for d in "${DOMAINS[@]}"; do
    s=$(rdap_status "$d")
    [ $first -eq 1 ] && first=0 || printf ','
    printf '{"domain":"%s","status":"%s"}' "$d" "$s"
    sleep "$THROTTLE"
  done
  printf ']\n'
else
  for d in "${DOMAINS[@]}"; do
    s=$(rdap_status "$d")
    case "$s" in
      AVAILABLE) printf '  \xE2\x9C\x85 %-28s AVAILABLE\n' "$d" ;;
      TAKEN)     printf '  \xE2\x9D\x8C %-28s taken\n' "$d" ;;
      *)         printf '  \xE2\x9D\x93 %-28s unknown (no RDAP / verify manually)\n' "$d" ;;
    esac
    sleep "$THROTTLE"
  done
fi
