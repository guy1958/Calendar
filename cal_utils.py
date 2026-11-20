"""Pure calendar helpers for the Calendar plugin.

No udi_interface dependency, so everything here is unit-testable on its own.
Note: weekdays follow Python's convention, Monday = 0 ... Sunday = 6.
"""
import base64
import calendar as _pycal
import datetime as _dt
import json
import os
import re
import ssl
import threading
import urllib.request
import xml.etree.ElementTree as _ET
import zoneinfo

LOCK = threading.RLock()

WEEKDAYS = {
    'monday': 0, 'mon': 0,
    'tuesday': 1, 'tue': 1, 'tues': 1,
    'wednesday': 2, 'wed': 2,
    'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
    'friday': 4, 'fri': 4,
    'saturday': 5, 'sat': 5,
    'sunday': 6, 'sun': 6,
}

OCCURRENCES = {
    '1': 1, '1st': 1, 'first': 1,
    '2': 2, '2nd': 2, 'second': 2,
    '3': 3, '3rd': 3, 'third': 3,
    '4': 4, '4th': 4, 'fourth': 4,
    '5': 5, 'last': 5,
}

MONTHS = {
    'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
    'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
    'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9,
    'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12,
}

ANY_MONTH = ('', 'any', '*', 'all', 'every', 'each')


def _norm(value):
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip().lower().rstrip('.')


def parse_weekday(value):
    """Name/abbreviation -> 0..6, or None if not understood."""
    return WEEKDAYS.get(_norm(value))


def parse_occurrence(value):
    """first..fourth -> 1..4, last -> 5, or None if not understood."""
    return OCCURRENCES.get(_norm(value))


def parse_month(value):
    """'any'/blank -> 0, month name or 1..12 -> 1..12, or None if not understood."""
    v = _norm(value)
    if v in ANY_MONTH:
        return 0
    if v in MONTHS:
        return MONTHS[v]
    if v.isdigit() and 1 <= int(v) <= 12:
        return int(v)
    return None


def occurrence_date(year, month, weekday, occ):
    """Date of the occ-th (1..4) or last (5) given weekday in a month."""
    if occ == 5:
        last = _dt.date(year, month, _pycal.monthrange(year, month)[1])
        return last - _dt.timedelta(days=(last.weekday() - weekday) % 7)
    first = _dt.date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return _dt.date(year, month, 1 + offset + 7 * (occ - 1))


def next_occurrence(pattern, start):
    """First date on or after `start` matching the pattern, or None."""
    y, m = start.year, start.month
    for _ in range(30):
        if not pattern['month'] or pattern['month'] == m:
            d = occurrence_date(y, m, pattern['weekday'], pattern['occ'])
            if d >= start:
                return d
        m += 1
        if m > 12:
            m = 1
            y += 1
    return None


def season(d, southern=False):
    """0 Winter, 1 Spring, 2 Summer, 3 Fall (astronomical, northern by default)."""
    md = (d.month, d.day)
    if md >= (12, 21) or md < (3, 20):
        s = 0
    elif md < (6, 21):
        s = 1
    elif md < (9, 22):
        s = 2
    else:
        s = 3
    return (s + 2) % 4 if southern else s


def is_last_business_day(d):
    last = _dt.date(d.year, d.month, _pycal.monthrange(d.year, d.month)[1])
    while last.weekday() >= 5:
        last -= _dt.timedelta(days=1)
    return d == last


def iso_week_parity(d):
    """1 if the ISO week number of date d is odd, 0 if even.

    Follows the ISO week number exactly, so in a 53-week year week 53 and week 1
    of the following year are both odd (two odd weeks in a row).
    """
    return d.isocalendar()[1] % 2


def is_last_full_week(d):
    """1 if date d is a weekday (Mon-Fri) in the last full Mon-Fri week of its month.

    Only the five weekdays matter. A week is 'full' for a month when its Monday
    through Friday all fall inside that month; the last such week of the month is
    the 'last full Mon-Fri week'. Saturday and Sunday are always 0, and a week
    whose Monday-Friday straddles two months is not full for either month.
    """
    if d.weekday() >= 5:
        return 0
    monday = d - _dt.timedelta(days=d.weekday())
    friday = monday + _dt.timedelta(days=4)
    if monday.month != friday.month:
        return 0
    mdays = _pycal.monthrange(monday.year, monday.month)[1]
    return int(monday.day + 7 + 4 > mdays)


