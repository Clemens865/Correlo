"""Data fetchers — one handler per fetch_type in the catalog."""

import csv
import datetime
import io
from collections import defaultdict
import aiohttp
from aiohttp import ClientSession


def make_date_range(days: int) -> tuple[str, str]:
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days)
    return start.isoformat(), end.isoformat()


def date_range_days(start: str, end: str) -> list[str]:
    """Generate list of date strings between start and end."""
    s = datetime.date.fromisoformat(start)
    e = datetime.date.fromisoformat(end)
    return [(s + datetime.timedelta(days=i)).isoformat() for i in range((e - s).days + 1)]


# ============================================================================
# OPEN-METEO
# ============================================================================

async def fetch_open_meteo_archive(session: ClientSession, config: dict,
                                    lat: float, lon: float, days: int, **kw) -> dict:
    var = config["variable"]
    start, end = make_date_range(days)
    # Use archive API for > 92 days, forecast API for <= 92
    if days <= 92:
        url = (f"https://api.open-meteo.com/v1/forecast"
               f"?latitude={lat}&longitude={lon}&daily={var}"
               f"&past_days={days}&forecast_days=0&timezone=auto")
    else:
        url = (f"https://archive-api.open-meteo.com/v1/archive"
               f"?latitude={lat}&longitude={lon}&daily={var}"
               f"&start_date={start}&end_date={end}&timezone=auto")
    async with session.get(url) as resp:
        data = await resp.json()
    labels = data["daily"]["time"]
    values = data["daily"][var]
    # sunshine_duration comes in seconds, convert to hours
    if var == "sunshine_duration":
        values = [v / 3600 if v is not None else None for v in values]
    return _clean(labels, values)


async def fetch_open_meteo_airquality(session: ClientSession, config: dict,
                                       lat: float, lon: float, days: int, **kw) -> dict:
    var = config["variable"]
    start, end = make_date_range(days)
    url = (f"https://air-quality-api.open-meteo.com/v1/air-quality"
           f"?latitude={lat}&longitude={lon}&hourly={var}"
           f"&start_date={start}&end_date={end}")
    async with session.get(url) as resp:
        data = await resp.json()
    # Aggregate hourly to daily means
    return _aggregate_daily(data["hourly"]["time"], data["hourly"][var])


async def fetch_open_meteo_marine(session: ClientSession, config: dict,
                                   lat: float, lon: float, days: int, **kw) -> dict:
    var = config["variable"]
    url = (f"https://marine-api.open-meteo.com/v1/marine"
           f"?latitude={lat}&longitude={lon}&daily={var}"
           f"&past_days={min(days, 90)}&forecast_days=0")
    async with session.get(url) as resp:
        data = await resp.json(content_type=None)
    daily = data.get("daily")
    if not daily or var not in daily or not daily[var]:
        raise Exception("No marine data — location may be too far from coast")
    return _clean(daily["time"], daily[var])


async def fetch_open_meteo_flood(session: ClientSession, config: dict,
                                  lat: float, lon: float, days: int, **kw) -> dict:
    var = config["variable"]
    start, end = make_date_range(days)
    url = (f"https://flood-api.open-meteo.com/v1/flood"
           f"?latitude={lat}&longitude={lon}&daily={var}"
           f"&start_date={start}&end_date={end}")
    async with session.get(url) as resp:
        data = await resp.json()
    return _clean(data["daily"]["time"], data["daily"][var])


# ============================================================================
# NOAA CLIMATE
# ============================================================================

async def fetch_noaa_temp_anomaly(session: ClientSession, config: dict, days: int, **kw) -> dict:
    end_year = datetime.date.today().year
    start_year = max(1880, end_year - days // 365)
    # Request monthly (1-month timescale) data for better alignment with other monthly datasets
    url = (f"https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/"
           f"global/time-series/globe/land_ocean/1/0/{start_year}-{end_year}.json")
    # NOAA can be very slow — use dedicated session with generous timeout
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=45)) as noaa_session:
        async with noaa_session.get(url) as resp:
            data = await resp.json(content_type=None)
    entries = data.get("data", {})
    labels = sorted(entries.keys())
    values = [float(entries[k].get("value", entries[k].get("anomaly", 0))) for k in labels]
    # Convert YYYYMM to YYYY-MM
    labels = [f"{k[:4]}-{k[4:]}" for k in labels]
    return {"labels": labels, "values": values}


async def fetch_noaa_co2(session: ClientSession, config: dict, days: int, **kw) -> dict:
    gas = config["gas"]
    scope = config["scope"]
    url = f"https://gml.noaa.gov/webdata/ccgg/trends/{gas}/{gas}_mm_{scope}.csv"
    async with session.get(url) as resp:
        text = await resp.text()
    labels, values = [], []
    for line in text.strip().split("\n"):
        if line.startswith("#") or line.startswith('"'):
            continue
        parts = line.split(",")
        if len(parts) < 4:
            continue
        try:
            year, month = int(parts[0]), int(parts[1])
            val = float(parts[3])  # average column
            if val > 0:
                labels.append(f"{year}-{month:02d}")
                values.append(val)
        except (ValueError, IndexError):
            continue
    # Trim to requested period
    if days < 36500 and len(labels) > 0:
        cutoff = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%Y-%m")
        filtered = [(l, v) for l, v in zip(labels, values) if l >= cutoff]
        if filtered:
            labels, values = zip(*filtered)
            labels, values = list(labels), list(values)
    return {"labels": labels, "values": values}


