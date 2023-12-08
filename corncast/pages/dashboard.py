import dash_bootstrap_components as dbc
from dash import Input, Output, html, dcc

import plotly.express as px

import pandas as pd

from datetime import datetime, timedelta

from corncast import Location, make_forecast_df, make_obs_df, parse_elev, analyze_obs

from app import app

locs = [
    Location("Mt. Rose Summit", 39.314, -119.917),
    Location("Mt. Shasta - Bunny Flat", 41.353, -122.234),
]
locations = {l.name: l for l in locs}

card = dbc.Card(
    [
        dbc.CardHeader("Card header"),
        dbc.CardBody(
            [
                html.H4("Card title", className="card-title"),
                html.P(
                    "Some quick example text to build on the card title and "
                    "make up the bulk of the card's content.",
                    className="card-text",
                ),
                dbc.Button("Go somewhere", color="primary"),
            ]
        ),
    ],
    className="m-sm p-sm",
)

summary_card = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H4("Summary", className="card-title"),
                html.P(
                    "Overview of conditions",
                    className="card-text",
                    id="summary",
                ),
            ]
        ),
    ],
    className="w-50 m-sm p-sm",
)

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
    className="w-50 m-sm p-sm",
)


def render_dashboard():
    return dbc.Container(
        [
            dbc.Row(dbc.Col(html.H1("Corn Forecast"))),
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Dropdown(
                            list(locations), next(iter(locations)), id="loc-selection"
                        ),
                        width=2,
                    ),
                    dbc.Col(dcc.Graph(id="obs-temp"), width=5),
                    dbc.Col(dcc.Graph(id="fcst-temp"), width=5),
                ],
                # align="center",
            ),
            dbc.Row(
                dbc.Col(
                    [
                        dbc.Stack(
                            [summary_card, card3],
                            direction="horizontal",
                        )
                    ]
                )
            ),
            dbc.Row(
                dbc.Col([dbc.Stack([card for _ in range(3)], direction="horizontal")])
            ),
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
    df = pd.read_json(data, orient="split")[["datetime_str", "prob_precip", "mean_wind", "cycle"]]
    df["cycle_str"] = df["cycle"].astype(str)
    out_df = df[["datetime_str", "prob_precip", "mean_wind", "cycle_str"]]
    table_header = [
        html.Thead(
            html.Tr(
                [
                    html.Th("Date"),
                    html.Th("Chance of Precipitation (%)"),
                    html.Th("Mean sustained windspeed"),
                    html.Th("Corn Cycle?"),
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
