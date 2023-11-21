import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates

from io import StringIO

from dateutil import tz
from datetime import datetime, timedelta

from noaa_sdk import NOAA

class Location(object):
    """Class that represents a location in the world.

    Attributes
    ----------
    name : string
        name of location
    lat : float
        latitude of location
    lon : float
        longitude of location
    noaa : noaa_sdk.NOAA
        API wrapper object
    """

    def __init__(self, name, lat, lon):
        """Create a Location.
        
        Parameters
        ----------
        name : string
            name of location
        lat : float
            latitude of location
        lon : float
            longitude of location
        """

        self._name = name
        self._lat = lat
        self._lon = lon
        self.noaa = NOAA(user_agent="CornCast testing <arjmukerji@gmail.com>", show_uri=True)
    
    def __str__(self):
        return f"{self._name} ({self._lat}, {self._lon})"

    def get_obs(self, start, end):
        """Return weather observations nearest this location. 
        
        Parameters
        ----------
        start : datetime
            beginning of time period we want observations from
        end : datetime
            end of time period we want observations from
        """

        return self.noaa.get_observations_by_lat_lon(self._lat, self._lon, start.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S'))
    
    def get_forecast(self):
        """Return weather forecast nearest this location."""

        res = self.noaa.points_forecast(self._lat, self._lon, type='forecastHourly')

        if 'status' in res and res['status'] == 503 and 'detail' in res:
            raise Exception('Status: {}, NOAA API Error Response: {}'.format(
                res['status'], res['detail']))
        elif 'properties' not in res:
            raise Exception(
                '"properties" attribute not found. Possible response json changes')
        elif 'properties' in res and 'periods' not in res['properties'] and type != 'forecastGridData':
            raise Exception(
                '"periods" attribute not found. Possible response json changes')
        # if type == 'forecastGridData':
        #     return res['properties']
        #print(res)
        return res['properties']['periods']

def reduce_obs(obs_df):
    """Given a data frame of weather observations from the NOAA API, return only the columns we want.
    
    Parameters
    ----------
    obs_df : pandas.DataFrame
        Data Frame wrapping raw observations from NOAA API

    Returns
    -------
    df_reduced : pandas.DataFrame
        Data Frame with all the same rows and only the relevant columns retained
    """

    keep_cols = ['station', 'timestamp']
    keep_cols.extend([col for col in obs_df.columns if ('temperature' in col or 'dewpoint' in col or 'precipitation' in col or 'wind' in col) and 'qualityControl' not in col])
    df_reduced = obs_df[keep_cols]
    return df_reduced

def calc_max_temp(obs_df, col='temperature.value'):
    """Return the maximum temperature in a data frame of weather observations."""

    return obs_df[col].max()

def calc_min_temp(obs_df, col='temperature.value'):
    """Return the minimum temperature in a data frame of weather observations."""

    return obs_df[col].min()

def freezethaw_yn(obs_df):
    """Was there a freeze-thaw cycle in this dataset of observations?"""

    if calc_max_temp(obs_df) > 0 and calc_min_temp(obs_df) < 0:
        return True
    
    else:
        return False

def plot_obs(df, **kwargs):
    """Make a line plot of temperature observations.
    
    Parameters
    ----------
    df : pandas.DataFrame
        Data Frame of observations from NOAA API.
    """

    ax = sns.lineplot(data=df, **kwargs)
    #locator = ticker.MultipleLocator(base=20)
    locator = mdates.HourLocator(byhour=[6,18])
    ax.xaxis.set_major_locator(locator)
    ax.set_xticks(ax.get_xticks(), ax.get_xticklabels(), rotation=45, ha='right')
    ax.set_xlabel("Date and time")
    ax.set_ylabel("Air Temperature (F)")
    return ax

def plot_forecast(df, **kwargs):
    """Make a line plot of the hourly forecast provided by the NOAA API.
    
    Parameters
    ----------
    df : pandas.DataFrame
        Data Frame of forecast periods from NOAA API.
    """

    ax = sns.lineplot(data=df, **kwargs)
    #locator = ticker.MultipleLocator(base=20)
    locator = mdates.HourLocator(byhour=[6,18])
    ax.xaxis.set_major_locator(locator)
    ax.set_xticks(ax.get_xticks(), ax.get_xticklabels(), rotation=45, ha='right')
    ax.set_xlabel("Date and time")
    ax.set_ylabel("Air Temperature (F)")
    return ax

def make_obs_df(loc, start, end, obs_tcol='temperature.value'):
    """Make data frame of weather station obs for a location from NOAA API

    Parameters
    ----------
    loc : Location
        Location to fetch observations for
    start : datetime
        beginning of time period we want observations from
    end : datetime
        end of time period we want observations from
    """

    obs_df_full = pd.concat([pd.json_normalize(o) for o in loc.get_obs(start, end)], ignore_index=True)
    # get rid of extraneous columns and rows with no temperature value
    obs_df_reduced = reduce_obs(obs_df_full).dropna(axis=0, subset=[obs_tcol])
    print(f"Timestamp before: {obs_df_reduced.timestamp.iloc[0]}")
    # observations come in local time at the station, but 
    obs_df_reduced.timestamp = pd.to_datetime(obs_df_reduced.timestamp, utc=True)
    print(f"Timestamp after: {obs_df_reduced.timestamp.iloc[0]}")
    obs_df_reduced['date'] = obs_df_reduced.timestamp.dt.floor('1D')
    obs_df_reduced['datehour'] = obs_df_reduced.timestamp.dt.floor('1H')
    # ensure we are only returning obs from one station
    assert(len(obs_df_reduced.station.unique())==1)
    # create a column for temp in Fahrenheit
    if obs_tcol == 'temperature.value':
        obs_tunit_col = obs_df_reduced['temperature.unitCode']
        if (obs_tunit_col == 'wmoUnit:degC').all() or (obs_tunit_col == 'C').all():
            obs_df_reduced['tempF'] = (obs_df_reduced[obs_tcol]*(9/5))+32
        else:
            obs_df_reduced['tempF'] = obs_df_reduced[obs_tcol]
    else:
        obs_df_reduced['tempF'] = obs_df_reduced[obs_tcol]
    
    return obs_df_reduced

def parse_windspeed(speeds):
    """Parse the wind speeds returned by NOAA forecast API
    
    Parameters
    ----------
    speeds : pd.Series
        Series of wind speeds, each like "25 mph"
    """

    if "mph" in speeds:
        speed_int = speeds.split(" mph")[0]
        unit = 'mph'
    elif "kmh" in speeds:
        speed_int = speeds.split(" kmh")[0]
        unit = 'wmoUnit:km_h-1'
    elif "kmph" in speeds:
        speed_int = speeds.split(" kmph")[0]
        unit = 'wmoUnit:km_h-1'
    else:
        raise ValueError("Input does not look like a windspeed!")
    return pd.Series([speed_int, unit], index=['windSpeedInt', 'windSpeedUnit'])

def make_forecast_df(loc):
    """Make a data frame from the NOAA API hourly forecast for a location

    Parameters
    ----------
    loc : Location
        Location to fetch observations for
    """

    obs_df_full = pd.DataFrame(pd.json_normalize(loc.get_forecast()))
    obs_df_full.startTime = pd.to_datetime(obs_df_full.startTime, utc=True)
    obs_df_full.endTime = pd.to_datetime(obs_df_full.endTime, utc=True)
    obs_df_full = obs_df_full.join(obs_df_full.windSpeed.apply(parse_windspeed))
    obs_df_full.windSpeedInt = pd.to_numeric(obs_df_full.windSpeedInt) #.astype(np.int32)
    #obs_df_full.info()
    # define which columns to keep and return
    cols_to_keep = ['startTime', 'endTime', 'isDaytime', 'temperature', 'temperatureUnit', 'windSpeed', 'windSpeedInt', 'windSpeedUnit', 'windDirection', 'shortForecast']
    cols_to_keep.extend([col for col in obs_df_full.columns if 'dewpoint' in col or 'relativeHumidity' in col or 'probabilityOfPrecipitation' in col])
    return obs_df_full[cols_to_keep]

def corn_forecast(loc):
    """Corn Forecast function.
    
    Parameters
    ----------
    loc : Location
        Location this corn forecast is for
    """

    # set up some variables
    now = datetime.now()
    obs_period = timedelta(days=5)
    start = now-obs_period
    end = now
    tcol = 'tempF'

    # start the forecast figure and get axes
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    fig.suptitle(f"Corn forecast for {loc}")

    # get and plot observations
    df = make_obs_df(loc, start, end)
    station_name = df.station.iloc[0]
    # Make sure the temperature column exists as expected
    assert(tcol in df.columns)
    # Smooth data - take the mean of each hour's observations and return just those values (1 per hour)
    hour_means = df.groupby(['datehour'])[tcol].mean().reset_index()
    ax1 = plot_obs(hour_means[::-1], x='datehour', y=tcol, ax=ax1)
    ax1.set_title(f"{station_name} observed")

    # Group by day and compute some stats
    day_df = df.groupby(['date'], as_index=False).apply(lambda x: pd.Series([freezethaw_yn(x)], index=['freeze_thaw']))
    print(f"Freeze-thaw cycle detected on {day_df.freeze_thaw.sum()} days.")

    # Get and plot forecast nearest this location
    fcst_df = make_forecast_df(loc)
    ax2 = plot_forecast(fcst_df, x='startTime', y='temperature', ax=ax2)
    ax2.set_title(f"Forecast")

    # Show the forecast figure and close it
    plt.show(fig)
    plt.close('all)')

    # Return data frames to fiddle with
    return (df, day_df, fcst_df)
