"""Calendar Month Info node.

Days in Month uses uom 56 (Raw) so it shows as a bare number (e.g. 30, not '30 days').
"""
import udi_interface

import cal_utils
from cal_utils import month_info

LOGGER = udi_interface.LOGGER


class MonthNode(udi_interface.Node):
    id = 'calmonth'
    drivers = [
        {'driver': 'ST', 'value': 30, 'uom': 56},
        {'driver': 'YEAR', 'value': 1970, 'uom': 77},
        {'driver': 'FIRST_WEEKDAY', 'value': 0, 'uom': 25},
        {'driver': 'LAST_WEEKDAY', 'value': 0, 'uom': 25},
        {'driver': 'IS_FIRST_DAY', 'value': 0, 'uom': 25},
        {'driver': 'IS_LAST_DAY', 'value': 0, 'uom': 25},
        {'driver': 'IS_LAST_BUSDAY', 'value': 0, 'uom': 25},
    ]

    def __init__(self, polyglot, primary, address, name):
        super().__init__(polyglot, primary, address, name)
        cal_utils.apply_declared_uoms(self)

    def update(self, today, southern=False):
        cal_utils.push_drivers(self, month_info(today), force=True)
