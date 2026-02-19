#!/usr/bin/env python3
"""OpenAI API Usage & Cost Reporter.

Queries the OpenAI Organization Usage API to report costs, token usage,
and per-model breakdowns. Requires an Admin API key (sk-admin-...).

Usage:
    OPENAI_ADMIN_KEY=sk-admin-... python3 openai_usage.py --days 7
    OPENAI_ADMIN_KEY=sk-admin-... python3 openai_usage.py --days 30 --json
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from collections import defaultdict

BASE_URL = "https://api.openai.com/v1/organization"


def get_api_key():
    key = os.environ.get("OPENAI_ADMIN_KEY", "")
    if not key:
        print("Error: OPENAI_ADMIN_KEY environment variable not set.", file=sys.stderr)
        print("Generate an admin key at: https://platform.openai.com/settings/organization/admin-keys", file=sys.stderr)
        sys.exit(1)
    return key


def api_request(path, params, api_key):
    """Make a GET request to the OpenAI Usage API, handling pagination."""
    all_results = []
    query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
    url = f"{BASE_URL}/{path}?{query}"

    while url:
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            if e.code == 403:
                print(f"Error 403 Forbidden: Your key doesn't have admin access.", file=sys.stderr)
                print(f"Admin keys start with 'sk-admin-'. Project keys (sk-proj-) won't work.", file=sys.stderr)
            else:
                print(f"HTTP {e.code}: {body}", file=sys.stderr)
            sys.exit(1)

        results = data.get("data", data.get("results", []))
        all_results.extend(results)

        # Handle pagination
        if data.get("has_more") and data.get("next_page"):
            url = f"{BASE_URL}/{path}?{data['next_page']}"
        else:
            url = None

    return all_results


def fetch_costs(api_key, start_time, end_time):
    """Fetch dollar costs grouped by line item (model-level) and day."""
    params = {
        "start_time": start_time,
        "end_time": end_time,
        "bucket_width": "1d",
        "group_by": "line_item",
        "limit": "180",
    }
    return api_request("costs", params, api_key)


def fetch_completions_usage(api_key, start_time, end_time):
    """Fetch token usage for completions."""
    params = {
        "start_time": start_time,
        "end_time": end_time,
        "bucket_width": "1d",
        "group_by": "model",
        "limit": "180",
    }
    return api_request("usage/completions", params, api_key)


def fetch_images_usage(api_key, start_time, end_time):
    """Fetch image generation usage."""
    params = {
        "start_time": start_time,
        "end_time": end_time,
        "bucket_width": "1d",
        "limit": "180",
    }
    return api_request("usage/images", params, api_key)


def fetch_embeddings_usage(api_key, start_time, end_time):
    """Fetch embeddings usage."""
    params = {
        "start_time": start_time,
        "end_time": end_time,
        "bucket_width": "1d",
        "group_by": "model",
        "limit": "180",
    }
    return api_request("usage/embeddings", params, api_key)


def fetch_audio_usage(api_key, start_time, end_time):
    """Fetch audio transcription usage."""
    params = {
        "start_time": start_time,
        "end_time": end_time,
        "bucket_width": "1d",
        "limit": "180",
    }
    return api_request("usage/audio_transcriptions", params, api_key)


def format_cost(cents):
    """Format cost from cents to dollars."""
    return f"${cents / 100:.4f}"


def format_tokens(count):
    """Format token count with commas."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.2f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def print_separator(char="─", width=60):
    print(char * width)


def print_costs_summary(cost_data):
    """Print a human-readable cost summary grouped by line item."""
    if not cost_data:
        print("No cost data found for this period.")
        return

    total_cents = 0
    model_costs = defaultdict(float)
    daily_costs = defaultdict(float)

    for bucket in cost_data:
        ts = bucket.get("start_time", 0)
        day = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        results = bucket.get("results", [])
        for r in results:
            cost = r.get("amount", {}).get("value", 0)
            line_item_field = r.get("line_item")
            if isinstance(line_item_field, dict):
                line_item = line_item_field.get("value", "unknown")
            elif isinstance(line_item_field, str):
                line_item = line_item_field
            else:
                line_item = "unknown"
            total_cents += cost
            model_costs[line_item] += cost
            daily_costs[day] += cost

    print()
    print("  OPENAI API COST SUMMARY")
    print_separator()
    print(f"  Total cost: {format_cost(total_cents)}")
    print()

    if model_costs:
        print("  Per-Line-Item Breakdown:")
        print_separator("─", 50)
        sorted_models = sorted(model_costs.items(), key=lambda x: x[1], reverse=True)
        for model, cost in sorted_models:
            pct = (cost / total_cents * 100) if total_cents > 0 else 0
            print(f"    {model:<35} {format_cost(cost):>10}  ({pct:.1f}%)")
        print()

    if daily_costs:
        print("  Daily Breakdown:")
        print_separator("─", 50)
        for day in sorted(daily_costs.keys()):
            cost = daily_costs[day]
            print(f"    {day}   {format_cost(cost):>10}")
        print()


