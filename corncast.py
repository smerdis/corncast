class Location(object):
    """Class that represents a location in the world."""
    def __init__(self, name, lat, lon):
        """Create a Location.
        
        Params:
        name    |   string, name of Location
        lat     |   float, latitude of location
        lon     |   float, longitude of location
        """
        self._name = name
        self._lat = lat
        self._lon = lon

    def get_obs(self, noaa, start, end):
        """Return weather observations nearest this location. 
        
        Params:
        noaa    |   NOAA SDK object
        start   |   Datetime or Pandas Timestamp, beginning of period to get observations for
        end     |   Datetime or Pandas Timestamp, end of period to get observations for
        """
        return noaa.get_observations_by_lat_lon(self._lat, self._lon, start.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S'))