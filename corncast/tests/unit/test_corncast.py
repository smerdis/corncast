import unittest
import pandas as pd
from datetime import datetime, timezone, timedelta
from corncast import (
    Location,
    parse_windspeed,
    parse_elev,
    make_obs_df,
    make_forecast_df,
)


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
        self.assertEqual(elev_ft, 3280.84)
        self.assertEqual(elev_str, "3281 feet")

        # Test with float value and unit code as pd.Series
        elev_value = pd.Series([1000.0, 2000.0])
        unit_code = pd.Series(["m", "m"])
        elev_ft, elev_str = parse_elev(elev_value, unit_code)
        self.assertEqual(elev_ft, 3280.84)
        self.assertEqual(elev_str, "3281 feet")

        # Test with invalid unit code
        with self.assertRaises(ValueError):
            parse_elev(1000.0, "invalid_unit")

        # Test with different lengths of elev_value and unit_code
        elev_value = pd.Series([1000.0, 2000.0])
        unit_code = pd.Series(["m"])
        with self.assertRaises(ValueError):
            parse_elev(elev_value, unit_code)


class DfTests(unittest.TestCase):
    def setUp(self):
        # Create a dummy Location object for testing
        self.location = Location(
            "Carson Pass, CA", 38.690, -120.000, snotels=["SNOTEL:1067_CA_SNTL"]
        )

    def test_make_obs_df_multiple_observations(self):
        # Test with multiple observations
        now = datetime.now(timezone.utc)
        obs_period = timedelta(days=5)
        start = now - obs_period
        end = now
        obs_df = make_obs_df(self.location, start, end)
        self.assertGreater(len(obs_df), 1)
        self.assertEqual(obs_df["station"].nunique(), 1)
        self.assertEqual(obs_df["timestamp"].nunique(), len(obs_df))
        self.assertTrue((obs_df["timestamp"] >= start).all())
        self.assertTrue((obs_df["timestamp"] <= end).all())
        self.assertTrue((obs_df["tempF"] >= -500).all())

    def test_make_forecast_df(self):
        # Test with a sample forecast JSON
        forecast_json = {
            "elevation": {"value": 1000.0, "unitCode": "m"},
            "periods": [
                {
                    "startTime": "2022-01-01T00:00:00-08:00",
                    "endTime": "2022-01-01T01:00:00-08:00",
                    "isDaytime": False,
                    "temperature": 32,
                    "temperatureUnit": "F",
                    "windSpeed": "10 mph",
                    "windDirection": "N",
                    "shortForecast": "Clear",
                },
                {
                    "startTime": "2022-01-01T01:00:00-08:00",
                    "endTime": "2022-01-01T02:00:00-08:00",
                    "isDaytime": False,
                    "temperature": 30,
                    "temperatureUnit": "F",
                    "windSpeed": "5 mph",
                    "windDirection": "N",
                    "shortForecast": "Clear",
                },
            ],
        }
        # Mock the get_forecast method of the Location object
        self.location.get_forecast = lambda full=False: forecast_json

        # Call the make_forecast_df function
        forecast_df = make_forecast_df(self.location)

        # Assert the expected values
        self.assertEqual(len(forecast_df), 2)
        self.assertFalse(forecast_df["isDaytime"][0])
        self.assertEqual(forecast_df["temperature"][0], 32)
        self.assertEqual(forecast_df["temperatureUnit"][0], "F")
        self.assertEqual(forecast_df["windSpeed"][0], "10 mph")
        self.assertEqual(forecast_df["windSpeedInt"][0], 10)
        self.assertEqual(forecast_df["windSpeedUnit"][0], "mph")
        self.assertEqual(forecast_df["windDirection"][0], "N")
        self.assertEqual(forecast_df["windSpeedInt"][1], 5)
        self.assertEqual(forecast_df["shortForecast"][0], "Clear")
        self.assertEqual(forecast_df["tempF"][0], 32)
        self.assertEqual(forecast_df["tempF"][1], 30)
        self.assertEqual(forecast_df["date"][0].strftime("%Y-%m-%d"), "2022-01-01")
        self.assertEqual(forecast_df["elev_ft"][0], 3280.84)


if __name__ == "__main__":
    unittest.main()
