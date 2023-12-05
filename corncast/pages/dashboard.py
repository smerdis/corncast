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
            html.H1(children="Corn Forecast", style={"textAlign": "center"}),
            dcc.Dropdown(list(locations), next(iter(locations)), id="loc-selection"),
            dcc.Graph(id="obs-temp"),
            dcc.Graph(id="fcst-temp"),
        ]
    )


@app.callback(Output("obs-temp", "figure"), Input("loc-selection", "value"))
def update_obs(value, tcol="tempF"):
    now = datetime.now()
    obs_period = timedelta(days=5)
    start = now - obs_period
    end = now
    obs_df = make_obs_df(locations[value], start, end)
    hour_means = obs_df.groupby(["datehour"])[tcol].mean().reset_index()
    return px.line(hour_means, x="datehour", y=tcol)


@app.callback(Output("fcst-temp", "figure"), Input("loc-selection", "value"))
def update_fcst(value, tcol="tempF"):
    fcst_df = make_forecast_df(locations[value])
    return px.line(fcst_df, x="startTime", y=tcol)
