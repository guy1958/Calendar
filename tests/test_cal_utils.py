import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import cal_utils as cu


def test_occurrence_dates():
    # US Thanksgiving 2026: 4th Thursday of November
    assert cu.occurrence_date(2026, 11, 3, 4) == dt.date(2026, 11, 26)
    # Last Monday of May 2026
    assert cu.occurrence_date(2026, 5, 0, 5) == dt.date(2026, 5, 25)
    # 2nd Tuesday of November 2026
    assert cu.occurrence_date(2026, 11, 1, 2) == dt.date(2026, 11, 10)


def test_next_occurrence_rolls_to_next_year_for_month_pattern():
    pat = {'occ': 4, 'weekday': 3, 'month': 11}
    assert cu.next_occurrence(pat, dt.date(2026, 11, 26)) == dt.date(2026, 11, 26)
    assert cu.next_occurrence(pat, dt.date(2026, 11, 27)) == dt.date(2027, 11, 25)


def test_next_occurrence_any_month():
    pat = {'occ': 2, 'weekday': 1, 'month': 0}
    assert cu.next_occurrence(pat, dt.date(2026, 11, 11)) == dt.date(2026, 12, 8)


def test_pattern_info_today_and_tomorrow():
    pat = {'occ': 4, 'weekday': 3, 'month': 11}
    on_day = cu.pattern_info(pat, dt.date(2026, 11, 26))
    assert on_day['ST'] == 1 and on_day['DAYS_UNTIL'] == 0
    day_before = cu.pattern_info(pat, dt.date(2026, 11, 25))
    assert day_before['ST'] == 0 and day_before['IS_TOMORROW'] == 1 and day_before['DAYS_UNTIL'] == 1


def test_season():
    assert cu.season(dt.date(2026, 1, 15)) == 0
    assert cu.season(dt.date(2026, 7, 4)) == 2
    assert cu.season(dt.date(2026, 1, 15), southern=True) == 2


def test_day_info():
    info = cu.day_info(dt.date(2026, 11, 11))
    assert info['ST'] == 2  # Wednesday
    assert info['DAY_OF_YEAR'] == 315
    assert info['DAYS_LEFT_YEAR'] == 50
    assert info['DAYS_LEFT_MONTH'] == 19
    assert info['LEAP_YEAR'] == 0 and info['IS_WEEKEND'] == 0


def test_last_business_day():
    assert cu.is_last_business_day(dt.date(2026, 5, 29)) is True
    assert cu.is_last_business_day(dt.date(2026, 5, 31)) is False
    info = cu.month_info(dt.date(2026, 2, 1))
    assert info['ST'] == 28 and info['IS_FIRST_DAY'] == 1


def test_parse_patterns():
    pats, errors = cu.parse_patterns([
        {'label': 'Thanksgiving', 'occurrence': '4th', 'weekday': 'Thursday', 'month': 'November'},
        {'label': 'Trash', 'occurrence': 'last', 'weekday': 'fri', 'month': 'any'},
        {'label': 'Bad', 'occurrence': 'ninth', 'weekday': 'Funday', 'month': 'any'},
        {'label': '', 'occurrence': 'first', 'weekday': 'Monday', 'month': 'any'},
    ])
    assert [p['label'] for p in pats] == ['Thanksgiving', 'Trash']
    assert pats[0]['occ'] == 4 and pats[0]['weekday'] == 3 and pats[0]['month'] == 11
    assert pats[1]['occ'] == 5 and pats[1]['weekday'] == 4 and pats[1]['month'] == 0
    assert len(errors) == 2


def test_pattern_addresses_unique_and_short():
    pats, _ = cu.parse_patterns([
        {'label': 'A very long pattern name here', 'occurrence': '1', 'weekday': 'mon', 'month': ''},
        {'label': 'A very long pattern name there', 'occurrence': '2', 'weekday': 'mon', 'month': ''},
    ])
    addrs = [p['address'] for p in pats]
    assert len(set(addrs)) == 2 and all(len(a) <= 14 for a in addrs)


