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