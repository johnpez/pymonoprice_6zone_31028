import unittest

import serial

from pymonoprice_6zone_31028 import (get_monoprice, get_async_monoprice, ZoneStatus)
from tests import create_dummy_port
import asyncio


class TestZoneStatus(unittest.TestCase):

    def test_zone_status_broken(self):
        self.assertIsNone(ZoneStatus.from_string(None))
        self.assertIsNone(ZoneStatus.from_string('+#>110001000010111210040+#'))
        self.assertIsNone(ZoneStatus.from_string('+#>a100010000101112100401+#'))
        self.assertIsNone(ZoneStatus.from_string('+#>a1000100dfsf112100401+#'))
        self.assertIsNone(ZoneStatus.from_string('+#>+#'))

class TestMonoprice(unittest.TestCase):
    def setUp(self):
        self.responses = {}
        self.monoprice = get_monoprice(create_dummy_port(self.responses))

    def test_zone_status(self):
        self.responses[b'?1+'] = b'+#>1100010000131112100401+#'
        status = self.monoprice.zone_status(1)
        self.assertEqual(11, status.zone)
        self.assertTrue(status.power)
        self.assertFalse(status.mute)
        self.assertEqual(13, status.volume)
        self.assertEqual(11, status.treble)
        self.assertEqual(12, status.bass)
        self.assertEqual(10, status.balance)
        self.assertEqual(4, status.source)
        self.assertEqual(0, len(self.responses))

    def test_set_power(self):
        self.responses[b'?13PR01+'] = b'+#'
        self.monoprice.set_power(13, True)
        self.responses[b'?13PR01+'] = b'+#'
        self.monoprice.set_power(13, 'True')
        self.responses[b'?13PR01+'] = b'+#'
        self.monoprice.set_power(13, 1)
        self.responses[b'?13PR00+'] = b'+#'
        self.monoprice.set_power(13, False)
        self.responses[b'?13PR00+'] = b'+#'
        self.monoprice.set_power(13, None)
        self.responses[b'?13PR00+'] = b'+#'
        self.monoprice.set_power(13, 0)
        self.responses[b'?13PR00+'] = b'+#'
        self.monoprice.set_power(13, '')
        self.assertEqual(0, len(self.responses))
        
    def test_set_mute(self):
        self.responses[b'?13MU01+'] = b'+#'
        self.monoprice.set_mute(13, True)
        self.responses[b'?13MU01+'] = b'+#'
        self.monoprice.set_mute(13, 'True')
        self.responses[b'?13MU01+'] = b'+#'
        self.monoprice.set_mute(13, 1)
        self.responses[b'?13MU00+'] = b'+#'
        self.monoprice.set_mute(13, False)
        self.responses[b'?13MU00+'] = b'+#'
        self.monoprice.set_mute(13, None)
        self.responses[b'?13MU00+'] = b'+#'
        self.monoprice.set_mute(13, 0)
        self.responses[b'?13MU00+'] = b'+#'
        self.monoprice.set_mute(13, '')
        self.assertEqual(0, len(self.responses))

    def test_set_volume(self):
        self.responses[b'?13VO01+'] = b'+#'
        self.monoprice.set_volume(13, 1)
        self.responses[b'?13VO38+'] = b'+#'
        self.monoprice.set_volume(13, 100)
        self.responses[b'?13VO00+'] = b'+#'
        self.monoprice.set_volume(13, -100)
        self.responses[b'?13VO20+'] = b'+#'
        self.monoprice.set_volume(13, 20)
        self.assertEqual(0, len(self.responses))

    def test_set_treble(self):
        self.responses[b'?13TR01+'] = b'+#'
        self.monoprice.set_treble(13, 1)
        self.responses[b'?13TR14+'] = b'+#'
        self.monoprice.set_treble(13, 100)
        self.responses[b'?13TR00+'] = b'+#'
        self.monoprice.set_treble(13, -100)
        self.responses[b'?13TR13+'] = b'+#'
        self.monoprice.set_treble(13, 13)
        self.assertEqual(0, len(self.responses))

    def test_set_bass(self):
        self.responses[b'?13BS01+'] = b'+#'
        self.monoprice.set_bass(13, 1)
        self.responses[b'?13BS14+'] = b'+#'
        self.monoprice.set_bass(13, 100)
        self.responses[b'?13BS00+'] = b'+#'
        self.monoprice.set_bass(13, -100)
        self.responses[b'?13BS13+'] = b'+#'
        self.monoprice.set_bass(13, 13)
        self.assertEqual(0, len(self.responses))

    def test_set_balance(self):
        self.responses[b'?13BL01+'] = b'+#'
        self.monoprice.set_balance(13, 1)
        self.responses[b'?13BL20+'] = b'+#'
        self.monoprice.set_balance(13, 100)
        self.responses[b'?13BL00+'] = b'+#'
        self.monoprice.set_balance(13, -100)
        self.responses[b'?13BL13+'] = b'+#'
        self.monoprice.set_balance(13, 13)
        self.assertEqual(0, len(self.responses))

    def test_set_source(self):
        self.responses[b'?13CH01+'] = b'+#'
        self.monoprice.set_source(13, 1)
        self.responses[b'?13CH06+'] = b'+#'
        self.monoprice.set_source(13, 100)
        self.responses[b'?13CH01+'] = b'+#'
        self.monoprice.set_source(13, -100)
        self.responses[b'?13CH03+'] = b'+#'
        self.monoprice.set_source(13, 3)
        self.assertEqual(0, len(self.responses))

    def test_restore_zone(self):
        zone = ZoneStatus.from_string('+#>1100010000131112100401+#')
        self.responses[b'?11PR01+'] = b'+#'
        self.responses[b'?11MU00+'] = b'+#'
        self.responses[b'?11VO13+'] = b'+#'
        self.responses[b'?11TR11+'] = b'+#'
        self.responses[b'?11BS12+'] = b'+#'
        self.responses[b'?11BL10+'] = b'+#'
        self.responses[b'?11CH04+'] = b'+#'
        self.monoprice.restore_zone(zone)
        self.assertEqual(0, len(self.responses))

    def test_timeout(self):
        with self.assertRaises(serial.SerialTimeoutException):
            self.monoprice.set_source(3, 3)


class TestAsyncMonoprice(TestMonoprice):

    def setUp(self):
        self.responses = {}
        loop = asyncio.get_event_loop()
        monoprice = loop.run_until_complete(get_async_monoprice(create_dummy_port(self.responses), loop))

        # Dummy monoprice that converts async to sync
        class DummyMonoprice():
            def __getattribute__(self, item):
                def f(*args, **kwargs):
                    return loop.run_until_complete(monoprice.__getattribute__(item)(*args, **kwargs))
                return f
        self.monoprice = DummyMonoprice()

    def test_timeout(self):
        with self.assertRaises(asyncio.TimeoutError):
            self.monoprice.set_source(3, 3)

if __name__ == '__main__':
    unittest.main()