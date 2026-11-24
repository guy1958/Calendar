"""Calendar Time node: current hour/minute plus the hub's sunrise and sunset.

All values use uom 56 (Raw) so the console and programs show bare numbers (e.g. 10, not
'10 Hour') that work directly in numeric comparisons.
"""
import udi_interface

import cal_utils

LOGGER = udi_interface.LOGGER


class TimeNode(udi_interface.Node):
    id = 'caltime'
    drivers = [
        {'driver': 'ST', 'value': 0, 'uom': 56},
        {'driver': 'MINUTE', 'value': 0, 'uom': 56},
        {'driver': 'SUNRISE_HOUR', 'value': 0, 'uom': 56},
        {'driver': 'SUNRISE_MIN', 'value': 0, 'uom': 56},
        {'driver': 'SUNSET_HOUR', 'value': 0, 'uom': 56},
        {'driver': 'SUNSET_MIN', 'value': 0, 'uom': 56},
        {'driver': 'GV1', 'value': 0, 'uom': 56},
        {'driver': 'GV2', 'value': 0, 'uom': 56},
    ]

    def __init__(self, polyglot, primary, address, name):
        super().__init__(polyglot, primary, address, name)
        cal_utils.apply_declared_uoms(self)
        # Shared with the controller: {'tz', 'sunrise', 'sunset'} as read from the hub (empty until then)
        self.sun = {}

    def _values(self):
        tz = cal_utils.get_tz(self.sun.get('tz'))
        now = cal_utils.now_in(tz)
        sunrise = cal_utils.epoch_to_local(self.sun['sunrise'], tz) if self.sun.get('sunrise') else None
        sunset = cal_utils.epoch_to_local(self.sun['sunset'], tz) if self.sun.get('sunset') else None
        vals = cal_utils.time_values(now, sunrise, sunset)
        vals['GV1'] = int(__import__('time').time())
        vals['GV2'] = (now.date() - __import__('datetime').date(1970, 1, 1)).days
        return vals

    def _push(self, force):
        cal_utils.push_drivers(self, self._values(), force=force)

    def update(self, today, southern=False):
        """Full refresh: re-send every value."""
        self._push(True)

    def tick(self):
        """Cheap periodic refresh: only values that changed are sent."""
        self._push(False)

    def tick_seconds(self):
        """Update Unix seconds and local epoch day without refreshing other drivers."""
        import time
        import datetime

        tz = cal_utils.get_tz(self.sun.get('tz'))
        local_today = cal_utils.now_in(tz).date()

        self.setDriver('GV1', int(time.time()), force=False, uom=56)
        self.setDriver(
            'GV2',
            (local_today - datetime.date(1970, 1, 1)).days,
            force=False,
            uom=56
        )
