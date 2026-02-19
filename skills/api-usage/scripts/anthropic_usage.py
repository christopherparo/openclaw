#!/usr/bin/env python3
"""Anthropic API Usage & Cost Reporter.

Queries the Anthropic Admin API to report costs, token usage,
and per-model breakdowns. Requires an Admin API key (sk-ant-admin...).

Usage:
    ANTHROPIC_ADMIN_KEY=sk-ant-admin-... python3 anthropic_usage.py --days 7
    ANTHROPIC_ADMIN_KEY=sk-ant-admin-... python3 anthropic_usage.py --days 30 --json
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta, time
from collections import defaultdict

BASE_URL = "https://api.anthropic.com/v1/organizations"


def get_api_key():
    key = os.environ.get("ANTHROPIC_ADMIN_KEY", "")
    if not key:
        print("Error: ANTHROPIC_ADMIN_KEY environment variable not set.", file=sys.stderr)
        print("Generate an admin key at: https://console.anthropic.com/settings/admin-keys", file=sys.stderr)
        sys.exit(1)
    return key


def api_request(path, params, api_key):
    """Make a GET request to the Anthropic Admin API, handling pagination."""
    all_data = []
    parts = []
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, list):
            for item in v:
                parts.append(f"{k}={urllib.parse.quote(str(item))}")
        else:
            parts.append(f"{k}={urllib.parse.quote(str(v))}")
    query = "&".join(parts)
    url = f"{BASE_URL}/{path}?{query}"

    while url:
        req = urllib.request.Request(url, headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            if e.code == 403:
                print("Error 403 Forbidden: Your key doesn't have admin access.", file=sys.stderr)
                print("Admin keys start with 'sk-ant-admin...'. Regular API keys won't work.", file=sys.stderr)
                print("Only organization accounts with admin role can create admin keys.", file=sys.stderr)
            else:
                print(f"HTTP {e.code}: {body}", file=sys.stderr)
            sys.exit(1)

        all_data.extend(data.get("data", []))

        if data.get("has_more") and data.get("next_page"):
            url = f"{BASE_URL}/{path}?page={data['next_page']}"
        else:
            url = None

    return all_data


def make_time_range(days):
    """Build ISO 8601 start/end timestamps snapped to day boundaries in UTC."""
    now = datetime.now(timezone.utc)
    end = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    start = end - timedelta(days=days)
    return (
        start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def fetch_costs(api_key, start_at, end_at, days):
    """Fetch dollar costs grouped by description (model + tier + token type)."""
    params = {
        "starting_at": start_at,
        "ending_at": end_at,
        "bucket_width": "1d",
        "group_by[]": ["description"],
        "limit": str(min(days, 31)),
    }
    return api_request("cost_report", params, api_key)


def fetch_usage(api_key, start_at, end_at, days):
    """Fetch token usage grouped by model."""
    params = {
        "starting_at": start_at,
        "ending_at": end_at,
        "bucket_width": "1d",
        "group_by[]": ["model"],
        "limit": str(min(days, 31)),
    }
    return api_request("usage_report/messages", params, api_key)


def format_cost(cents_str):
    """Format cost from cents (string or float) to dollars."""
    cents = float(cents_str)
    return f"${cents / 100:.4f}"


def format_tokens(count):
    """Format token count with human-readable suffixes."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.2f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def print_separator(char="─", width=60):
    print(char * width)


def print_costs_summary(cost_data):
    """Print a human-readable cost summary from the cost_report endpoint."""
    if not cost_data:
        print("  No cost data found for this period.")
        print("  (Note: Anthropic cost data requires an organization account with admin access)")
        return

    total_cents = 0.0
    model_costs = defaultdict(float)
    daily_costs = defaultdict(float)

    for bucket in cost_data:
        day = bucket.get("starting_at", "")[:10]
        for r in bucket.get("results", []):
            amount = float(r.get("amount", 0))
            model = r.get("model") or "unknown"
            token_type = r.get("token_type") or r.get("cost_type") or ""
            label = model
            if token_type:
                label = f"{model} ({token_type})"
            total_cents += amount
            model_costs[label] += amount
            daily_costs[day] += amount

    print()
    print("  ANTHROPIC API COST SUMMARY")
    print_separator()
    print(f"  Total cost: {format_cost(total_cents)}")
    print()

    if model_costs:
        print("  Per-Model Breakdown:")
        print_separator("─", 55)
        sorted_models = sorted(model_costs.items(), key=lambda x: x[1], reverse=True)
        for model, cost in sorted_models:
            pct = (cost / total_cents * 100) if total_cents > 0 else 0
            print(f"    {model:<40} {format_cost(cost):>10}  ({pct:.1f}%)")
        print()

    if daily_costs:
        print("  Daily Breakdown:")
        print_separator("─", 55)
        for day in sorted(daily_costs.keys()):
            cost = daily_costs[day]
            if day:
                print(f"    {day}   {format_cost(cost):>10}")
        print()


