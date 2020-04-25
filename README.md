# pymonoprice_6zone_31028
Python3 interface implementation for the Monoprice 6 zone amplifier product number 31028. This is NOT the same as the seemingly more common product 10761.

This package is a blatant ripoff of https://github.com/etsinko/pymonoprice. Any and all credit should go to Egor Tsinko, I simply hacked his work to make it compatible with the 31028, which I mistakenly bought thinking it was the 10761.

Use at your own risk, this is not heavily tested and I don't write much python, but, it is working for me.

## Notes
This is for use with [Home-Assistant](http://home-assistant.io)

## Usage
```python
from pymonoprice_6zone_31028 import get_monoprice

monoprice = get_monoprice('/dev/ttyUSB0')
# Valid zones are 1-6 for main monoprice amplifier
zone_status = monoprice.zone_status(1)

# Print zone status
print('Zone Number = {}'.format(zone_status.zone))
print('Power is {}'.format('On' if zone_status.power else 'Off'))
print('Mute is {}'.format('On' if zone_status.mute else 'Off'))
print('Volume = {}'.format(zone_status.volume))
print('Treble = {}'.format(zone_status.treble))
print('Bass = {}'.format(zone_status.bass))
print('Balance = {}'.format(zone_status.balance))
print('Source = {}'.format(zone_status.source))

# Turn off zone #11
monoprice.set_power(1, False)

# Mute zone #12
monoprice.set_mute(2, True)

# Set volume for zone #13
monoprice.set_volume(3, 15)

# Set source 1 for zone #14 
monoprice.set_source(4, 1)

# Set treble for zone #15
monoprice.set_treble(5, 10)

# Set bass for zone #16
monoprice.set_bass(6, 7)

# Set balance for zone #1
monoprice.set_balance(1, 3)

# Restore zone #1 to it's original state
monoprice.restore_zone(zone_status)
```

## Usage with asyncio

With `asyncio` flavor all methods of Monoprice object are coroutines.

```python
import asyncio
from pymonoprice_6zone_31028 import get_async_monoprice

async def main(loop):
    monoprice = await get_async_monoprice('/dev/ttyUSB0', loop)
    zone_status = await monoprice.zone_status(11)
    if zone_status.power:
        await monoprice.set_power(zone_status.zone, False)

loop = asyncio.get_event_loop()
loop.run_until_complete(main(loop))

```