async def fetch_noaa_sea_level(session: ClientSession, config: dict, days: int, **kw) -> dict:
    url = "https://www.star.nesdis.noaa.gov/socd/lsa/SeaLevelRise/slr/slr_sla_gbl_free_all_66.csv"
    async with session.get(url) as resp:
        text = await resp.text()
    labels, values = [], []
    for line in text.strip().split("\n"):
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split(",")
        if len(parts) < 2:
            continue
        try:
            year_dec = float(parts[0])
            # Find first non-empty satellite value
            val = None
            for p in parts[1:]:
                p = p.strip()
                if p:
                    try:
                        val = float(p)
                        break
                    except ValueError:
                        continue
            if val is not None:
                year = int(year_dec)
                month = int((year_dec - year) * 12) + 1
                labels.append(f"{year}-{month:02d}")
                values.append(val)
        except (ValueError, IndexError):
            continue
    return {"labels": labels, "values": values}


async def fetch_nsidc_ice(session: ClientSession, config: dict, days: int, **kw) -> dict:
    hemi = "N" if config["hemisphere"] == "north" else "S"
    url = f"https://noaadata.apps.nsidc.org/NOAA/G02135/{config['hemisphere']}/daily/data/{hemi}_seaice_extent_daily_v4.0.csv"
    async with session.get(url) as resp:
        text = await resp.text()
    labels, values = [], []
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    for line in text.strip().split("\n"):
        if "Year" in line or "Missing" in line or not line.strip():
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            continue
        try:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            date_str = f"{y}-{m:02d}-{d:02d}"
            if date_str < cutoff:
                continue
            val = float(parts[3])
            if val > 0:
                labels.append(date_str)
                values.append(val)
        except (ValueError, IndexError):
            continue
    return {"labels": labels, "values": values}


