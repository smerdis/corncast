import unittest
import pandas as pd
from datetime import datetime
from corncast import Location, parse_windspeed


class CorncastTests(unittest.TestCase):
    """
    A test case for the Corncast application.
    """

    def test_parse_windspeed(self):
        self.assertIsInstance(parse_windspeed("10 mph"), pd.Series)
        self.assertEqual(parse_windspeed("10 mph")["windSpeedInt"], "10")
        self.assertEqual(parse_windspeed("10 mph")["windSpeedUnit"], "mph")
