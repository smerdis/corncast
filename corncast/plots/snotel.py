from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import zeep
from io import StringIO
import xmltodict
from datetime import date, timedelta, datetime


def snotel_plot(loc):
    wsdl_url = "https://hydroportal.cuahsi.org/Snotel/cuahsi_1_1.asmx?WSDL"
    stations = loc.get_snotels()

    client = zeep.Client(wsdl=wsdl_url, plugins=[zeep.plugins.HistoryPlugin()])
    namespaces = {"cuahsi": "http://www.cuahsi.org/waterML/1.1/"}
    ns = namespaces["cuahsi"]
    site_code = "SNOTEL:652_NV_SNTL"
    response = client.service["GetSiteInfo"](site_code)

    out = xmltodict.parse(response, process_namespaces=True, namespaces=namespaces)
    resp_dict = out[f"{ns}:sitesResponse"]
    # output of next code is something like
    # "{'@http://www.w3.org/2001/XMLSchema-instance:type': 'LatLonPointType', 'http://www.cuahsi.org/waterML/1.1/:latitude': '39.315731048583984', 'http://www.cuahsi.org/waterML/1.1/:longitude': '-119.89472961425781'}"
    coords = resp_dict[f"{ns}:site"][f"{ns}:siteInfo"][f"{ns}:geoLocation"][
        f"{ns}:geogLocation"
    ]
    lat = float(coords[f"{ns}:latitude"])
    lon = float(coords[f"{ns}:longitude"])
    elevation_m = float(resp_dict[f"{ns}:site"][f"{ns}:siteInfo"][f"{ns}:elevation_m"])

    var_code = f"SNOTEL:SNWD_D"
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    vals = xmltodict.parse(
        client.service["GetValues"](site_code, var_code, start_date, end_date, "")
    )
    val_list = vals["timeSeriesResponse"]["timeSeries"]["values"]["value"]
    most_recent_val = val_list[-1]
    val_series = pd.to_numeric([v["#text"] for v in val_list])
    date_str = date.strftime(
        datetime.strptime(most_recent_val["@dateTime"], "%Y-%m-%dT%H:%M:%S"), "%m-%d"
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=pd.date_range(start=start_date, end=end_date), y=val_series)
    )
    fig.update_layout(
        title=f"Snow Depth (in) at {site_code} (({lat:.3f}, {lon:.3f}), {3.28*elevation_m:.0f} ft)"
    )

    return fig
