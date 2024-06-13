# CornCast: Corn snow forecasting tool
There are many forecasting tools for those who love powder. But what about corn? I aim to fill the gap.

CornCast fetches and displays all relevant information for spring skiing/riding in one place. At the moment, the layout is a simple four-panel (2 x 2) dashboard:

 * **Top left (Observations)**: Current conditions at the nearest weather station to the location. Coordinates and altitude are provided. Data from NOAA.
 * **Top right (Forecast)**: NOAA point forecast for the zone closest to the location. This forecast point is usually different from the nearest weather station, so continuity with the observations pane is not to be expected. Coordinates and elevation of the forecast point are also displayed.
 * **Bottom left (Snowpack)**: Current snowpack conditions reported by representative SNOTEL sensor. If there is no representative SNOTEL sensor for a location (e.g. Mt. Shasta), this graph is left blank. SNOTEL data is accessed via SOAP API from CUAHSI.
 * **Bottom right (Tabular Forecast)**: Daily summary of quantities relevant to corn formation. For the moment, this includes 1) freeze-thaw cycle, 2) chance of precipitation, and 3) wind speed.
