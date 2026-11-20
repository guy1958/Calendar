"""Calendar Weekday Instance node -- e.g. 'the 2nd Wednesday of the month'."""
import udi_interface

import cal_utils
from cal_utils import weekday_instance_info

LOGGER = udi_interface.LOGGER


class WeekdayNode(udi_interface.Node):
    id = 'calweekday'
    drivers = [
        {'driver': 'ST', 'value': 1, 'uom': 25},
        {'driver': 'WEEKDAY', 'value': 0, 'uom': 25},
        {'driver': 'IS_LAST_INST', 'value': 0, 'uom': 25},
    ]

    def __init__(self, polyglot, primary, address, name):
        super().__init__(polyglot, primary, address, name)
        cal_utils.apply_declared_uoms(self)

    def update(self, today, southern=False):
        cal_utils.push_drivers(self, weekday_instance_info(today), force=True)