async def fetch_noaa_sunspots(session: ClientSession, config: dict, days: int, **kw) -> dict:
    url = "https://services.swpc.noaa.gov/json/solar-cycle/observed-solar-cycle-indices.json"
    async with session.get(url) as resp:
        data = await resp.json()
    labels, values = [], []
    cutoff_year = datetime.date.today().year - max(1, days // 365)
    for entry in data:
        tag = entry.get("time-tag", "")
        ssn = entry.get("ssn", -1)
        if ssn < 0 or not tag:
            continue
        year = int(tag[:4])
        if year < cutoff_year:
            continue
        labels.append(tag[:7])
        values.append(float(ssn))
    return {"labels": labels, "values": values}


# ============================================================================
# NASA POWER
# ============================================================================

async def fetch_nasa_power(session: ClientSession, config: dict,
                            lat: float, lon: float, days: int, **kw) -> dict:
    param = config["parameter"]
    start_date = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%Y%m%d")
    end_date = datetime.date.today().strftime("%Y%m%d")
    url = (f"https://power.larc.nasa.gov/api/temporal/daily/point"
           f"?start={start_date}&end={end_date}"
           f"&latitude={lat}&longitude={lon}"
           f"&community=RE&parameters={param}&format=json")
    async with session.get(url) as resp:
        data = await resp.json()
    params = data.get("properties", {}).get("parameter", {}).get(param, {})
    labels, values = [], []
    for date_str, val in sorted(params.items()):
        if val is not None and val != -999.0:
            labels.append(f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}")
            values.append(float(val))
    return {"labels": labels, "values": values}


# ============================================================================
# USGS EARTHQUAKES
# ============================================================================

async def fetch_usgs_daily(session: ClientSession, config: dict, days: int, **kw) -> dict:
    start, end = make_date_range(days)
    url = (f"https://earthquake.usgs.gov/fdsnws/event/1/query"
           f"?format=geojson&starttime={start}&endtime={end}"
           f"&minmagnitude=2.5&orderby=time&limit=20000")
    async with session.get(url) as resp:
        data = await resp.json()
    by_day: dict[str, list[float]] = {}
    for f in data.get("features", []):
        ts = f["properties"]["time"]
        day = datetime.datetime.fromtimestamp(ts / 1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
        by_day.setdefault(day, []).append(f["properties"]["mag"])
    all_days = date_range_days(start, end)
    if config["mode"] == "max":
        values = [max(by_day.get(d, [0])) for d in all_days]
    else:
        values = [len(by_day.get(d, [])) for d in all_days]
    return {"labels": all_days, "values": values}


# ============================================================================
# COINGECKO
# ============================================================================

async def fetch_coingecko(session: ClientSession, config: dict, days: int, **kw) -> dict:
    coin = config["coin"]
    field = config["field"]
    d = min(days, 365)
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart?vs_currency=usd&days={d}&interval=daily"
    async with session.get(url) as resp:
        if resp.status == 429:
            raise Exception("CoinGecko rate limit — try again in a minute")
        if resp.status != 200:
            raise Exception(f"CoinGecko returned {resp.status}")
        data = await resp.json(content_type=None)
    entries = data.get(field, [])
    if not entries:
        raise Exception(f"No {field} data for {coin}")
    labels = [datetime.datetime.fromtimestamp(e[0] / 1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d") for e in entries]
    values = [e[1] for e in entries]
    return {"labels": labels, "values": values}


# ============================================================================
# FRANKFURTER
# ============================================================================

async def fetch_frankfurter(session: ClientSession, config: dict, days: int, **kw) -> dict:
    cur = config["currency"]
    start, end = make_date_range(days)
    url = f"https://api.frankfurter.app/{start}..{end}?from=EUR&to={cur}"
    async with session.get(url) as resp:
        data = await resp.json()
    rates = data.get("rates", {})
    sorted_dates = sorted(rates.keys())
    values = [rates[d][cur] for d in sorted_dates]
    return {"labels": sorted_dates, "values": values}


# ============================================================================
# WORLD BANK
# ============================================================================

async def fetch_world_bank(session: ClientSession, config: dict,
                            country: str = "WLD", days: int = 23000, **kw) -> dict:
    indicator = config["indicator"]
    end_year = datetime.date.today().year
    # Ensure at least 10 years for yearly data (WB has 2-3 year lag)
    years = max(10, days // 365)
    start_year = max(1960, end_year - years)
    url = (f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
           f"?format=json&date={start_year}:{end_year}&per_page=500")
    async with session.get(url) as resp:
        data = await resp.json()
    if not isinstance(data, list) or len(data) < 2:
        return {"labels": [], "values": []}
    entries = [(e["date"], e["value"]) for e in data[1] if e["value"] is not None]
    entries.sort(key=lambda x: x[0])
    return {"labels": [e[0] for e in entries], "values": [e[1] for e in entries]}


# ============================================================================
# COVID-19 (disease.sh)
# ============================================================================

async def fetch_covid(session: ClientSession, config: dict, days: int, **kw) -> dict:
    metric = config["metric"]
    country = config["country"]
    if country == "all":
        url = "https://disease.sh/v3/covid-19/historical/all?lastdays=all"
    else:
        url = f"https://disease.sh/v3/covid-19/historical/{country}?lastdays=all"
    async with session.get(url) as resp:
        if resp.status != 200:
            raise Exception(f"COVID API returned {resp.status} — service may be down")
        data = await resp.json(content_type=None)
    if country != "all":
        data = data.get("timeline", data)
    series = data.get(metric, {})
    # Convert cumulative to daily new
    sorted_dates = sorted(series.keys(), key=lambda d: datetime.datetime.strptime(d, "%m/%d/%y"))
    labels, values = [], []
    prev = 0
    for d in sorted_dates:
        v = series[d]
        daily = max(0, v - prev)
        prev = v
        dt = datetime.datetime.strptime(d, "%m/%d/%y")
        labels.append(dt.strftime("%Y-%m-%d"))
        values.append(daily)
    return {"labels": labels, "values": values}


# ============================================================================
# OPENFDA
# ============================================================================

async def fetch_openfda(session: ClientSession, config: dict, days: int, **kw) -> dict:
    # Use search with date range to get relevant data
    start = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%Y%m%d")
    end = datetime.date.today().strftime("%Y%m%d")
    url = f"https://api.fda.gov/drug/event.json?search=receivedate:[{start}+TO+{end}]&count=receivedate"
    async with session.get(url) as resp:
        if resp.status != 200:
            raise Exception(f"OpenFDA returned {resp.status}")
        data = await resp.json(content_type=None)
    labels, values = [], []
    for entry in data.get("results", []):
        t = entry["time"]
        labels.append(f"{t[:4]}-{t[4:6]}-{t[6:]}")
        values.append(entry["count"])
    return {"labels": labels, "values": values}


# ============================================================================
# UK CARBON INTENSITY
# ============================================================================

async def fetch_uk_carbon(session: ClientSession, config: dict, days: int, **kw) -> dict:
    # API max range ~14 days per request, so chunk it
    by_day = defaultdict(list)
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=min(days, 2800))  # API has data from ~2018
    chunk_days = 14

    current = start_date
    while current < end_date:
        chunk_end = min(current + datetime.timedelta(days=chunk_days), end_date)
        url = f"https://api.carbonintensity.org.uk/intensity/{current.isoformat()}/{chunk_end.isoformat()}"
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    current = chunk_end
                    continue
                data = await resp.json(content_type=None)
            for entry in data.get("data", []):
                day = entry["from"][:10]
                val = entry["intensity"].get("actual") or entry["intensity"].get("forecast")
                if val is not None:
                    by_day[day].append(val)
        except Exception:
            pass
        current = chunk_end

    sorted_days = sorted(by_day.keys())
    values = [sum(by_day[d]) / len(by_day[d]) for d in sorted_days]
    return {"labels": sorted_days, "values": values}


# ============================================================================
# WIKIPEDIA PAGEVIEWS
# ============================================================================

async def fetch_wikipedia(session: ClientSession, config: dict, days: int, **kw) -> dict:
    article = config["article"]
    end = datetime.date.today().strftime("%Y%m%d")
    start = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%Y%m%d")
    # Earliest data is 20150701
    if start < "20150701":
        start = "20150701"
    url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
           f"en.wikipedia/all-access/all-agents/{article}/daily/{start}/{end}")
    headers = {
        "User-Agent": "APICorrelationExplorer/1.0 (https://github.com/api-correlation-explorer; contact@example.com)",
        "Accept": "application/json",
    }
    # Use a separate session to avoid default header conflicts
    async with aiohttp.ClientSession() as wiki_session:
        async with wiki_session.get(url, headers=headers) as resp:
            if resp.status != 200:
                raise Exception(f"Wikipedia API returned {resp.status}")
            data = await resp.json(content_type=None)
    labels, values = [], []
    for item in data.get("items", []):
        ts = item["timestamp"]
        labels.append(f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}")
        values.append(item["views"])
    return {"labels": labels, "values": values}


# ============================================================================
# INATURALIST
# ============================================================================

async def fetch_inaturalist(session: ClientSession, config: dict, days: int, **kw) -> dict:
    taxon_id = config["taxon_id"]
    end = datetime.date.today().isoformat()
    start = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    url = (f"https://api.inaturalist.org/v1/observations/histogram"
           f"?date_field=observed&interval=month&taxon_id={taxon_id}"
           f"&d1={start}&d2={end}")
    async with session.get(url) as resp:
        data = await resp.json()
    months = data.get("results", {}).get("month", {})
    sorted_months = sorted(months.keys())
    labels = [m[:7] for m in sorted_months]  # "2024-01-01" -> "2024-01"
    values = [months[m] for m in sorted_months]
    return {"labels": labels, "values": values}


# ============================================================================
# NPM DOWNLOADS
# ============================================================================

async def fetch_npm(session: ClientSession, config: dict, days: int, **kw) -> dict:
    pkg = config["package"]
    end = datetime.date.today().isoformat()
    start = (datetime.date.today() - datetime.timedelta(days=min(days, 365 * 3))).isoformat()
    url = f"https://api.npmjs.org/downloads/range/{start}:{end}/{pkg}"
    async with session.get(url) as resp:
        data = await resp.json()
    labels = [d["day"] for d in data.get("downloads", [])]
    values = [d["downloads"] for d in data.get("downloads", [])]
    return {"labels": labels, "values": values}


# ============================================================================
# HELPERS
# ============================================================================

def _clean(labels: list, values: list) -> dict:
    """Remove null values from paired label/value lists."""
    clean_l, clean_v = [], []
    for l, v in zip(labels, values):
        if v is not None:
            clean_l.append(l)
            clean_v.append(float(v))
    return {"labels": clean_l, "values": clean_v}


def _aggregate_daily(labels: list[str], values: list) -> dict:
    """Aggregate hourly data to daily means."""
    by_day = defaultdict(list)
    for label, val in zip(labels, values):
        if val is None:
            continue
        day = label[:10]
        by_day[day].append(val)
    sorted_days = sorted(by_day.keys())
    means = [sum(by_day[d]) / len(by_day[d]) for d in sorted_days]
    return {"labels": sorted_days, "values": means}


# ============================================================================
# EUROSTAT
# ============================================================================

# Country code mapping: our 2-letter codes to Eurostat geo codes
_EUROSTAT_GEO = {
    "AT": "AT", "DE": "DE", "FR": "FR", "GB": "UK", "US": "US",
    "JP": "JP", "CN": "CN", "IN": "IN", "BR": "BR", "AU": "AU",
    "CA": "CA", "CH": "CH", "KR": "KR", "SG": "SG", "ZA": "ZA",
    "NG": "NG", "EU": "EU27_2020", "WLD": "EU27_2020",
}


async def fetch_eurostat(session: ClientSession, config: dict,
                          country: str = "AT", days: int = 9000, **kw) -> dict:
    dataset = config["dataset"]
    geo = _EUROSTAT_GEO.get(country, country)
    end_year = datetime.date.today().year
    start_year = max(2000, end_year - max(1, days // 365))

    params = f"geo={geo}&sinceTimePeriod={start_year}"
    for k, v in config.get("filter_params", {}).items():
        params += f"&{k}={v}"

    url = f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}?{params}"
    async with session.get(url) as resp:
        data = await resp.json(content_type=None)

    # JSON-stat 2.0 format: values in "value" dict, time labels in dimension
    values_dict = data.get("value", {})
    time_dim = data.get("dimension", {}).get("time", {}).get("category", {})
    time_index = time_dim.get("index", {})

    # Build sorted time->value pairs
    index_to_time = {v: k for k, v in time_index.items()}
    labels, values = [], []
    for idx in sorted(index_to_time.keys()):
        time_label = index_to_time[idx]
        val = values_dict.get(str(idx))
        if val is not None:
            labels.append(time_label)
            values.append(float(val))

    return {"labels": labels, "values": values}


# ============================================================================
# BLS (Bureau of Labor Statistics)
# ============================================================================

async def fetch_bls(session: ClientSession, config: dict, days: int = 7300, **kw) -> dict:
    series_id = config["series_id"]
    end_year = datetime.date.today().year
    start_year = max(2000, end_year - max(1, days // 365))

    url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
    payload = {
        "seriesid": [series_id],
        "startyear": str(start_year),
        "endyear": str(end_year),
    }
    async with session.post(url, json=payload) as resp:
        data = await resp.json(content_type=None)

    labels, values = [], []
    series = data.get("Results", {}).get("series", [])
    if series:
        for entry in reversed(series[0].get("data", [])):
            period = entry.get("period", "")
            if not period.startswith("M") or period == "M13":
                continue
            month = int(period[1:])
            year = entry["year"]
            label = f"{year}-{month:02d}"
            try:
                values.append(float(entry["value"]))
                labels.append(label)
            except (ValueError, KeyError):
                continue

    return {"labels": labels, "values": values}


# ============================================================================
# UN SDG
# ============================================================================

# Country code to UN numeric area code
_UN_AREA = {
    "AT": "40", "DE": "276", "FR": "250", "GB": "826", "US": "840",
    "JP": "392", "CN": "156", "IN": "356", "BR": "76", "AU": "36",
    "CA": "124", "CH": "756", "KR": "410", "SG": "702", "ZA": "710",
    "NG": "566", "WLD": "1", "EU": "1",
}


async def fetch_un_sdg(session: ClientSession, config: dict,
                        country: str = "WLD", days: int = 9500, **kw) -> dict:
    indicator = config["indicator"]
    area = _UN_AREA.get(country, "1")
    url = (f"https://unstats.un.org/sdgs/UNSDGAPIV5/v1/sdg/Indicator/Data"
           f"?indicator={indicator}&areaCode={area}&pageSize=200")
    # UN SDG API can be slow — use dedicated session with longer timeout
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as sdg_session:
        async with sdg_session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"UN SDG API returned {resp.status}")
            data = await resp.json(content_type=None)

    entries = []
    for item in data.get("data", []):
        try:
            year = str(item["timePeriodStart"])
            val = float(item["value"])
            entries.append((year, val))
        except (ValueError, KeyError, TypeError):
            continue

    # Deduplicate by year (take first occurrence)
    seen = set()
    labels, values = [], []
    for year, val in sorted(entries, key=lambda x: x[0]):
        if year not in seen:
            seen.add(year)
            labels.append(year)
            values.append(val)

    return {"labels": labels, "values": values}


# ============================================================================
# ECB (European Central Bank)
# ============================================================================

async def fetch_ecb(session: ClientSession, config: dict, days: int = 9500, **kw) -> dict:
    flow = config["flow"]
    key = config["key"]
    url = f"https://data-api.ecb.europa.eu/service/data/{flow}/{key}"
    headers = {"Accept": "application/vnd.sdmx.data+json;version=1.0.0-wd"}

    years_back = max(1, days // 365)
    start_year = datetime.date.today().year - years_back

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as ecb_session:
        async with ecb_session.get(
            f"{url}?startPeriod={start_year}", headers=headers
        ) as resp:
            if resp.status != 200:
                raise Exception(f"ECB API returned {resp.status}")
            data = await resp.json(content_type=None)

    # Parse SDMX-JSON
    datasets = data.get("dataSets", [])
    if not datasets:
        return {"labels": [], "values": []}

    series = datasets[0].get("series", {})
    # Get first series key
    first_key = next(iter(series), None)
    if not first_key:
        return {"labels": [], "values": []}

    observations = series[first_key].get("observations", {})
    time_periods = data.get("structure", {}).get("dimensions", {}).get("observation", [])
    time_values = []
    for dim in time_periods:
        if dim.get("id") == "TIME_PERIOD":
            time_values = dim.get("values", [])
            break

    labels, values = [], []
    for idx_str, obs in sorted(observations.items(), key=lambda x: int(x[0])):
        idx = int(idx_str)
        if idx < len(time_values) and obs:
            labels.append(time_values[idx]["id"])
            values.append(float(obs[0]))

    return {"labels": labels, "values": values}


# ============================================================================
# UK ONS (Office for National Statistics)
# ============================================================================

async def fetch_ons(session: ClientSession, config: dict, days: int = 13000, **kw) -> dict:
    series_id = config["series_id"]
    dataset_id = config["dataset_id"]
    gran = config["granularity"]

    url = f"https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/{series_id.lower()}/{dataset_id}/data"
    if "gdp" in dataset_id or "qna" in dataset_id:
        url = f"https://www.ons.gov.uk/economy/grossdomesticproductgdp/timeseries/{series_id.lower()}/{dataset_id}/data"
    if "lms" in dataset_id:
        url = f"https://www.ons.gov.uk/employmentandlabourmarket/peoplenotinwork/unemployment/timeseries/{series_id.lower()}/{dataset_id}/data"

    async with session.get(url) as resp:
        if resp.status != 200:
            raise Exception(f"ONS API returned {resp.status}")
        data = await resp.json(content_type=None)

    cutoff_year = datetime.date.today().year - max(1, days // 365)
    labels, values = [], []

    source = data.get("months", []) if gran == "monthly" else data.get("quarters", [])
    for entry in source:
        try:
            val = float(entry["value"])
            year = int(entry["year"])
            if year < cutoff_year:
                continue
            if gran == "monthly":
                # Convert month name to number: "January" -> "01"
                month_names = ["January","February","March","April","May","June",
                               "July","August","September","October","November","December"]
                month_str = entry.get("month", "")
                month_num = month_names.index(month_str) + 1 if month_str in month_names else 0
                label = f"{entry['year']}-{month_num:02d}" if month_num else f"{entry['year']}-{month_str}"
            else:
                # Convert quarter to month: Q1->01, Q2->04, Q3->07, Q4->10
                q = entry.get("quarter", "Q1")
                q_map = {"Q1": "01", "Q2": "04", "Q3": "07", "Q4": "10"}
                label = f"{entry['year']}-{q_map.get(q, '01')}"
            labels.append(label)
            values.append(val)
        except (ValueError, KeyError, TypeError):
            continue

    return {"labels": labels, "values": values}


# ============================================================================
# INE Spain
# ============================================================================

async def fetch_ine_spain(session: ClientSession, config: dict, days: int = 9000, **kw) -> dict:
    code = config["series_code"]
    n = max(10, min(500, days // 30))  # Approximate months
    url = f"https://servicios.ine.es/wstempus/js/EN/DATOS_SERIE/{code}?nult={n}"

    async with session.get(url) as resp:
        if resp.status != 200:
            raise Exception(f"INE Spain API returned {resp.status}")
        data = await resp.json(content_type=None)

    labels, values = [], []
    for entry in data.get("Data", []):
        try:
            ts = entry["Fecha"] / 1000  # ms to seconds
            dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
            labels.append(dt.strftime("%Y-%m"))
            values.append(float(entry["Valor"]))
        except (ValueError, KeyError, TypeError):
            continue

    # Sort chronologically
    pairs = sorted(zip(labels, values))
    if pairs:
        labels, values = zip(*pairs)
        labels, values = list(labels), list(values)

    return {"labels": labels, "values": values}


# ============================================================================
# GeoSphere Austria (formerly ZAMG)
# ============================================================================

async def fetch_geosphere(session: ClientSession, config: dict, days: int = 365, **kw) -> dict:
    param = config["parameter"]
    station = config["station_id"]
    start = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    end = datetime.date.today().isoformat()

    url = (f"https://dataset.api.hub.geosphere.at/v1/station/historical/klima-v2-1d"
           f"?parameters={param}&station_ids={station}&start={start}&end={end}"
           f"&output_format=geojson")

    async with session.get(url) as resp:
        if resp.status != 200:
            raise Exception(f"GeoSphere API returned {resp.status}")
        data = await resp.json(content_type=None)

    timestamps = data.get("timestamps", [])
    features = data.get("features", [])
    if not features:
        return {"labels": [], "values": []}

    param_data = features[0].get("properties", {}).get("parameters", {}).get(param, {}).get("data", [])

    labels, values = [], []
    for ts, val in zip(timestamps, param_data):
        if val is not None:
            labels.append(ts[:10])  # "2024-01-01T..." -> "2024-01-01"
            values.append(float(val))

    return {"labels": labels, "values": values}


# ============================================================================
# US TREASURY
# ============================================================================

async def fetch_us_treasury(session: ClientSession, config: dict, days: int = 365, **kw) -> dict:
    endpoint = config["endpoint"]
    field = config["field"]
    start = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    url = (f"https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/"
           f"{endpoint}?sort=-record_date&filter=record_date:gte:{start}"
           f"&page[size]=10000&fields=record_date,{field}")
    async with session.get(url) as resp:
        if resp.status != 200:
            raise Exception(f"Treasury API returned {resp.status}")
        data = await resp.json(content_type=None)
    labels, values = [], []
    for entry in reversed(data.get("data", [])):
        try:
            labels.append(entry["record_date"])
            val = float(entry[field]) / 1e12  # Convert to trillions
            values.append(val)
        except (ValueError, KeyError):
            continue
    return {"labels": labels, "values": values}


async def fetch_us_treasury_mts(session: ClientSession, config: dict, days: int = 365, **kw) -> dict:
    endpoint = config["endpoint"]
    field = config["field"]
    url = (f"https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/"
           f"{endpoint}?sort=-record_date&page[size]=500"
           f"&fields=record_date,{field}")
    async with session.get(url) as resp:
        if resp.status != 200:
            raise Exception(f"Treasury MTS API returned {resp.status}")
        data = await resp.json(content_type=None)
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    labels, values = [], []
    for entry in reversed(data.get("data", [])):
        try:
            date = entry["record_date"]
            if date < cutoff:
                continue
            labels.append(date[:7])  # YYYY-MM
            val = float(entry[field]) / 1e9  # Convert to billions
            values.append(val)
        except (ValueError, KeyError):
            continue
    return {"labels": labels, "values": values}


# ============================================================================
# BRAZIL — Banco Central (BCB SGS)
# ============================================================================

async def fetch_bcb_sgs(session: ClientSession, config: dict, days: int = 365, **kw) -> dict:
    sid = config["series_id"]
    start = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%d/%m/%Y")
    end = datetime.date.today().strftime("%d/%m/%Y")
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{sid}/dados?formato=json&dataInicial={start}&dataFinal={end}"
    async with session.get(url) as resp:
        if resp.status != 200:
            raise Exception(f"BCB API returned {resp.status}")
        data = await resp.json(content_type=None)
    labels, values = [], []
    for entry in data:
        try:
            # Date format: "dd/mm/yyyy"
            d = entry["data"]
            parts = d.split("/")
            iso_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
            labels.append(iso_date)
            values.append(float(entry["valor"]))
        except (ValueError, KeyError, IndexError):
            continue
    return {"labels": labels, "values": values}


# ============================================================================
# BANK OF CANADA
# ============================================================================

async def fetch_bank_of_canada(session: ClientSession, config: dict, days: int = 365, **kw) -> dict:
    series = config["series"]
    start = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    end = datetime.date.today().isoformat()
    url = f"https://www.bankofcanada.ca/valet/observations/{series}/json?start_date={start}&end_date={end}"
    async with session.get(url) as resp:
        if resp.status != 200:
            raise Exception(f"Bank of Canada API returned {resp.status}")
        data = await resp.json(content_type=None)
    labels, values = [], []
    for obs in data.get("observations", []):
        try:
            labels.append(obs["d"])
            values.append(float(obs[series]["v"]))
        except (ValueError, KeyError, TypeError):
            continue
    return {"labels": labels, "values": values}


# ============================================================================
# ARGENTINA — datos.gob.ar series API
# ============================================================================

async def fetch_argentina_series(session: ClientSession, config: dict, days: int = 365, **kw) -> dict:
    sid = config["series_id"]
    start = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    url = f"https://apis.datos.gob.ar/series/api/series/?ids={sid}&start_date={start}&limit=5000&format=json"
    async with session.get(url) as resp:
        if resp.status != 200:
            raise Exception(f"Argentina API returned {resp.status}")
        data = await resp.json(content_type=None)
    labels, values = [], []
    for row in data.get("data", []):
        try:
            if row[1] is not None:
                labels.append(row[0][:10])  # Date
                values.append(float(row[1]))
        except (ValueError, IndexError, TypeError):
            continue
    return {"labels": labels, "values": values}


# ============================================================================
# CDC SODA (Socrata Open Data API)
# ============================================================================

async def fetch_cdc_soda(session: ClientSession, config: dict, days: int = 365, **kw) -> dict:
    dataset = config["dataset"]
    date_field = config["date_field"]
    value_field = config["value_field"]
    extra_filter = config.get("filter", "")

    start = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    where = f"{date_field} > '{start}'"
    if extra_filter:
        where += f" AND {extra_filter}"
    url = (f"https://data.cdc.gov/resource/{dataset}.json"
           f"?$where={where}&$order={date_field}&$limit=10000")
    async with session.get(url) as resp:
        if resp.status != 200:
            raise Exception(f"CDC API returned {resp.status}")
        data = await resp.json(content_type=None)
    labels, values = [], []
    for entry in data:
        try:
            date = entry[date_field][:10]
            val = float(entry[value_field])
            labels.append(date)
            values.append(val)
        except (ValueError, KeyError, TypeError):
            continue
    return {"labels": labels, "values": values}


# ============================================================================
# GLOBAL WARMING API (global-warming.org)
# ============================================================================

async def fetch_global_warming(session: ClientSession, config: dict, days: int = 9000, **kw) -> dict:
    endpoint = config["endpoint"]
    key = config["key"]
    value_field = config["value_field"]
    url = f"https://global-warming.org/api/{endpoint}"
    async with session.get(url) as resp:
        if resp.status != 200:
            raise Exception(f"Global Warming API returned {resp.status}")
        data = await resp.json(content_type=None)
    items = data.get(key, [])
    labels, values = [], []
    for item in items:
        try:
            date_dec = float(item["date"])
            year = int(date_dec)
            month = round((date_dec - year) * 12) + 1
            if month > 12:
                month = 12
            if month < 1:
                month = 1
            labels.append(f"{year}-{month:02d}")
            values.append(float(item[value_field]))
        except (ValueError, KeyError):
            continue
    # Trim to requested period
    if days < 36500 and labels:
        cutoff = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%Y-%m")
        filtered = [(l, v) for l, v in zip(labels, values) if l >= cutoff]
        if filtered:
            labels, values = zip(*filtered)
            labels, values = list(labels), list(values)
    return {"labels": labels, "values": values}


# ============================================================================
# WHO Global Health Observatory
# ============================================================================

_WHO_COUNTRY = {
    "AT": "AUT", "DE": "DEU", "FR": "FRA", "GB": "GBR", "US": "USA",
    "JP": "JPN", "CN": "CHN", "IN": "IND", "BR": "BRA", "AU": "AUS",
    "CA": "CAN", "CH": "CHE", "KR": "KOR", "SG": "SGP", "ZA": "ZAF",
    "NG": "NGA", "WLD": "GLOBAL", "EU": "EUR",
}


async def fetch_who_gho(session: ClientSession, config: dict,
                         country: str = "WLD", days: int = 11000, **kw) -> dict:
    indicator = config["indicator"]
    dim1 = config.get("dim1", "")
    iso3 = _WHO_COUNTRY.get(country, country)

    url = f"https://ghoapi.azureedge.net/api/{indicator}"
    filters = [f"SpatialDim eq '{iso3}'"]
    if dim1:
        filters.append(f"Dim1 eq '{dim1}'")
    url += "?$filter=" + " and ".join(filters) + "&$orderby=TimeDim"

    async with session.get(url) as resp:
        if resp.status != 200:
            raise Exception(f"WHO GHO API returned {resp.status}")
        data = await resp.json(content_type=None)

    entries = []
    for item in data.get("value", []):
        try:
            year = str(item["TimeDim"])
            val = float(item["NumericValue"])
            entries.append((year, val))
        except (ValueError, KeyError, TypeError):
            continue

    # Deduplicate by year (take first)
    seen = set()
    labels, values = [], []
    for year, val in sorted(entries, key=lambda x: x[0]):
        if year not in seen:
            seen.add(year)
            labels.append(year)
            values.append(val)

    return {"labels": labels, "values": values}


# ============================================================================
# UNHCR Refugee Data
# ============================================================================

_UNHCR_COUNTRY = {
    "AT": "AUT", "DE": "DEU", "FR": "FRA", "GB": "GBR", "US": "USA",
    "JP": "JPN", "CN": "CHN", "IN": "IND", "BR": "BRA", "AU": "AUS",
    "CA": "CAN", "CH": "CHE", "KR": "KOR", "SG": "SGP", "ZA": "ZAF",
    "NG": "NGA", "WLD": "SYR", "EU": "SYR",
}


async def fetch_unhcr(session: ClientSession, config: dict,
                       country: str = "WLD", days: int = 20000, **kw) -> dict:
    metric = config["metric"]
    iso3 = _UNHCR_COUNTRY.get(country, country)
    url = f"https://api.unhcr.org/population/v1/population/?year_from=2000&year_to=2025&coo={iso3}&limit=1000"

    async with session.get(url) as resp:
        if resp.status != 200:
            raise Exception(f"UNHCR API returned {resp.status}")
        data = await resp.json(content_type=None)

    # Aggregate by year
    by_year: dict[str, int] = {}
    for item in data.get("items", []):
        try:
            year = str(item["year"])
            val = int(item.get(metric, 0) or 0)
            by_year[year] = by_year.get(year, 0) + val
        except (ValueError, KeyError, TypeError):
            continue

    labels = sorted(by_year.keys())
    values = [by_year[y] for y in labels]
    return {"labels": labels, "values": values}


# ============================================================================
# PyPI Stats
# ============================================================================

async def fetch_pypi(session: ClientSession, config: dict, days: int = 180, **kw) -> dict:
    pkg = config["package"]
    url = f"https://pypistats.org/api/packages/{pkg}/overall?mirrors=true"
    async with session.get(url) as resp:
        if resp.status != 200:
            raise Exception(f"PyPI Stats returned {resp.status}")
        data = await resp.json(content_type=None)

    # Aggregate categories per day
    by_day: dict[str, int] = {}
    for entry in data.get("data", []):
        day = entry.get("date", "")
        downloads = int(entry.get("downloads", 0))
        by_day[day] = by_day.get(day, 0) + downloads

    sorted_days = sorted(by_day.keys())
    values = [by_day[d] for d in sorted_days]
    return {"labels": sorted_days, "values": values}


# ============================================================================
# NASA Near-Earth Objects
# ============================================================================

async def fetch_nasa_neo(session: ClientSession, config: dict, days: int = 7, **kw) -> dict:
    end = datetime.date.today()
    start = end - datetime.timedelta(days=min(days, 7))  # API max 7 days
    url = (f"https://api.nasa.gov/neo/rest/v1/feed"
           f"?start_date={start.isoformat()}&end_date={end.isoformat()}"
           f"&api_key=DEMO_KEY")

    async with session.get(url) as resp:
        if resp.status != 200:
            raise Exception(f"NASA NEO API returned {resp.status}")
        data = await resp.json(content_type=None)

    neo = data.get("near_earth_objects", {})
    labels = sorted(neo.keys())
    values = [len(neo[d]) for d in labels]
    return {"labels": labels, "values": values}


# ============================================================================
# DISPATCHER
# ============================================================================

FETCH_HANDLERS = {
    "open_meteo_archive": fetch_open_meteo_archive,
    "open_meteo_airquality": fetch_open_meteo_airquality,
    "open_meteo_marine": fetch_open_meteo_marine,
    "open_meteo_flood": fetch_open_meteo_flood,
    "noaa_temp_anomaly": fetch_noaa_temp_anomaly,
    "noaa_co2": fetch_noaa_co2,
    "noaa_sea_level": fetch_noaa_sea_level,
    "nsidc_ice": fetch_nsidc_ice,
    "noaa_sunspots": fetch_noaa_sunspots,
    "nasa_power": fetch_nasa_power,
    "usgs_daily": fetch_usgs_daily,
    "coingecko": fetch_coingecko,
    "frankfurter": fetch_frankfurter,
    "world_bank": fetch_world_bank,
    "covid": fetch_covid,
    "openfda": fetch_openfda,
    "uk_carbon": fetch_uk_carbon,
    "wikipedia": fetch_wikipedia,
    "inaturalist": fetch_inaturalist,
    "npm": fetch_npm,
    "eurostat": fetch_eurostat,
    "bls": fetch_bls,
    "un_sdg": fetch_un_sdg,
    "ecb": fetch_ecb,
    "ons": fetch_ons,
    "ine_spain": fetch_ine_spain,
    "geosphere": fetch_geosphere,
    "us_treasury": fetch_us_treasury,
    "us_treasury_mts": fetch_us_treasury_mts,
    "bcb_sgs": fetch_bcb_sgs,
    "bank_of_canada": fetch_bank_of_canada,
    "argentina_series": fetch_argentina_series,
    "cdc_soda": fetch_cdc_soda,
    "global_warming": fetch_global_warming,
    "who_gho": fetch_who_gho,
    "unhcr": fetch_unhcr,
    "pypi": fetch_pypi,
    "nasa_neo": fetch_nasa_neo,
}
