import datetime as dt
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import cal_utils as cu


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

class _Cls:
    drivers = [
        {'driver': 'ST', 'value': 0, 'uom': 56},
        {'driver': 'MINUTE', 'value': 0, 'uom': 56},
    ]


class _FakeNode:
    """Mimics udi_interface.Node: setDriver(driver, value, report, force, uom, text) and reportDriver."""
    drivers = _Cls.drivers

    def __init__(self, stored_uom=None):
        import copy
        self.drivers = copy.deepcopy(type(self).drivers)
        if stored_uom is not None:      # what Node.__init__ -> _updateDrivers does from the database
            for d in self.drivers:
                d['uom'] = stored_uom
        self.sent = []

    def setDriver(self, driver, value, report=True, force=False, uom=None, text=None):
        drv = next(d for d in self.drivers if d['driver'] == driver)
        changed = False
        if uom is not None and drv['uom'] != uom:
            drv['uom'] = uom
            changed = True
        if drv['value'] != value:
            drv['value'] = value
            changed = True
        if report and (changed or force):
            self.sent.append((driver, value, drv['uom']))
        return changed


def test_declared_uoms_reads_class_list():
    assert cu.declared_uoms(_Cls) == {'ST': 56, 'MINUTE': 56}


def test_apply_declared_uoms_undoes_stored_uom():
    node = _FakeNode(stored_uom=19)
    assert {d['uom'] for d in node.drivers} == {19}
    cu.apply_declared_uoms(node)
    assert {d['uom'] for d in node.drivers} == {56}
    # the class-level declaration is never mutated
    assert {d['uom'] for d in _FakeNode.drivers} == {56}


def test_push_drivers_reports_declared_uom_even_if_stored_uom_came_back():
    # e.g. a CONFIG event replaced the node's drivers with the database's old uom
    node = _FakeNode(stored_uom=19)
    cu.push_drivers(node, {'ST': 10, 'MINUTE': 5}, force=True)
    assert node.sent == [('ST', 10, 56), ('MINUTE', 5, 56)]


def test_push_drivers_without_force_sends_only_changes_but_fixes_uom():
    node = _FakeNode()
    cu.push_drivers(node, {'ST': 10, 'MINUTE': 5}, force=False)
    node.sent.clear()
    cu.push_drivers(node, {'ST': 10, 'MINUTE': 6}, force=False)   # only MINUTE changed
    assert node.sent == [('MINUTE', 6, 56)]
    node.sent.clear()
    node.drivers[0]['uom'] = 19                                    # database's uom sneaks back in
    cu.push_drivers(node, {'ST': 10, 'MINUTE': 6}, force=False)   # same values, but the uom is corrected and sent
    assert node.sent == [('ST', 10, 56)]


def test_push_drivers_ignores_keys_the_node_does_not_have():
    node = _FakeNode()
    cu.push_drivers(node, {'ST': 1, 'SECOND': 7}, force=True)
    assert [s[0] for s in node.sent] == ['ST']


DECL = [{'driver': 'ST', 'uom': 56}, {'driver': 'MINUTE', 'uom': 56}]


def test_stored_defs_differ_on_uom():
    stored = [{'driver': 'ST', 'uom': 19, 'value': 10}, {'driver': 'MINUTE', 'uom': 44, 'value': 5}]
    assert cu.stored_defs_differ(stored, DECL) is True


def test_stored_defs_differ_on_driver_no_longer_declared():
    stored = [{'driver': 'ST', 'uom': 56}, {'driver': 'MINUTE', 'uom': 56}, {'driver': 'SECOND', 'uom': 57}]
    assert cu.stored_defs_differ(stored, DECL) is True


def test_stored_defs_match_ignores_value_and_uom_type():
    stored = [{'driver': 'ST', 'uom': '56', 'value': 3}, {'driver': 'MINUTE', 'uom': 56, 'value': 'x'}]
    assert cu.stored_defs_differ(stored, DECL) is False


def test_stored_defs_new_node_or_missing_driver_is_not_stale():
    assert cu.stored_defs_differ([], DECL) is False
    assert cu.stored_defs_differ(None, DECL) is False
    assert cu.stored_defs_differ([{'driver': 'ST', 'uom': 56}], DECL) is False


def test_stale_addresses_sorted_and_selective():
    stored = {
        'time': [{'driver': 'ST', 'uom': 19}],
        'today': [{'driver': 'ST', 'uom': 25}],
        'month': [{'driver': 'ST', 'uom': 10}],
        'weekday': [],
    }
    declared = {
        'time': [{'driver': 'ST', 'uom': 56}],
        'today': [{'driver': 'ST', 'uom': 56}],
        'month': [{'driver': 'ST', 'uom': 10}],
        'weekday': [{'driver': 'ST', 'uom': 25}],
    }
    assert cu.stale_addresses(stored, declared) == ['time', 'today']


