# Calendar

Exposes information about the regular (Gregorian) calendar and the time of day as nodes, computed locally from the controller's clock. Sunrise and sunset are read from the controller itself. No cloud service, account or API key.

## Nodes

- **Calendar Today** -- day of week, day of month, month (shown by name), month number (1-12), year, day of year, ISO week number, ISO week odd/even, last full Mon-Fri week of the month, weekend flag, leap-year flag, season, days left in the month and year (these two are plain numbers with no unit label, e.g. `19`, not `19 days`, for use in numeric comparisons).
- **Calendar Tomorrow** -- the same date information for tomorrow (handy for "is tomorrow a weekend / the 1st?" in programs), including month number and last full Mon-Fri week.
- **Calendar Month Info** -- days in the month (a plain number, e.g. `30`), current year, weekday of the first and last day, and flags for first day, last day and last business day (last Monday-Friday) of the month.
- **Calendar Weekday Instance** -- which instance of today's weekday this is within the month (1st to 5th), the weekday itself, and whether it is the last of that weekday this month. For example, Wednesday November 11, 2026 is the 2nd Wednesday.
- **Calendar Time** (node name **Time**) -- the current **Hour** (0-23) and **Minute**, plus the controller's own **Sunrise Hour / Sunrise Minute** and **Sunset.
also includes **Unix Time** which is the number of seconds since Jan 1, 1970, and **Local Epoch Day** which is the number of days, also since Jan 1, 1970
- **Hour / Sunset Minute** for today (24-hour clock, local time). All of these are plain numbers with no unit label (for example `10`, not `10 Hour`), so they can be used directly in numeric comparisons in programs.
- **Weekday Pattern nodes (Nth weekday)** -- one node per pattern you define, e.g. "2nd Tuesday of every month", "last Friday of the month" or "4th Thursday of November". Each node reports *Is Today*, *Is Tomorrow*, *Days Until Next* (a plain number, 0 on the day itself), and the date of the next occurrence (day, month, year).

## Configuration

Open the plugin's configuration page:

- **Southern Hemisphere** -- reverses the seasons for the Season property.
- **Weekday Patterns** -- a list. Each entry has a **Pattern Name** (becomes the node name), **Which Occurrence** (first/second/third/fourth/last), **Weekday**, and optional **Month** ("any" for every month, or a month name/number). Pattern nodes are added, renamed or removed automatically when you save. Entries that cannot be understood are skipped and explained in a notice on the configuration page.

## Notes

- Dates use the local time zone of the controller. Values refresh when the date changes and at least every 5 minutes.
- The **Rebuild Nodes** command re-creates any missing nodes.
- Days of the week run Monday-Sunday. Season boundaries are the astronomical ones (about Mar 20 / Jun 21 / Sep 22 / Dec 21).
- **Month** uses the controller's built-in month unit, so the console shows the month name (e.g. November). **Month Number** reports the same month as a plain number from 1 to 12 (November = 11), handy for numeric comparisons and ranges in programs. Both are on Today and Tomorrow (Month Number on Tomorrow is tomorrow's month, so it changes on the last day of a month).
- **Days Left in Month** and **Days Left in Year** on the Today node, **Days in Month** on the Month Info node, and **Days Until Next** on the pattern nodes are reported in the controller's "Raw" unit, so they show as bare numbers (Days Left is 0 on the last day of the month / year; Days Until Next is 0 when the pattern falls today). No property shows a "days" label.
- **Current Year** on the Month Info node is the calendar year of today's date (e.g. 2026), the same value as Year on the Today node.
- **ISO Week Odd/Even** follows the ISO week number exactly (odd number = Odd). Some years have 53 ISO weeks; in those years week 53 and week 1 of the next year are both Odd, so two Odd weeks occur back to back (e.g. Dec 28, 2026 - Jan 10, 2027).
- **Last Full Mon-Fri Week** is Yes on the five weekdays (Monday to Friday) of the last week in a month whose Monday to Friday all fall inside that month. Only the weekdays count: Saturday and Sunday are always No. For example, in November 2026 it is Yes Monday Nov 23 through Friday Nov 27. The week of Nov 30 - Dec 4 is not entirely within one month, so it is No. A month that ends on a Friday counts that week (April 2027: Apr 26-30). On the Tomorrow node it reports the value for tomorrow's date, so it is Yes on Sunday Nov 22 (tomorrow is Monday Nov 23) and No on Friday Nov 27 (tomorrow is Saturday).
- **Time node: clock.** Hour and Minute use the controller's time zone and are reported as plain numbers (the controller's "Raw" unit), with no "Hour"/"Minute" label. The plugin refreshes every 10 seconds, so Minute can change up to about 10 seconds after the real clock rolls over; only changed values are sent to the controller. There is no seconds property.
- **Time node: sunrise and sunset.** These are the controller's own calculated values (the same ones its schedules use), read from the contoller's `/rest/time` once a day and converted to the controller's local time zone. Minutes are truncated (5:43:41 shows as 5:43). The plugin needs access to the controller for this (`Allow API Access`), which is enabled in its registration. If the controller can't be read, a notice appears on the configuration page, the plugin retries every minute, and the four sun properties keep their last value (0 until the first successful read).
- A pattern renamed to a different name becomes a new node (the old one is removed), so programs referencing it need updating.

## Upgrading from an older version

Polyglot (PG3) stores each node's property units when the node is first created, and the plugin library copies those stored units over what the plugin declares. So a unit or property change in a new plugin version would never reach nodes that already exist. Since 1.12.0 the plugin always reports its own declared units, and when it starts it also checks its nodes (Today, Tomorrow, Month Info, Weekday Instance, Time and, since 1.14.0, every configured pattern node): any whose stored definition is out of date (a different unit, or a property that no longer exists, such as the old Time *Second*) is deleted and re-added automatically, once per definition revision. A small marker file (`persist/node_defs.json`) stops this from repeating. Programs that use properties of a re-added node need those conditions re-selected.

## License Notice

This plugin's development referenced the following source(s), whose license is not on the standard permissive allowlist. Review their license terms before relying on or redistributing this plugin:

- [GitHub - api-evangelist/sunrise-sunset: Sunrise Sunset — independent third-party profile of a public API surface, by API Evangelist. Free REST API providing sunrise, sunset, solar noon, day length, and civil, nautical, and astronomical twilight times for any geographic location and date. No API key or account required; attribution to sunrise-sunset.org is required. · GitHub](https://github.com/api-evangelist/sunrise-sunset) -- license: unknown

See LICENSE.md for full third-party attribution.
