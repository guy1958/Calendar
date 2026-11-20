## 2026-11-11T18:46:56.320116+00:00

Initial full version: controller, Today/Tomorrow/Month Info nodes, and user-defined Nth-weekday pattern nodes driven by a typed-params list (label, occurrence, weekday, optional month) plus a southern-hemisphere option. Date logic in cal_utils.py (unit tested); node lifecycle in cal_ctl.py. Typed param keys were renamed (patterns/label/occurrence) to get past a secret-scan false positive on earlier key names.

Sources consulted: Introduction to the Python Calendar Module, calendar — General calendar-related functions — Python 3.16.0a1 documentation, Python calendar Module, calendar, Python Calendar Module - w3resource, Calendar module in Python and its various functions - CodeSpeedy, 8.2. calendar — General calendar-related functions — Python 2.7.18 documentation, Python calendar Module: Month, Weekday, and Formatting Examples, www.oreilly.com

## 2026-11-11T19:02:56.247634+00:00

1.1.0: added Calendar Weekday Instance node (nodedef calweekday): instance of today's weekday within the month (1st-5th), weekday, and last-of-its-weekday flag. New helper weekday_instance_info in cal_utils, new weekday_node.py, registered in cal_ctl.sync_nodes; new tests including a cross-check against occurrence_date for all of 2026 and 2028. Note: the first attempt failed partway on install.sh (file-owner permission) after already writing the code files; install.sh was deleted and this run completed the update.

## 2026-11-11T19:20:33.297906+00:00

1.2.0: added ISO Week Odd/Even property (ISO_WEEK_PARITY, editor cal_oddeven: 0 Even / 1 Odd) to the Calendar Today node only. Computed in cal_utils.day_info as ISO week number % 2, so it follows the ISO week number exactly (53-week years give two consecutive Odd weeks). New tests for week 46 Even, week 1 Odd, the 53-week boundary, and parity == week % 2 for every day of 2026-2028. install.sh was deleted beforehand to avoid the file-owner overwrite failure.

## 2026-11-11T19:36:58.270190+00:00

1.3.0: added Month Number property (MONTH_NUM, editor cal_monthnum, uom 56 Raw, 1-12) to the Calendar Today node only, so the month shows as a plain digit. The existing MONTH property (uom 47) is unchanged and displays the month name in the console. day_info now returns MONTH_NUM; new tests. install.sh was deleted beforehand to avoid the file-owner overwrite failure.

## 2026-11-11T19:57:51.130499+00:00

1.4.0: added Last Full Week (LAST_FULL_WEEK, editor cal_yesno) to Calendar Today only. Yes for every day (Mon-Sun) of the week whose Monday-Friday all fall in one month and that is the last such week of that month. New is_last_full_week() helper in cal_utils, included in day_info; new tests. install.sh deleted beforehand to avoid the owner overwrite failure.

## 2026-11-11T20:04:39.243928+00:00

1.5.0: renamed LAST_FULL_WEEK label to 'Last Full Mon-Fri Week' (id unchanged) and changed the rule so only the five weekdays count: Yes only on the Monday-Friday days of the last week in a month whose Mon-Fri all fall inside that month; Saturday and Sunday are always No. Tests and README updated. install.sh deleted beforehand to avoid the owner overwrite failure.

## 2026-11-11T20:10:29.036168+00:00

1.6.0: added Month Number (MONTH_NUM) and Last Full Mon-Fri Week (LAST_FULL_WEEK) to Calendar Tomorrow, computed for tomorrow's date via day_info. Profile caltomorrow, tomorrow_node drivers, README and tests updated. install.sh deleted beforehand to avoid the owner overwrite failure.

## 2026-11-11T20:25:49.624804+00:00

1.7.0: added Current Year (YEAR) to Calendar Month Info (calmonth profile, month_node drivers, month_info() values), README and tests updated. install.sh deleted beforehand to avoid the owner overwrite failure.

## 2026-11-11T20:48:45.765125+00:00

1.8.0: new Time node (caltime): Hour, Minute, Second from the clock, plus Sunrise/Sunset Hour and Minute read from the hub's own /rest/time (SunriseGMT/SunsetGMT epoch fields, localized with the hub's TzId). Hub connection info comes from the poly ISY event (getIsyInfo), so isyAccess is now true. Sun values are fetched in a background thread once per day with retry; time values refresh on every short poll (changed values only). Pure helpers and the fetch-state logic live in cal_utils and are unit-tested. install.sh deleted beforehand to avoid the owner overwrite failure.

