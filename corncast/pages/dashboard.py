import dash_bootstrap_components as dbc
from dash import Input, Output, html, dcc

import plotly.express as px

from datetime import datetime, timedelta

from corncast import Location, make_forecast_df, make_obs_df

from app import app

locs = [
    Location("Mt. Rose Summit", 39.314, -119.917),
    Location("Mt. Shasta - Bunny Flat", 41.353, -122.234),
]
locations = {l.name: l for l in locs}


def render_dashboard():
    return html.Div(
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
                [
                    dbc.Card(
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
                    )
                ]
            ),
        ]
    )


@app.callback(Output("obs-temp", "figure"), Input("loc-selection", "value"))
def update_obs(value, tcol="tempF"):
    now = datetime.now()
    obs_period = timedelta(days=5)
    start = now - obs_period
    end = now
    obs_df = make_obs_df(locations[value], start, end)
    if tcol not in obs_df.columns:
        raise KeyError(
            f"Temperature column '{tcol}' not found in make_obs_df() output data frame!"
        )

    # information about the weather station these observations are from
    station_name = obs_df.station.iloc[0]
    elev_value = obs_df["elevation.value"].iloc[0]
    if (uc := obs_df["elevation.unitCode"].iloc[0]) == "m" or uc == "wmoUnit:m":
        elev_str = f"{3.28*elev_value:.0f} feet"
    elif uc == "ft" or uc == "feet":
        elev_str = f"{elev_value:.0f} feet"
    else:
        raise ValueError("Cannot parse elevation.unitCode!")

    # group by hour, take the mean of temp readings within that hour, plot
    hour_means = obs_df.groupby(["datehour"])[tcol].mean().reset_index()
    return px.line(
        hour_means,
        x="datehour",
        y=tcol,
        title=f"Observations at {station_name.split('/')[-1]} ({elev_str})",
    ).add_hline(y=32, line_dash="dot")


@app.callback(Output("fcst-temp", "figure"), Input("loc-selection", "value"))
def update_fcst(value, tcol="tempF"):
    fcst_df = make_forecast_df(locations[value])
    if tcol not in fcst_df.columns:
        raise KeyError(
            f"Temperature column '{tcol}' not found in make_forecast_df() output data frame!"
        )

    return px.line(
        fcst_df, x="startTime", y=tcol,
        title=f"Forecast for {locations[value]} ({fcst_df['elev_ft'].iloc[0]:.0f} feet)"
    ).add_hline(y=32, line_dash="dot")
