import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'tests'))

import cal_utils as cu
from pattern_node import PatternNode
from test_node_defs import _FakePoly, _Ctrl

PATTERNS = {'southern_hemisphere': False,
            'patterns': [{'label': 'Trash', 'occurrence': 'second', 'weekday': 'Tuesday', 'month': 'any'}]}
OLD = [{'driver': 'ST', 'value': 0, 'uom': 25}, {'driver': 'DAYS_UNTIL', 'value': 6, 'uom': 10},
       {'driver': 'NEXT_DAY', 'value': 8, 'uom': 9}]


def _ctl():
    import cal_ctl
    return cal_ctl


def _ctrl(poly, tmp_path):
    ctrl = _Ctrl(poly, tmp_path)
    ctrl._cal_typed = dict(PATTERNS)
    return ctrl


def test_days_until_is_unitless_and_rev_bumped():
    assert cu.declared_uoms(PatternNode)['DAYS_UNTIL'] == 56
    assert cu.NODE_DEFS_REV >= 4


def test_stale_pattern_node_is_removed_then_readded_with_declared_uom(tmp_path):
    ctl = _ctl()
    poly = _FakePoly({'r_trash': OLD})
    ctrl = _ctrl(poly, tmp_path)
    ctl.sync_nodes(ctrl)
    assert poly.deleted == ['r_trash']
    assert 'r_trash' not in poly.added
    ctl.node_deleted(ctrl, {'address': 'r_trash'})
    assert 'r_trash' in poly.added
    uoms = {d['driver']: d['uom'] for d in poly.added['r_trash'].drivers}
    assert uoms['DAYS_UNTIL'] == 56
    assert ctrl._cal_pending_del == {}
    reported = [m['set'][0] for m, kind in poly.sent
                if kind == 'status' and m['set'][0]['address'] == 'r_trash' and m['set'][0]['driver'] == 'DAYS_UNTIL']
    assert reported and all(r['uom'] == 56 for r in reported)


def test_rebuild_while_removal_pending_does_not_readd_early_or_delete_again(tmp_path):
    ctl = _ctl()
    poly = _FakePoly({'r_trash': OLD})
    ctrl = _ctrl(poly, tmp_path)
    ctl.sync_nodes(ctrl)
    ctl.sync_nodes(ctrl)
    assert poly.deleted == ['r_trash']
    assert 'r_trash' not in poly.added
    ctl.node_deleted(ctrl, {'address': 'r_trash'})
    assert 'r_trash' in poly.added


def test_up_to_date_pattern_node_is_left_alone(tmp_path):
    ctl = _ctl()
    poly = _FakePoly({'r_trash': [dict(d) for d in PatternNode.drivers]})
    ctrl = _ctrl(poly, tmp_path)
    ctl.sync_nodes(ctrl)
    assert poly.deleted == []
    assert 'r_trash' in poly.added


def test_new_pattern_has_nothing_to_migrate_and_unconfigured_one_is_still_removed(tmp_path):
    ctl = _ctl()
    poly = _FakePoly({'r_gone': OLD})
    poly.added['r_gone'] = object()
    ctrl = _ctrl(poly, tmp_path)
    ctl.sync_nodes(ctrl)
    assert 'r_trash' in poly.added
    assert poly.deleted == ['r_gone']          # removed as unconfigured, not as a migration
    assert ctrl._cal_pending_del == {}


def test_pattern_migration_runs_only_once(tmp_path):
    ctl = _ctl()
    poly = _FakePoly({'r_trash': OLD})
    ctrl = _ctrl(poly, tmp_path)
    ctl.sync_nodes(ctrl)
    ctl.node_deleted(ctrl, {'address': 'r_trash'})
    ctrl2 = _ctrl(poly, tmp_path)               # restart, stored record still stale in this fake
    ctl.sync_nodes(ctrl2)
    assert poly.deleted == ['r_trash']
