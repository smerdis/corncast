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
        self.assertEqual(parse_windspeed("10 kmph")["windSpeedInt"], "10")
        self.assertEqual(parse_windspeed("10 kmph")["windSpeedUnit"], "wmoUnit:km_h-1")
        self.assertEqual(parse_windspeed("10 kmh")["windSpeedInt"], "10")
        self.assertEqual(parse_windspeed("10 kmh")["windSpeedUnit"], "wmoUnit:km_h-1")
        self.assertEqual(parse_windspeed("0 mph")["windSpeedInt"], "0")
        self.assertEqual(parse_windspeed("0 mph")["windSpeedUnit"], "mph")
        self.assertEqual(parse_windspeed("0 kmph")["windSpeedInt"], "0")
        self.assertEqual(parse_windspeed("0 kmph")["windSpeedUnit"], "wmoUnit:km_h-1")
        self.assertEqual(parse_windspeed("0 kmh")["windSpeedInt"], "0")
        self.assertEqual(parse_windspeed("0 kmh")["windSpeedUnit"], "wmoUnit:km_h-1")
        self.assertRaises(ValueError, parse_windspeed, "10")
        self.assertRaises(ValueError, parse_windspeed, "10mph")
        self.assertRaises(ValueError, parse_windspeed, "10 kt")
        self.assertRaises(ValueError, parse_windspeed, "0")
        self.assertRaises(ValueError, parse_windspeed, "")