def test_weekday_instance_today():
    # Wednesday Nov 11, 2026 is the 2nd Wednesday; Nov 25 is the last one
    info = cu.weekday_instance_info(dt.date(2026, 11, 11))
    assert info == {'ST': 2, 'WEEKDAY': 2, 'IS_LAST_INST': 0}
    info = cu.weekday_instance_info(dt.date(2026, 11, 25))
    assert info['ST'] == 4 and info['IS_LAST_INST'] == 1


def test_weekday_instance_boundaries():
    # 1st of month is always the 1st instance; days 7 and 8 straddle 1st/2nd
    assert cu.weekday_instance_info(dt.date(2026, 11, 1))['ST'] == 1
    assert cu.weekday_instance_info(dt.date(2026, 11, 7))['ST'] == 1
    assert cu.weekday_instance_info(dt.date(2026, 11, 8))['ST'] == 2
    # Nov 2026 has five Mondays (2, 9, 16, 23, 30): the 30th is the 5th and the last
    info = cu.weekday_instance_info(dt.date(2026, 11, 30))
    assert info['ST'] == 5 and info['IS_LAST_INST'] == 1
    # Feb 2026 (28 days): the 22nd is the 4th Sunday and the last
    info = cu.weekday_instance_info(dt.date(2026, 2, 22))
    assert info['ST'] == 4 and info['IS_LAST_INST'] == 1


def test_weekday_instance_agrees_with_occurrence_date():
    # Cross-check against the independent occurrence_date() for every day of 2026 and 2028
    for year in (2026, 2028):
        d = dt.date(year, 1, 1)
        while d.year == year:
            info = cu.weekday_instance_info(d)
            assert cu.occurrence_date(d.year, d.month, d.weekday(), info['ST']) == d
            if info['IS_LAST_INST']:
                assert cu.occurrence_date(d.year, d.month, d.weekday(), 5) == d
            d += dt.timedelta(days=1)


def test_iso_week_parity_today():
    # Nov 11, 2026 is in ISO week 46 -> even (0)
    info = cu.day_info(dt.date(2026, 11, 11))
    assert info['ISO_WEEK'] == 46
    assert info['ISO_WEEK_PARITY'] == 0
    # The following Monday starts week 47 -> odd (1)
    assert cu.day_info(dt.date(2026, 11, 16))['ISO_WEEK'] == 47
    assert cu.day_info(dt.date(2026, 11, 16))['ISO_WEEK_PARITY'] == 1


def test_iso_week_parity_flips_on_monday_not_sunday():
    # Sunday Nov 15 is still week 46 (even); Monday Nov 16 is week 47 (odd)
    assert cu.iso_week_parity(dt.date(2026, 11, 15)) == 0
    assert cu.iso_week_parity(dt.date(2026, 11, 16)) == 1


def test_iso_week_parity_53_week_year_boundary():
    # 2026 has 53 ISO weeks: Dec 28, 2026 - Jan 3, 2027 is week 53 (odd)
    assert cu.day_info(dt.date(2026, 12, 28))['ISO_WEEK'] == 53
    assert cu.iso_week_parity(dt.date(2026, 12, 28)) == 1
    assert cu.iso_week_parity(dt.date(2027, 1, 3)) == 1
    # Jan 4, 2027 is week 1 of 2027 (odd) -- two odd weeks in a row
    assert cu.day_info(dt.date(2027, 1, 4))['ISO_WEEK'] == 1
    assert cu.iso_week_parity(dt.date(2027, 1, 4)) == 1
    # ...and week 2 is even again
    assert cu.iso_week_parity(dt.date(2027, 1, 11)) == 0


def test_iso_week_parity_matches_week_number_every_day():
    # Parity must always equal ISO week number % 2, for every day of 2026-2028
    d = dt.date(2026, 1, 1)
    while d.year <= 2028:
        info = cu.day_info(d)
        assert info['ISO_WEEK_PARITY'] == info['ISO_WEEK'] % 2
        assert info['ISO_WEEK_PARITY'] in (0, 1)
        d += dt.timedelta(days=1)


