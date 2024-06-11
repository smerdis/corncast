import dash_bootstrap_components as dbc
from dash import Input, Output, html, dcc

import plotly.express as px

from io import StringIO
import pandas as pd

from datetime import datetime, timedelta

from corncast import Location, make_forecast_df, make_obs_df, parse_elev, analyze_obs

from app import app
from plots.snotel import snotel_plot

locs = [
    Location("Crater Lake, OR", 42.896, -122.134, snotels=["SNOTEL:1000_OR_SNTL"]),
    Location("Donner Pass, CA", 39.317, -120.33, snotels=["SNOTEL:428_CA_SNTL"]),
    Location("Mt. Bachelor, OR", 43.979, -121.683, snotels=["SNOTEL:815_OR_SNTL"]),
    Location("Mt. Baker, WA", 48.856, -121.674, snotels=["SNOTEL:909_WA_SNTL"]),
    Location("Mt. Hood, OR", 45.331, -121.711, snotels=["SNOTEL:651_OR_SNTL"]),
    Location(
        "Mt. Rainier - Paradise, WA", 46.785, -121.735, snotels=["SNOTEL:679_WA_SNTL"]
    ),
    Location("Mt. Rose Summit, NV", 39.314, -119.917, snotels=["SNOTEL:652_NV_SNTL"]),
    Location("Mt. Shasta, CA", 41.353, -122.234),
    Location(
        "North Cascades National Park, WA",
        48.530,
        -120.990,
        snotels=["SNOTEL:817_WA_SNTL"],
    ),
    Location("Snoqualmie Pass, WA", 47.391, -121.400, snotels=["SNOTEL:672_WA_SNTL"]),
    Location("Sonora Pass, CA", 38.325, -119.647, snotels=["SNOTEL:574_CA_SNTL"]),
    Location("Stevens Pass, WA", 47.750, -121.090, snotels=["SNOTEL:791_WA_SNTL"]),
    Location("Tahoe City, CA", 39.171, -120.144, snotels=["SNOTEL:848_CA_SNTL"]),
    Location("White Pass, WA", 46.639, -121.389, snotels=["SNOTEL:863_WA_SNTL"]),
]
locations = {l.name: l for l in locs}

card3 = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H4("Daily forecast", className="card-title"),
                html.P(
                    "Summary of conditions over the next week",
                    className="card-text",
                    id="daily-fcst",
                ),
            ]
        ),
    ],
    className="m-sm p-sm",
)


def render_dashboard():
    """
    Render the dashboard layout.

    This function creates a layout for the dashboard using Dash Bootstrap Components (dbc).
    The layout includes a title, a dropdown for location selection, two graphs for observation and forecast temperatures,
    a graph for snow telemetry data, and a storage component for forecast aggregation.

    Returns
    -------
    dbc.Container
        A dbc.Container object that represents the layout of the dashboard.
        The container is fluid, meaning it will take up the full width of the viewport.
    """
    return dbc.Container(
        id="app-container",
        children=[
            dbc.Row([dbc.Col([html.H1("Corn Snow Monitoring Dashboard")])]),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dcc.Dropdown(
                                list(locations),
                                next(iter(locations)),
                                id="loc-selection",
                            ),
                        ]
                    ),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dcc.Graph(id="obs-temp"),
                        ],
                        xs=6,
                    ),
                    dbc.Col(
                        [
                            dcc.Graph(id="fcst-temp"),
                        ],
                        xs=6,
                    ),
                ]
            ),
            dbc.Row([dbc.Col([dcc.Graph(id="snotel-graph")], xs=6), dbc.Col(card3)]),
            dcc.Store(id="fcst-agg"),
        ],
        fluid=True,
    )


@app.callback(Output("obs-temp", "figure"), Input("loc-selection", "value"))
def update_obs(value, xcol="datehour", tcol="tempF"):
    """Update observed temperatures graph when location is changed.
    This function calls make_obs_df() which hits the NOAA API endpoint
    and returns a dataframe of observations from the nearest station."""

    now = datetime.now()
    obs_period = timedelta(days=5)
    start = now - obs_period
    end = now
    obs_df = make_obs_df(locations[value], start, end)

    # information about the weather station these observations are from
    station_name = obs_df.station.iloc[0]
    _, elev_str = parse_elev(obs_df["elevation.value"], obs_df["elevation.unitCode"])

    # group by hour, take the mean of temp readings within that hour, plot
    hour_means = obs_df.groupby([xcol])[tcol].mean().reset_index()
    return px.line(
        hour_means,
        x=xcol,
        y=tcol,
        labels={xcol: "", tcol: "Temperature (F)"},
        title=f"Observations at {station_name.split('/')[-1]} ({elev_str})",
    ).add_hline(y=32, line_dash="dot")


