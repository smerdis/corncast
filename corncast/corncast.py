import pandas as pd
import warnings
from datetime import datetime, timedelta
from tzfpy import get_tz
from noaa_sdk import NOAA


class Location(object):
    """
    Class that represents a location in the world.

    Attributes
    ----------
    name : str
        Name of the location.
    lat : float
        Latitude of the location.
    lon : float
        Longitude of the location.
    noaa : noaa_sdk.NOAA
        API wrapper object for NOAA.
    snotels : list of str
        List of SNOTEL stations that represent this Location.
    tz : str
        Timezone of the location. e.g. 'America/Los_Angeles'
    """

    def __init__(self, name, lat, lon, snotels=[]):
        """
        Initialize a Location object.

        Parameters
        ----------
        name : str
            Name of the location.
        lat : float
            Latitude of the location.
        lon : float
            Longitude of the location.
        snotels : list of str, optional
            List of SNOTEL stations that represent this Location, by default [].
        tz : str
            Timezone of the location. e.g. 'America/Los_Angeles'
        """

        self.name = name
        self._lat = lat
        self._lon = lon
        self.noaa = NOAA(
            user_agent="CornCast testing <arjmukerji@gmail.com>", show_uri=True
        )
        self._snotels = snotels
        self.tz = get_tz(lon, lat)

    def __str__(self):
        """
        Return a string representation of the Location object.

        Returns
        -------
        str
            String representation of the Location object.
        """
        return f"{self.name} ({self._lat:.3f}, {self._lon:.3f})"

    def lat(self):
        """
        Get the latitude of the location.

        Returns
        -------
        float
            Latitude of the location.
        """
        return self._lat

    def lon(self):
        """
        Get the longitude of the location.

        Returns
        -------
        float
            Longitude of the location.
        """
        return self._lon

    def get_snotels(self):
        """
        Get the list of SNOTEL stations that represent this Location.

        Returns
        -------
        list of str
            List of SNOTEL stations that represent this Location.
        """
        return self._snotels

    def get_obs(self, start, end):
        """
        Return a generator yielding weather observations nearest this location for a given time period.

        This function calls the `get_observations_by_lat_lon` method of the `noaa` object,
        passing in the latitude and longitude of the current instance, and the start and end times formatted as strings.
        The `get_observations_by_lat_lon` method is expected to return a generator that yields dictionaries containing weather observations.

        Parameters
        ----------
        start : datetime
            The datetime representing the beginning of the time period for which we want observations.
            This is converted to a string in the format "YYYY-MM-DD HH:MM:SS" before being passed to the `get_observations_by_lat_lon` method.
        end : datetime
            The datetime representing the end of the time period for which we want observations.
            This is converted to a string in the format "YYYY-MM-DD HH:MM:SS" before being passed to the `get_observations_by_lat_lon` method.

        Returns
        -------
        generator
            A generator that yields dictionaries. Each dictionary represents weather observations nearest this location for a specific time within the given time period.

        Notes
        -----
        The `get_observations_by_lat_lon` method of the `noaa` object is expected to use the `yield` keyword, hence this function returns a generator.
        """

        # NOAA API function relies on yield(), so returns a Generator
        return self.noaa.get_observations_by_lat_lon(
            self._lat,
            self._lon,
            start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    def get_forecast(self, full=False):
        """
        Return weather forecast nearest this location.

        Parameters
        ----------
        full : bool, optional
            If True, return the full 'properties' dict returned by NOAA, by default False.
            If False, return only the 'periods' element of this dict.

        Returns
        -------
        dict or list of dict
            Weather forecast nearest this location. The type of the return value depends on the 'full' parameter.
        """

        res = self.noaa.points_forecast(self._lat, self._lon, type="forecastHourly")

        if "status" in res and res["status"] == 503 and "detail" in res:
            raise Exception(
                "Status: {}, NOAA API Error Response: {}".format(
                    res["status"], res["detail"]
                )
            )
        elif "properties" not in res:
            raise Exception(
                '"properties" attribute not found. Possible response json changes'
            )
        elif (
            "properties" in res
            and "periods" not in res["properties"]
            and type != "forecastGridData"
        ):
            raise Exception(
                '"periods" attribute not found. Possible response json changes'
            )
        if full:
            return res["properties"]
        else:
            return res["properties"]["periods"]


def reduce_obs(obs_df):
    """
    Reduces the given DataFrame of weather observations from the NOAA API by retaining only the relevant columns for further analysis.

    The function keeps the 'station' and 'timestamp' columns,
    as well as any columns that contain the words 'temperature', 'dewpoint', 'precipitation', 'wind', or 'elevation'.
    It discards any columns that contain the word 'qualityControl'.

    Parameters
    ----------
    obs_df : pandas.DataFrame
        DataFrame containing raw weather observations from the NOAA API. Each row represents a single observation, and each column represents a different attribute of the observation.

    Returns
    -------
    pandas.DataFrame
        A new DataFrame that contains all the same rows as the input DataFrame, but only the relevant columns. The columns are in the same order as in the input DataFrame.
    """

    keep_cols = ["station", "timestamp"]
    keep_cols.extend(
        [
            col
            for col in obs_df.columns
            if (
                "temperature" in col
                or "dewpoint" in col
                or "precipitation" in col
                or "wind" in col
                or "elevation" in col
            )
            and "qualityControl" not in col
        ]
    )
    df_reduced = obs_df[keep_cols]
    return df_reduced


def analyze_obs(obs_df, tcol="tempF"):
    """
    Analyze a DataFrame of weather observations and compute summary statistics.

    This function calculates whether there was a freeze/thaw cycle (i.e., the temperature went both above and below 32 degrees Fahrenheit),
    the total precipitation over the last 3 hours, the maximum probability of precipitation, and the mean wind speed.
    It returns these statistics as a pandas Series.

    Parameters
    ----------
    obs_df : pandas.DataFrame
        DataFrame of hourly weather observations. Each row represents a single observation, and each column represents a different attribute of the observation.
        The DataFrame must contain a column for the temperature, and it may optionally contain columns for the precipitation over the last 3 hours, the probability of precipitation, and the wind speed.

    tcol : str, optional
        The name of the column in `obs_df` that contains the temperature data, by default "tempF".

    Returns
    -------
    pandas.Series
        A Series of summary statistics. The index of the Series is the names of the statistics, and the values are the calculated statistics.
        The names of the statistics are 'cycle', 'obs_precip', 'obs_precip_iszero', 'prob_precip', and 'mean_wind'.
    """

    summary = dict()
    above = obs_df[tcol].max() > 32
    below = obs_df[tcol].min() < 32
    cycle = above & below  # freeze/thaw cycle
    summary["cycle"] = cycle
    if "precipitationLast3Hours.value" in obs_df.columns:  # observed (past) data
        obs_precip = obs_df["precipitationLast3Hours.value"].sum()
        obs_precip_iszero = obs_precip < 0.01
        summary["obs_precip"] = obs_precip
        summary["obs_precip_iszero"] = obs_precip_iszero
    if "probabilityOfPrecipitation.value" in obs_df.columns:  # forecast (future) data
        prob_precip = obs_df["probabilityOfPrecipitation.value"].max()
        summary["prob_precip"] = prob_precip
    # summary["max_wind"] = obs_df['windSpeedInt'].max()
    summary["mean_wind"] = obs_df["windSpeedInt"].mean().astype("int")
    return pd.Series(summary)


def make_obs_df(loc, start, end, obs_tcol="temperature.value"):
    """
    Fetches weather station observations for a specific location from the NOAA API and formats them into a DataFrame.

    This function fetches the observations, reduces the DataFrame to only the relevant columns,
    converts the timestamps to datetime objects, ensures that all observations are from the same station,
    and creates a new column for the temperature in Fahrenheit.

    Parameters
    ----------
    loc : Location
        The location to fetch observations for.
    start : datetime
        The beginning of the time period to fetch observations from.
    end : datetime
        The end of the time period to fetch observations from.
    obs_tcol : str, optional
        The name of the column in the fetched data that contains the observed temperature data.
        If not provided, it defaults to 'temperature.value'.
        If the 'temperature.unitCode' column is not 'wmoUnit:degC' or 'C', the temperature is assumed to be in Fahrenheit.
        Otherwise, it is converted to Fahrenheit.

    Returns
    -------
    pandas.DataFrame
        A DataFrame of the fetched observations. The DataFrame contains columns for:
        the timestamp, the date, the hour of the day, the nearest 12-hour period, the nearest 6-hour period, and the temperature in Fahrenheit.
        Each row represents a single observation.

    Raises
    ------
    AssertionError
        If the fetched observations are from more than one station.
    """

    with warnings.catch_warnings():
        # pd.concat() raises a FutureWarning on this operation that cannot be
        # avoided without expensive computations on each observation (slow)
        # so we suppress the warning for this operation only
        warnings.simplefilter("ignore")
        obs_df_full = pd.concat(
            [pd.json_normalize(o) for o in loc.get_obs(start, end)], ignore_index=True
        )
    # get rid of extraneous columns and rows with no temperature value
    obs_df_reduced = reduce_obs(obs_df_full).dropna(axis=0, subset=[obs_tcol])
    # observations come in local time at the station
    obs_df_reduced.timestamp = pd.to_datetime(obs_df_reduced.timestamp, utc=True)
    obs_df_reduced["date"] = obs_df_reduced.timestamp.dt.floor("1D")
    obs_df_reduced["datehour"] = obs_df_reduced.timestamp.dt.floor("1H")
    obs_df_reduced["datehour_local"] = obs_df_reduced.datehour.dt.tz_convert(loc.tz)
    obs_df_reduced["date_nearest12"] = obs_df_reduced.timestamp.dt.floor("12H")
    obs_df_reduced["date_nearest6"] = obs_df_reduced.timestamp.dt.floor("6H")
    # ensure we are only returning obs from one station
    assert len(obs_df_reduced.station.unique()) == 1
    # create a column for temp in Fahrenheit
    if obs_tcol == "temperature.value":
        obs_tunit_col = obs_df_reduced["temperature.unitCode"]
        if (obs_tunit_col == "wmoUnit:degC").all() or (obs_tunit_col == "C").all():
            obs_df_reduced["tempF"] = (obs_df_reduced[obs_tcol] * (9 / 5)) + 32
        else:
            obs_df_reduced["tempF"] = obs_df_reduced[obs_tcol]
    else:
        obs_df_reduced["tempF"] = obs_df_reduced[obs_tcol]

    return obs_df_reduced


def parse_windspeed(speeds):
    """
    Parse the wind speeds returned by NOAA forecast API and split them into numerical speed and unit.

    This function takes a string representation of wind speed with its unit (e.g., "25 mph") and splits it into the numerical speed and the unit.
    The numerical speed is converted to an integer, and the unit is kept as a string.
    If the input string does not contain a recognizable unit, the function raises a ValueError.

    Parameters
    ----------
    speeds : str
        A string representation of wind speed with its unit, e.g., "25 mph".

    Returns
    -------
    pandas.Series
        A Series with two elements, both strings: the numerical wind speed (integer value) and the unit.
        The index of the Series is ['windSpeedInt', 'windSpeedUnit'].

    Raises
    ------
    ValueError
        If the input string does not contain a recognizable unit ("mph", "kmh", or "kmph").
    """

    if " mph" in speeds:
        speed_int = speeds.split(" mph")[0]
        unit = "mph"
    elif "kmh" in speeds:
        speed_int = speeds.split(" kmh")[0]
        unit = "wmoUnit:km_h-1"
    elif "kmph" in speeds:
        speed_int = speeds.split(" kmph")[0]
        unit = "wmoUnit:km_h-1"
    else:
        raise ValueError("Input does not look like a windspeed!")
    return pd.Series([speed_int, unit], index=["windSpeedInt", "windSpeedUnit"])


def parse_elev(elev_value, unit_code):
    """
    Parses elevation data from the NOAA API and converts it to feet.

    This function takes elevation data and its unit code as input, either as individual values or as pandas Series.
    It converts the elevation data to feet if necessary, and returns the converted elevation as both a float and a formatted string.

    Parameters
    ----------
    elev_value : float or pd.Series
        The elevation data from the NOAA API.
        If a Series, all values must be identical and the Series must be of the same length as `unit_code`.
    unit_code : str or pd.Series
        The unit code for the elevation data from the NOAA API.
        If a Series, all values must be identical and the Series must be of the same length as `elev_value`.

    Returns
    -------
    elev_ft : float
        The elevation data converted to feet.
    elev_str : str
        The elevation data converted to feet and formatted as a string, e.g., "8709 feet".

    Raises
    ------
    ValueError
        If `elev_value` and `unit_code` are Series of different lengths,
        if only one of them is a Series,
        or if `unit_code` is not a recognized unit ("m", "wmoUnit:m", "ft", or "feet").
    """

    # Handle different input types
    if isinstance(elev_value, pd.Series):
        if isinstance(unit_code, pd.Series):
            if len(elev_value) != len(unit_code):
                raise ValueError(
                    "Elevation value and unit series must be of equal length!"
                )
            ev = elev_value.iloc[0]
            uc = unit_code.iloc[0]
        else:
            raise ValueError("Both inputs must be pd.Series!")
    else:
        ev = elev_value
        uc = unit_code

    if uc == "m" or uc == "wmoUnit:m":
        elev_ft = 3.28 * ev
    elif uc == "ft" or uc == "feet":
        elev_ft = ev
    else:
        raise ValueError("Cannot parse elevation unit code!")
    return elev_ft, f"{elev_ft:.0f} feet"


def make_forecast_df(loc):
    """
    Fetches the NOAA API hourly forecast for a location and formats it into a DataFrame.

    This function does the following:
    - fetches the forecast
    - parses the elevation data
    - normalizes the forecast data into a DataFrame
    - converts the start and end times to datetime objects
    - parses the wind speed data

    and selects the relevant columns to keep.
    It also creates new columns for the temperature in Fahrenheit
    and the nearest date, 12-hour period, and 6-hour period.

    Parameters
    ----------
    loc : Location
        The location to fetch the forecast for.

    Returns
    -------
    out_df : pandas.DataFrame
        A DataFrame in the expected format for hourly data.
        The DataFrame contains columns for:
        - the start time, end time, and whether it's daytime
        - the temperature and the temperature unit
        - the wind speed, the parsed wind speed, the wind speed unit, the wind direction
        - the short forecast
        - any columns related to dewpoint, relative humidity, or probability of precipitation
        - the temperature in Fahrenheit
        - the date, the nearest 12-hour period, the nearest 6-hour period, and the elevation in feet.
        Each row represents a single hour of the forecast.
    """

    fcst_json = loc.get_forecast(full=True)
    elev_ft, _ = parse_elev(
        fcst_json["elevation"]["value"], fcst_json["elevation"]["unitCode"]
    )
    obs_df_full = pd.DataFrame(pd.json_normalize(fcst_json["periods"]))
    obs_df_full.startTime = pd.to_datetime(obs_df_full.startTime)
    obs_df_full.endTime = pd.to_datetime(obs_df_full.endTime)
    obs_df_full = obs_df_full.join(obs_df_full.windSpeed.apply(parse_windspeed))
    obs_df_full.windSpeedInt = pd.to_numeric(obs_df_full.windSpeedInt)
    # define which columns to keep and return
    cols_to_keep = [
        "startTime",
        "endTime",
        "isDaytime",
        "temperature",
        "temperatureUnit",
        "windSpeed",
        "windSpeedInt",
        "windSpeedUnit",
        "windDirection",
        "shortForecast",
    ]
    cols_to_keep.extend(
        [
            col
            for col in obs_df_full.columns
            if "dewpoint" in col
            or "relativeHumidity" in col
            or "probabilityOfPrecipitation" in col
        ]
    )
    out_df = obs_df_full[cols_to_keep].copy()
    out_df["tempF"] = out_df["temperature"]
    out_df["date"] = out_df.startTime.dt.floor("1D")
    out_df["date_nearest12"] = out_df.startTime.dt.floor("12H")
    out_df["date_nearest6"] = out_df.startTime.dt.floor("6H")
    out_df["elev_ft"] = elev_ft
    return out_df
