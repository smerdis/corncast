import unittest
import pandas as pd
from datetime import datetime
from corncast import Location, parse_windspeed, parse_elev


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

    def test_parse_elev(self):
        # Test with float value and unit code as strings
        elev_ft, elev_str = parse_elev(1000.0, "m")
        self.assertEqual(elev_ft, 3280.0)
        self.assertEqual(elev_str, "3280 feet")

        # Test with float value and unit code as pd.Series
        elev_value = pd.Series([1000.0, 2000.0])
        unit_code = pd.Series(["m", "m"])
        elev_ft, elev_str = parse_elev(elev_value, unit_code)
        self.assertEqual(elev_ft, 3280.0)
        self.assertEqual(elev_str, "3280 feet")

        # Test with invalid unit code
        with self.assertRaises(ValueError):
            parse_elev(1000.0, "invalid_unit")

        # Test with different lengths of elev_value and unit_code
        elev_value = pd.Series([1000.0, 2000.0])
        unit_code = pd.Series(["m"])
        with self.assertRaises(ValueError):
            parse_elev(elev_value, unit_code)


if __name__ == "__main__":
    unittest.main()