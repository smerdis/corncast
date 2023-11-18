class Location(object):
    """Class that represents a location in the world.

    Attributes
    ----------
    name : string
        name of location
    lat : float
        latitude of location
    lon : float
        longitude of location
    """

    def __init__(self, name, lat, lon):
        """Create a Location.
        
        Parameters
        ----------
        name : string
            name of location
        lat : float
            latitude of location
        lon : float
            longitude of location
        """

        self._name = name
        self._lat = lat
        self._lon = lon

    def get_obs(self, noaa, start, end):
        """Return weather observations nearest this location. 
        
        Parameters
        ----------
        noaa : object
            noaa_sdk.NOAA api wrapper object
        start : datetime
            beginning of time period we want observations from
        end : datetime
            end of time period we want observations from
        """

        return noaa.get_observations_by_lat_lon(self._lat, self._lon, start.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S'))