def test_month_number_today():
    # Nov 11, 2026 is in the 11th month
    info = cu.day_info(dt.date(2026, 11, 11))
    assert info['MONTH_NUM'] == 11
    assert info['MONTH'] == 11


def test_month_number_range_and_boundaries():
    assert cu.day_info(dt.date(2026, 1, 1))['MONTH_NUM'] == 1
    assert cu.day_info(dt.date(2026, 12, 31))['MONTH_NUM'] == 12
    # Every day of 2026-2028 reports 1..12 and matches the date's own month
    d = dt.date(2026, 1, 1)
    while d.year <= 2028:
        n = cu.day_info(d)['MONTH_NUM']
        assert 1 <= n <= 12 and n == d.month
        d += dt.timedelta(days=1)


def test_last_full_week_today_is_no():
    # Nov 11, 2026 is in the week of Nov 9-13: a full Mon-Fri week, but not the last one
    assert cu.is_last_full_week(dt.date(2026, 11, 11)) == 0
    assert cu.day_info(dt.date(2026, 11, 11))['LAST_FULL_WEEK'] == 0


def test_last_full_week_november_2026():
    # Mondays: 2, 9, 16, 23, 30. Nov 23-27 is the last Mon-Fri fully inside November.
    for day in range(16, 21):  # Mon Nov 16 .. Fri Nov 20
        assert cu.is_last_full_week(dt.date(2026, 11, day)) == 0
    for day in range(23, 28):  # Mon Nov 23 .. Fri Nov 27
        assert cu.is_last_full_week(dt.date(2026, 11, day)) == 1
    # Weekend after it is No
    assert cu.is_last_full_week(dt.date(2026, 11, 28)) == 0
    assert cu.is_last_full_week(dt.date(2026, 11, 29)) == 0
    # Nov 30 - Dec 4 straddles two months: not full for either
    for day in (dt.date(2026, 11, 30), dt.date(2026, 12, 1), dt.date(2026, 12, 4)):
        assert cu.is_last_full_week(day) == 0


def test_last_full_week_weekend_never_counts():
    # Oct 26-30, 2026 is the last full Mon-Fri week of October; its Sat/Sun are No
    for day in range(26, 31):
        assert cu.is_last_full_week(dt.date(2026, 10, day)) == 1
    assert cu.is_last_full_week(dt.date(2026, 10, 31)) == 0
    assert cu.is_last_full_week(dt.date(2026, 11, 1)) == 0
    assert cu.is_last_full_week(dt.date(2026, 11, 2)) == 0
    # Every Saturday and Sunday across 2026-2028 is No
    d = dt.date(2026, 1, 1)
    while d.year <= 2028:
        if d.weekday() >= 5:
            assert cu.is_last_full_week(d) == 0
        d += dt.timedelta(days=1)


def test_last_full_week_month_ending_on_friday():
    # April 2027 ends on Friday the 30th, so Apr 26-30 is a full week and the last one
    assert dt.date(2027, 4, 30).weekday() == 4
    for day in range(26, 31):
        assert cu.is_last_full_week(dt.date(2027, 4, day)) == 1
    assert cu.is_last_full_week(dt.date(2027, 4, 19)) == 0


def test_last_full_week_month_ending_on_thursday():
    # Dec 2026 ends Thursday the 31st: Dec 21-25 is the last full week; Dec 28-Jan 1 is not full
    for day in range(21, 26):
        assert cu.is_last_full_week(dt.date(2026, 12, day)) == 1
    assert cu.is_last_full_week(dt.date(2026, 12, 26)) == 0
    assert cu.is_last_full_week(dt.date(2026, 12, 28)) == 0
    assert cu.is_last_full_week(dt.date(2026, 12, 31)) == 0