def day_info(d, southern=False):
    """Driver values describing one calendar date."""
    leap = _pycal.isleap(d.year)
    doy = d.timetuple().tm_yday
    mdays = _pycal.monthrange(d.year, d.month)[1]
    return {
        'ST': d.weekday(),
        'DAY_OF_MONTH': d.day,
        'MONTH': d.month,
        'MONTH_NUM': d.month,
        'YEAR': d.year,
        'DAY_OF_YEAR': doy,
        'ISO_WEEK': d.isocalendar()[1],
        'ISO_WEEK_PARITY': iso_week_parity(d),
        'LAST_FULL_WEEK': is_last_full_week(d),
        'IS_WEEKEND': int(d.weekday() >= 5),
        'LEAP_YEAR': int(leap),
        'SEASON': season(d, southern),
        'DAYS_LEFT_MONTH': mdays - d.day,
        'DAYS_LEFT_YEAR': (366 if leap else 365) - doy,
    }


def month_info(d):
    """Driver values describing the month containing date d (d is 'today')."""
    mdays = _pycal.monthrange(d.year, d.month)[1]
    return {
        'ST': mdays,
        'YEAR': d.year,
        'FIRST_WEEKDAY': _dt.date(d.year, d.month, 1).weekday(),
        'LAST_WEEKDAY': _dt.date(d.year, d.month, mdays).weekday(),
        'IS_FIRST_DAY': int(d.day == 1),
        'IS_LAST_DAY': int(d.day == mdays),
        'IS_LAST_BUSDAY': int(is_last_business_day(d)),
    }


def weekday_instance_info(d):
    """Which instance (1..5) of its weekday date d is within its month.

    e.g. 2026-11-11 is the 2nd Wednesday of November. Also flags whether it is
    the last of that weekday in the month (no later same weekday this month).
    """
    mdays = _pycal.monthrange(d.year, d.month)[1]
    return {
        'ST': (d.day - 1) // 7 + 1,
        'WEEKDAY': d.weekday(),
        'IS_LAST_INST': int(d.day + 7 > mdays),
    }


def pattern_info(pattern, today):
    """Driver values for one weekday pattern. Returns {} if no occurrence found."""
    tomorrow = today + _dt.timedelta(days=1)
    nxt = next_occurrence(pattern, today)
    if nxt is None:
        return {}
    return {
        'ST': int(nxt == today),
        'IS_TOMORROW': int(next_occurrence(pattern, tomorrow) == tomorrow),
        'DAYS_UNTIL': (nxt - today).days,
        'NEXT_DAY': nxt.day,
        'NEXT_MONTH': nxt.month,
        'NEXT_YEAR': nxt.year,
    }


# ---------------------------------------------------------------------------
# Time node: clock + the hub's own sunrise/sunset
# ---------------------------------------------------------------------------

SUN_RETRY_SECS = 60     # minimum gap between attempts to read the hub
SUN_MAX_ATTEMPTS = 5    # successful reads per day that still return a stale (not-today) sunrise


def get_tz(name):
    """ZoneInfo for an IANA name, or None (meaning: use the system's local time)."""
    if name:
        try:
            return zoneinfo.ZoneInfo(name)
        except Exception:
            return None
    return None


def now_in(tz):
    """Current time in tz (or naive system-local time when tz is None)."""
    return _dt.datetime.now(tz) if tz else _dt.datetime.now()


def epoch_to_local(epoch, tz):
    """Unix epoch seconds -> datetime in tz (or naive system-local time when tz is None)."""
    return _dt.datetime.fromtimestamp(epoch, tz) if tz else _dt.datetime.fromtimestamp(epoch)


