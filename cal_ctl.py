"""Node management for the Calendar controller (kept out of plugin.py so it stays small)."""
import datetime
import os
import threading
import time

import udi_interface

import cal_utils
from today_node import TodayNode
from tomorrow_node import TomorrowNode
from month_node import MonthNode
from weekday_node import WeekdayNode
from time_node import TimeNode
from pattern_node import PatternNode

LOGGER = udi_interface.LOGGER

REFRESH_PASSES = 3  # a few quick re-sends after (re)building nodes, in case ISY hadn't registered them yet

# (address, node class, display name) of the nodes that always exist
FIXED_NODES = (('today', TodayNode, 'Today'),
               ('tomorrow', TomorrowNode, 'Tomorrow'),
               ('month', MonthNode, 'Month Info'),
               ('weekday', WeekdayNode, 'Weekday Instance'),
               ('time', TimeNode, 'Time'))


def _typed(ctrl):
    return getattr(ctrl, '_cal_typed', None) or {}


def southern(ctrl):
    v = _typed(ctrl).get('southern_hemisphere', False)
    if isinstance(v, str):
        return v.strip().lower() in ('true', '1', 'yes', 'y')
    return bool(v)


def _sun(ctrl):
    """The sunrise/sunset data shared with the Time node ({'tz', 'sunrise', 'sunset'})."""
    if getattr(ctrl, '_cal_sun', None) is None:
        ctrl._cal_sun = {}
    return ctrl._cal_sun


def _sunstate(ctrl):
    if getattr(ctrl, '_cal_sunstate', None) is None:
        ctrl._cal_sunstate = {'date': None, 'attempt_date': None, 'attempts': 0, 'last_try': 0.0, 'busy': False}
    return ctrl._cal_sunstate


def _pending(ctrl):
    """{address: time the removal was requested} of nodes being deleted for re-adding."""
    if getattr(ctrl, '_cal_pending_del', None) is None:
        ctrl._cal_pending_del = {}
    return ctrl._cal_pending_del


def _set_notice(ctrl, errors):
    try:
        if errors:
            ctrl.poly.Notices['calpatterns'] = ' '.join(errors)
        else:
            ctrl.poly.Notices.delete('calpatterns')
    except Exception as ex:
        LOGGER.debug('notices unavailable: %s', ex)


def _set_sun_notice(ctrl, message):
    try:
        if message:
            ctrl.poly.Notices['calsun'] = message
        else:
            ctrl.poly.Notices.delete('calsun')
    except Exception as ex:
        LOGGER.debug('notices unavailable: %s', ex)


# ---------------------------------------------------------------------------
# One-time migration of nodes whose stored definition is out of date
# ---------------------------------------------------------------------------

def _plan_migration(ctrl, nodes, pattern_addrs=()):
    """Addresses of nodes (fixed ones and the configured pattern nodes) that Polyglot stores with an
    outdated definition.

    Runs at most once per NODE_DEFS_REV: the marker is written before anything is deleted, and if it
    cannot be written no migration is attempted at all, so this can never repeat on every restart.
    """
    path = os.path.join(ctrl.persist_dir, cal_utils.MIGRATION_FILE)
    if cal_utils.read_node_defs_rev(path) >= cal_utils.NODE_DEFS_REV:
        return []
    candidates = [(addr, cls.drivers) for addr, cls, _name in FIXED_NODES]
    candidates += [(addr, PatternNode.drivers) for addr in pattern_addrs]
    declared, stored = {}, {}
    for addr, drivers in candidates:
        if addr in nodes:
            continue
        declared[addr] = drivers
        try:
            stored[addr] = ctrl.poly.db_getNodeDrivers(addr, True) or []
        except Exception as ex:
            LOGGER.debug('stored record for %s unavailable: %s', addr, ex)
            stored[addr] = []
    stale = cal_utils.stale_addresses(stored, declared)
    try:
        cal_utils.write_node_defs_rev(path, cal_utils.NODE_DEFS_REV)
    except Exception as ex:
        LOGGER.warning('Could not record the node migration marker (%s); skipping the migration', ex)
        return []
    return stale