def print_usage_summary(usage_data):
    """Print token usage summary from the usage_report/messages endpoint."""
    if not usage_data:
        return

    model_tokens = defaultdict(lambda: {
        "uncached_input": 0,
        "output": 0,
        "cache_read": 0,
        "cache_creation": 0,
    })

    for bucket in usage_data:
        for r in bucket.get("results", []):
            model = r.get("model") or "unknown"
            model_tokens[model]["uncached_input"] += r.get("uncached_input_tokens", 0)
            model_tokens[model]["output"] += r.get("output_tokens", 0)
            model_tokens[model]["cache_read"] += r.get("cache_read_input_tokens", 0)
            cache_creation = r.get("cache_creation", {})
            if isinstance(cache_creation, dict):
                for v in cache_creation.values():
                    if isinstance(v, (int, float)):
                        model_tokens[model]["cache_creation"] += int(v)

    if not model_tokens:
        return

    print("  ANTHROPIC TOKEN USAGE")
    print_separator()
    print(f"  {'Model':<28} {'Input':>10} {'Output':>10} {'Cache Read':>10} {'Cache Write':>11}")
    print_separator("─", 75)

    total_input = 0
    total_output = 0
    total_cache_read = 0
    total_cache_creation = 0

    sorted_models = sorted(
        model_tokens.items(),
        key=lambda x: x[1]["uncached_input"] + x[1]["output"],
        reverse=True,
    )
    for model, data in sorted_models:
        total_input += data["uncached_input"]
        total_output += data["output"]
        total_cache_read += data["cache_read"]
        total_cache_creation += data["cache_creation"]
        print(
            f"  {model:<28} "
            f"{format_tokens(data['uncached_input']):>10} "
            f"{format_tokens(data['output']):>10} "
            f"{format_tokens(data['cache_read']):>10} "
            f"{format_tokens(data['cache_creation']):>11}"
        )

    print_separator("─", 75)
    print(
        f"  {'TOTAL':<28} "
        f"{format_tokens(total_input):>10} "
        f"{format_tokens(total_output):>10} "
        f"{format_tokens(total_cache_read):>10} "
        f"{format_tokens(total_cache_creation):>11}"
    )
    print()


def main():
    parser = argparse.ArgumentParser(description="Anthropic API Usage & Cost Reporter")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back (default: 7)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON data")
    parser.add_argument("--costs-only", action="store_true", help="Only show dollar costs, skip token details")
    args = parser.parse_args()

    api_key = get_api_key()

    effective_days = min(args.days, 31)
    if effective_days != args.days:
        print(f"  Note: Anthropic cost API supports max 31 days; clamping from {args.days} to 31.", file=sys.stderr)

    start_at, end_at = make_time_range(effective_days)
    period_start = start_at[:10]
    period_end = end_at[:10]

    cost_data = fetch_costs(api_key, start_at, end_at, effective_days)

    usage_data = []
    if not args.costs_only:
        usage_data = fetch_usage(api_key, start_at, end_at, effective_days)

    if args.json:
        output = {
            "period": {"start": period_start, "end": period_end, "days": effective_days},
            "costs": cost_data,
            "usage": usage_data,
        }
        print(json.dumps(output, indent=2))
        return

    print()
    print(f"  Period: {period_start} to {period_end} ({effective_days} days)")
    print_separator("═")

    print_costs_summary(cost_data)

    if not args.costs_only:
        print_usage_summary(usage_data)

    print_separator("═")
    print()


if __name__ == "__main__":
    main()