def test_marker_roundtrip_and_failures(tmp_path):
    path = str(tmp_path / 'sub' / cu.MIGRATION_FILE)
    assert cu.read_node_defs_rev(path) == 0
    cu.write_node_defs_rev(path, cu.NODE_DEFS_REV)
    assert cu.read_node_defs_rev(path) == cu.NODE_DEFS_REV
    with open(path, 'w') as f:
        f.write('not json')
    assert cu.read_node_defs_rev(path) == 0


# ---------------------------------------------------------------------------
# Source-level guarantees for every node class
# ---------------------------------------------------------------------------

NODE_FILES = ['today_node.py', 'tomorrow_node.py', 'month_node.py', 'weekday_node.py', 'time_node.py',
              'pattern_node.py']


def _src(name):
    with open(os.path.join(HERE, name)) as f:
        return f.read()


def test_every_node_reapplies_declared_uoms_and_pushes_with_uom():
    for name in NODE_FILES:
        src = _src(name)
        assert 'cal_utils.apply_declared_uoms(self)' in src, name
        assert 'cal_utils.push_drivers(' in src, name
        # no bare setDriver loop that would let a stored uom win
        assert 'self.setDriver(key, info[key]' not in src, name


def test_time_node_declares_no_second_and_all_uom_56():
    src = _src('time_node.py')
    assert 'SECOND' not in src
    assert set(re.findall(r"'uom': (\d+)", src)) == {'56'}


# ---------------------------------------------------------------------------
# Migration flow with a fake Polyglot (uses the real node classes and cal_ctl)
# ---------------------------------------------------------------------------

class _Notices(dict):
    def delete(self, key):
        self.pop(key, None)


class _FakePoly:
    ISY = 'ISY'
    DELNODEDONE = 'DELNODEDONE'

    def __init__(self, stored):
        self.stored = stored            # {address: [driver dicts]} as PG3 would hold them
        self.added = {}
        self.deleted = []
        self.sent = []
        self.subs = {}
        self.Notices = _Notices()

    def db_getNodeDrivers(self, addr=None, init=False):
        return [dict(d) for d in self.stored.get(addr, [])]

    def addNode(self, node, conn_status=None, rename=False):
        self.added[node.address] = node
        return node

    def delNode(self, address):
        self.deleted.append(address)
        self.added.pop(address, None)

    def getNodes(self):
        return dict(self.added)

    def getValidAddress(self, a):
        return a.lower()[:14]

    def getValidName(self, n):
        return n

    def send(self, message, kind):
        self.sent.append((message, kind))

    def subscribe(self, event, handler, *a):
        self.subs[event] = handler


class _Ctrl:
    name = 'Calendar'
    address = 'ctl'

    def __init__(self, poly, persist_dir):
        self.poly = poly
        self.persist_dir = str(persist_dir)


def _stale_store():
    return {
        'time': [{'driver': 'ST', 'value': 10, 'uom': 19}, {'driver': 'MINUTE', 'value': 5, 'uom': 44},
                 {'driver': 'SECOND', 'value': 9, 'uom': 57}],
        'today': [{'driver': 'ST', 'value': 3, 'uom': 25}, {'driver': 'DAYS_LEFT_MONTH', 'value': 18, 'uom': 10},
                  {'driver': 'DAYS_LEFT_YEAR', 'value': 49, 'uom': 10}],
    }


def _import_ctl():
    import cal_ctl
    return cal_ctl


def test_migration_removes_stale_nodes_then_readds_with_declared_uoms(tmp_path):
    ctl = _import_ctl()
    poly = _FakePoly(_stale_store())
    ctrl = _Ctrl(poly, tmp_path)
    ctl.sync_nodes(ctrl)
    # stale ones were deleted and not yet re-added; the others were added normally
    assert sorted(poly.deleted) == ['time', 'today']
    assert 'time' not in poly.added and 'today' not in poly.added
    assert {'tomorrow', 'month', 'weekday'} <= set(poly.added)
    assert cu.read_node_defs_rev(os.path.join(str(tmp_path), cu.MIGRATION_FILE)) == cu.NODE_DEFS_REV
    # Polyglot confirms the removals -> each node is re-added with the declared uoms (not the stored 19/44/10)
    ctl.node_deleted(ctrl, {'address': 'time'})
    assert 'time' in poly.added and 'today' not in poly.added
    ctl.node_deleted(ctrl, {'address': 'today'})
    assert 'today' in poly.added
    assert {d['uom'] for d in poly.added['time'].drivers} == {56}
    assert 'SECOND' not in [d['driver'] for d in poly.added['time'].drivers]
    uoms = {d['driver']: d['uom'] for d in poly.added['today'].drivers}
    assert uoms['DAYS_LEFT_MONTH'] == 56 and uoms['DAYS_LEFT_YEAR'] == 56
    # and the values they then report carry uom 56
    reported = [m['set'][0] for m, kind in poly.sent if kind == 'status' and m['set'][0]['address'] in ('time', 'today')]
    assert reported and all(r['uom'] == 56 for r in reported if r['driver'] in ('ST', 'MINUTE', 'DAYS_LEFT_MONTH', 'DAYS_LEFT_YEAR') and r['address'] == 'time' or r['driver'].startswith('DAYS_LEFT'))
    assert ctrl._cal_pending_del == {}