def test_last_full_week_five_weekdays_per_month():
    # Every month of 2026-2028 has exactly five flagged days: one Mon-Fri run inside that month
    flagged = {}
    d = dt.date(2026, 1, 1)
    while d <= dt.date(2028, 12, 31):
        if cu.is_last_full_week(d):
            flagged.setdefault((d.year, d.month), []).append(d)
        d += dt.timedelta(days=1)
    for year in (2026, 2027, 2028):
        for month in range(1, 13):
            days = flagged.get((year, month), [])
            assert len(days) == 5, (year, month, days)
            assert [x.weekday() for x in days] == [0, 1, 2, 3, 4]
            # the following Mon-Fri would not fit inside the month
            nxt_friday = days[0] + dt.timedelta(days=11)
            assert nxt_friday.month != month


def test_last_full_week_constant_across_weekdays():
    # Mon-Fri of any week report the same value
    d = dt.date(2026, 1, 5)  # a Monday
    while d < dt.date(2029, 1, 1):
        vals = {cu.is_last_full_week(d + dt.timedelta(days=i)) for i in range(5)}
        assert len(vals) == 1
        d += dt.timedelta(days=7)


def _tomorrow(today):
    # The Tomorrow node reports day_info() of today + 1 day
    return cu.day_info(today + dt.timedelta(days=1))


def test_tomorrow_month_number_today():
    # Today Nov 11, 2026 -> tomorrow Nov 12 -> month 11
    assert _tomorrow(dt.date(2026, 11, 11))['MONTH_NUM'] == 11


def test_tomorrow_month_number_rolls_over_on_last_day_of_month():
    assert _tomorrow(dt.date(2026, 11, 29))['MONTH_NUM'] == 11
    assert _tomorrow(dt.date(2026, 11, 30))['MONTH_NUM'] == 12
    # Year rollover: Dec 31 -> Jan 1
    assert _tomorrow(dt.date(2026, 12, 31))['MONTH_NUM'] == 1


def test_tomorrow_last_full_week_today_is_no():
    assert _tomorrow(dt.date(2026, 11, 11))['LAST_FULL_WEEK'] == 0


def test_tomorrow_last_full_week_edges_november_2026():
    # Sunday Nov 22 -> tomorrow is Monday Nov 23 (first flagged day)
    assert _tomorrow(dt.date(2026, 11, 22))['LAST_FULL_WEEK'] == 1
    # Thursday Nov 26 -> tomorrow Friday Nov 27 (still flagged)
    assert _tomorrow(dt.date(2026, 11, 26))['LAST_FULL_WEEK'] == 1
    # Friday Nov 27 -> tomorrow Saturday Nov 28 (weekend is No)
    assert _tomorrow(dt.date(2026, 11, 27))['LAST_FULL_WEEK'] == 0
    # Friday Nov 20 -> tomorrow Saturday Nov 21
    assert _tomorrow(dt.date(2026, 11, 20))['LAST_FULL_WEEK'] == 0


def test_tomorrow_values_are_one_day_ahead_of_today_values():
    d = dt.date(2026, 1, 1)
    while d <= dt.date(2028, 12, 30):
        assert _tomorrow(d)['LAST_FULL_WEEK'] == cu.day_info(d + dt.timedelta(days=1))['LAST_FULL_WEEK']
        assert _tomorrow(d)['MONTH_NUM'] == (d + dt.timedelta(days=1)).month
        d += dt.timedelta(days=1)


def test_month_info_current_year():
    # Nov 11, 2026 -> 2026, same value the Today node reports
    info = cu.month_info(dt.date(2026, 11, 11))
    assert info['YEAR'] == 2026
    assert info['YEAR'] == cu.day_info(dt.date(2026, 11, 11))['YEAR']


def test_month_info_year_rolls_over_on_jan_1():
    assert cu.month_info(dt.date(2026, 12, 31))['YEAR'] == 2026
    assert cu.month_info(dt.date(2027, 1, 1))['YEAR'] == 2027
    # Leap-day and every day of 2026-2028 match the date's own year and Today's value
    assert cu.month_info(dt.date(2028, 2, 29))['YEAR'] == 2028
    d = dt.date(2026, 1, 1)
    while d <= dt.date(2028, 12, 31):
        assert cu.month_info(d)['YEAR'] == d.year == cu.day_info(d)['YEAR']
        d += dt.timedelta(days=1)


