"""
Functions and data structures for generating past and future weather along with info
about energy being generated from PH panels.
"""
import random
from collections import namedtuple
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd


random.seed(42)


class RandomWeatherGenerator:
    SUNNY: str = 'sunny'
    PARTLY_CLOUDY: str = 'partly_cloudy'
    CLOUDY: str = 'cloudy'
    RAINY: str = 'rainy'
    
    WEATHER_PROBS = {
        SUNNY: 0.4,
        PARTLY_CLOUDY: 0.3,
        CLOUDY: 0.2,
        RAINY: 0.1,
    }
    WEATHER_TRANSITIONS = pd.DataFrame({
        SUNNY: [0.4, 0.25, 0.2, 0.05],
        PARTLY_CLOUDY: [0.2, 0.3, 0.4, 0.1],
        CLOUDY: [0.05, 0.4, 0.4, 0.15],
        RAINY: [0.05, 0.1, 0.3, 0.55],
    }, index=[SUNNY, PARTLY_CLOUDY, CLOUDY, RAINY])
    
    @classmethod
    def get_random_weather(cls) -> str:
        return random.choices(
            population=list(cls.WEATHER_PROBS.keys()),
            weights=list(cls.WEATHER_PROBS.values()),
        )[0]

    @classmethod
    def get_next_weather(cls, current_weather: str) -> str:
        row = cls.WEATHER_TRANSITIONS[current_weather]
        return random.choices(
            population=row.index,
            weights=row.values,
        )[0]

# Parameters of a Gaussian distribution to sample the base temperature at particular
# weather types
WEATHER_TEMPERATURE_DISTRIBUTIONS = {
    RandomWeatherGenerator.SUNNY: {'mu': 25, 'sigma': 2},
    RandomWeatherGenerator.PARTLY_CLOUDY: {'mu': 20, 'sigma': 2},
    RandomWeatherGenerator.CLOUDY: {'mu': 18, 'sigma': 3},
    RandomWeatherGenerator.RAINY: {'mu': 15, 'sigma': 5},
}

# Simple hourly factor to simulate diurnal cycle (peak at 14h/2pm, low at 4h/4am)
# The values represent the temperature deviation (in Celsius) from the daily mean.
HOUR_FACTORS: dict[int, float] = {
    0: -2.0, 1: -2.5, 2: -3.0, 3: -3.2, 4: -3.0, 5: -2.5, 6: -1.5,
    7: -0.5, 8: 0.5, 9: 1.5, 10: 2.5, 11: 3.0, 12: 3.5, 13: 4.0, 
    14: 4.5, 15: 4.0, 16: 3.5, 17: 2.5, 18: 1.5, 19: 0.5, 20: -0.5, 
    21: -1.0, 22: -1.5, 23: -2.0
}
        
WEATHER_MULTIPLIERS = {
    RandomWeatherGenerator.SUNNY: 1.0,
    RandomWeatherGenerator.PARTLY_CLOUDY: 0.6,
    RandomWeatherGenerator.CLOUDY: 0.3,
    RandomWeatherGenerator.RAINY: 0.1,
}

# Fixed base target mean humidity for each weather type (0-100%)
HUMIDITY_TARGETS: dict[str, float] = {
    RandomWeatherGenerator.SUNNY: 40.0,
    RandomWeatherGenerator.PARTLY_CLOUDY: 60.0,
    RandomWeatherGenerator.CLOUDY: 75.0,
    RandomWeatherGenerator.RAINY: 92.0,
}


def get_temperature_c_for_weather(
    weather_name: str,
    hour_of_day: int,
    current_temperature: float | None = None,
) -> float:
    """
    Generates temperature by factoring in the weather type, previous temperature,
    and a simple hourly factor for the daily cycle.
    """
    gauss_params = WEATHER_TEMPERATURE_DISTRIBUTIONS[weather_name]
    
    # 1. Calculate the base mean for the hour
    hourly_adjustment = HOUR_FACTORS.get(hour_of_day, 0.0)
    target_mu = gauss_params['mu'] + hourly_adjustment
    
    # 2. Smooth the transition between the previous temperature and the new target
    final_mu = target_mu
    if current_temperature is not None:
        # Simple smoothing: 1 part current temp, 3 parts target MU
        final_mu = (current_temperature + target_mu * 3) / 4
        
    # 3. Generate temperature using the standard deviation for the weather type
    # We use a reduced sigma for hourly steps to prevent wild swings.
    return random.gauss(
        mu=final_mu,
        sigma=gauss_params['sigma'] * 0.4,
    )
    
    
def get_humidity_for_weather(
    weather_name: str,
    current_humidity: float | None,
) -> float:
    """
    Generates humidity based primarily on weather type and smoothing from 
    the previous hour's humidity.
    """
    target_mean = HUMIDITY_TARGETS[weather_name]
    
    # 1. Smoothing/Inheritance from previous humidity
    final_mu = target_mean
    if current_humidity is not None:
        # Smooth transition: 1 part target mean, 2 parts current humidity
        final_mu = (target_mean + current_humidity * 2) / 3

    # 2. Generate humidity with slight random variation
    # Use a small sigma to ensure humidity remains relatively stable
    new_humidity = random.gauss(mu=final_mu, sigma=2.0)
    
    # 3. Clip the result to a valid humidity range
    return max(0.0, min(100.0, new_humidity))