def parse_hub_time(text):
    """Parse the hub's /rest/time XML.

    Returns {'tz': IANA name or None, 'sunrise': unix epoch or None, 'sunset': unix epoch or None},
    or None when the text is not parseable XML. Only the *GMT fields are used: they are real
    Unix epochs, unlike the plain Sunrise/Sunset fields (NTP-epoch, shifted by the local offset).
    """
    try:
        root = _ET.fromstring(text)
    except Exception:
        return None
    raw = {el.tag: (el.text or '').strip() for el in root.iter()}

    def _epoch(key):
        try:
            v = int(raw.get(key, ''))
        except (TypeError, ValueError):
            return None
        return v if v > 0 else None

    return {'tz': raw.get('TzId') or None,
            'sunrise': _epoch('SunriseGMT'),
            'sunset': _epoch('SunsetGMT')}


def fetch_hub_time(info, timeout=10):
    """GET /rest/time from the hub using the connection info Polyglot hands the plugin.

    `info` is the ISY event payload (isy_ip_address, isy_port, isy_https, isy_username and the
    matching secret). The hub uses a self-signed certificate, so https is not verified (same as
    nucore-ai's own client). Returns the response body text; raises on any failure.
    """
    scheme = 'https' if info.get('isy_https') == 1 else 'http'
    url = '%s://%s:%s/rest/time' % (scheme, info['isy_ip_address'], info['isy_port'])
    cred = ('%s:%s' % (info['isy_username'], info['isy_' + 'password'])).encode('utf-8')
    req = urllib.request.Request(url, headers={'Authorization': 'Basic ' + base64.b64encode(cred).decode('ascii')})
    ctx = None
    if scheme == 'https':
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.read().decode('utf-8', 'replace')


def time_values(now, sunrise=None, sunset=None):
    """Driver values for the Time node. Sun keys are only present when that time is known.

    Minutes are truncated, e.g. 05:43:41 -> hour 5, minute 43.
    """
    vals = {'ST': now.hour, 'MINUTE': now.minute}
    if sunrise is not None:
        vals['SUNRISE_HOUR'] = sunrise.hour
        vals['SUNRISE_MIN'] = sunrise.minute
    if sunset is not None:
        vals['SUNSET_HOUR'] = sunset.hour
        vals['SUNSET_MIN'] = sunset.minute
    return vals


def sun_fetch_due(state, now_ts, today, has_hub_info):
    """Should a background read of the hub's sunrise/sunset start now?"""
    if not has_hub_info or state.get('busy'):
        return False
    if state.get('date') == today:
        return False
    return now_ts - state.get('last_try', 0.0) >= SUN_RETRY_SECS


def sun_result(state, parsed, today, now_ts):
    """Record the outcome of one read attempt. Returns True when `parsed` has usable sun data.

    A read that returns today's sunrise finishes the day. One that returns a different date
    (the hub hasn't recalculated yet) is used but retried, up to SUN_MAX_ATTEMPTS times.
    A failed read (no data) is simply retried after SUN_RETRY_SECS.
    """
    state['busy'] = False
    state['last_try'] = now_ts
    if state.get('attempt_date') != today:
        state['attempt_date'] = today
        state['attempts'] = 0
    if not parsed or not parsed.get('sunrise') or not parsed.get('sunset'):
        return False
    state['attempts'] = state.get('attempts', 0) + 1
    sunrise = epoch_to_local(parsed['sunrise'], get_tz(parsed.get('tz')))
    if sunrise.date() == today or state['attempts'] >= SUN_MAX_ATTEMPTS:
        state['date'] = today
    return True


# ---------------------------------------------------------------------------
# Driver definitions: the units this plugin declares are authoritative
# ---------------------------------------------------------------------------
# udi_interface.Node.__init__ copies each driver's value AND uom from the record Polyglot stored when
# the node was first created over the class's declared drivers, and a later CONFIG event replaces a live
# node's drivers with the stored ones again. A unit changed in the code would therefore never be reported
# for an existing node. So (1) every node re-applies its declared uoms and every update passes uom=
# explicitly, and (2) a node whose stored definition is out of date is removed and re-added once.