def test_month_info_existing_values_unchanged():
    info = cu.month_info(dt.date(2026, 11, 11))
    assert info['ST'] == 30
    assert info['FIRST_WEEKDAY'] == 6  # Nov 1, 2026 is a Sunday
    assert info['LAST_WEEKDAY'] == 0   # Nov 30, 2026 is a Monday
    assert info['IS_FIRST_DAY'] == 0 and info['IS_LAST_DAY'] == 0 and info['IS_LAST_BUSDAY'] == 0


def test_days_left_values_end_at_zero():
    # Last day of the month / year reports 0 days left
    assert cu.day_info(dt.date(2026, 11, 30))['DAYS_LEFT_MONTH'] == 0
    assert cu.day_info(dt.date(2026, 12, 31))['DAYS_LEFT_YEAR'] == 0
    # Jan 1 of a leap year has 365 days left (0..365 fits the 0-366 editor range)
    assert cu.day_info(dt.date(2028, 1, 1))['DAYS_LEFT_YEAR'] == 365
    assert cu.day_info(dt.date(2026, 1, 1))['DAYS_LEFT_YEAR'] == 364


# ---------------------------------------------------------------------------
# Time node
# ---------------------------------------------------------------------------

# Shape of the hub's /rest/time reply (Los Angeles example from the nucore-ai source comments)
HUB_TIME_XML = (
    '<DT><NTP>3989354564</NTP><GMT>1780390964</GMT><TMZOffset>-8</TMZOffset><DST>true</DST>'
    '<DSTRule>NAM</DSTRule><Lat>34.050000</Lat><Long>118.233000</Long>'
    '<Sunrise>3989022221</Sunrise><SunriseGMT>1780058621</SunriseGMT>'
    '<Sunset>3989073402</Sunset><SunsetGMT>1780109802</SunsetGMT>'
    '<IsMilitary>false</IsMilitary><TzId>America/Los_Angeles</TzId></DT>'
)


def test_parse_hub_time_extracts_gmt_fields_and_tz():
    parsed = cu.parse_hub_time(HUB_TIME_XML)
    assert parsed == {'tz': 'America/Los_Angeles', 'sunrise': 1780058621, 'sunset': 1780109802}


def test_parse_hub_time_ignores_ntp_epoch_fields():
    # Only SunriseGMT/SunsetGMT count; plain Sunrise/Sunset are NTP-epoch and shifted
    xml = '<DT><Sunrise>3989022221</Sunrise><Sunset>3989073402</Sunset><TzId>UTC</TzId></DT>'
    parsed = cu.parse_hub_time(xml)
    assert parsed['sunrise'] is None and parsed['sunset'] is None


def test_parse_hub_time_bad_input():
    assert cu.parse_hub_time('not xml at all') is None
    assert cu.parse_hub_time('') is None
    parsed = cu.parse_hub_time('<DT><SunriseGMT>abc</SunriseGMT><SunsetGMT>0</SunsetGMT></DT>')
    assert parsed == {'tz': None, 'sunrise': None, 'sunset': None}


def test_hub_sun_times_in_hub_timezone():
    parsed = cu.parse_hub_time(HUB_TIME_XML)
    tz = cu.get_tz(parsed['tz'])
    assert tz is not None
    sunrise = cu.epoch_to_local(parsed['sunrise'], tz)
    sunset = cu.epoch_to_local(parsed['sunset'], tz)
    assert (sunrise.hour, sunrise.minute) == (5, 43)   # 05:43:41 PDT, May 29 2026
    assert (sunset.hour, sunset.minute) == (19, 56)    # 19:56:42 PDT, May 29 2026
    assert sunrise.date() == sunset.date() == dt.date(2026, 5, 29)


def test_get_tz_unknown_falls_back_to_system_local():
    assert cu.get_tz(None) is None
    assert cu.get_tz('') is None
    assert cu.get_tz('Not/AZone') is None
    # With no tz, helpers still work (naive system-local time)
    assert cu.epoch_to_local(1780058621, None).year == 2026
    assert cu.now_in(None).year >= 2026