SolarInfo = namedtuple('SolarInfo', 'kwh_generation irradiance')


def get_solar_irradiance_and_kwh_generation(weather_name: str, temperature_c: float, hour_of_day: int) -> SolarInfo:
    """
    Generates solar irradiance and energy generation per hour.
    """
    if hour_of_day < 6 or hour_of_day > 18:
        return SolarInfo(kwh_generation=0, irradiance=0)

    hour_factor = 1 - abs(hour_of_day - 12) / 6  # Peak at hour 12

    base_kwh_generation = 5.0 * hour_factor  # Max 5 kWh at peak
    
    # Apply weather multiplier
    kwh_generation = base_kwh_generation * WEATHER_MULTIPLIERS[weather_name]
    
    # Add some random variation
    kwh_generation *= random.uniform(0.8, 1.2)
    kwh_generation = max(0, kwh_generation)
    
    # TODO[MD]: Add impact from temperature on the efficiency of the PV panel
        
    # Solar irradiance calculation
    irradiance = 800 * hour_factor * WEATHER_MULTIPLIERS[weather_name] if kwh_generation > 0 else 0
    
    return SolarInfo(kwh_generation=kwh_generation, irradiance=irradiance)


def get_wind_speed(weather_name: str, hour_of_day: int) -> float:
    """
    Generates a fairly simplistic wind speed (m/s) based on weather type and 
    a minor time-of-day adjustment.
    """
    
    # 1. Baseline Wind Speed Parameters (Meters per second)
    # Mean (mu) and Standard Deviation (sigma) for each weather type
    WIND_SPEED_DISTRIBUTIONS: dict[str, dict[str, float]] = {
        RandomWeatherGenerator.SUNNY: {'mu': 3.0, 'sigma': 1.0},
        RandomWeatherGenerator.PARTLY_CLOUDY: {'mu': 4.5, 'sigma': 1.5},
        RandomWeatherGenerator.CLOUDY: {'mu': 6.0, 'sigma': 2.0},
        RandomWeatherGenerator.RAINY: {'mu': 8.0, 'sigma': 2.5},
    }
    
    params = WIND_SPEED_DISTRIBUTIONS[weather_name]
    
    # 2. Time-of-Day Adjustment (Slightly higher winds during daytime hours)
    # We use a simple factor that peaks around midday (12)
    daytime_factor = 0.0
    if 8 <= hour_of_day <= 18: # Daytime hours
        daytime_factor = 1.0 * (1 - abs(hour_of_day - 13) / 5) # Max bonus of 1.0 m/s around 1 PM
    
    # 3. Calculate Final Mean and Generate Wind Speed
    final_mu = params['mu'] + daytime_factor
    
    # Generate value using Gaussian distribution
    wind_speed = random.gauss(mu=final_mu, sigma=params['sigma'])
    
    # 4. Ensure wind speed is not negative
    return max(0.0, wind_speed)

    
@dataclass
class WeatherRecord:
    date_time: datetime
    weather_name: str
    humidity: float
    wind_speed: float
    temperature_c: float
    irradiance: float
    kwh_generated: float
    wind_speed: float
    

def weather_hour_by_hour_gen(
    start_date: datetime,
    num_days: int,
) -> WeatherRecord:
    """
    Generator function for generating 
    
    :param start_date: Description
    :type start_date: datetime
    :param num_days: Description
    :type num_days: int
    :return: Description
    :rtype: WeatherRecord
    """
    current_hour = start_date.hour
    current_weather = RandomWeatherGenerator.get_random_weather()
    current_temperature_c = get_temperature_c_for_weather(current_weather, current_hour)
    current_humidity = get_humidity_for_weather(current_weather, current_humidity=None)
    current_solar_info = get_solar_irradiance_and_kwh_generation(current_weather, current_temperature_c, current_hour)
    current_wind_speed = get_wind_speed(current_weather, current_hour)
    
    for day in range(num_days):
        for hour in range(24):
            timestamp = (start_date + timedelta(days=day, hours=hour)).replace(minute=0, second=0, microsecond=0)
            
            yield WeatherRecord(
                date_time=timestamp,
                weather_name=current_weather,
                temperature_c=current_temperature_c,
                humidity=current_humidity,
                irradiance=current_solar_info.irradiance,
                kwh_generated=current_solar_info.kwh_generation,
                wind_speed=current_wind_speed,
            )
            
            current_weather = RandomWeatherGenerator.get_next_weather(current_weather)
            current_temperature_c = get_temperature_c_for_weather(current_weather, hour, current_temperature_c)
            current_humidity = get_humidity_for_weather(current_weather, current_humidity)
            current_solar_info = get_solar_irradiance_and_kwh_generation(current_weather, current_temperature_c, hour)
            current_wind_speed = get_wind_speed(current_weather, hour)


