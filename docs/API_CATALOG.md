# API Correlation Explorer — Complete Data Source Catalog

**Last updated:** 2026-03-05
**Total verified sources:** 50+ APIs across 15 categories
**Total available metrics:** 5,000+ (including 1,516 World Bank + 3,056 WHO indicators)

---

## TIER 1: No Auth, CORS Enabled, Tested & Working

### 1. Weather — Open-Meteo

| ID | Variable | Unit | Archive Since |
|----|----------|------|---------------|
| `temperature_2m_max` | Daily max temp | °C | 1940 |
| `temperature_2m_min` | Daily min temp | °C | 1940 |
| `temperature_2m_mean` | Daily mean temp | °C | 1940 |
| `apparent_temperature_max` | Feels-like max | °C | 1940 |
| `precipitation_sum` | Precipitation | mm | 1940 |
| `rain_sum` | Rain (excl snow) | mm | 1940 |
| `snowfall_sum` | Snowfall | cm | 1940 |
| `wind_speed_10m_max` | Max wind | km/h | 1940 |
| `wind_gusts_10m_max` | Max gusts | km/h | 1940 |
| `wind_direction_10m_dominant` | Wind dir | ° | 1940 |
| `shortwave_radiation_sum` | Solar radiation | MJ/m² | 1940 |
| `et0_fao_evapotranspiration` | Evapotranspiration | mm | 1940 |
| `sunshine_duration` | Sunshine | seconds | 1940 |
| `surface_pressure_mean` | Pressure | hPa | forecast only |
| `relative_humidity_2m_mean` | Humidity | % | forecast only |
| `uv_index_max` | UV index | index | forecast only |

- **Forecast:** `https://api.open-meteo.com/v1/forecast` (92 days back)
- **Archive:** `https://archive-api.open-meteo.com/v1/archive` (1940–present)
- **Climate models:** `https://climate-api.open-meteo.com/v1/climate` (1950–2050, CMIP6)
- **Location:** Any lat/lon | **Rate limit:** 10,000/day | **Granularity:** Daily/Hourly

### 2. Air Quality — Open-Meteo

| Variable | Unit | Description |
|----------|------|-------------|
| `pm2_5` | μg/m³ | Fine particles |
| `pm10` | μg/m³ | Coarse particles |
| `ozone` | μg/m³ | O₃ |
| `nitrogen_dioxide` | μg/m³ | NO₂ |
| `sulphur_dioxide` | μg/m³ | SO₂ |
| `carbon_monoxide` | μg/m³ | CO |
| `dust` | μg/m³ | Saharan dust |
| `european_aqi` | index | EU Air Quality Index |
| `us_aqi` | index | US Air Quality Index |
| `alder_pollen` | grains/m³ | Pollen (6 types) |

- **URL:** `https://air-quality-api.open-meteo.com/v1/air-quality`
- **History:** 2020–present | **Granularity:** Hourly (aggregate to daily)

### 3. Marine — Open-Meteo

| Variable | Unit |
|----------|------|
| `wave_height_max` | m |
| `wave_period_max` | s |
| `swell_wave_height_max` | m |
| `sea_surface_temperature` | °C |

- **URL:** `https://marine-api.open-meteo.com/v1/marine`
- **History:** ~2000–present | **Location:** Coastal/ocean

### 4. Flood — Open-Meteo

| Variable | Unit |
|----------|------|
| `river_discharge` | m³/s |
| `river_discharge_mean/max/min` | m³/s |

- **URL:** `https://flood-api.open-meteo.com/v1/flood`
- **History:** 1984–present

### 5. Climate — NOAA Global Temperature Anomaly

- **URL:** `https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/global/time-series/globe/land_ocean/1/1/1880-2025.json`
- **Data:** Temperature anomaly (°C, base 1901-2000)
- **Range:** **1880–2025** (146 years) | **Granularity:** Monthly/Annual
- **Format:** JSON `{ data: { "188001": { value: "-0.37" } } }`

### 6. Climate — NOAA CO₂ (Keeling Curve)

- **URL:** `https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.csv`
- **Data:** Monthly avg CO₂ concentration (ppm)
- **Range:** **1958–2026** (68 years) | **Granularity:** Monthly
- **Format:** CSV (comment lines start with `#`)
- **Also:** Global CO₂ (`co2_mm_gl.csv`, 1979+), CH₄ (`ch4_mm_gl.csv`, 1983+), N₂O (`n2o_mm_gl.csv`, 2001+)

