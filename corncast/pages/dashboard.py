import dash_bootstrap_components as dbc
from dash import Input, Output, html, dcc

import plotly.express as px

import pandas as pd

from datetime import datetime, timedelta

from corncast import Location, make_forecast_df, make_obs_df, parse_elev, analyze_obs

from app import app
from plots.snotel import snotel_plot

locs = [
    Location("Donner Pass", 39.317, -120.33, snotels=["SNOTEL:428_CA_SNTL"]),
    Location("Mt. Rose Summit", 39.314, -119.917, snotels=["SNOTEL:652_NV_SNTL"]),
    Location("Mt. Shasta", 41.353, -122.234),
    Location("Mt. Hood", 45.331, -121.711, snotels=["SNOTEL:651_OR_SNTL"]),
    Location("Mt. Baker", 48.856, -121.674, snotels=["SNOTEL:909_WA_SNTL"]),
    Location(
        "Mt. Rainier - Paradise", 46.785, -121.735, snotels=["SNOTEL:679_WA_SNTL"]
    ),
    Location("Mt. Bachelor", 43.979, -121.683, snotels=["SNOTEL:815_OR_SNTL"]),
    Location("Sonora Pass", 38.325, -119.647, snotels=["SNOTEL:574_CA_SNTL"]),
    Location("Tahoe City", 39.171, -120.144, snotels=["SNOTEL:848_CA_SNTL"]),
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
    """Update the forecast temperatures graph when location is changed.
    This function calls make_forecast_df(), which hits the NOAA API endpoint
    and returns a data frame with 'startTime' and  'tempF' columns."""

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
    """Analyze hourly forecast returned by NOAA when the location is changed.
    This function calls make_forecast_df(), which hits the NOAA API endpoint
    Now we want to analyze that data frame and store the analyses in fcst-agg
    Many other functions will then update and populate different cards."""

    period = "date"
    fmt = "%m-%d"
    fcst_df = make_forecast_df(locations[value])
    fcst_agg = fcst_df.groupby([period], as_index=False).apply(analyze_obs)
    fcst_agg["datetime_str"] = fcst_agg[period].dt.strftime(fmt)
    return fcst_agg.to_json(date_format="iso", orient="split")


@app.callback(Output("daily-fcst", "children"), Input("fcst-agg", "data"))
def update_precip_fcst(data):
    df = pd.read_json(data, orient="split")[
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
                    html.Th("Mean sustained windspeed"),
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
    """Update snotel graph when location is changed."""

    return snotel_plot(locations[value])
