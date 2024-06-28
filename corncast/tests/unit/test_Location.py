import unittest
from datetime import datetime
from corncast import Location
from collections.abc import Iterator


class LocationTests(unittest.TestCase):
    """
    A test case for the Location class.
    """

    def setUp(self):
        self.location = Location(
            "Carson Pass, CA", 38.690, -120.000, snotels=["SNOTEL:1067_CA_SNTL"]
        )

    def test_init(self):
        self.assertEqual(self.location.name, "Carson Pass, CA")
        self.assertEqual(self.location.lat(), 38.690)
        self.assertEqual(self.location.lon(), -120.000)
        self.assertEqual(self.location.get_snotels(), ["SNOTEL:1067_CA_SNTL"])
        self.assertEqual(self.location.tz, "America/Los_Angeles")

    def test_str(self):
        self.assertEqual(str(self.location), "Carson Pass, CA (38.690, -120.000)")

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
