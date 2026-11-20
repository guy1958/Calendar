"""Calendar Weekday Pattern node -- one instance per customer-defined pattern.

Days Until Next uses uom 56 (Raw) so it shows as a bare number (e.g. 6, not '6 days').
"""
import udi_interface

import cal_utils
from cal_utils import pattern_info

LOGGER = udi_interface.LOGGER


class PatternNode(udi_interface.Node):
    id = 'calrule'
    drivers = [
        {'driver': 'ST', 'value': 0, 'uom': 25},
        {'driver': 'IS_TOMORROW', 'value': 0, 'uom': 25},
        {'driver': 'DAYS_UNTIL', 'value': 0, 'uom': 56},
        {'driver': 'NEXT_DAY', 'value': 1, 'uom': 9},
        {'driver': 'NEXT_MONTH', 'value': 1, 'uom': 47},
        {'driver': 'NEXT_YEAR', 'value': 1970, 'uom': 77},
    ]

    def __init__(self, polyglot, primary, address, name, pattern):
        super().__init__(polyglot, primary, address, name)
        cal_utils.apply_declared_uoms(self)
        self.pattern = pattern

    def update(self, today, southern=False):
        info = pattern_info(self.pattern, today)
        if not info:
            LOGGER.warning('%s: no upcoming occurrence found for pattern %s', self.name, self.pattern)
            return
        cal_utils.push_drivers(self, info, force=True)