def test_migration_runs_only_once(tmp_path):
    ctl = _import_ctl()
    poly = _FakePoly(_stale_store())
    ctrl = _Ctrl(poly, tmp_path)
    ctl.sync_nodes(ctrl)
    ctl.node_deleted(ctrl, {'address': 'time'})
    ctl.node_deleted(ctrl, {'address': 'today'})
    assert len(poly.deleted) == 2
    # the stored records are still stale (as a real database may be), but the marker stops any repeat
    ctl.sync_nodes(ctrl)
    ctrl2 = _Ctrl(poly, tmp_path)          # a restart: new controller object, same persist dir
    ctl.sync_nodes(ctrl2)
    assert len(poly.deleted) == 2


def test_no_migration_when_stored_definitions_match(tmp_path):
    ctl = _import_ctl()
    from time_node import TimeNode
    from today_node import TodayNode
    poly = _FakePoly({'time': [dict(d) for d in TimeNode.drivers], 'today': [dict(d) for d in TodayNode.drivers]})
    ctrl = _Ctrl(poly, tmp_path)
    ctl.sync_nodes(ctrl)
    assert poly.deleted == []
    assert {'today', 'tomorrow', 'month', 'weekday', 'time'} <= set(poly.added)
    assert cu.read_node_defs_rev(os.path.join(str(tmp_path), cu.MIGRATION_FILE)) == cu.NODE_DEFS_REV


def test_fresh_install_has_nothing_to_migrate(tmp_path):
    ctl = _import_ctl()
    poly = _FakePoly({})
    ctrl = _Ctrl(poly, tmp_path)
    ctl.sync_nodes(ctrl)
    assert poly.deleted == []
    assert {'today', 'tomorrow', 'month', 'weekday', 'time'} <= set(poly.added)


def test_unconfirmed_removal_is_readded_after_the_wait(tmp_path):
    ctl = _import_ctl()
    poly = _FakePoly(_stale_store())
    ctrl = _Ctrl(poly, tmp_path)
    ctrl._cal_started = True
    ctl.sync_nodes(ctrl)
    assert 'time' not in poly.added
    ctl.short_poll(ctrl)                     # too early: still waiting for confirmation
    assert 'time' not in poly.added and 'today' not in poly.added
    for addr in list(ctrl._cal_pending_del):
        ctrl._cal_pending_del[addr] = time.time() - cu.MIGRATION_WAIT_SECS - 1
    ctl.short_poll(ctrl)
    assert 'time' in poly.added and 'today' in poly.added
    assert ctrl._cal_pending_del == {}
    assert len(poly.deleted) == 2            # no second round of deletes


def test_unwritable_marker_means_no_migration(tmp_path, monkeypatch):
    ctl = _import_ctl()
    poly = _FakePoly(_stale_store())
    ctrl = _Ctrl(poly, tmp_path)

    def boom(path, rev):
        raise OSError('read-only')

    monkeypatch.setattr(cu, 'write_node_defs_rev', boom)
    ctl.sync_nodes(ctrl)
    assert poly.deleted == []
    # the nodes are still added (declared uoms are re-applied anyway)
    assert 'time' in poly.added and 'today' in poly.added
    assert {d['uom'] for d in poly.added['time'].drivers} == {56}


def test_unrelated_delete_confirmations_are_ignored(tmp_path):
    ctl = _import_ctl()
    poly = _FakePoly(_stale_store())
    ctrl = _Ctrl(poly, tmp_path)
    ctl.sync_nodes(ctrl)
    ctl.node_deleted(ctrl, {'address': 'r_somepattern'})
    ctl.node_deleted(ctrl, None)
    assert 'time' not in poly.added and 'today' not in poly.added
    assert set(ctrl._cal_pending_del) == {'time', 'today'}
