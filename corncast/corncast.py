import pandas as pd
import warnings
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

        self.name = name
        self._lat = lat
        self._lon = lon
        self.noaa = NOAA(
            user_agent="CornCast testing <arjmukerji@gmail.com>", show_uri=True
        )

    def __str__(self):
        return f"{self.name} ({self._lat:.2f}, {self._lon:.2f})"

    def get_obs(self, start, end):
        """Return weather observations nearest this location.

        Parameters
        ----------
        start : datetime
            beginning of time period we want observations from
        end : datetime
            end of time period we want observations from
        """

        return self.noaa.get_observations_by_lat_lon(
            self._lat,
            self._lon,
            start.strftime("%Y-%m-%d %H:%M:%S"),
            end.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def get_forecast(self, full=False):
        """Return weather forecast nearest this location.

        Parameters
        ----------
        full : bool
            Return the full 'properties' dict returned by NOAA (default False)
            If false, return only the 'periods' element of this dict
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
    """Analyze a period of observations in Fahrenheit and compute summary stats.

    Parameters
    ----------
    obs_df : pandas.DataFrame
        Data Frame of hourly temperatures in Fahrenheit

    Returns
    -------
    summary : pandas.Series
        Series of summary statistics with label as index
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
    return pd.Series(summary)


def make_obs_df(loc, start, end, obs_tcol="temperature.value"):
    """Make data frame of weather station obs for a location from NOAA API

    Parameters
    ----------
    loc : Location
        Location to fetch observations for
    start : datetime
        beginning of time period we want observations from
    end : datetime
        end of time period we want observations from
    obs_tcol : str
        name of column containing observed temperature data, optional.
        If not provided, assume 'temperature.value'
        ^ This is returned by json_normalize() with 'temperature.unitCode'
        If 'temperature.unitCode' is not 'wmoUnit:degC' or 'C',
        obs_tcol assumed to be in Fahrenheit
        Otherwise, it is converted to F

    Returns
    -------
    out_df : pandas.DataFrame
        Data Frame in expected format for hourly data.
        'tempF' contains the observed temperature in Fahrenheit
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
    """Parse the wind speeds returned by NOAA forecast API

    Parameters
    ----------
    speeds : pd.Series
        Series of wind speeds, each like "25 mph"

    Returns
    -------
    out : pandas.Series
        Series with wind speed (integer, e.g. 25) and unit (e.g. "mph")
    """

    if "mph" in speeds:
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
    """NOAA API can return elevation data (for observations, forecasts, etc)
    in a variety of formats. This function centralizes the logic of parsing
    these responses into an elevation string that can be displayed.

    Parameters
    ----------
    elev_value : pd.Series
        Series (can be of length 1) with elevation.value from NOAA
    unit_code : pd.Series
        Series of identical length with elevation.unitCode from NOAA

    Returns
    -------
    elev_ft : np.float
        Elevation value in feet
    elev_str : string
        Elevation string, e.g. "8709 feet"
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
    """Make a data frame from the NOAA API hourly forecast for a location

    Parameters
    ----------
    loc : Location
        Location to fetch observations for

    Returns
    -------
    out_df : pandas.DataFrame
        Data Frame in expected format for hourly data
        'tempF' contains the observed temperature in Fahrenheit
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