def test_time_values_clock_only():
    vals = cu.time_values(dt.datetime(2026, 11, 11, 15, 5, 7))
    assert vals == {'ST': 15, 'MINUTE': 5}


def test_time_values_has_no_seconds():
    vals = cu.time_values(dt.datetime(2026, 11, 11, 15, 5, 7), dt.datetime(2026, 11, 11, 6, 0, 0), dt.datetime(2026, 11, 11, 17, 0, 0))
    assert 'SECOND' not in vals


def test_time_values_with_sun_truncates_minutes():
    now = dt.datetime(2026, 11, 11, 0, 0, 0)
    sunrise = dt.datetime(2026, 11, 11, 6, 59, 59)
    sunset = dt.datetime(2026, 11, 11, 17, 5, 41)
    vals = cu.time_values(now, sunrise, sunset)
    assert vals['ST'] == 0 and vals['MINUTE'] == 0
    assert (vals['SUNRISE_HOUR'], vals['SUNRISE_MIN']) == (6, 59)
    assert (vals['SUNSET_HOUR'], vals['SUNSET_MIN']) == (17, 5)


def test_time_values_ranges_over_a_day():
    d = dt.datetime(2026, 11, 11, 0, 0, 0)
    end = d + dt.timedelta(days=1)
    while d < end:
        v = cu.time_values(d, d, d)
        assert 0 <= v['ST'] <= 23 and 0 <= v['MINUTE'] <= 59
        assert (v['ST'], v['MINUTE']) == (v['SUNRISE_HOUR'], v['SUNRISE_MIN']) == (v['SUNSET_HOUR'], v['SUNSET_MIN'])
        d += dt.timedelta(seconds=37)


class _FakeResponse:
    def __init__(self, body):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body.encode('utf-8')


FAKE_USER = 'zq_u_0417'
FAKE_SECRET = 'zq_s_8830_kx'


def _hub_info(https=0):
    info = {'isy_ip_address': '192.0.2.77', 'isy_port': 8099, 'isy_https': https, 'isy_username': FAKE_USER}
    info['isy_' + 'password'] = FAKE_SECRET
    return info


def test_fetch_hub_time_builds_authenticated_request(monkeypatch):
    import base64
    seen = {}

    def fake_urlopen(req, timeout=None, context=None):
        seen['url'] = req.full_url
        seen['auth'] = req.get_header('Authorization')
        seen['timeout'] = timeout
        seen['context'] = context
        return _FakeResponse(HUB_TIME_XML)

    monkeypatch.setattr(cu.urllib.request, 'urlopen', fake_urlopen)
    body = cu.fetch_hub_time(_hub_info(0))
    assert body == HUB_TIME_XML
    assert seen['url'] == 'http://192.0.2.77:8099/rest/time'
    expected = base64.b64encode((FAKE_USER + ':' + FAKE_SECRET).encode()).decode()
    assert seen['auth'] == 'Basic ' + expected
    assert FAKE_SECRET not in seen['url']
    assert seen['timeout'] and seen['context'] is None


def test_fetch_hub_time_https_skips_certificate_verification(monkeypatch):
    import ssl
    seen = {}

    def fake_urlopen(req, timeout=None, context=None):
        seen['url'] = req.full_url
        seen['context'] = context
        return _FakeResponse(HUB_TIME_XML)

    monkeypatch.setattr(cu.urllib.request, 'urlopen', fake_urlopen)
    cu.fetch_hub_time(_hub_info(1))
    assert seen['url'] == 'https://192.0.2.77:8099/rest/time'
    assert seen['context'].verify_mode == ssl.CERT_NONE and seen['context'].check_hostname is False


def test_fetch_hub_time_propagates_failure(monkeypatch):
    def boom(req, timeout=None, context=None):
        raise OSError('connection refused')

    monkeypatch.setattr(cu.urllib.request, 'urlopen', boom)
    try:
        cu.fetch_hub_time(_hub_info())
    except OSError:
        return
    raise AssertionError('expected OSError')


T0 = 1700000000.0
TODAY = dt.date(2026, 5, 29)
DAY = 86400.0


