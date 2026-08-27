import numpy as np
import pandas as pd


def generate_germany_solar_profile(index):
    # 1. Setup Timeframe (8760 hours)
    max_MW = 1.0

    # 2. Seasonal Modulation (Winter vs Summer)
    # Day 172 (June 21) is peak; Day 355 (Dec 21) is minimum
    day_of_year = index.dayofyear
    seasonal_factor = 0.5 * (1 + np.cos(2 * np.pi * (day_of_year - 172) / 365))
    # Adjusting so winter isn't zero, but significantly lower (~15-20% of summer)
    seasonal_factor = 0.15 + 0.85 * seasonal_factor

    # 3. Daily Solar Curve (Sine wave during daylight)
    # Germany Latitude (approx 51°N) varies daylight from ~8h (winter) to ~16h (summer)
    daylight_hours = 8 + 8 * seasonal_factor

    solar_profile = []
    for i, t in enumerate(index):
        hour = t.hour
        # Center of day is 12:00
        sunrise = 13 - (daylight_hours[i] / 2.5)
        sunset = 13 + (daylight_hours[i] / 2.5)

        if sunrise < hour < sunset:
            # Sine wave peaked at noon
            daily_sine = np.sin(np.pi * (hour - sunrise) / (sunset - sunrise))
            # Combine with seasonal strength and system size
            # 0.85 is a generic performance ratio (losses)
            output = daily_sine * seasonal_factor[i] * max_MW
            solar_profile.append(max(0, output))
        else:
            solar_profile.append(0)

    profile = pd.Series(index=index, data=solar_profile)

    return profile
