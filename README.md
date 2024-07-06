# CornCast: Corn snow forecasting dashboard
There are many forecasting tools for those who love powder. But what about [corn](https://opensnow.com/news/post/spring-skiing-explained)? I aim to fill the gap.

CornCast fetches and displays all relevant information for spring skiing/riding in one place. Try it out [here](http://54.219.161.234:7000/).

At the moment, the layout is a simple four-panel (2 x 2) dashboard:

 * **Top left (Observations)**: Current conditions at the nearest weather station to the location. Coordinates and altitude are provided. Data from NOAA.
 * **Top right (Forecast)**: NOAA point forecast for the zone closest to the location. This forecast point is usually different from the nearest weather station, so continuity with the observations pane is not to be expected. Coordinates and elevation of the forecast point are also displayed.
 * **Bottom left (Snow Depth)**: Current snow depth conditions reported by representative SNOTEL sensor. If there is no representative SNOTEL sensor for a location (e.g. Mt. Shasta), this graph is left blank. SNOTEL data is collected by the [NRCS](https://www.nrcs.usda.gov/) and accessed via SOAP API from [CUAHSI](https://www.cuahsi.org/).
 * **Bottom right (Tabular Forecast)**: Daily summary of quantities relevant to corn formation. For the moment, this includes 1) freeze-thaw cycle, 2) chance of precipitation, and 3) wind speed.

CornCast is built with [noaa-sdk](https://github.com/paulokuong/noaa) and [Plotly Dash](https://dash.plotly.com/). 
