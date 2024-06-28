import unittest
from datetime import datetime
from corncast import Location
from collections.abc import Iterator


class LocationTests(unittest.TestCase):
    """
    A test case for the Location class.
    """

    def setUp(self):
        self.location = Location("New York", 40.7128, -74.0060)

    def test_init(self):
        self.assertEqual(self.location.name, "New York")
        self.assertEqual(self.location.lat(), 40.7128)
        self.assertEqual(self.location.lon(), -74.0060)
        self.assertEqual(self.location.get_snotels(), [])
        self.assertEqual(self.location.tz, "America/New_York")

    def test_str(self):
        self.assertEqual(str(self.location), "New York (40.713, -74.006)")

    def test_get_obs(self):
        start = datetime(2022, 1, 1)
        end = datetime(2022, 1, 2)
        observations = self.location.get_obs(start, end)
        self.assertIsInstance(observations, Iterator)

    def test_get_forecast(self):
        forecast = self.location.get_forecast()
        self.assertIsInstance(forecast, list)


if __name__ == "__main__":
    unittest.main()
