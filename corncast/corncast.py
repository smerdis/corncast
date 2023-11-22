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
    
def analyze_obs(obs_df, tcol='tempF'):
    """Analyze a period of observations in Fahrenheit and compute summary stats."""

    above = obs_df[tcol].max() > 32
    below = obs_df[tcol].min() < 32
    return pd.Series({'max_above_freezing': above, 'max_below_freezing': below})

def dt_axis_ang(plot_func):
    """Decorator that angles datetime x-axis labels at 45 degrees and labels the axis."""

    def wrapper(**args):
        ax = plot_func(**args)
        ax.set_xticks(ax.get_xticks(), ax.get_xticklabels(), rotation=45, ha='right')
        ax.set_xlabel("Date and time")
        return ax
    return wrapper

def dt_axis(plot_func):
    """Decorator that locates datetime x-axis ticks at particular hours."""

    def wrapper(**args):
        ax = plot_func(**args)
        locator = mdates.HourLocator(byhour=[6,18])
        ax.xaxis.set_major_locator(locator)
        return ax
    return wrapper

@dt_axis_ang
@dt_axis
def plot_hourly(**kwargs):
    ax = sns.lineplot(**kwargs)
    ax.axhline(y=32, linestyle='dotted')
    return ax

@dt_axis_ang
def dec_cat_plot(**kwargs):
    ax = sns.pointplot(**kwargs)
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
    obs_df_reduced['date_nearest12'] = obs_df_reduced.timestamp.dt.floor('12H')
    obs_df_reduced['date_nearest6'] = obs_df_reduced.timestamp.dt.floor('6H')
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
    out_df = obs_df_full[cols_to_keep].copy()
    out_df['date_nearest12'] = out_df.startTime.dt.floor('12H')
    out_df['date_nearest6'] = out_df.startTime.dt.floor('6H')
    return out_df

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
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7, 4), sharey=True)
    fig.suptitle(f"Data for {loc}")

    # get and plot observations
    df = make_obs_df(loc, start, end)
    station_name = df.station.iloc[0]
    # Make sure the temperature column exists as expected
    assert(tcol in df.columns)
    # Smooth data - take the mean of each hour's observations and return just those values (1 per hour)
    hour_means = df.groupby(['datehour'])[tcol].mean().reset_index()
    ax1 = plot_hourly(data=hour_means[::-1], x='datehour', y=tcol, ax=ax1)
    ax1.set_title(f"{station_name} observed data")

    # Get and plot forecast nearest this location
    fcst_df = make_forecast_df(loc)
    ax2 = plot_hourly(data=fcst_df, x='startTime', y='temperature', ax=ax2)
    ax2.set_title(f"Forecast data")

    # Show the forecast figure and close it
    plt.show(fig)
    plt.close('all)')

    # Calculate and show the categorical forecast for periods (6 or 24h initially)
    fig_cat, (ax_6h, ax_fcst_6h) = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
    fig_cat.suptitle(f"Categorical corn forecast for {loc}")

    # Group by day and compute some stats
    obs_24h_df = df.groupby(['date'], as_index=False).apply(lambda x: pd.Series([freezethaw_yn(x)], index=['freeze_thaw']))
    print(f"Freeze-thaw cycle detected on {obs_24h_df.freeze_thaw.sum()} days:\n{obs_24h_df[obs_24h_df.freeze_thaw]}")

    # Group by 6h
    obs_6h_df = df.groupby(['date_nearest6'], as_index=False).apply(analyze_obs)
    print(obs_6h_df)
    ax_6h = dec_cat_plot(data=obs_6h_df[::-1], x='date_nearest6', y='max_above_freezing', ax=ax_6h)

    plt.show(fig_cat)
    plt.close('all')

    # Return data frames to fiddle with
    return (df, obs_24h_df, obs_6h_df, fcst_df)