@app.callback(Output("fcst-temp", "figure"), Input("loc-selection", "value"))
def update_fcst(value, xcol="startTime", tcol="tempF"):
    """
    Update the observed temperatures graph when the location is changed.

    This function retrieves weather observations from the NOAA API for the selected location,
    groups the observations by hour, calculates the mean temperature for each hour, and
    returns a plotly express line graph of these hourly mean temperatures.

    Parameters
    ----------
    value : str
        The selected location. This should be a key in the `locations` dictionary.
    xcol : str, optional
        The name of the column in the dataframe to use for the x-axis of the graph. Default is "datehour".
    tcol : str, optional
        The name of the column in the dataframe to use for the y-axis of the graph. Default is "tempF".

    Returns
    -------
    plotly.graph_objs._figure.Figure
        A plotly express line graph of hourly mean temperatures at the selected location.

    Notes
    -----
    This function calls `make_obs_df()` which hits the NOAA API endpoint
    and returns a dataframe of observations from the nearest station.
    """

    fcst_df = make_forecast_df(locations[value])
    return px.line(
        fcst_df,
        x="startTime",
        y=tcol,
        labels={xcol: "", tcol: "Temperature (F)"},
        title=f"Forecast for {locations[value]} ({fcst_df['elev_ft'].iloc[0]:.0f} feet)",
    ).add_hline(y=32, line_dash="dot")


@app.callback(Output("fcst-agg", "data"), Input("loc-selection", "value"))
def analyze_hourly_fcst(value):
    """
    Analyze hourly forecast data and return it as JSON.

    This function retrieves the forecast data for the selected location from the NOAA API,
    groups the data by date, applies the `analyze_obs` function to each group, and
    returns the aggregated data as a JSON string.

    Parameters
    ----------
    value : str
        The selected location. This should be a key in the `locations` dictionary.

    Returns
    -------
    str
        The aggregated forecast data as a JSON string. The JSON string is in "split" orientation,
        and dates are formatted as ISO 8601 strings.

    Notes
    -----
    This function calls `make_forecast_df()` which hits the NOAA API endpoint
    and returns a dataframe of forecast data from the nearest station.
    The `analyze_obs` function is applied to each group of data by date.
    """
    period = "date"
    fmt = "%m-%d"
    fcst_df = make_forecast_df(locations[value])
    fcst_agg = fcst_df.groupby([period], as_index=False).apply(analyze_obs)
    fcst_agg["datetime_str"] = fcst_agg[period].dt.strftime(fmt)
    return fcst_agg.to_json(date_format="iso", orient="split")


@app.callback(Output("daily-fcst", "children"), Input("fcst-agg", "data"))
def update_precip_fcst(data):
    """
    Update the precipitation forecast table when new data is received.

    This function takes the aggregated forecast data as a JSON string, converts it to a dataframe,
    selects the necessary columns, and creates a new table with these columns.
    The table is then returned as a dbc.Table object.

    Parameters
    ----------
    data : str
        The aggregated forecast data as a JSON string. The JSON string should be in "split" orientation,
        and dates should be formatted as ISO 8601 strings.

    Returns
    -------
    dbc.Table
        A dbc.Table object that represents the updated precipitation forecast table. The table is striped and centered.

    Notes
    -----
    The table includes the following columns: "Date", "Chance of Precipitation (%)", "Mean sustained windspeed", and "Freeze-thaw cycle?".
    """
    df = pd.read_json(StringIO(data), orient="split")[
        ["datetime_str", "prob_precip", "mean_wind", "cycle"]
    ]
    df["cycle_str"] = df["cycle"].astype(str)
    out_df = df[["datetime_str", "prob_precip", "mean_wind", "cycle_str"]]

    table_header = [
        html.Thead(
            html.Tr(
                [
                    html.Th("Date"),
                    html.Th("Chance of Precipitation (%)"),
                    html.Th("Mean sustained windspeed (mph)"),
                    html.Th("Freeze-thaw cycle?"),
                ]
            )
        )
    ]
    out_table_body = dbc.Table.from_dataframe(
        out_df,
    ).children[
        1:
    ]  # first child element is the header with default column names, we don't want it

    return dbc.Table(
        table_header + out_table_body, striped=True, className="text-md-center"
    )


@app.callback(Output("snotel-graph", "figure"), Input("loc-selection", "value"))
def update_snotel(value):
    """
    Update the SNOTEL graph when the location is changed.

    This function retrieves the SNOTEL data for the selected location from the `locations` dictionary,
    and returns a plotly graph of this data.

    Parameters
    ----------
    value : str
        The selected location. This should be a key in the `locations` dictionary.

    Returns
    -------
    plotly.graph_objs._figure.Figure
        A plotly graph of the SNOTEL data at the selected location.

    Notes
    -----
    This function calls `snotel_plot()` which retrieves the SNOTEL data for the selected location
    and returns a plotly graph of this data.
    """
    plot = snotel_plot(locations[value])
    if plot == {}:
        return px.line(title="No SNOTEL data available")
    return plot
