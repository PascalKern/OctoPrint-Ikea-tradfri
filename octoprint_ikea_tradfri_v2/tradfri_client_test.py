import unittest

from octoprint_ikea_tradfri_v2 import TradfriClient


class MyTestCase(unittest.TestCase):
    def test_something(self):
        client = TradfriClient("192.168.0.124", "Nh1aEgM5okubRdRI")
        sockets = client.get_sockets()
        print("Sockets %s" % sockets)
        # client.shutdown()
        self.assertEqual(True, True)  # add assertion here


if __name__ == '__main__':
    unittest.main()
