"""Calendar Tomorrow node."""
import datetime

import udi_interface

import cal_utils
from cal_utils import day_info

LOGGER = udi_interface.LOGGER


class TomorrowNode(udi_interface.Node):
    id = 'caltomorrow'
    drivers = [
        {'driver': 'ST', 'value': 0, 'uom': 25},
        {'driver': 'DAY_OF_MONTH', 'value': 1, 'uom': 9},
        {'driver': 'MONTH', 'value': 1, 'uom': 47},
        {'driver': 'MONTH_NUM', 'value': 1, 'uom': 56},
        {'driver': 'YEAR', 'value': 1970, 'uom': 77},
        {'driver': 'DAY_OF_YEAR', 'value': 1, 'uom': 56},
        {'driver': 'ISO_WEEK', 'value': 1, 'uom': 56},
        {'driver': 'LAST_FULL_WEEK', 'value': 0, 'uom': 25},
        {'driver': 'IS_WEEKEND', 'value': 0, 'uom': 25},
        {'driver': 'LEAP_YEAR', 'value': 0, 'uom': 25},
        {'driver': 'SEASON', 'value': 0, 'uom': 25},
    ]

    def __init__(self, polyglot, primary, address, name):
        super().__init__(polyglot, primary, address, name)
        cal_utils.apply_declared_uoms(self)

    def update(self, today, southern=False):
        info = day_info(today + datetime.timedelta(days=1), southern)
        cal_utils.push_drivers(self, info, force=True)
