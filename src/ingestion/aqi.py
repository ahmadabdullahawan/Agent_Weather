"""Computes the US EPA Air Quality Index from pollutant concentrations.

AQICN reports AQI directly (already on the EPA 0-500 scale), but
OpenWeather's Air Pollution API only gives raw concentrations (ug/m3) on
its own 1-5 index. To fuse the two sources onto one comparable scale, we
derive an EPA AQI from OpenWeather's PM2.5/PM10 concentrations ourselves,
using the standard EPA piecewise-linear breakpoint tables. The official
AQI is the max of the per-pollutant sub-indices; we use PM2.5 and PM10,
the two pollutants that dominate AQI in this region.

This uses instantaneous concentrations rather than the EPA's official
rolling-average windows (24h for PM2.5/PM10), which is a simplification
appropriate for a forecasting exercise, not regulatory reporting.
"""

# (C_low, C_high, I_low, I_high) breakpoints, EPA 2024 tables.
PM25_BREAKPOINTS = [
    (0.0, 9.0, 0, 50),
    (9.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 125.4, 151, 200),
    (125.5, 225.4, 201, 300),
    (225.5, 325.4, 301, 500),
]

PM10_BREAKPOINTS = [
    (0, 54, 0, 50),
    (55, 154, 51, 100),
    (155, 254, 101, 150),
    (255, 354, 151, 200),
    (355, 424, 201, 300),
    (425, 604, 301, 500),
]


def _sub_index(conc: float, breakpoints: list[tuple[float, float, int, int]], decimals: int) -> float:
    """EPA's official algorithm requires truncating (not rounding) the
    concentration to a fixed precision before breakpoint lookup — the
    published breakpoint tables use adjacent edges like "...54" then
    "55..." that only partition the real line once the input is
    pre-truncated to that same precision. Skipping this step leaves gaps
    between breakpoints (e.g. PM10 = 54.7 matches no range at all), and
    naively falling back to "clamp to worst category" for anything that
    doesn't match turns ordinary mid-range values into false 500s."""
    if conc is None:
        return None
    factor = 10**decimals
    truncated = int(conc * factor) / factor
    for c_low, c_high, i_low, i_high in breakpoints:
        if c_low <= truncated <= c_high:
            return (i_high - i_low) / (c_high - c_low) * (truncated - c_low) + i_low
    if truncated > breakpoints[-1][1]:
        return breakpoints[-1][3]
    return breakpoints[0][2]


def compute_aqi(pm2_5: float, pm10: float) -> float:
    sub_indices = [
        i
        for i in (
            _sub_index(pm2_5, PM25_BREAKPOINTS, decimals=1),
            _sub_index(pm10, PM10_BREAKPOINTS, decimals=0),
        )
        if i is not None
    ]
    return max(sub_indices) if sub_indices else None