def plot_weather(weather_gen) -> None:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    
    datetimes = []
    humidities = []
    irradiance = []
    kwh_generations = []
    temperatures_c = []
    weather_names = []
    wind_speeds = []

    for row in weather_gen:
        datetimes.append(row.date_time)
        humidities.append(row.humidity)
        irradiance.append(row.irradiance)
        kwh_generations.append(row.kwh_generated)
        temperatures_c.append(row.temperature_c)
        weather_names.append(row.weather_name)
        wind_speeds.append(row.wind_speed)

    # 1. Combine the lists into a pandas DataFrame for easy indexing and plotting
    data_dict = {
        'temperature_c': temperatures_c,
        'humidity': humidities,
        'irradiance': irradiance,
        'kwh_generated': kwh_generations,
        'weather_name': weather_names,
        'wind_speed': wind_speeds,
    }
    df = pd.DataFrame(data_dict, index=datetimes)
    df.index.name = 'date_time'

    # 2. Define colors for visualizing different weather types (assuming typical names)
    WEATHER_COLORS: dict[str, str] = {
        'sunny': '#FFC300',         # Yellow/Gold
        'partly_cloudy': '#A9CCE3', # Light Blue/Gray
        'cloudy': '#7F8C8D',        # Gray
        'rainy': '#4A6178',         # Dark Blue/Gray
    }

    # 3. Create the multi-subplot figure
    fig, axes = plt.subplots(nrows=4, ncols=1, figsize=(15, 14), sharex=True)
    fig.suptitle('Simulated Weather Data Analysis', fontsize=16)

    # --- Plot 1: Temperature and Weather Type ---
    axes[0].plot(df.index, df['temperature_c'], label='Temperature ($^\circ$C)', color='darkred', linewidth=2)
    axes[0].set_ylabel('Temp ($^\circ$C)')
    axes[0].grid(True, linestyle='--', alpha=0.5)
    axes[0].legend(loc='upper left')

    # Add colored background patches for weather type visualization
    if not df.empty:
        current_weather = df['weather_name'].iloc[0]
        start_index = df.index[0]

        for i in range(1, len(df)):
            if df['weather_name'].iloc[i] != current_weather:
                axes[0].axvspan(start_index, df.index[i], facecolor=WEATHER_COLORS.get(current_weather, 'white'), alpha=0.25, edgecolor='none')
                current_weather = df['weather_name'].iloc[i]
                start_index = df.index[i]
        # Draw the final patch
        axes[0].axvspan(start_index, df.index[-1], facecolor=WEATHER_COLORS.get(current_weather, 'white'), alpha=0.25, edgecolor='none')

        # Add legend for weather colors using patches
        patch_list = [
            mpatches.Patch(color=WEATHER_COLORS.get(w, 'gray'), alpha=0.25, label=w.replace('_', ' ').title()) 
            for w in sorted(df['weather_name'].unique())
        ]
        axes[0].legend(handles=patch_list, loc='upper right', ncol=2, title='Weather State')


    # --- Plot 2: Humidity and Wind Speed ---
    axes[1].plot(df.index, df['humidity'], label='Humidity (%)', color='blue', linewidth=1.5)
    axes[1].set_ylabel('Humidity (%)')
    axes[1].grid(True, linestyle='--', alpha=0.5)

    # Use secondary Y-axis for Wind Speed
    ax2 = axes[1].twinx()
    ax2.plot(df.index, df['wind_speed'], label='Wind Speed (m/s)', color='teal', linestyle=':', linewidth=1.5)
    ax2.set_ylabel('Wind Speed (m/s)', color='teal')
    ax2.tick_params(axis='y', labelcolor='teal')
    axes[1].legend(loc='upper left')
    ax2.legend(loc='upper right')


    # --- Plot 3: Solar Generation (KWh) ---
    axes[2].plot(df.index, df['kwh_generated'], label='KWh Generated', color='orange', linewidth=2)
    axes[2].fill_between(df.index, df['kwh_generated'], color='orange', alpha=0.3)
    axes[2].set_ylabel('Solar Energy (KWh/h)')
    axes[2].grid(True, linestyle='--', alpha=0.5)
    axes[2].legend(loc='upper left')


    # --- Plot 4: Irradiance (W/m²) ---
    axes[3].plot(df.index, df['irradiance'], label='Irradiance (W/m$^2$)', color='gold', linewidth=1.5)
    axes[3].set_ylabel('Irradiance (W/m$^2$)')
    axes[3].grid(True, linestyle='--', alpha=0.5)
    axes[3].legend(loc='upper left')

    # Final adjustments
    axes[-1].set_xlabel('Date and Time') # Only set X-label on the bottom plot
    plt.xticks(rotation=45)
    plt.tight_layout(rect=[0, 0.03, 1, 0.98])
    plt.show()