### 7. Solar — NOAA Solar Cycle Indices

- **URL:** `https://services.swpc.noaa.gov/json/solar-cycle/observed-solar-cycle-indices.json`
- **Data:** Sunspot number (SSN), smoothed SSN, F10.7 radio flux
- **Range:** **1749–2026** (277 years!) | **Granularity:** Monthly
- **Format:** JSON array, 3,326 records

### 8. Sea Level — NOAA Satellite Altimetry

- **URL:** `https://www.star.nesdis.noaa.gov/socd/lsa/SeaLevelRise/slr/slr_sla_gbl_free_all_66.csv`
- **Data:** Sea level anomaly (mm) from multiple satellites
- **Range:** 1993–2025 | **Granularity:** ~10-day intervals
- **Trend:** 3.17 mm/year

### 9. Sea Ice — NSIDC Arctic/Antarctic Extent

- **Arctic:** `https://noaadata.apps.nsidc.org/NOAA/G02135/north/daily/data/N_seaice_extent_daily_v4.0.csv`
- **Antarctic:** `S_seaice_extent_daily_v4.0.csv`
- **Data:** Ice extent (10⁶ km²)
- **Range:** **1978–2026** (daily) | **Format:** CSV

### 10. Sea Level — PSMSL Tide Gauges

- **URL:** `https://psmsl.org/data/obtaining/rlr.annual.data/{STATION_ID}.rlrdata`
- **Data:** Revised Local Reference sea level (mm)
- **Range:** Some stations to **1807** (219 years!) | **1,500+ stations**
- **Format:** Semicolon-delimited text

### 11. Oceanography — NOAA Tides & Currents

- **URL:** `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?...`
- **Products:** `hourly_height`, `water_temperature`, `air_temperature`, `wind`, `air_pressure`
- **Range:** Decades per station | **200+ US coastal stations**

### 12. Solar Energy — NASA POWER

- **URL:** `https://power.larc.nasa.gov/api/temporal/daily/point?...`
- **Data:** 139+ parameters: solar irradiance, temperature, humidity, wind, UV, aerosol
- **Range:** **1981–present** | **Any lat/lon globally**
- **Granularity:** Daily, Monthly, Annual

### 13. Seismology — USGS Earthquakes

- **URL:** `https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&...`
- **Data:** Magnitude, depth, location, felt reports, tsunami flag
- **Range:** **1900–present** | **Per-event** (aggregate to daily)

### 14. Cryptocurrency — CoinGecko

- **URL:** `https://api.coingecko.com/api/v3/coins/{id}/market_chart?vs_currency=usd&days=365`
- **Data:** Price, market cap, volume for 18,000+ coins
- **Range:** **365 days** (free tier limit) | **Daily**
- **Rate limit:** 10 req/min | **Coins:** BTC, ETH, SOL, DOGE, ADA, XRP, LTC, LINK, AVAX, DOT

### 15. Currency — Frankfurter (ECB)

- **URL:** `https://api.frankfurter.app/{start}..{end}?from=EUR&to=USD,GBP,JPY`
- **Data:** 30 currency pairs
- **Range:** **1999–present** (27 years) | **Daily** (business days)

### 16. COVID-19 — disease.sh

- **URL:** `https://disease.sh/v3/covid-19/historical/{country}?lastdays=all`
- **Data:** Daily cases, deaths, recovered for 231 countries
- **Range:** 2020-01-22 to 2023-03-09 (1,143 days) | **CORS:** Yes

### 17. Drug Safety — OpenFDA

- **URL:** `https://api.fda.gov/drug/event.json?count=receivedate`
- **Data:** Daily adverse drug event report counts
- **Range:** **1986–2025** (39 years!) | **Format:** JSON
- **Rate limit:** 240 req/min

### 18. Mortality — CDC NCHS

- **URL:** `https://data.cdc.gov/resource/muzy-jte6.json?$where=jurisdiction_of_occurrence='United States'`
- **Data:** Weekly deaths by 14 causes (heart, cancer, COVID, flu, diabetes, etc.)
- **Range:** 2017–present | **Granularity:** Weekly

### 19. Biodiversity — iNaturalist

