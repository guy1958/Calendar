import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import cal_utils as cu
from month_node import MonthNode
from pattern_node import PatternNode


def test_days_in_month_is_unitless():
    assert cu.declared_uoms(MonthNode)['ST'] == 56


def test_days_until_next_is_unitless():
    assert cu.declared_uoms(PatternNode)['DAYS_UNTIL'] == 56


def test_profile_month_editor_matches_node_uom():
    import json
    with open(os.path.join(HERE, 'profile.json')) as f:
        prof = json.load(f)
    editors = {e['id']: e for e in prof['editors']}
    month = next(n for n in prof['nodedefs'] if n['id'] == 'calmonth')
    st = next(p for p in month['properties'] if p['id'] == 'ST')
    rng = editors[st['editor']]['ranges'][0]
    assert rng['uom'] == '56'
    assert rng['min'] <= 28 and rng['max'] >= 31
    rule = next(n for n in prof['nodedefs'] if n['id'] == 'calrule')
    du = next(p for p in rule['properties'] if p['id'] == 'DAYS_UNTIL')
    assert editors[du['editor']]['ranges'][0]['uom'] == '56'


def test_node_defs_rev_bumped_for_month_change():
    assert cu.NODE_DEFS_REV >= 3


def test_month_stored_with_days_unit_is_stale_but_time_today_match():
    from time_node import TimeNode
    from today_node import TodayNode
    old_month = [{'driver': 'ST', 'uom': 10, 'value': 30}, {'driver': 'YEAR', 'uom': 77}]
    assert cu.stored_defs_differ(old_month, MonthNode.drivers) is True
    assert cu.stored_defs_differ([dict(d) for d in TimeNode.drivers], TimeNode.drivers) is False
    assert cu.stored_defs_differ([dict(d) for d in TodayNode.drivers], TodayNode.drivers) is False
