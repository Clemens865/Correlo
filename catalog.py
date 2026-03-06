"""API Catalog — all curated data sources for the Correlation Explorer."""

LOCATIONS = [
    {"id": "vienna", "name": "Vienna, AT", "lat": 48.21, "lon": 16.37, "country": "AT"},
    {"id": "london", "name": "London, UK", "lat": 51.51, "lon": -0.13, "country": "GB"},
    {"id": "nyc", "name": "New York, US", "lat": 40.71, "lon": -74.01, "country": "US"},
    {"id": "tokyo", "name": "Tokyo, JP", "lat": 35.68, "lon": 139.69, "country": "JP"},
    {"id": "sydney", "name": "Sydney, AU", "lat": -33.87, "lon": 151.21, "country": "AU"},
    {"id": "berlin", "name": "Berlin, DE", "lat": 52.52, "lon": 13.41, "country": "DE"},
    {"id": "paris", "name": "Paris, FR", "lat": 48.86, "lon": 2.35, "country": "FR"},
    {"id": "mumbai", "name": "Mumbai, IN", "lat": 19.08, "lon": 72.88, "country": "IN"},
    {"id": "saopaulo", "name": "São Paulo, BR", "lat": -23.55, "lon": -46.63, "country": "BR"},
    {"id": "cairo", "name": "Cairo, EG", "lat": 30.04, "lon": 31.24, "country": "WLD"},
    {"id": "la", "name": "Los Angeles, US", "lat": 34.05, "lon": -118.24, "country": "US"},
    {"id": "singapore", "name": "Singapore, SG", "lat": 1.35, "lon": 103.82, "country": "SG"},
    {"id": "beijing", "name": "Beijing, CN", "lat": 39.90, "lon": 116.40, "country": "CN"},
    {"id": "moscow", "name": "Moscow, RU", "lat": 55.76, "lon": 37.62, "country": "WLD"},
    {"id": "nairobi", "name": "Nairobi, KE", "lat": -1.29, "lon": 36.82, "country": "WLD"},
]

COUNTRIES = [
    {"code": "WLD", "name": "World"},
    {"code": "AT", "name": "Austria"}, {"code": "DE", "name": "Germany"},
    {"code": "US", "name": "USA"}, {"code": "GB", "name": "United Kingdom"},
    {"code": "FR", "name": "France"}, {"code": "JP", "name": "Japan"},
    {"code": "CN", "name": "China"}, {"code": "IN", "name": "India"},
    {"code": "BR", "name": "Brazil"}, {"code": "AU", "name": "Australia"},
    {"code": "CA", "name": "Canada"}, {"code": "CH", "name": "Switzerland"},
    {"code": "KR", "name": "South Korea"}, {"code": "SG", "name": "Singapore"},
    {"code": "ZA", "name": "South Africa"}, {"code": "NG", "name": "Nigeria"},
    {"code": "EU", "name": "European Union"},
]

PERIODS = [
    {"value": "7d", "label": "7 days", "days": 7},
    {"value": "30d", "label": "30 days", "days": 30},
    {"value": "90d", "label": "90 days", "days": 90},
    {"value": "1y", "label": "1 year", "days": 365},
    {"value": "2y", "label": "2 years", "days": 730},
    {"value": "5y", "label": "5 years", "days": 1825},
    {"value": "10y", "label": "10 years", "days": 3650},
    {"value": "25y", "label": "25 years", "days": 9125},
    {"value": "50y", "label": "50 years", "days": 18250},
    {"value": "max", "label": "Max available", "days": 36500},
]

# Each entry: id, name, category, desc, unit, granularity,
# location_type: "latlon" | "country" | "global"
# max_history: approx days of data available
# fetch_type: how the server fetches it
# fetch_config: parameters for the fetch handler

