#!/usr/bin/env python3
"""API Correlation Explorer — Server with proxy + AI layers."""

import json
import os
import time
import hashlib
from pathlib import Path

from dotenv import load_dotenv
from aiohttp import web, ClientSession, ClientTimeout
import anthropic

from catalog import (
    CATALOG, LOCATIONS, COUNTRIES, PERIODS,
    get_catalog_for_api, get_api_by_id,
)
from fetchers import FETCH_HANDLERS

load_dotenv(Path(__file__).parent / ".env")

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CACHE: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 300  # 5 minutes


# --- Server routes ----------------------------------------------------------

async def handle_catalog(request):
    return web.json_response({
        "apis": get_catalog_for_api(),
        "locations": LOCATIONS,
        "countries": COUNTRIES,
        "periods": PERIODS,
    })


async def handle_fetch_dataset(request):
    """Fetch a dataset by catalog ID with location/country + days params."""
    body = await request.json()
    api_id = body.get("id")
    days = int(body.get("days", 30))
    lat = float(body.get("lat", 48.21))
    lon = float(body.get("lon", 16.37))
    country = body.get("country", "WLD")

    api = get_api_by_id(api_id)
    if not api:
        return web.json_response({"error": f"Unknown API: {api_id}"}, status=400)

    # Clamp days to max available
    max_days = api.get("max_history_days", 365)
    days = min(days, max_days)

    cache_key = hashlib.md5(
        f"{api_id}:{lat}:{lon}:{country}:{days}".encode()
    ).hexdigest()

    if cache_key in CACHE and time.time() - CACHE[cache_key][0] < CACHE_TTL:
        return web.json_response(CACHE[cache_key][1])

    session: ClientSession = request.app["session"]
    fetch_type = api["fetch_type"]
    handler = FETCH_HANDLERS.get(fetch_type)

    if not handler:
        return web.json_response(
            {"error": f"No handler for fetch_type: {fetch_type}"}, status=500
        )

    try:
        result = await handler(
            session=session,
            config=api["fetch_config"],
            lat=lat, lon=lon,
            days=days,
            country=country,
        )

        result["id"] = api_id
        result["name"] = api["name"]
        result["unit"] = api.get("unit", "")
        result["category"] = api["category"]
        result["count"] = len(result.get("values", []))

        CACHE[cache_key] = (time.time(), result)
        return web.json_response(result)

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_proxy(request):
    """Generic proxy for custom API URLs."""
    url = request.query.get("url")
    if not url:
        return web.json_response({"error": "Missing url param"}, status=400)

    cache_key = hashlib.md5(url.encode()).hexdigest()
    if cache_key in CACHE and time.time() - CACHE[cache_key][0] < CACHE_TTL:
        return web.json_response(CACHE[cache_key][1])

    session: ClientSession = request.app["session"]
    try:
        headers = {}
        auth_header = request.headers.get("X-Api-Auth")
        if auth_header:
            headers["Authorization"] = auth_header

        async with session.get(url, headers=headers) as resp:
            data = await resp.json()

        CACHE[cache_key] = (time.time(), data)
        return web.json_response(data)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_ai_parse(request):
    """AI Layer 1: Parse an arbitrary JSON response to find labels + values."""
    body = await request.json()
    raw_json = body.get("data")
    url = body.get("url", "unknown")

    if not raw_json:
        return web.json_response({"error": "Missing data"}, status=400)

    sample = json.dumps(raw_json)[:4000]

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"""Analyze this JSON API response and extract the data structure.
URL: {url}

JSON (first 4000 chars):
{sample}

Respond with ONLY valid JSON:
{{
  "name": "short descriptive name for this dataset",
  "description": "what this data represents",
  "path_labels": "dot.path.to.labels.array (dates, names, or categories)",
  "path_values": "dot.path.to.numeric.values.array",
  "unit": "unit of measurement",
  "data_type": "time_series|categorical|single_value",
  "granularity": "daily|hourly|monthly|yearly|unknown",
  "sample_label": "first label value",
  "sample_value": "first numeric value",
  "confidence": 0.0-1.0
}}"""
        }]
    )
    try:
        result = json.loads(msg.content[0].text)
        return web.json_response(result)
    except json.JSONDecodeError:
        return web.json_response({"raw": msg.content[0].text}, status=422)


