from dash import Dash, html, dcc, Output, Input
import plotly.express as px
import pandas as pd

from app import app

from environment.settings import APP_HOST, APP_PORT, APP_DEBUG

from pages.dashboard import render_dashboard
from pages.page_not_found import page_not_found

server = app.server


def serve_content():
    return html.Div(
        [dcc.Location(id="url", refresh=False), html.Div(id="page-content")]
    )


app.layout = serve_content()


@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def display_page(pathname):
    if pathname in "/" or pathname in "/dashboard":
        return render_dashboard()
    return page_not_found()


if __name__ == "__main__":
    app.run_server(debug=APP_DEBUG, host=APP_HOST, port=APP_PORT)