def node_deleted(ctrl, data):
    """Handler for Polyglot's DELNODEDONE: re-add a migrated node once its removal is confirmed."""
    addr = data.get('address') if isinstance(data, dict) else None
    with cal_utils.LOCK:
        pending = _pending(ctrl)
        if addr not in pending:
            return
        pending.pop(addr)
        LOGGER.info('Node %s removed; re-adding it with the current definition', addr)
        sync_nodes(ctrl)
        update_all(ctrl)


def _check_pending(ctrl):
    """If Polyglot never confirmed a removal, re-add the node anyway after MIGRATION_WAIT_SECS."""
    pending = getattr(ctrl, '_cal_pending_del', None)
    if pending and time.time() - min(pending.values()) > cal_utils.MIGRATION_WAIT_SECS:
        LOGGER.warning('Removal of %s was not confirmed within %d s; re-adding anyway',
                       sorted(pending), cal_utils.MIGRATION_WAIT_SECS)
        pending.clear()
        sync_nodes(ctrl)
        update_all(ctrl)


def sync_nodes(ctrl):
    """Create the fixed nodes, and add/remove pattern nodes to match the configured patterns."""
    with cal_utils.LOCK:
        poly = ctrl.poly
        nodes = getattr(ctrl, '_cal_nodes', None)
        if nodes is None:
            nodes = ctrl._cal_nodes = {}
        pending = _pending(ctrl)

        # Work out the configured patterns first: the migration below needs their addresses.
        patterns, errors = cal_utils.parse_patterns(_typed(ctrl).get('patterns'))
        _set_notice(ctrl, errors)
        for e in errors:
            LOGGER.warning('patterns: %s', e)

        wanted = {}
        for p in patterns:
            p['address'] = poly.getValidAddress(p['address'])
            wanted[p['address']] = p

        for addr in _plan_migration(ctrl, nodes, list(wanted)):
            LOGGER.warning('Node %s is stored with an outdated definition; removing it so it is re-added with the '
                           'current one (programs using its properties need re-selecting)', addr)
            try:
                poly.delNode(addr)
                pending[addr] = time.time()
            except Exception as ex:
                LOGGER.warning('could not remove node %s: %s', addr, ex)

        for addr, cls, nm in FIXED_NODES:
            if addr in nodes or addr in pending:
                continue
            node = cls(poly, ctrl.address, addr, nm)
            if addr == 'time':
                node.sun = _sun(ctrl)
            poly.addNode(node)
            nodes[addr] = node

        # Remove pattern nodes that are no longer configured (ones created this run and ones from earlier runs).
        stale = {a for a in nodes if a.startswith('r_') and a not in wanted}
        try:
            stale |= {a for a in poly.getNodes() if str(a).startswith('r_') and a not in wanted}
        except Exception as ex:
            LOGGER.debug('getNodes unavailable: %s', ex)
        for addr in stale:
            try:
                poly.delNode(addr)
            except Exception as ex:
                LOGGER.warning('could not delete node %s: %s', addr, ex)
            nodes.pop(addr, None)

        for addr, p in wanted.items():
            if addr in pending:
                continue        # being removed for a definition update; re-added once Polyglot confirms
            node = nodes.get(addr)
            if node is None:
                node = PatternNode(poly, ctrl.address, addr, poly.getValidName(p['label']), p)
                poly.addNode(node)
                nodes[addr] = node
            else:
                node.pattern = p
        ctrl._cal_refresh = REFRESH_PASSES


def update_all(ctrl):
    with cal_utils.LOCK:
        today = datetime.date.today()
        ctrl._cal_last_date = today
        south = southern(ctrl)
        for node in list(getattr(ctrl, '_cal_nodes', {}).values()):
            try:
                node.update(today, south)
            except Exception as ex:
                LOGGER.error('%s: update failed: %s', getattr(node, 'name', '?'), ex)


# ---------------------------------------------------------------------------
# Hub sunrise/sunset (Time node)
# ---------------------------------------------------------------------------