def print_completions_summary(completions_data):
    """Print completions token usage summary."""
    if not completions_data:
        return

    model_tokens = defaultdict(lambda: {"input": 0, "output": 0, "requests": 0})

    for bucket in completions_data:
        results = bucket.get("results", [])
        for r in results:
            model = r.get("model", {}).get("value", "unknown") if isinstance(r.get("model"), dict) else r.get("model", "unknown")
            model_tokens[model]["input"] += r.get("input_tokens", 0)
            model_tokens[model]["output"] += r.get("output_tokens", 0)
            model_tokens[model]["requests"] += r.get("num_model_requests", 0)

    if not model_tokens:
        return

    print("  COMPLETIONS TOKEN USAGE")
    print_separator()
    print(f"  {'Model':<30} {'Input':>10} {'Output':>10} {'Requests':>10}")
    print_separator("─", 65)

    total_input = 0
    total_output = 0
    total_requests = 0

    sorted_models = sorted(model_tokens.items(), key=lambda x: x[1]["input"] + x[1]["output"], reverse=True)
    for model, data in sorted_models:
        total_input += data["input"]
        total_output += data["output"]
        total_requests += data["requests"]
        print(f"  {model:<30} {format_tokens(data['input']):>10} {format_tokens(data['output']):>10} {data['requests']:>10,}")

    print_separator("─", 65)
    print(f"  {'TOTAL':<30} {format_tokens(total_input):>10} {format_tokens(total_output):>10} {total_requests:>10,}")
    print()


def print_images_summary(images_data):
    """Print image generation summary."""
    if not images_data:
        return

    total_images = 0
    total_requests = 0

    for bucket in images_data:
        results = bucket.get("results", [])
        for r in results:
            total_images += r.get("num_images", 0)
            total_requests += r.get("num_model_requests", 0)

    if total_images == 0 and total_requests == 0:
        return

    print("  IMAGE GENERATION")
    print_separator()
    print(f"  Images generated: {total_images:,}")
    print(f"  API requests:     {total_requests:,}")
    print()


def print_audio_summary(audio_data):
    """Print audio transcription summary."""
    if not audio_data:
        return

    total_seconds = 0
    total_requests = 0

    for bucket in audio_data:
        results = bucket.get("results", [])
        for r in results:
            total_seconds += r.get("num_seconds", 0)
            total_requests += r.get("num_model_requests", 0)

    if total_seconds == 0 and total_requests == 0:
        return

    print("  AUDIO TRANSCRIPTION")
    print_separator()
    minutes = total_seconds / 60
    print(f"  Duration:     {minutes:.1f} minutes ({total_seconds:,} seconds)")
    print(f"  API requests: {total_requests:,}")
    print()


def print_embeddings_summary(embeddings_data):
    """Print embeddings usage summary."""
    if not embeddings_data:
        return

    total_tokens = 0
    total_requests = 0

    for bucket in embeddings_data:
        results = bucket.get("results", [])
        for r in results:
            total_tokens += r.get("input_tokens", 0)
            total_requests += r.get("num_model_requests", 0)

    if total_tokens == 0 and total_requests == 0:
        return

    print("  EMBEDDINGS")
    print_separator()
    print(f"  Input tokens: {format_tokens(total_tokens)}")
    print(f"  API requests: {total_requests:,}")
    print()


def main():
    parser = argparse.ArgumentParser(description="OpenAI API Usage & Cost Reporter")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back (default: 7)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON data")
    parser.add_argument("--costs-only", action="store_true", help="Only show dollar costs, skip token details")
    args = parser.parse_args()

    api_key = get_api_key()

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=args.days)
    start_time = int(start.timestamp())
    end_time = int(now.timestamp())

    period_start = start.strftime("%Y-%m-%d")
    period_end = now.strftime("%Y-%m-%d")

    # Fetch costs (always)
    cost_data = fetch_costs(api_key, start_time, end_time)

    # Fetch detailed usage (unless --costs-only)
    completions_data = []
    images_data = []
    audio_data = []
    embeddings_data = []

    if not args.costs_only:
        completions_data = fetch_completions_usage(api_key, start_time, end_time)
        images_data = fetch_images_usage(api_key, start_time, end_time)
        audio_data = fetch_audio_usage(api_key, start_time, end_time)
        embeddings_data = fetch_embeddings_usage(api_key, start_time, end_time)

    if args.json:
        output = {
            "period": {"start": period_start, "end": period_end, "days": args.days},
            "costs": cost_data,
            "completions": completions_data,
            "images": images_data,
            "audio": audio_data,
            "embeddings": embeddings_data,
        }
        print(json.dumps(output, indent=2))
        return

    # Human-readable output
    print()
    print(f"  Period: {period_start} to {period_end} ({args.days} days)")
    print_separator("═")

    print_costs_summary(cost_data)

    if not args.costs_only:
        print_completions_summary(completions_data)
        print_images_summary(images_data)
        print_audio_summary(audio_data)
        print_embeddings_summary(embeddings_data)

    print_separator("═")
    print()


if __name__ == "__main__":
    main()
