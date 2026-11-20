"""Calendar Today node.

Days Left in Month / Year use uom 56 (Raw) so they show as bare numbers (e.g. 19, not '19 days')
for numeric comparisons in programs.
"""
import udi_interface

import cal_utils
from cal_utils import day_info

LOGGER = udi_interface.LOGGER


class TodayNode(udi_interface.Node):
    id = 'caltoday'
    drivers = [
        {'driver': 'ST', 'value': 0, 'uom': 25},
        {'driver': 'DAY_OF_MONTH', 'value': 1, 'uom': 9},
        {'driver': 'MONTH', 'value': 1, 'uom': 47},
        {'driver': 'MONTH_NUM', 'value': 1, 'uom': 56},
        {'driver': 'YEAR', 'value': 1970, 'uom': 77},
        {'driver': 'DAY_OF_YEAR', 'value': 1, 'uom': 56},
        {'driver': 'ISO_WEEK', 'value': 1, 'uom': 56},
        {'driver': 'ISO_WEEK_PARITY', 'value': 0, 'uom': 25},
        {'driver': 'LAST_FULL_WEEK', 'value': 0, 'uom': 25},
        {'driver': 'IS_WEEKEND', 'value': 0, 'uom': 25},
        {'driver': 'LEAP_YEAR', 'value': 0, 'uom': 25},
        {'driver': 'SEASON', 'value': 0, 'uom': 25},
        {'driver': 'DAYS_LEFT_MONTH', 'value': 0, 'uom': 56},
        {'driver': 'DAYS_LEFT_YEAR', 'value': 0, 'uom': 56},
    ]

    def __init__(self, polyglot, primary, address, name):
        super().__init__(polyglot, primary, address, name)
        cal_utils.apply_declared_uoms(self)

    def update(self, today, southern=False):
        cal_utils.push_drivers(self, day_info(today, southern), force=True)
