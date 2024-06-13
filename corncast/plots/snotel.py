from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import zeep
import xmltodict
from datetime import date, timedelta, datetime


def snotel_plot(loc):
    """
    Generates a plot of the snow depth at a SNOTEL station near a given location.

    This function uses the SOAP service provided by CUAHSI to fetch the snow depth data.
    It first fetches the site information using the GetSiteInfo service, and then fetches
    the snow depth values for the past week using the GetValues service. The snow depth
    values are then plotted on a line chart using Plotly.

    Parameters
    ----------
    loc : Location
        A Location object representing the location near which to find a SNOTEL station.

    Returns
    -------
    go.Figure
        A Plotly Figure object representing the snow depth plot. If no SNOTEL stations
        are found near the given location, an empty dictionary is returned.

    Raises
    ------
    zeep.exceptions.Fault
        If there is a problem with the SOAP service or the provided site code.
    xmltodict.expat.ExpatError
        If there is a problem parsing the XML response from the SOAP service.
    KeyError
        If the expected data is not found in the SOAP service response.
    """

    wsdl_url = "https://hydroportal.cuahsi.org/Snotel/cuahsi_1_1.asmx?WSDL"
    client = zeep.Client(wsdl=wsdl_url)

    stations = loc.get_snotels()
    if len(stations) == 0:
        # deal with no SNOTEL station info for this location
        return {}
    if len(stations) == 1:
        site_code = stations[0]  # e.g. "SNOTEL:652_NV_SNTL"
    else:
        site_code = stations[0]  # TODO figure out how to do this bit

    namespaces = {"cuahsi": "http://www.cuahsi.org/waterML/1.1/"}
    ns = namespaces["cuahsi"]
    response = client.service["GetSiteInfo"](site_code)
    out = xmltodict.parse(response, process_namespaces=True, namespaces=namespaces)
    resp_dict = out[f"{ns}:sitesResponse"]
    coords = resp_dict[f"{ns}:site"][f"{ns}:siteInfo"][f"{ns}:geoLocation"][
        f"{ns}:geogLocation"
    ]
    lat = float(coords[f"{ns}:latitude"])
    lon = float(coords[f"{ns}:longitude"])
    elevation_m = float(resp_dict[f"{ns}:site"][f"{ns}:siteInfo"][f"{ns}:elevation_m"])

    var_code = f"SNOTEL:SNWD_D"  # Snow depth, daily
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    vals = xmltodict.parse(
        client.service["GetValues"](site_code, var_code, start_date, end_date, "")
    )
    val_list = vals["timeSeriesResponse"]["timeSeries"]["values"]["value"]
    val_series = pd.to_numeric([v["#text"] for v in val_list])
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=pd.date_range(start=start_date, end=end_date),
            y=val_series,
            name="Snow Depth (in)",
        )
    )
    fig.update_layout(
        title=f"<b>Snow Depth</b> at {site_code} (({lat:.3f}, {lon:.3f}), {3.28*elevation_m:.0f} ft)",
        yaxis_title=f"Snow Depth (in)",
    )

    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)

    return fig