- **URL:** `https://api.inaturalist.org/v1/observations/histogram?date_field=observed&interval=month&taxon_id=3`
- **Data:** Observation counts by species/location/time
- **Range:** 2008–present | **329M+ observations**

### 20. Biodiversity — GBIF

- **URL:** `https://api.gbif.org/v1/occurrence/counts/year?basisOfRecord=HUMAN_OBSERVATION`
- **Data:** Yearly observation counts, filterable by species/country
- **Range:** 1500–present (meaningful from 1900) | **3.76B records**

### 21. Public Interest — Wikipedia Pageviews

- **URL:** `https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/{article}/daily/{start}/{end}`
- **Data:** Daily views for any article
- **Range:** **2015-07–present** | Any Wikipedia language
- **Ideas:** Bitcoin, Climate_change, COVID-19, ChatGPT, Earthquake

### 22. Space Weather — NOAA Real-Time

- **Solar Wind:** `https://services.swpc.noaa.gov/products/solar-wind/plasma-7-day.json` (density, speed, temp)
- **Magnetic Field:** `https://services.swpc.noaa.gov/products/solar-wind/mag-7-day.json` (Bx, By, Bz)
- **Kp Index:** `https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json` (geomagnetic, 3-hourly)

### 23. GHG Emissions — Climate TRACE

- **URL:** `https://api.climatetrace.org/v6/country/emissions?countries=USA&since=2015&to=2022`
- **Data:** CO₂, CH₄, N₂O by country | **Range:** 2015–2022

---

## TIER 2: No Auth, Needs Server Proxy (no CORS)

### 24. Health — WHO Global Health Observatory

- **URL:** `https://ghoapi.azureedge.net/api/{IndicatorCode}?$filter=SpatialDim eq '{ISO3}'`
- **Data:** **3,056 indicators** — life expectancy, obesity, infant mortality, TB, HIV, tobacco use, etc.
- **Range:** 1990–2021 (yearly) | **190+ countries**

### 25. Economics — World Bank

- **URL:** `https://api.worldbank.org/v2/country/{ISO2}/indicator/{ID}?format=json&date=1960:2024`
- **Data:** **1,516 indicators** — GDP, population, CO₂, unemployment, life expectancy, internet users, etc.
- **Range:** **1960–2023** (yearly) | **264 countries**
- Key: `NY.GDP.MKTP.CD`, `SP.POP.TOTL`, `FP.CPI.TOTL.ZG`, `SL.UEM.TOTL.ZS`, `SP.DYN.LE00.IN`

### 26. Economics — Eurostat

- **URL:** `https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/{dataset}?startPeriod=2020&endPeriod=2024`
- **Data:** EU unemployment, GDP, tourism, energy, demographics, trade
- **Range:** 1990s–present | **Monthly/Quarterly/Annual**

### 27. Economics — IMF DataMapper

- **URL:** `https://www.imf.org/external/datamapper/api/v1/{indicator}/{country}`
- **Data:** GDP growth, inflation, unemployment, debt for all countries
- **Range:** 1980–2029 (includes forecasts)

### 28. Health — UN SDG Indicators

- **URL:** `https://unstats.un.org/sdgs/UNSDGAPIV5/v1/sdg/`
- **Data:** 231 Sustainable Development Goal indicators
- **Range:** 2000–present | **By country**

### 29. Space — NASA DONKI

- **URL:** `https://kauai.ccmc.gsfc.nasa.gov/DONKI/WS/get/FLR?startDate=...`
- **Endpoints:** Solar flares (FLR), CMEs (CME), geomagnetic storms (GST)
- **Range:** ~2010–present | **Per-event**

---

## TIER 3: Free API Key Required

### 30. US Economics — FRED

- **URL:** `https://api.stlouisfed.org/fred/series/observations?series_id=UNRATE&api_key={key}`
- **Data:** **800,000+ series** — Fed funds rate, GDP, CPI, housing, S&P 500, trade
- **Range:** Some from 1700s, most 1940s+ | **Daily to Annual**
- **Key:** Free registration at fred.stlouisfed.org

### 31. US Economics — BLS

- **URL:** `https://api.bls.gov/publicAPI/v2/timeseries/data/`
- **Data:** CPI (from 1913), unemployment (from 1948), PPI, wages
- **Rate limit:** 25/day without key, 500/day with free key

### 32. US Energy — EIA