def isy_info(ctrl, info):
    """Handler for Polyglot's ISY event: the hub's connection details (None if not accessible)."""
    if not info:
        with cal_utils.LOCK:
            ctrl._cal_isy = None
        LOGGER.warning('Hub connection details are not available; sunrise/sunset cannot be read')
        _set_sun_notice(ctrl, 'The plugin cannot reach the hub, so sunrise and sunset are unavailable. '
                              'Check that hub access is enabled for this plugin.')
        return
    with cal_utils.LOCK:
        ctrl._cal_isy = dict(info)
    LOGGER.info('Hub connection details received (%s)', info.get('isy_ip_address'))
    maybe_fetch_sun(ctrl)


def maybe_fetch_sun(ctrl):
    """Start a background read of the hub's sunrise/sunset if one is due."""
    with cal_utils.LOCK:
        isy = getattr(ctrl, '_cal_isy', None)
        state = _sunstate(ctrl)
        today = datetime.date.today()
        now_ts = time.time()
        if not cal_utils.sun_fetch_due(state, now_ts, today, bool(isy)):
            return
        state['busy'] = True
        state['last_try'] = now_ts
        isy = dict(isy)
    threading.Thread(target=_sun_worker, args=(ctrl, isy, today), name='cal-sun', daemon=True).start()


def _sun_worker(ctrl, isy, today):
    parsed = None
    try:
        parsed = cal_utils.parse_hub_time(cal_utils.fetch_hub_time(isy))
    except Exception as ex:
        LOGGER.warning('Could not read sunrise/sunset from the hub: %s', ex)
    with cal_utils.LOCK:
        ok = cal_utils.sun_result(_sunstate(ctrl), parsed, today, time.time())
        if ok:
            sun = _sun(ctrl)
            sun.clear()
            sun.update(parsed)
            LOGGER.info('Hub sunrise/sunset read (timezone %s)', parsed.get('tz'))
            node = getattr(ctrl, '_cal_nodes', {}).get('time')
            if node is not None:
                try:
                    node.update(today)
                except Exception as ex:
                    LOGGER.error('Time: update failed: %s', ex)
            _set_sun_notice(ctrl, None)
        else:
            if parsed is not None:
                LOGGER.warning('The hub time response had no sunrise/sunset values')
            _set_sun_notice(ctrl, 'Could not read sunrise and sunset from the hub; will retry every minute.')


def start(ctrl):
    try:
        ctrl.poly.subscribe(ctrl.poly.DELNODEDONE, lambda data: node_deleted(ctrl, data))
    except Exception as ex:
        LOGGER.warning('Could not subscribe to node removal events: %s', ex)
    with cal_utils.LOCK:
        ctrl._cal_started = True
        sync_nodes(ctrl)
        update_all(ctrl)
    try:
        ctrl.poly.subscribe(ctrl.poly.ISY, lambda info: isy_info(ctrl, info))
        ctrl.poly.send({'getIsyInfo': {}}, 'system')
    except Exception as ex:
        LOGGER.warning('Could not request hub connection details: %s', ex)
    LOGGER.info('%s: calendar nodes ready', ctrl.name)


def rebuild(ctrl):
    with cal_utils.LOCK:
        sync_nodes(ctrl)
        update_all(ctrl)


def set_typed(ctrl, custom_params):
    """Store the customer's typed config; if already running, apply it right away."""
    with cal_utils.LOCK:
        try:
            ctrl._cal_typed = dict(custom_params or {})
        except Exception:
            ctrl._cal_typed = {}
        if getattr(ctrl, '_cal_started', False):
            rebuild(ctrl)


def short_poll(ctrl):
    """Cheap check every few seconds: refresh on date rollover or after a (re)build; tick the clock; read sun data if due."""
    with cal_utils.LOCK:
        if not getattr(ctrl, '_cal_started', False):
            return
        _check_pending(ctrl)
        pending = getattr(ctrl, '_cal_refresh', 0)
        if pending > 0 or getattr(ctrl, '_cal_last_date', None) != datetime.date.today():
            ctrl._cal_refresh = max(0, pending - 1)
            update_all(ctrl)
        else:
            node = getattr(ctrl, '_cal_nodes', {}).get('time')
            if node is not None:
                try:
                    node.tick()
                except Exception as ex:
                    LOGGER.error('Time: tick failed: %s', ex)
        maybe_fetch_sun(ctrl)