CATALOG = [
    # =========================================================================
    # WEATHER (Open-Meteo) — location: latlon, up to 85 years
    # =========================================================================
    *[{
        "id": f"meteo-{var.replace('_', '-')}", "name": name,
        "category": "Weather", "desc": desc, "unit": unit,
        "granularity": "daily", "location_type": "latlon",
        "max_history_days": 31000,  # ~85 years
        "fetch_type": "open_meteo_archive",
        "fetch_config": {"variable": var},
    } for var, name, desc, unit in [
        ("temperature_2m_max", "Temperature (max)", "Daily max temperature", "°C"),
        ("temperature_2m_min", "Temperature (min)", "Daily min temperature", "°C"),
        ("temperature_2m_mean", "Temperature (mean)", "Daily mean temperature", "°C"),
        ("apparent_temperature_max", "Feels-Like Temp (max)", "Apparent temperature max", "°C"),
        ("precipitation_sum", "Precipitation", "Daily precipitation sum", "mm"),
        ("rain_sum", "Rain", "Daily rain (excl. snow)", "mm"),
        ("snowfall_sum", "Snowfall", "Daily snowfall", "cm"),
        ("wind_speed_10m_max", "Wind Speed (max)", "Daily max wind speed", "km/h"),
        ("wind_gusts_10m_max", "Wind Gusts (max)", "Daily max wind gusts", "km/h"),
        ("shortwave_radiation_sum", "Solar Radiation", "Daily solar radiation sum", "MJ/m²"),
        ("et0_fao_evapotranspiration", "Evapotranspiration", "Reference evapotranspiration", "mm"),
        ("sunshine_duration", "Sunshine Duration", "Daily sunshine hours", "hours"),
    ]],

    # =========================================================================
    # AIR QUALITY (Open-Meteo) — location: latlon, ~4 years
    # =========================================================================
    *[{
        "id": f"aq-{var.replace('_', '-')}", "name": name,
        "category": "Air Quality", "desc": desc, "unit": unit,
        "granularity": "daily", "location_type": "latlon",
        "max_history_days": 1800,
        "fetch_type": "open_meteo_airquality",
        "fetch_config": {"variable": var},
    } for var, name, desc, unit in [
        ("pm2_5", "PM2.5", "Fine particles", "μg/m³"),
        ("pm10", "PM10", "Coarse particles", "μg/m³"),
        ("ozone", "Ozone (O₃)", "Ground-level ozone", "μg/m³"),
        ("nitrogen_dioxide", "NO₂", "Nitrogen dioxide", "μg/m³"),
        ("sulphur_dioxide", "SO₂", "Sulphur dioxide", "μg/m³"),
        ("carbon_monoxide", "CO", "Carbon monoxide", "μg/m³"),
        ("european_aqi", "EU Air Quality Index", "European AQI", "index"),
        ("us_aqi", "US Air Quality Index", "US AQI", "index"),
    ]],

    # =========================================================================
    # MARINE (Open-Meteo) — location: latlon (coastal), recent
    # =========================================================================
    *[{
        "id": f"marine-{var.replace('_', '-')}", "name": name,
        "category": "Marine", "desc": desc, "unit": unit,
        "granularity": "daily", "location_type": "latlon",
        "max_history_days": 90,
        "fetch_type": "open_meteo_marine",
        "fetch_config": {"variable": var},
    } for var, name, desc, unit in [
        ("wave_height_max", "Wave Height (max)", "Max wave height", "m"),
        ("wave_period_max", "Wave Period (max)", "Max wave period", "s"),
    ]],

    # =========================================================================
    # FLOOD (Open-Meteo) — location: latlon, 40 years
    # =========================================================================
    {
        "id": "flood-discharge", "name": "River Discharge",
        "category": "Hydrology", "desc": "River discharge volume", "unit": "m³/s",
        "granularity": "daily", "location_type": "latlon",
        "max_history_days": 14600,
        "fetch_type": "open_meteo_flood",
        "fetch_config": {"variable": "river_discharge"},
    },

    # =========================================================================
    # CLIMATE — NOAA (global, no location needed)
    # =========================================================================
    {
        "id": "noaa-temp-anomaly", "name": "Global Temperature Anomaly",
        "category": "Climate", "desc": "Global land+ocean temp anomaly (base 1901-2000)", "unit": "°C",
        "granularity": "monthly", "location_type": "global",
        "max_history_days": 53000,  # 1880
        "fetch_type": "noaa_temp_anomaly", "fetch_config": {},
    },
    {
        "id": "noaa-co2", "name": "CO₂ Concentration (Mauna Loa)",
        "category": "Climate", "desc": "Monthly avg CO₂ (Keeling Curve)", "unit": "ppm",
        "granularity": "monthly", "location_type": "global",
        "max_history_days": 25000,  # 1958
        "fetch_type": "noaa_co2", "fetch_config": {"gas": "co2", "scope": "mlo"},
    },
    {
        "id": "noaa-co2-global", "name": "CO₂ Concentration (Global)",
        "category": "Climate", "desc": "Global mean CO₂", "unit": "ppm",
        "granularity": "monthly", "location_type": "global",
        "max_history_days": 17000,  # 1979
        "fetch_type": "noaa_co2", "fetch_config": {"gas": "co2", "scope": "gl"},
    },
    {
        "id": "noaa-ch4", "name": "Methane (CH₄) Global",
        "category": "Climate", "desc": "Global mean methane", "unit": "ppb",
        "granularity": "monthly", "location_type": "global",
        "max_history_days": 15700,  # 1983
        "fetch_type": "noaa_co2", "fetch_config": {"gas": "ch4", "scope": "gl"},
    },
    {
        "id": "noaa-sea-level", "name": "Global Sea Level Rise",
        "category": "Climate", "desc": "Satellite altimetry sea level anomaly", "unit": "mm",
        "granularity": "10-day", "location_type": "global",
        "max_history_days": 12000,  # 1993
        "fetch_type": "noaa_sea_level", "fetch_config": {},
    },
    {
        "id": "nsidc-arctic-ice", "name": "Arctic Sea Ice Extent",
        "category": "Climate", "desc": "Northern hemisphere sea ice", "unit": "M km²",
        "granularity": "daily", "location_type": "global",
        "max_history_days": 17500,  # 1978
        "fetch_type": "nsidc_ice", "fetch_config": {"hemisphere": "north"},
    },

    # =========================================================================
    # SOLAR / SPACE — NOAA
    # =========================================================================
    {
        "id": "noaa-sunspots", "name": "Sunspot Number",
        "category": "Space", "desc": "Monthly sunspot number (SSN)", "unit": "count",
        "granularity": "monthly", "location_type": "global",
        "max_history_days": 101000,  # 1749!
        "fetch_type": "noaa_sunspots", "fetch_config": {},
    },

    # =========================================================================
    # NASA POWER — location: latlon, 1981+
    # =========================================================================
    *[{
        "id": f"power-{param.lower().replace('_', '-')}", "name": name,
        "category": "Energy/Climate", "desc": desc, "unit": unit,
        "granularity": "daily", "location_type": "latlon",
        "max_history_days": 16400,  # 1981
        "fetch_type": "nasa_power",
        "fetch_config": {"parameter": param},
    } for param, name, desc, unit in [
        ("ALLSKY_SFC_SW_DWN", "Solar Irradiance (All-Sky)", "Surface shortwave downward irradiance", "kWh/m²/day"),
        ("T2M", "Temperature (NASA)", "2m air temperature", "°C"),
        ("PRECTOTCORR", "Precipitation (NASA)", "Corrected total precipitation", "mm/day"),
    ]],

    # =========================================================================
    # SEISMOLOGY — USGS
    # =========================================================================
    {
        "id": "usgs-mag", "name": "Earthquake Magnitude (max/day)",
        "category": "Seismology", "desc": "Strongest earthquake per day (M2.5+)", "unit": "magnitude",
        "granularity": "daily", "location_type": "global",
        "max_history_days": 36500,
        "fetch_type": "usgs_daily", "fetch_config": {"mode": "max"},
    },
    {
        "id": "usgs-count", "name": "Earthquake Count (daily)",
        "category": "Seismology", "desc": "Number of M2.5+ earthquakes per day", "unit": "count",
        "granularity": "daily", "location_type": "global",
        "max_history_days": 36500,
        "fetch_type": "usgs_daily", "fetch_config": {"mode": "count"},
    },

    # =========================================================================
    # CRYPTO — CoinGecko (365 days free)
    # =========================================================================
    *[{
        "id": f"crypto-{coin}", "name": f"{name} Price",
        "category": "Crypto", "desc": f"Daily {name} price in USD", "unit": "USD",
        "granularity": "daily", "location_type": "global",
        "max_history_days": 365,
        "fetch_type": "coingecko",
        "fetch_config": {"coin": coin, "field": "prices"},
    } for coin, name in [
        ("bitcoin", "Bitcoin"), ("ethereum", "Ethereum"), ("solana", "Solana"),
        ("dogecoin", "Dogecoin"), ("cardano", "Cardano"), ("ripple", "Ripple"),
        ("litecoin", "Litecoin"), ("chainlink", "Chainlink"),
    ]],
    {
        "id": "crypto-btc-volume", "name": "Bitcoin Trading Volume",
        "category": "Crypto", "desc": "Daily BTC trading volume", "unit": "USD",
        "granularity": "daily", "location_type": "global",
        "max_history_days": 365,
        "fetch_type": "coingecko",
        "fetch_config": {"coin": "bitcoin", "field": "total_volumes"},
    },

    # =========================================================================
    # CURRENCY — Frankfurter (1999+)
    # =========================================================================
    *[{
        "id": f"fx-{cur.lower()}", "name": f"EUR/{cur} Exchange Rate",
        "category": "Currency", "desc": f"Daily EUR to {cur} rate", "unit": cur,
        "granularity": "daily", "location_type": "global",
        "max_history_days": 9500,  # 1999
        "fetch_type": "frankfurter",
        "fetch_config": {"currency": cur},
    } for cur in ["USD", "GBP", "JPY", "CHF", "AUD", "CAD", "CNY", "KRW", "BRL", "INR"]],

    # =========================================================================
    # WORLD BANK — country-level, yearly, 1960+
    # =========================================================================
    *[{
        "id": f"wb-{code.lower().replace('.', '-')}", "name": name,
        "category": "Economics", "desc": desc, "unit": unit,
        "granularity": "yearly", "location_type": "country",
        "max_history_days": 23000,  # ~1960
        "fetch_type": "world_bank",
        "fetch_config": {"indicator": code},
    } for code, name, desc, unit in [
        ("NY.GDP.MKTP.CD", "GDP", "Gross Domestic Product", "Current USD"),
        ("NY.GDP.PCAP.CD", "GDP per Capita", "GDP per capita", "Current USD"),
        ("NY.GDP.MKTP.KD.ZG", "GDP Growth", "Annual GDP growth rate", "%"),
        ("SP.POP.TOTL", "Population", "Total population", "people"),
        ("SP.POP.GROW", "Population Growth", "Annual population growth", "%"),
        ("FP.CPI.TOTL.ZG", "Inflation (CPI)", "Consumer price inflation", "%"),
        ("SL.UEM.TOTL.ZS", "Unemployment", "Unemployment rate", "% labor force"),
        ("SP.DYN.LE00.IN", "Life Expectancy", "Life expectancy at birth", "years"),
        ("SP.DYN.TFRT.IN", "Fertility Rate", "Births per woman", "births"),
        ("SH.DYN.MORT", "Child Mortality", "Under-5 mortality rate", "per 1,000"),
        ("IT.NET.USER.ZS", "Internet Users", "Internet users", "% population"),
        ("IT.CEL.SETS.P2", "Mobile Subscriptions", "Mobile phone subscriptions", "per 100"),
        ("EG.USE.PCAP.KG.OE", "Energy Use", "Energy use per capita", "kg oil equiv"),
        ("EG.ELC.ACCS.ZS", "Electricity Access", "Access to electricity", "%"),
        ("EN.GHG.CO2.MT.CE.AR5", "CO₂ Emissions", "Total CO₂ emissions", "Mt CO₂e"),
        ("AG.LND.FRST.ZS", "Forest Area", "Forest area", "% of land"),
        ("NE.TRD.GNFS.ZS", "Trade", "Trade as share of GDP", "% GDP"),
        ("MS.MIL.XPND.GD.ZS", "Military Spending", "Military expenditure", "% GDP"),
        ("SH.XPD.CHEX.GD.ZS", "Health Spending", "Health expenditure", "% GDP"),
        ("SE.XPD.TOTL.GD.ZS", "Education Spending", "Education expenditure", "% GDP"),
        ("SP.URB.TOTL.IN.ZS", "Urbanization", "Urban population share", "%"),
        ("SI.POV.GINI", "GINI Index", "Income inequality", "0-100"),
        ("AG.PRD.FOOD.XD", "Food Production Index", "Food production", "index 2014-16=100"),
    ]],

    # =========================================================================
    # COVID-19 — disease.sh
    # =========================================================================
    *[{
        "id": f"covid-{metric}", "name": f"COVID-19 {metric.title()} (Global)",
        "category": "Health", "desc": f"Daily new COVID-19 {metric} globally", "unit": "count",
        "granularity": "daily", "location_type": "global",
        "max_history_days": 1200,
        "fetch_type": "covid", "fetch_config": {"metric": metric, "country": "all"},
    } for metric in ["cases", "deaths", "recovered"]],

    # =========================================================================
    # DRUG SAFETY — OpenFDA
    # =========================================================================
    {
        "id": "fda-drug-events", "name": "Drug Adverse Events",
        "category": "Health", "desc": "Daily FDA adverse drug event reports", "unit": "reports/day",
        "granularity": "daily", "location_type": "global",
        "max_history_days": 14000,  # 1986
        "fetch_type": "openfda", "fetch_config": {},
    },

    # =========================================================================
    # UK ENERGY — Carbon Intensity
    # =========================================================================
    {
        "id": "uk-carbon", "name": "UK Carbon Intensity",
        "category": "Energy", "desc": "UK grid carbon intensity (daily avg)", "unit": "gCO₂/kWh",
        "granularity": "daily", "location_type": "global",
        "max_history_days": 3000,  # 2018
        "fetch_type": "uk_carbon", "fetch_config": {},
    },

    # =========================================================================
    # WIKIPEDIA — Pageviews
    # =========================================================================
    *[{
        "id": f"wiki-{article.lower().replace(' ', '-').replace('_', '-')[:20]}",
        "name": f"Wikipedia: {article.replace('_', ' ')}",
        "category": "Public Interest", "desc": f"Daily pageviews for '{article.replace('_', ' ')}'", "unit": "views/day",
        "granularity": "daily", "location_type": "global",
        "max_history_days": 3900,  # 2015
        "fetch_type": "wikipedia", "fetch_config": {"article": article},
    } for article in [
        "Bitcoin", "Ethereum", "Climate_change", "Artificial_intelligence",
        "COVID-19_pandemic", "Inflation", "Earthquake", "ChatGPT",
        "Machine_learning", "Renewable_energy",
    ]],

    # =========================================================================
    # BIODIVERSITY — iNaturalist
    # =========================================================================
    *[{
        "id": f"inat-{key}", "name": f"iNaturalist: {name}",
        "category": "Ecology", "desc": f"Monthly {name.lower()} observations worldwide", "unit": "observations",
        "granularity": "monthly", "location_type": "global",
        "max_history_days": 6200,  # 2008
        "fetch_type": "inaturalist", "fetch_config": {"taxon_id": tid},
    } for key, name, tid in [
        ("birds", "Birds", 3), ("insects", "Insects", 47158),
        ("plants", "Plants", 47126), ("mammals", "Mammals", 40151),
    ]],

    # =========================================================================
    # TECHNOLOGY — npm, HN
    # =========================================================================
    *[{
        "id": f"npm-{pkg}", "name": f"npm: {pkg}",
        "category": "Technology", "desc": f"Daily downloads of npm package '{pkg}'", "unit": "downloads/day",
        "granularity": "daily", "location_type": "global",
        "max_history_days": 547,
        "fetch_type": "npm", "fetch_config": {"package": pkg},
    } for pkg in ["react", "vue", "svelte", "typescript", "openai"]],

    # =========================================================================
    # EUROSTAT — EU/country-level, monthly/quarterly/annual
    # =========================================================================
    *[{
        "id": f"estat-{code.lower().replace('_', '-')}", "name": name,
        "category": "Economics/EU", "desc": desc, "unit": unit,
        "granularity": gran, "location_type": "country",
        "max_history_days": max_days,
        "fetch_type": "eurostat",
        "fetch_config": {"dataset": code, "filter_params": filt},
    } for code, name, desc, unit, gran, max_days, filt in [
        ("prc_hicp_midx", "EU Inflation Index (HICP)", "Harmonised CPI", "index (2015=100)",
         "monthly", 9000, {"coicop": "CP00", "unit": "I15"}),
        ("une_rt_m", "EU Unemployment Rate", "Monthly unemployment rate", "%",
         "monthly", 9000, {"s_adj": "SA", "age": "TOTAL", "sex": "T", "unit": "PC_ACT"}),
        ("sts_inpr_m", "EU Industrial Production", "Industrial production index", "index",
         "monthly", 7300, {"s_adj": "SCA", "nace_r2": "B-D", "unit": "I15"}),
        ("tour_occ_nim", "EU Tourist Nights", "Nights spent in accommodation", "nights",
         "monthly", 5500, {"nace_r2": "I551-I553", "unit": "NR", "c_resid": "TOTAL"}),
    ]],

    # =========================================================================
    # BLS — US economic data, monthly
    # =========================================================================
    *[{
        "id": f"bls-{key}", "name": name,
        "category": "Economics/US", "desc": desc, "unit": unit,
        "granularity": "monthly", "location_type": "global",
        "max_history_days": 7300,  # ~20 years
        "fetch_type": "bls",
        "fetch_config": {"series_id": series_id},
    } for key, name, desc, unit, series_id in [
        ("cpi", "US CPI (All Items)", "Consumer Price Index for All Urban Consumers", "index",
         "CUUR0000SA0"),
        ("unemployment", "US Unemployment Rate", "Civilian unemployment rate", "%",
         "LNS14000000"),
        ("nonfarm", "US Nonfarm Payrolls", "Total nonfarm employment (thousands)", "thousands",
         "CES0000000001"),
    ]],

    # =========================================================================
    # UN SDG — Sustainable Development Goals
    # =========================================================================
    *[{
        "id": f"sdg-{indicator.replace('.', '-')}", "name": name,
        "category": "Development", "desc": desc, "unit": unit,
        "granularity": "yearly", "location_type": "country",
        "max_history_days": 9500,  # ~2000
        "fetch_type": "un_sdg",
        "fetch_config": {"indicator": indicator},
    } for indicator, name, desc, unit in [
        ("8.1.1", "GDP Growth per Capita", "Annual growth rate of real GDP per capita", "%"),
        ("3.2.1", "Under-5 Mortality", "Under-five mortality rate", "per 1,000 live births"),
        ("7.2.1", "Renewable Energy Share", "Renewable energy share in total consumption", "%"),
        ("9.5.1", "R&D Expenditure", "Research and development expenditure as % of GDP", "% GDP"),
    ]],

    # =========================================================================
    # ECB — European Central Bank (exchange rates, interest rates)
    # =========================================================================
    *[{
        "id": f"ecb-{key}", "name": name,
        "category": "Finance/ECB", "desc": desc, "unit": unit,
        "granularity": gran, "location_type": "global",
        "max_history_days": max_days,
        "fetch_type": "ecb",
        "fetch_config": {"flow": flow, "key": ecb_key},
    } for key, name, desc, unit, gran, max_days, flow, ecb_key in [
        ("eurusd-m", "ECB EUR/USD (monthly)", "ECB monthly EUR/USD rate", "USD",
         "monthly", 9500, "EXR", "M.USD.EUR.SP00.A"),
        ("eurgbp-m", "ECB EUR/GBP (monthly)", "ECB monthly EUR/GBP rate", "GBP",
         "monthly", 9500, "EXR", "M.GBP.EUR.SP00.A"),
        ("eurjpy-m", "ECB EUR/JPY (monthly)", "ECB monthly EUR/JPY rate", "JPY",
         "monthly", 9500, "EXR", "M.JPY.EUR.SP00.A"),
        ("eurchf-m", "ECB EUR/CHF (monthly)", "ECB monthly EUR/CHF rate", "CHF",
         "monthly", 9500, "EXR", "M.CHF.EUR.SP00.A"),
        ("euribor-3m", "EURIBOR 3-Month", "3-month Euro interbank offered rate", "%",
         "monthly", 9500, "FM", "M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA"),
        ("euribor-12m", "EURIBOR 12-Month", "12-month EURIBOR", "%",
         "monthly", 9500, "FM", "M.U2.EUR.RT.MM.EURIBOR1YD_.HSTA"),
    ]],

    # =========================================================================
    # UK ONS — Office for National Statistics
    # =========================================================================
    *[{
        "id": f"ons-{key}", "name": name,
        "category": "Economics/UK", "desc": desc, "unit": unit,
        "granularity": gran, "location_type": "global",
        "max_history_days": max_days,
        "fetch_type": "ons",
        "fetch_config": {"series_id": series_id, "dataset_id": dataset_id, "granularity": gran},
    } for key, name, desc, unit, gran, max_days, series_id, dataset_id in [
        ("cpi", "UK CPI Inflation Rate", "UK consumer price inflation (annual rate)", "%",
         "monthly", 13000, "L55O", "mm23"),
        ("gdp-qoq", "UK GDP Growth (QoQ)", "UK GDP quarter-on-quarter growth", "%",
         "quarterly", 18000, "IHYQ", "qna"),
        ("unemployment", "UK Unemployment Rate", "UK unemployment rate", "%",
         "monthly", 13000, "MGSX", "lms"),
    ]],

    # =========================================================================
    # INE Spain — National Statistics
    # =========================================================================
    *[{
        "id": f"ine-{key}", "name": name,
        "category": "Economics/ES", "desc": desc, "unit": unit,
        "granularity": "monthly", "location_type": "global",
        "max_history_days": 9000,
        "fetch_type": "ine_spain",
        "fetch_config": {"series_code": code},
    } for key, name, desc, unit, code in [
        ("cpi", "Spain CPI (Annual Variation)", "Spanish CPI annual variation", "%", "IPC251856"),
        ("cpi-food", "Spain CPI Food", "Spanish food price annual variation", "%", "IPC206449"),
    ]],

    # =========================================================================
    # GeoSphere Austria (formerly ZAMG) — Austrian weather stations
    # =========================================================================
    *[{
        "id": f"geosphere-{key}", "name": f"Austria: {name}",
        "category": "Weather/Austria", "desc": desc, "unit": unit,
        "granularity": "daily", "location_type": "global",
        "max_history_days": 36500,
        "fetch_type": "geosphere",
        "fetch_config": {"parameter": param, "station_id": "5904"},
    } for key, name, desc, unit, param in [
        ("temp-mean", "Mean Temperature (Vienna)", "Daily mean temp — Vienna Hohe Warte", "°C", "tl_mittel"),
        ("temp-max", "Max Temperature (Vienna)", "Daily max temp — Vienna Hohe Warte", "°C", "tlmax"),
        ("precip", "Precipitation (Vienna)", "Daily precipitation — Vienna Hohe Warte", "mm", "rr"),
    ]],

    # =========================================================================
    # US TREASURY — Fiscal Data
    # =========================================================================
    {
        "id": "treasury-debt", "name": "US National Debt",
        "category": "Economics/US", "desc": "US total public debt outstanding", "unit": "Trillion USD",
        "granularity": "daily", "location_type": "global",
        "max_history_days": 11000,
        "fetch_type": "us_treasury",
        "fetch_config": {"endpoint": "accounting/od/debt_to_penny", "field": "tot_pub_debt_out_amt"},
    },

    # =========================================================================
    # BRAZIL — Banco Central (BCB)
    # =========================================================================
    *[{
        "id": f"bcb-{key}", "name": name,
        "category": "Economics/BR", "desc": desc, "unit": unit,
        "granularity": gran, "location_type": "global",
        "max_history_days": max_days,
        "fetch_type": "bcb_sgs",
        "fetch_config": {"series_id": sid},
    } for key, name, desc, unit, gran, max_days, sid in [
        ("ipca", "Brazil IPCA Inflation", "Monthly consumer price inflation", "%",
         "monthly", 11000, 433),
        ("selic", "Brazil Selic Rate", "Central bank target rate", "%",
         "daily", 9000, 11),
        ("usdbrl", "USD/BRL Exchange Rate", "Daily USD to BRL rate", "BRL",
         "daily", 9000, 1),
    ]],

    # =========================================================================
    # CANADA — Bank of Canada
    # =========================================================================
    *[{
        "id": f"boc-{key}", "name": name,
        "category": "Economics/CA", "desc": desc, "unit": unit,
        "granularity": "daily", "location_type": "global",
        "max_history_days": 3650,
        "fetch_type": "bank_of_canada",
        "fetch_config": {"series": series},
    } for key, name, desc, unit, series in [
        ("usdcad", "USD/CAD Exchange Rate", "Daily USD/CAD rate", "CAD", "FXUSDCAD"),
        ("eurcad", "EUR/CAD Exchange Rate", "Daily EUR/CAD rate", "CAD", "FXEURCAD"),
    ]],

    # =========================================================================
    # ARGENTINA — datos.gob.ar
    # =========================================================================
    {
        "id": "arg-usdars", "name": "USD/ARS Exchange Rate",
        "category": "Economics/AR", "desc": "Daily USD to Argentine Peso rate", "unit": "ARS",
        "granularity": "daily", "location_type": "global",
        "max_history_days": 3650,
        "fetch_type": "argentina_series",
        "fetch_config": {"series_id": "168.1_T_CAMBIOR_D_0_0_26"},
    },

    # =========================================================================
    # CDC — US Health Data
    # =========================================================================
    {
        "id": "cdc-excess-deaths", "name": "US Excess Deaths",
        "category": "Health/US", "desc": "Weekly excess deaths estimate", "unit": "deaths/week",
        "granularity": "weekly", "location_type": "global",
        "max_history_days": 3000,
        "fetch_type": "cdc_soda",
        "fetch_config": {"dataset": "xkkf-xrst", "date_field": "week_ending_date", "value_field": "excess_estimate", "filter": "state='United States' AND outcome='All causes' AND type='Predicted (weighted)'"},
    },

    # =========================================================================
    # GLOBAL WARMING API (global-warming.org)
    # =========================================================================
    {
        "id": "gw-n2o", "name": "Nitrous Oxide (N₂O)",
        "category": "Climate", "desc": "Global N₂O concentration", "unit": "ppb",
        "granularity": "monthly", "location_type": "global",
        "max_history_days": 9000,
        "fetch_type": "global_warming",
        "fetch_config": {"endpoint": "nitrous-oxide-api", "key": "nitrous", "value_field": "average"},
    },

    # =========================================================================
    # WHO Global Health Observatory
    # =========================================================================
    *[{
        "id": f"who-{key}", "name": name,
        "category": "Health", "desc": desc, "unit": unit,
        "granularity": "yearly", "location_type": "country",
        "max_history_days": 11000,
        "fetch_type": "who_gho",
        "fetch_config": {"indicator": indicator, "dim1": dim1},
    } for key, name, desc, unit, indicator, dim1 in [
        ("life-exp", "Life Expectancy (WHO)", "Healthy life expectancy at birth", "years", "WHOSIS_000001", "SEX_BTSX"),
        ("neonatal-mort", "Neonatal Mortality (WHO)", "Neonatal mortality rate", "per 1,000 live births", "MDG_0000000003", ""),
        ("immunization-dpt", "DPT Immunization (WHO)", "DPT3 immunization coverage among 1yr olds", "%", "WHS4_100", ""),
        ("physicians", "Physicians Density (WHO)", "Medical doctors per 10,000 population", "per 10,000", "HWF_0001", ""),
    ]],

    # =========================================================================
    # UNHCR Refugee Data
    # =========================================================================
    {
        "id": "unhcr-refugees", "name": "UNHCR Refugees (Syria origin)",
        "category": "Demographics", "desc": "Syrian refugee population worldwide", "unit": "persons",
        "granularity": "yearly", "location_type": "global",
        "max_history_days": 20000,
        "fetch_type": "unhcr",
        "fetch_config": {"metric": "refugees"},
    },

    # =========================================================================
    # PyPI Stats (Python package downloads)
    # =========================================================================
    *[{
        "id": f"pypi-{key}", "name": f"PyPI: {pkg}",
        "category": "Technology", "desc": f"Daily downloads for {pkg} Python package", "unit": "downloads/day",
        "granularity": "daily", "location_type": "global",
        "max_history_days": 180,
        "fetch_type": "pypi",
        "fetch_config": {"package": pkg},
    } for key, pkg in [
        ("requests", "requests"),
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("fastapi", "fastapi"),
        ("langchain", "langchain"),
    ]],

    # =========================================================================
    # NASA Near-Earth Objects
    # =========================================================================
    {
        "id": "nasa-neo", "name": "Near-Earth Asteroids",
        "category": "Space", "desc": "Daily count of near-Earth asteroid approaches", "unit": "objects/day",
        "granularity": "daily", "location_type": "global",
        "max_history_days": 7,
        "fetch_type": "nasa_neo",
        "fetch_config": {},
    },
]


def get_catalog_for_api():
    """Return catalog entries without internal fetch details."""
    return [{
        "id": api["id"],
        "name": api["name"],
        "category": api["category"],
        "desc": api["desc"],
        "unit": api["unit"],
        "granularity": api["granularity"],
        "location_type": api["location_type"],
        "max_history_days": api["max_history_days"],
    } for api in CATALOG]


def get_api_by_id(api_id: str) -> dict | None:
    return next((a for a in CATALOG if a["id"] == api_id), None)