- **URL:** `https://api.eia.gov/v2/`
- **Data:** Crude oil, gasoline, natural gas, electricity, renewables, emissions
- **Range:** 1949–present | **Daily to Annual**

### 33. Air Quality — OpenAQ v3

- **URL:** `https://api.openaq.org/v3/measurements`
- **Data:** PM2.5, PM10, O₃, NO₂, SO₂ from 65,000+ stations, 100+ countries
- **Range:** 2015–present | **Hourly**

### 34. Fire — NASA FIRMS

- **URL:** `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/...`
- **Data:** Fire detections (lat, lon, brightness, FRP)
- **Range:** 2000–present | **Near real-time**

### 35. Stocks — Alpha Vantage

- **URL:** `https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=...`
- **Data:** Stock prices, forex, crypto, technical indicators
- **Range:** 20+ years | **Rate limit:** 25/day free

---

## TIER 4: Technology & Academic

### 36. npm Downloads

- **URL:** `https://api.npmjs.org/downloads/range/{start}:{end}/{package}`
- **Data:** Daily download counts per package
- **Range:** ~2015–present | **No auth**

### 37. Academic — OpenAlex

- **URL:** `https://api.openalex.org/works?filter=concept.id:C154945302&group_by=publication_year`
- **Data:** Publication counts by year/field/institution
- **Range:** All academic history | **10 req/s**

### 38. Academic — Crossref

- **URL:** `https://api.crossref.org/works?filter=from-pub-date:2024-01,type:journal-article&rows=0`
- **Data:** Monthly publication volumes | **50 req/s**

### 39. Tech — Hacker News (Algolia)

- **URL:** `https://hn.algolia.com/api/v1/search?tags=story&numericFilters=created_at_i>X,created_at_i<Y&hitsPerPage=0`
- **Data:** Story counts per time window
- **Range:** 2006–present | **10,000 req/hr**

### 40. Tech — Stack Overflow

- **URL:** `https://api.stackexchange.com/2.3/questions?tagged=python&site=stackoverflow&filter=total`
- **Data:** Question counts by tag | **300 req/day** (no key)

### 41. Marine Biodiversity — OBIS

- **URL:** `https://api.obis.org/v3/facet?facets=date_year`
- **Data:** Marine species observation counts by year
- **Range:** 1800–present | **168M+ records**

---

## Interesting Correlation Ideas

### Climate System (monthly/yearly, 1958–present)
- CO₂ (NOAA Keeling) vs Global Temperature Anomaly
- CO₂ vs Arctic Sea Ice Extent
- Temperature vs Sea Level Rise
- Sunspot Number vs Global Temperature

### Weather vs Health (daily, 2020–present)
- Temperature vs COVID-19 cases
- Air Quality (PM2.5) vs CDC respiratory deaths
- Humidity vs Flu deaths

### Economics (yearly, 1960–2023)
- GDP per capita vs Life Expectancy (World Bank)
- Internet Users % vs GDP growth
- CO₂ emissions vs GDP
- Military spending vs Education spending

### Finance (daily, 1999–present)
- EUR/USD vs Bitcoin price
- Currency volatility vs Earthquake frequency (spurious!)
- BTC price vs Wikipedia "Bitcoin" pageviews

### Technology (daily, 2015–present)
- npm React downloads vs Stack Overflow React questions
- Wikipedia "ChatGPT" views vs OpenAlex AI papers
- HN story count vs npm package downloads

### Ecology (yearly, 1900–present)
- GBIF observation counts vs Global temperature
- Forest area % vs CO₂ emissions (World Bank)
- Sea surface temperature vs Marine biodiversity (OBIS)

---

## Implementation Priority

### Phase 1 (build now — no auth, clean JSON)
Open-Meteo (all), NOAA (solar, CO2, temp, sea level, ice), USGS, CoinGecko, Frankfurter, disease.sh, Wikipedia, World Bank, OpenFDA, iNaturalist, GBIF, npm, HN

### Phase 2 (add proxy for CORS)
WHO GHO, Eurostat, IMF, NASA DONKI, UN SDG, Climate TRACE, CDC

### Phase 3 (free API key)
FRED, BLS, EIA, OpenAQ, NASA FIRMS, Alpha Vantage

### Phase 4 (custom connector)
Any URL the user pastes — AI auto-detects fields