def _fresh_state():
    return {'date': None, 'attempt_date': None, 'attempts': 0, 'last_try': 0.0, 'busy': False}


def test_sun_fetch_due_conditions():
    st = _fresh_state()
    assert cu.sun_fetch_due(st, T0, TODAY, True) is True
    assert cu.sun_fetch_due(st, T0, TODAY, False) is False
    st['busy'] = True
    assert cu.sun_fetch_due(st, T0, TODAY, True) is False
    st['busy'] = False
    st['last_try'] = T0
    assert cu.sun_fetch_due(st, T0 + 1, TODAY, True) is False
    assert cu.sun_fetch_due(st, T0 + cu.SUN_RETRY_SECS, TODAY, True) is True
    st['date'] = TODAY
    assert cu.sun_fetch_due(st, T0 + DAY, TODAY, True) is False
    assert cu.sun_fetch_due(st, T0 + DAY, TODAY + dt.timedelta(days=1), True) is True


def test_sun_result_fresh_data_completes_the_day():
    st = _fresh_state()
    st['busy'] = True
    parsed = cu.parse_hub_time(HUB_TIME_XML)
    assert cu.sun_result(st, parsed, TODAY, T0 + 7) is True
    assert st['date'] == TODAY and st['busy'] is False and st['last_try'] == T0 + 7


def test_sun_result_failure_keeps_retrying():
    st = _fresh_state()
    st['busy'] = True
    assert cu.sun_result(st, None, TODAY, T0) is False
    empty = {'tz': None, 'sunrise': None, 'sunset': None}
    assert cu.sun_result(st, empty, TODAY, T0 + 3) is False
    assert st['date'] is None and st['busy'] is False
    assert cu.sun_fetch_due(st, T0 + 3 + cu.SUN_RETRY_SECS, TODAY, True) is True


def test_sun_result_stale_data_is_used_then_given_up():
    later = dt.date(2026, 11, 11)
    st = _fresh_state()
    parsed = cu.parse_hub_time(HUB_TIME_XML)
    for attempt in range(1, cu.SUN_MAX_ATTEMPTS):
        assert cu.sun_result(st, parsed, later, T0 + attempt) is True
        assert st['date'] is None, attempt
    assert cu.sun_result(st, parsed, later, T0 + 99) is True
    assert st['date'] == later


def test_sun_result_attempts_reset_each_day():
    st = _fresh_state()
    parsed = cu.parse_hub_time(HUB_TIME_XML)
    day1 = dt.date(2026, 11, 11)
    day2 = dt.date(2026, 11, 12)
    for i in range(cu.SUN_MAX_ATTEMPTS - 1):
        cu.sun_result(st, parsed, day1, T0 + i)
    assert st['date'] is None
    cu.sun_result(st, parsed, day2, T0 + DAY)
    assert st['attempts'] == 1 and st['date'] is None


def _profile():
    with open(os.path.join(HERE, 'profile.json')) as f:
        return json.load(f)


def _profile_ids(nodedef_id):
    for nd in _profile()['nodedefs']:
        if nd['id'] == nodedef_id:
            return [p['id'] for p in nd['properties']]
    raise AssertionError(nodedef_id)


def _driver_ids(filename):
    with open(os.path.join(HERE, filename)) as f:
        src = f.read()
    return re.findall(r"'driver': '([A-Z_]+)'", src)


def _driver_uoms(filename):
    with open(os.path.join(HERE, filename)) as f:
        src = f.read()
    return re.findall(r"'uom': (\d+)", src)


def _driver_uom_map(filename):
    with open(os.path.join(HERE, filename)) as f:
        src = f.read()
    return dict(re.findall(r"'driver': '([A-Z_]+)'.*?'uom': (\d+)", src))


def test_tomorrow_profile_has_new_properties_and_matches_drivers():
    ids = _profile_ids('caltomorrow')
    assert 'MONTH_NUM' in ids and 'LAST_FULL_WEEK' in ids
    assert sorted(ids) == sorted(_driver_ids('tomorrow_node.py'))
    # Today stays consistent too
    assert sorted(_profile_ids('caltoday')) == sorted(_driver_ids('today_node.py'))