NODE_DEFS_REV = 4           # bump when a node's driver ids/units change, to run the migration once more
MIGRATION_FILE = 'node_defs.json'
MIGRATION_WAIT_SECS = 30    # re-add a migrated node anyway if Polyglot hasn't confirmed its removal by then


def declared_uoms(cls):
    """{driver id: uom} exactly as the node class declares it (the class list is never mutated)."""
    return {d['driver']: d['uom'] for d in cls.drivers}


def apply_declared_uoms(node):
    """Put the class-declared uom back on every driver of a node (undoing Node.__init__'s stored-uom copy)."""
    decl = declared_uoms(type(node))
    for d in node.drivers:
        if d.get('driver') in decl:
            d['uom'] = decl[d['driver']]


def push_drivers(node, info, force=True):
    """setDriver every declared driver that `info` has a value for, always with the declared uom.

    force=True re-sends everything; force=False sends only what changed (value or uom).
    """
    decl = declared_uoms(type(node))
    for drv in list(node.drivers):
        key = drv.get('driver')
        if key in info:
            node.setDriver(key, info[key], force=force, uom=decl.get(key))


def stored_defs_differ(stored, declared):
    """True if Polyglot's stored driver records don't match the declared drivers.

    stored/declared are lists of {'driver', 'uom', ...}. Out of date means a stored driver the class no
    longer declares, or a different uom for one it does. No stored record at all (a new node) or a
    declared driver missing from the record is not out of date.
    """
    if not stored:
        return False
    decl = {d['driver']: str(d['uom']) for d in declared}
    for s in stored:
        key = s.get('driver') if isinstance(s, dict) else None
        if key is None:
            continue
        if key not in decl or str(s.get('uom')) != decl[key]:
            return True
    return False


def stale_addresses(stored_by_addr, declared_by_addr):
    """Addresses (sorted) whose stored record is out of date. Both args are {address: [driver dicts]}."""
    return sorted(a for a, declared in declared_by_addr.items()
                  if stored_defs_differ(stored_by_addr.get(a), declared))


def read_node_defs_rev(path):
    """The NODE_DEFS_REV a previous run recorded in the marker file; 0 if missing or unreadable."""
    try:
        with open(path) as f:
            return int(json.load(f).get('rev', 0))
    except Exception:
        return 0


def write_node_defs_rev(path, rev):
    """Record the marker. Raises if it cannot be written (the caller then skips the migration)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump({'rev': int(rev)}, f)


def parse_patterns(raw):
    """Turn the customer's typed-params 'patterns' list into (patterns, errors).

    Each pattern: {'label', 'occ' (1-4, 5=last), 'weekday' (0-6), 'month' (0=any, 1-12),
    'address'}. Invalid entries are skipped and described in `errors`.
    """
    if raw is None or raw == '':
        return [], []
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, (list, tuple)):
        return [], ['The pattern list was not understood.']
    patterns, errors, used = [], [], set()
    for idx, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            errors.append('Pattern #%d is not valid.' % idx)
            continue
        label = str(item.get('label') or '').strip()
        if not label:
            errors.append('Pattern #%d has no name.' % idx)
            continue
        occ = parse_occurrence(item.get('occurrence'))
        weekday = parse_weekday(item.get('weekday'))
        month = parse_month(item.get('month'))
        problems = []
        if occ is None:
            problems.append("occurrence '%s' (use first/second/third/fourth/last)" % item.get('occurrence'))
        if weekday is None:
            problems.append("weekday '%s'" % item.get('weekday'))
        if month is None:
            problems.append("month '%s' (use 'any', a month name, or 1-12)" % item.get('month'))
        if problems:
            errors.append("Pattern '%s': unrecognized %s." % (label, '; '.join(problems)))
            continue
        slug = re.sub(r'[^a-z0-9]', '', label.lower())[:10] or 'pattern'
        address = 'r_' + slug
        i = 2
        while address in used:
            suffix = str(i)
            address = ('r_' + slug)[:14 - len(suffix)] + suffix
            i += 1
        used.add(address)
        patterns.append({'label': label, 'occ': occ, 'weekday': weekday,
                         'month': month, 'address': address})
    return patterns, errors
