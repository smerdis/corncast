# CornCast: Corn snow forecasting dashboard
There are many forecasting tools for those who love powder. But what about [corn](https://opensnow.com/news/post/spring-skiing-explained)? I aim to fill the gap.

CornCast fetches and displays relevant information for spring skiing/riding in one place. You can run it locally using [Docker](https://www.docker.com/products/docker-desktop/). Clone this repository, navigate to the ``corncast/`` folder inside the repository, then run these commands:

    docker build -t corncast:latest .  
    docker run -p 7000:7000 corncast:latest

CornCast will then be available at [http://127.0.0.1:7000](http://127.0.0.1:7000). At the moment, the layout is a simple four-panel (2 x 2) dashboard:

 * **Top left (Observations)**: Current conditions at the nearest weather station to the location. Station identifier and altitude are provided. Data from [NWS](https://weather.gov).
 * **Top right (Forecast)**: NWS point forecast for the zone closest to the location. This forecast point is usually different from the nearest weather station, so continuity with the observations pane is not expected. Coordinates and elevation of the forecast point are also displayed.
 * **Bottom left (Snow Depth)**: Current snow depth reported by representative [SNOTEL](https://www.nrcs.usda.gov/wps/portal/wcc/home/aboutUs/monitoringPrograms/automatedSnowMonitoring/) sensor. If there is no representative SNOTEL sensor for a location (e.g. Mt. Shasta), this graph is left blank. SNOTEL data is collected by [NRCS](https://www.nrcs.usda.gov/) and accessed via SOAP API from [CUAHSI](https://www.cuahsi.org/).
 * **Bottom right (Tabular Forecast)**: Daily summary of quantities relevant to corn formation. For the moment, this includes 1) freeze-thaw cycle, 2) chance of precipitation, and 3) wind speed.

CornCast is built with [noaa-sdk](https://github.com/paulokuong/noaa), [pandas](https://pandas.pydata.org/), and [Plotly Dash](https://dash.plotly.com/). Fast timezone lookups are courtesy of [tzfpy](https://github.com/ringsaturn/tzfpy).
