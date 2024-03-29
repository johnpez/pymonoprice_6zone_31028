import asyncio
import functools
import logging
import re
import serial
from functools import wraps
from serial_asyncio import create_serial_connection
from threading import RLock

_LOGGER = logging.getLogger(__name__)
ZONE_PATTERN = re.compile('#(\dZS) (VO\d\d) (PO\d) (MU\d) (IS\d)\+')

EOL = b'+'
LEN_EOL = len(EOL)
TIMEOUT = 2  # Number of seconds before serial operation timeout

TREBLE_DEFAULT = 7
BASS_DEFAULT = 7
BALANCE_DEFAULT = 32

class ZoneStatus(object):

    def __init__(self,
                 zone: int,
                 volume: int,   # 0 - 38
                 power: bool,
                 mute: bool,    # 1 = muted, shows muted if off
                 source: int,   # 0 = BUS, 1 = LINE
                ):

        self.zone = zone
        self.volume = volume
        self.power = bool(power)
        self.mute = bool(mute)
        self.source = source

        # These aren't passed in the Zone Status response, lets worry about them later
        # self.treble = treble
        # self.bass = bass
        # self.balance = balance
        self.treble = TREBLE_DEFAULT
        self.bass = BASS_DEFAULT
        self.balance = BALANCE_DEFAULT

    @classmethod
    def from_string(cls, string: str):

        if not string:
            return None
        
        # Still use this to validate the string, though my regex isn't good enough to properly parse this string to array =(
        match = re.search(ZONE_PATTERN, string)
        if not match:
            return None

        parts = re.sub(r'[^0-9 ]+','',string).split()

        return ZoneStatus( *[int(m) for m in parts])

class Monoprice(object):
    """
    Monoprice amplifier interface
    """

    def zone_status(self, zone: int):
        """
        Get the structure representing the status of the zone
        :param zone: zone 1..6
        :return: status of the zone or None
        """
        raise NotImplemented()

    def set_power(self, zone: int, power: bool):
        """
        Turn zone on or off
        :param zone: zone 1..6
        :param power: True to turn on, False to turn off
        """
        raise NotImplemented()

    def set_mute(self, zone: int, mute: bool):
        """
        Mute zone on or off
        :param zone: zone 1..6
        :param mute: True to mute, False to unmute
        """
        raise NotImplemented()

    def set_volume(self, zone: int, volume: int):
        """
        Set volume for zone
        :param zone: zone 1..6
        :param volume: integer from 0 to 38 inclusive
        """
        raise NotImplemented()

    def set_treble(self, zone: int, treble: int):
        """
        Set treble for zone
        :param zone: zone 1..6
        :param treble: integer from 0 to 14 inclusive, where 0 is -7 treble and 14 is +7
        """
        raise NotImplemented()

    def set_bass(self, zone: int, bass: int):
        """
        Set bass for zone
        :param zone: zone 1..6
        :param bass: integer from 0 to 14 inclusive, where 0 is -7 bass and 14 is +7
        """
        raise NotImplemented()

    def set_balance(self, zone: int, balance: int):
        """
        Set balance for zone
        :param zone: zone 1..6
        :param balance: integer from 0 to 20 inclusive, where 0 is -10(left), 0 is center and 20 is +10 (right)
        """
        raise NotImplemented()

    def set_source(self, zone: int, source: int):
        """
        Set source for zone
        :param zone: zone 1..6
        :param source: integer from 0 to 6 inclusive
        """
        raise NotImplemented()

    def restore_zone(self, status: ZoneStatus):
        """
        Restores zone to it's previous state
        :param status: zone state to restore
        """
        raise NotImplemented()


# Helpers

def _format_zone_status_request(zone: int) -> bytes:
    return '?{}ZS+'.format(zone).encode()


def _format_set_power(zone: int, power: bool) -> bytes:
    return '!{}PR{}+'.format(zone, '1' if power else '0').encode()


def _format_set_mute(zone: int, mute: bool) -> bytes:
    return '!{}MU{}+'.format(zone, '1' if mute else '0').encode()