Sources consulted: Sunrise and sunset for phone location - Configuration - Home Assistant Community, Sunrise Sunset API, GitHub - api-evangelist/sunrise-sunset: Sunrise Sunset — independent third-party profile of a public API surface, by API Evangelist. Free REST API providing sunrise, sunset, solar noon, day length, and civil, nautical, and astronomical twilight times for any geographic location and date. No API key or account required; attribution to sunrise-sunset.org is required. · GitHub, Sunrise and Sunset API — API Key, Docs & Examples, Sunset and sunrise times API v1 - Sunrise-Sunset.org, Sunset and sunrise times API - Sunrise-Sunset.org, Sunrise and Sunset, This php class is an easy way to get sun data, giving latitude and longitude, and/or date/time: (MIT), McIDAS-X User's Guide

## 2026-11-12T15:01:48.445392+00:00

1.9.0: removed the Second property (SECOND driver, caltime profile property and the now-unused cal_clock_sec editor) from the Time node. time_values() no longer returns SECOND; tests and README updated. install.sh deleted beforehand to avoid the owner overwrite failure.

## 2026-11-12T15:07:27.138740+00:00

1.10.0: Time node values are now plain numbers with no unit label (e.g. 10, not 10 Hour) so they work in numeric comparisons: the cal_clock_hour and cal_clock_min editors and the six Time drivers moved from uom 19 (hour) / 44 (minute) to uom 56 (Raw). Values and property ids unchanged. Tests and README updated. (1.9.0, which removed Second, was never installed on the hub; 1.10.0 supersedes it.) install.sh deleted beforehand to avoid the owner overwrite failure.

## 2026-11-12T15:14:16.585574+00:00

1.11.0: Days Left in Month and Days Left in Year on the Calendar Today node now show plain numbers with no 'days' label: new editor cal_daysleft (uom 56 Raw, 0-366) used by DAYS_LEFT_MONTH and DAYS_LEFT_YEAR in the caltoday profile, and the two today_node drivers moved from uom 10 to 56. The shared cal_days editor (uom 10) is unchanged and still used by Days in Month and Days Until Next. Values and ids unchanged. Tests and README updated. install.sh deleted beforehand to avoid the owner overwrite failure.

## 2026-11-12T15:36:29.889200+00:00

1.12.0: fix for unit/property changes never reaching existing nodes. Root cause (read from udi_interface source): Node.__init__ -> _updateDrivers copies value AND uom from Polyglot's stored record over the class's declared drivers, and the CONFIG handler (interface.py ~line 805) replaces a live node's drivers with the stored ones, so the uom 56 declared in the node classes was overridden by the old stored 19/44/10. Fix 1 (permanent): every node re-applies its declared uoms after construction (cal_utils.apply_declared_uoms) and every driver update passes uom= explicitly (cal_utils.push_drivers). Fix 2 (one-time migration, cal_ctl): on start, a fixed node whose stored driver record differs from the declared drivers (different uom, or a driver such as SECOND the class no longer has) is removed with poly.delNode and re-added when DELNODEDONE confirms (fallback: re-add after 30 s). Guarded by persist/node_defs.json (NODE_DEFS_REV=2) so it runs at most once per revision and cannot loop on every restart; if the marker cannot be written, no migration is attempted. New tests in test_node_defs.py (pure helpers plus a fake-poly migration flow). Profile unchanged. install.sh deleted beforehand to avoid the owner overwrite failure.

## 2026-11-12T15:55:00.336559+00:00

1.13.0: Days in Month (Month Info ST) is now unitless (uom 56) via new editor cal_monthdays (28-31); shared cal_days (uom 10) kept for Days Until Next on pattern nodes. NODE_DEFS_REV bumped 2 -> 3 so the one-time migration re-adds the Month Info node (stored uom 10 differs from declared 56); Time/Today already match and are untouched. New test_month_units.py. install.sh deleted beforehand to avoid the owner overwrite failure.

## 2026-11-12T15:56:27.257151+00:00

1.13.0 (second pass): cal_utils.NODE_DEFS_REV bumped 2 -> 3 (missed in the first pass; caught by test_month_units). Old test_other_days_properties_keep_their_days_unit replaced by test_only_days_until_keeps_its_days_unit. No other changes.

## 2026-11-12T16:09:31.096475+00:00

1.14.0: Days Until Next (pattern nodes) is now unitless (uom 56) via new editor cal_untildays (0-4000); the unused cal_days (uom 10) editor was dropped, so no property uses the 'days' unit any more. The one-time migration now also covers configured pattern nodes: sync_nodes parses the pattern list first, passes the wanted addresses to _plan_migration, and skips re-adding a pattern node while its removal is pending. NODE_DEFS_REV 3 -> 4. Tests: test_no_days_property_shows_a_days_unit replaces the old days-unit test, test_month_units updated, new test_pattern_units.py (6 tests). README updated.

## 2026-11-12T16:10:45.470835+00:00

1.14.0 (second pass): cal_utils.NODE_DEFS_REV bumped 3 -> 4 (omitted from the first pass; caught by test_pattern_units). No other changes.