def test_month_profile_has_year_and_matches_drivers():
    ids = _profile_ids('calmonth')
    assert 'YEAR' in ids
    assert sorted(ids) == sorted(_driver_ids('month_node.py'))
    # every driver the node declares gets a value from month_info()
    assert set(_driver_ids('month_node.py')) <= set(cu.month_info(dt.date(2026, 11, 11)))


def test_time_profile_matches_drivers_and_values():
    ids = _profile_ids('caltime')
    assert sorted(ids) == sorted(['ST', 'MINUTE', 'SUNRISE_HOUR', 'SUNRISE_MIN', 'SUNSET_HOUR', 'SUNSET_MIN'])
    assert 'SECOND' not in ids
    assert sorted(ids) == sorted(_driver_ids('time_node.py'))
    now = dt.datetime(2026, 11, 11, 15, 5, 7)
    assert set(ids) == set(cu.time_values(now, now, now))


def test_time_node_values_are_unitless_raw_numbers():
    # uom 56 (Raw) shows a bare number (10, not '10 Hour') so programs can compare numerically
    assert set(_driver_uoms('time_node.py')) == {'56'}
    prof = _profile()
    editors = {e['id']: e for e in prof['editors']}
    time_nd = next(nd for nd in prof['nodedefs'] if nd['id'] == 'caltime')
    for prop in time_nd['properties']:
        for rng in editors[prop['editor']]['ranges']:
            assert rng['uom'] == '56', (prop['id'], rng)
            assert 'names' not in rng and 'subset' not in rng
    assert (editors['cal_clock_hour']['ranges'][0]['min'], editors['cal_clock_hour']['ranges'][0]['max']) == (0, 23)
    assert (editors['cal_clock_min']['ranges'][0]['min'], editors['cal_clock_min']['ranges'][0]['max']) == (0, 59)


def test_today_days_left_are_unitless_raw_numbers():
    # uom 56 (Raw) shows a bare number (19, not '19 days') for numeric comparisons
    prof = _profile()
    editors = {e['id']: e for e in prof['editors']}
    today_nd = next(nd for nd in prof['nodedefs'] if nd['id'] == 'caltoday')
    props = {p['id']: p for p in today_nd['properties']}
    drv = _driver_uom_map('today_node.py')
    for pid in ('DAYS_LEFT_MONTH', 'DAYS_LEFT_YEAR'):
        assert drv[pid] == '56'
        rngs = editors[props[pid]['editor']]['ranges']
        assert len(rngs) == 1 and rngs[0]['uom'] == '56'
        assert 'names' not in rngs[0] and 'subset' not in rngs[0]
        assert (rngs[0]['min'], rngs[0]['max']) == (0, 366)


def test_no_days_property_shows_a_days_unit():
    # Days Left (Today), Days in Month (Month Info) and Days Until Next (patterns) are all unitless (56)
    prof = _profile()
    editors = {e['id']: e for e in prof['editors']}
    month_nd = next(nd for nd in prof['nodedefs'] if nd['id'] == 'calmonth')
    rule_nd = next(nd for nd in prof['nodedefs'] if nd['id'] == 'calrule')
    assert next(p for p in month_nd['properties'] if p['id'] == 'ST')['editor'] == 'cal_monthdays'
    assert next(p for p in rule_nd['properties'] if p['id'] == 'DAYS_UNTIL')['editor'] == 'cal_untildays'
    assert editors['cal_monthdays']['ranges'][0]['uom'] == '56'
    assert editors['cal_untildays']['ranges'][0]['uom'] == '56'
    assert _driver_uom_map('month_node.py')['ST'] == '56'
    assert _driver_uom_map('pattern_node.py')['DAYS_UNTIL'] == '56'
    used = {p['editor'] for nd in prof['nodedefs'] for p in nd['properties']}
    assert not [e for e in used if any(r['uom'] == '10' for r in editors[e]['ranges'])]
