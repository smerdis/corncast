import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates

from dateutil import parser, tz
from datetime import datetime, date, time, timedelta

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

    def get_obs(self, noaa, start, end):
        """Return weather observations nearest this location. 
        
        Parameters
        ----------
        noaa : noaa_sdk.NOAA
            noaa_sdk.NOAA api wrapper object
        start : datetime
            beginning of time period we want observations from
        end : datetime
            end of time period we want observations from
        """

        return noaa.get_observations_by_lat_lon(self._lat, self._lon, start.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S'))
    
def reduce_obs(obs_df):
    """Given a data frame of weather observations from the NOAA API, calculate quantities of interest.
    
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
    keep_cols.extend([col for col in obs_df.columns if 'temperature' in col or 'dewpoint' in col or 'precipitation' in col or 'wind' in col])
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
    
def corn_forecast(loc):
    """Corn Forecast function.
    
    Parameters
    ----------
    loc : Location
        Location this corn forecast is for
    """

    n = NOAA(user_agent="CornCast testing <arjmukerji@gmail.com>", show_uri=True)

    now = datetime.now(tz=tz.UTC)
    obs_period = timedelta(days=5)
    start = now-obs_period
    end = now

    obs_list = [pd.json_normalize(o) for o in loc.get_obs(n, start, end)]
    obs_df_full = pd.concat(obs_list, ignore_index=True)
    obs_df_reduced = reduce_obs(obs_df_full).dropna(axis=0, subset=['temperature.value'])
    obs_df_reduced.timestamp = pd.to_datetime(obs_df_reduced.timestamp)
    assert(len(obs_df_reduced.station.unique())==1)
    station_name = obs_df_reduced.station.iloc[0]

    disp_cols = ['station', 'timestamp', 'temperature.value', 'dewpoint.value', 'precipitationLast3Hours.value']

    df = obs_df_reduced
    sns.lineplot(data=df[::-1], x='timestamp', y='temperature.value')
    ax = plt.gca()
    #locator = ticker.MultipleLocator(base=20)
    locator = mdates.HourLocator(byhour=[6,18])
    ax.xaxis.set_major_locator(locator)
    ax.set_xticks(ax.get_xticks(), ax.get_xticklabels(), rotation=45, ha='right')
    ax.set_xlabel("Date and time")
    ax.set_ylabel("Air Temperature (C)")
    ax.set_title(f"{station_name} observations")
    plt.show()
    plt.close('all')


    return df[disp_cols]