def _format_set_volume(zone: int, volume: int) -> bytes:
    volume = int(max(0, min(volume, 38)))
    return '!{}VO{:02}+'.format(zone, volume).encode()


def _format_set_treble(zone: int, treble: int) -> bytes:
    treble = int(max(0, min(treble, 14)))
    return '!{}TR{:02}+'.format(zone, treble).encode()


def _format_set_bass(zone: int, bass: int) -> bytes:
    bass = int(max(0, min(bass, 14)))
    return '!{}BS{:02}+'.format(zone, bass).encode()


def _format_set_balance(zone: int, balance: int) -> bytes:
    balance = max(0, min(balance, 63))
    return '!{}BA{:02}+'.format(zone, balance).encode()


def _format_set_source(zone: int, source: int) -> bytes:
    source = int(max(0, min(source, 1)))
    return '!{}IS{:02}+'.format(zone, source).encode()


def get_monoprice(port_url):
    """
    Return synchronous version of Monoprice interface
    :param port_url: serial port, i.e. '/dev/ttyUSB0'
    :return: synchronous implementation of Monoprice interface
    """

    lock = RLock()

    def synchronized(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                return func(*args, **kwargs)
        return wrapper

    class MonopriceSync(Monoprice):
        def __init__(self, port_url):
            self._port = serial.serial_for_url(port_url, do_not_open=True)
            self._port.baudrate = 9600
            self._port.stopbits = serial.STOPBITS_ONE
            self._port.bytesize = serial.EIGHTBITS
            self._port.parity = serial.PARITY_NONE
            self._port.timeout = TIMEOUT
            self._port.write_timeout = TIMEOUT
            self._port.open()

        def _process_request(self, request: bytes, skip=0):
            """
            :param request: request that is sent to the monoprice
            :param skip: number of bytes to skip for end of transmission decoding
            :return: ascii string returned by monoprice
            """
            _LOGGER.debug('Sending "%s"', request)
            # clear
            self._port.reset_output_buffer()
            self._port.reset_input_buffer()
            # send
            self._port.write(request)
            self._port.flush()
            # receive
            result = bytearray()
            while True:
                c = self._port.read(1)
                if not c:
                    raise serial.SerialTimeoutException(
                        'Connection timed out! Last received bytes {}'.format([hex(a) for a in result]))
                result += c
                if len(result) > skip and result[-LEN_EOL:] == EOL:
                    break
            ret = bytes(result)
            _LOGGER.debug('Received "%s"', ret)
            return ret.decode('ascii')

        @synchronized
        def zone_status(self, zone: int):
            # Ignore first 6 bytes as they will contain 3 byte command and 3 bytes of EOL
            return ZoneStatus.from_string(self._process_request(_format_zone_status_request(zone), skip=6))

        @synchronized
        def set_power(self, zone: int, power: bool):
            self._process_request(_format_set_power(zone, power))

        @synchronized
        def set_mute(self, zone: int, mute: bool):
            self._process_request(_format_set_mute(zone, mute))

        @synchronized
        def set_volume(self, zone: int, volume: int):
            self._process_request(_format_set_volume(zone, volume))

        @synchronized
        def set_treble(self, zone: int, treble: int):
            self._process_request(_format_set_treble(zone, treble))

        @synchronized
        def set_bass(self, zone: int, bass: int):
            self._process_request(_format_set_bass(zone, bass))

        @synchronized
        def set_balance(self, zone: int, balance: int):
            self._process_request(_format_set_balance(zone, balance))

        @synchronized
        def set_source(self, zone: int, source: int):
            self._process_request(_format_set_source(zone, source))

        @synchronized
        def restore_zone(self, status: ZoneStatus):
            self.set_power(status.zone, status.power)
            self.set_mute(status.zone, status.mute)
            self.set_volume(status.zone, status.volume)
            self.set_treble(status.zone, status.treble)
            self.set_bass(status.zone, status.bass)
            self.set_balance(status.zone, status.balance)
            self.set_source(status.zone, status.source)

    return MonopriceSync(port_url)

async def get_async_monoprice(port_url, loop):
    """
    Return asynchronous version of Monoprice interface
    :param port_url: serial port, i.e. '/dev/ttyUSB0'
    :return: asynchronous implementation of Monoprice interface
    """

    lock = asyncio.Lock()

    def locked_coro(coro):
        @wraps(coro)
        async def wrapper(*args, **kwargs):
            async with lock:
                return await coro(*args, **kwargs)
        return wrapper

    class MonopriceAsync(Monoprice):
        def __init__(self, monoprice_protocol):
            self._protocol = monoprice_protocol

        @locked_coro
        async def zone_status(self, zone: int):
            # Ignore first 6 bytes as they will contain 3 byte command and 3 bytes of EOL
            string = await self._protocol.send(
                _format_zone_status_request(zone), skip=6
            )
            return ZoneStatus.from_string(string)

        @locked_coro
        async def set_power(self, zone: int, power: bool):
            await self._protocol.send(_format_set_power(zone, power))

        @locked_coro
        async def set_mute(self, zone: int, mute: bool):
            await self._protocol.send(_format_set_mute(zone, mute))

        @locked_coro
        async def set_volume(self, zone: int, volume: int):
            await self._protocol.send(_format_set_volume(zone, volume))

        @locked_coro
        async def set_treble(self, zone: int, treble: int):
            await self._protocol.send(_format_set_treble(zone, treble))

        @locked_coro
        async def set_bass(self, zone: int, bass: int):
           await self._protocol.send(_format_set_bass(zone, bass))

        @locked_coro
        async def set_balance(self, zone: int, balance: int):
            await self._protocol.send(_format_set_balance(zone, balance))

        @locked_coro
        async def set_source(self, zone: int, source: int):
            await self._protocol.send(_format_set_source(zone, source))

        @locked_coro
        async def restore_zone(self, status: ZoneStatus):
            await self._protocol.send(_format_set_power(status.zone, status.power))
            await self._protocol.send(_format_set_mute(status.zone, status.mute))
            await self._protocol.send(_format_set_volume(status.zone, status.volume))
            await self._protocol.send(_format_set_treble(status.zone, status.treble))
            await self._protocol.send(_format_set_bass(status.zone, status.bass))
            await self._protocol.send(_format_set_balance(status.zone, status.balance))
            await self._protocol.send(_format_set_source(status.zone, status.source))

    class MonopriceProtocol(asyncio.Protocol):
        def __init__(self, loop):
            super().__init__()
            self._loop = loop
            self._lock = asyncio.Lock()
            self._transport = None
            self._connected = asyncio.Event()
            self.q = asyncio.Queue()

        def connection_made(self, transport):
            self._transport = transport
            self._connected.set()
            _LOGGER.debug('port opened %s', self._transport)

        def data_received(self, data):
            asyncio.ensure_future(self.q.put(data), loop=self._loop)

        async def send(self, request: bytes, skip=0):
            await self._connected.wait()
            result = bytearray()
            # Only one transaction at a time
            async with self._lock:
                self._transport.serial.reset_output_buffer()
                self._transport.serial.reset_input_buffer()
                while not self.q.empty():
                    self.q.get_nowait()
                self._transport.write(request)
                try:
                    while True:
                        result += await asyncio.wait_for(self.q.get(), TIMEOUT, loop=self._loop)
                        if len(result) > skip and result[-LEN_EOL:] == EOL:
                            ret = bytes(result)
                            _LOGGER.debug('Received "%s"', ret)
                            return ret.decode('ascii')
                except asyncio.TimeoutError:
                    _LOGGER.error("Timeout during receiving response for command '%s', received='%s'", request, result)
                    raise

    _, protocol = await create_serial_connection(loop, functools.partial(MonopriceProtocol, loop),
                                                      port_url, baudrate=9600)
    return MonopriceAsync(protocol)