async def handle_ai_discover(request):
    """AI Layer 2: Suggest APIs for a natural language query."""
    body = await request.json()
    query = body.get("query", "")

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    catalog_summary = "\n".join(
        f"- {a['id']}: {a['name']} ({a['category']}) — {a['desc']} [{a['location_type']}, {a['granularity']}]"
        for a in get_catalog_for_api()
    )

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": f"""The user wants to explore data correlations. Their question:
"{query}"

Available pre-configured APIs ({len(CATALOG)} total):
{catalog_summary}

Location types: "latlon" = needs city coordinates, "country" = needs country code, "global" = no location needed.
Granularity: daily, monthly, yearly, 10-day.

Respond with ONLY valid JSON:
{{
  "interpretation": "what the user is asking about",
  "suggestions": [
    {{
      "catalog_id": "id from catalog or null if custom",
      "name": "dataset name",
      "why": "why this is relevant",
      "custom_url": "full URL if not in catalog, null otherwise"
    }}
  ],
  "comparison_pairs": [
    {{
      "a": "first dataset id or name",
      "b": "second dataset id or name",
      "hypothesis": "what correlation to expect and why"
    }}
  ],
  "also_try": "other interesting angles the user might not have considered"
}}"""
        }]
    )
    try:
        result = json.loads(msg.content[0].text)
        return web.json_response(result)
    except json.JSONDecodeError:
        return web.json_response({"raw": msg.content[0].text}, status=422)


async def handle_ai_insight(request):
    """AI Layer 3: Explain correlation results."""
    body = await request.json()

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"""Analyze this correlation result between two datasets. Use markdown formatting.

**Dataset A:** {body.get('nameA', '?')} ({body.get('unitA', '?')})
**Dataset B:** {body.get('nameB', '?')} ({body.get('unitB', '?')})

| Metric | Value |
|--------|-------|
| Pearson | {body.get('pearson', 0):.4f} |
| Spearman | {body.get('spearman', 0):.4f} |
| R² | {body.get('r_squared', 0):.4f} |
| Data points | {body.get('n', 0)} |
| Period | {body.get('period', '30 days')} |

Write a structured analysis using markdown with these sections:

## Correlation Strength
One sentence on what the r value means (weak/moderate/strong, positive/negative).

## Interpretation
2-3 sentences: Is this likely causal, coincidental, or driven by a confounding variable? Be direct and scientifically honest.

## Explore Further
Suggest 2-3 specific datasets that would be interesting to compare next, as a bullet list.

Use **bold** for emphasis. Keep it concise but insightful."""
        }]
    )
    return web.json_response({"insight": msg.content[0].text})


async def handle_index(request):
    return web.FileResponse(Path(__file__).parent / "www" / "index.html")


async def on_startup(app):
    app["session"] = ClientSession(timeout=ClientTimeout(total=30))


async def on_cleanup(app):
    await app["session"].close()


def run():
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/catalog", handle_catalog)
    app.router.add_post("/api/fetch", handle_fetch_dataset)
    app.router.add_get("/api/proxy", handle_proxy)
    app.router.add_post("/api/ai/parse", handle_ai_parse)
    app.router.add_post("/api/ai/discover", handle_ai_discover)
    app.router.add_post("/api/ai/insight", handle_ai_insight)
    app.router.add_static("/pkg/", Path(__file__).parent / "www" / "pkg")
    app.router.add_static("/js/", Path(__file__).parent / "www" / "js")
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    port = int(os.environ.get("PORT", 8080))
    print(f"\n  API Correlation Explorer")
    print(f"  {len(CATALOG)} data sources across {len(set(a['category'] for a in CATALOG))} categories")
    print(f"  Open http://localhost:{port}\n")
    web.run_app(app, host="localhost", port=port, print=None)


if __name__ == "__main__":
    run()
