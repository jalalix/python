# JalaliX - Python

Jalali (Persian / Shamsi) calendar on top of a millisecond Unix timestamp. Pure Python 3.9+, no runtime dependencies.

[![PyPI](https://img.shields.io/pypi/v/jalalix.svg)](https://pypi.org/project/jalalix/)
[![license](https://img.shields.io/pypi/l/jalalix.svg)](./LICENSE)

```bash
pip install jalalix
```

```python
from jalalix import JalaliX

date = JalaliX.create('2025-02-25')

date.format('YYYY/MM/DD')  # 1403/12/07
date.format('DD MMM YYYY', {'persianDigits': True})  # ۰۷ اسفند ۱۴۰۳

JalaliX.parseJalali('1403/12/07').toISODate()  # 2025-02-25
```

`toISODate()` uses wall-clock getters in the active timezone. Prefer it over UTC-based slicing when you need a calendar date string.

## Install

```bash
pip install jalalix
```

```python
from jalalix import JalaliX
```

## Usage

### create / format

```python
now = JalaliX.create(datetime.now(), {'timezone': 'Asia/Tehran'})

now.format('YYYY/MM/DD')
now.format('WN، DD MMM YYYY')
now.format('YYYY/MM/DD', {'persianDigits': True})
now.format('DD MMM YYYY', {'calendar': 'gregorian'})
```

`format` also accepts the older positional form: `format(str, persianDigits?, gregorian?)`.

### parseJalali

```python
JalaliX.parseJalali('1403/12/07')
JalaliX.parseJalali('۱۴۰۳-۱۲-۰۷ 14:30')
JalaliX.parseJalali('1403.12.07')
```

Named `parseJalali` because built-in `datetime` already covers Gregorian parsing. Accepts `/`, `-`, or `.` as the date separator.

### normalizeQueryDate

Soft-normalize loose API/query date values to a Gregorian `Y-m-d H:i:s` string (or `None`). Does not raise on junk input.

```python
JalaliX.normalizeQueryDate('1403/12/07', {'timezone': 'Asia/Tehran'})
# '2025-02-25 00:00:00'

JalaliX.normalizeQueryDate('undefined')  # None
JalaliX.normalizeQueryDate(1740430800000, {'timezone': 'Asia/Tehran'})
# '2025-02-25 00:30:00'
```

Handles sentinels (`None`, `''`, `'null'`, `'undefined'`, `'Invalid Date'`, `NaN`) → `None`; unix timestamps (seconds or milliseconds; non-positive → `None`); Persian/Arabic-Indic digits; `/` `-` `.` separators; fractional seconds; optional `Z` / offset suffixes.

Detects Jalali when the year is in `jalaliYearMin`…`jalaliYearMax` (default `1`…`1899`) **and** the civil date is valid; otherwise Gregorian when valid, or returns the digit-cleaned string. Non-string/non-number values pass through unchanged.

### toISODate

```python
d = JalaliX.create('2025-02-25T00:30:00+03:30')

d.toISODate()          # 2025-02-25
d.toISODate('jalali')  # 1403-12-07
```

### add / start / end

```python
JalaliX.create('2025-02-25').addMonths(1).getStartOfMonth().format('YYYY/MM/DD')
# e.g. 1404/01/01

d = JalaliX.create('2025-02-25', {'timezone': 'Asia/Tehran'})
d.addDays(7).format('YYYY/MM/DD')
d.getEndOfWeek().format('YYYY/MM/DD')
```

### Persian / Arabic digits

```python
JalaliX.toPersian('1403/12/07')   # ۱۴۰۳/۱۲/۰۷
JalaliX.fromPersian('۱۴۰۳/۱۲/۰۷')  # 1403/12/07
JalaliX.fromPersian('١٤٠٣/١٢/٠٧')  # 1403/12/07 (Arabic-Indic)
```

## Timezone

Internal storage is always a **UTC Unix millisecond instant** plus an IANA timezone id. `setTimezone` is **instant-preserving**: the timestamp stays the same; only the zone (and therefore wall clock / Jalali day) changes.

```python
d = JalaliX.create(1740430800000)  # 2025-02-25T00:30:00+03:30

tehran = d.setTimezone('Asia/Tehran')
tehran.format('YYYY/MM/DD')  # 1403/12/07
tehran.format('HH:mm')         # 00:30

utc = d.setTimezone('UTC')
utc.format('YYYY/MM/DD')  # 1403/12/06
utc.format('HH:mm')         # 21:00

tehran.getTime() == utc.getTime()  # True
```

- **Aliases:** `utc` / `gmt` → `UTC`; `local` / `default` / `system` → host IANA when detectable, else `UTC`.
- **Invalid zone** → `ValueError`.
- Offsets use stdlib `zoneinfo`, with a **vendored** TZif set under `jalalix/zoneinfo/` (`UTC`, `Etc/UTC`, `Asia/Tehran`, `Asia/Tokyo`, `Europe/London`, `America/New_York`) so Windows works without the PyPI `tzdata` package.

```python
JalaliX.create(datetime.now(), {'timezone': 'Asia/Tehran'})
```

## Months

Easy to get wrong:

- `getMonth()` → **1…12** (Farvardin = 1)
- `setMonth(m)` / `setFullYear(y, m)` → **0…11**, same as JS `Date` (Farvardin = 0)

```python
d = JalaliX.create(datetime.now())
d.setFullYear(1404, 0, 1)  # 1 Farvardin 1404
d.getMonth()  # 1
```

## Format tokens

| Token               | Meaning                         |
| ------------------- | ------------------------------- |
| `YYYY` `YY`         | year                            |
| `MMM` `MM` `M`      | month name / number             |
| `DD` `D`            | day                             |
| `HH` `hh` `mm` `ss` | time                            |
| `A` `a`             | meridiem (ق.ظ. / ب.ظ. or AM/PM) |
| `WN` `WL`           | weekday name / letter           |
| `w` `DDD`           | week of year / day of year      |
| `X` `x`             | unix seconds / -                |

-

## API -

Method names match the TypeScript packa - (camelCase).

-

### Static

| API                                   | Description                                                                                                                                              |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `create(date, options?)`              | Build from unix ms, ISO/`YYYY-MM-DD` string, `datetime`, `date`, or `JalaliX`. Optional `{'timezone': str}`.                                             |
| `parseJalali(str, options?)`          | Parse a Jalali date/time string (`/` `-` `.`, Persian/Arabic digits, optional time).                                                                     |
| `normalizeQueryDate(value, options?)` | Soft-normalize loose query/form values → Gregorian `Y-m-d H:i:s` or `None`. Options: `timezone`, `jalaliYearMin`, `jalaliYearMax` (defaults `1`…`1899`). |
| `isValidDate(value)`                  | `True` if `value` is a `JalaliX`, `datetime`, or `date` instance.                                                                                        |
| `toPersian(str)`                      | Replace Western digits `0-9` with Persian `۰-۹`.                                                                                                         |
| `fromPersian(str)`                    | Replace Persian `۰-۹` and Arabic-Indic `٠-٩` with Western digits.                                                                                        |
| `compare(a, b)`                       | `True` if `a` is strictly before `b` (by unix ms).                                                                                                       |
| `persianNumbers`                      | List of Persian digit characters `۰`…`۹`.                                                                                                                |
| `arabicNumbers`                       | List of Arabic-Indic digit characters `٠`…`٩`.                                                                                                           |

### Constructor

| API            | Description                                                            |
| -------------- | ---------------------------------------------------------------------- |
| `JalaliX(ms?)` | Build from optional millisecond timestamp; timezone defaults to `UTC`. |

### Instance - getters

| API                                                                  | Description                                                           |
| -------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `getFullYear()`                                                      | Jalali year in the active timezone.                                   |
| `getMonth()`                                                         | Jalali month **1…12** (Farvardin = 1).                                |
| `getDate()`                                                          | Jalali day of month **1…31**.                                         |
| `getDay()`                                                           | Weekday **1…7** (Saturday = 1 … Friday = 7).                          |
| `getHours()` / `getMinutes()` / `getSeconds()` / `getMilliseconds()` | Wall-clock time in the active timezone.                               |
| `getTime()`                                                          | Unix timestamp in milliseconds (UTC instant).                         |
| `getTimezone()`                                                      | Active IANA timezone id.                                              |
| `getWeekOfYear()`                                                    | Jalali week-of-year (1-based).                                        |
| `getDayOfYear()`                                                     | Day of Jalali year (1…365/366).                                       |
| `getDayISO()`                                                        | ISO-style weekday index used internally for week math.                |
| `getHoursISO()`                                                      | Hours in 0…23 for formatting helpers.                                 |
| `getMeridiem()`                                                      | Localized meridiem string (ق.ظ./ب.ظ. or AM/PM depending on calendar). |

### Instance - setters

| API                                | Description                                              |
| ---------------------------------- | -------------------------------------------------------- |
| `setTime(ms)`                      | Set the UTC instant from unix milliseconds.              |
| `setMilliseconds(ms)`              | Set milliseconds (wall clock).                           |
| `setSeconds(sec, ms?)`             | Set seconds (and optional ms).                           |
| `setMinutes(min, sec?, ms?)`       | Set minutes (and optional lower units).                  |
| `setHours(h, min?, sec?, ms?)`     | Set hours (and optional lower units).                    |
| `setDate(day)`                     | Set Jalali day of month.                                 |
| `setMonth(month, date?)`           | Set Jalali month **0…11** (Farvardin = 0); optional day. |
| `setFullYear(year, month?, date?)` | Set Jalali year; optional month **0…11** and day.        |
| `setTimezone(tz)`                  | Instant-preserving zone change; returns a new instance.  |

### Instance - math, range, format

| API                                                                                             | Description                                                                               |
| ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `addYears(n)` / `addMonths(n)` / `addWeeks(n)` / `addDays(n)`                                   | Add calendar units; mutate and return `self`.                                             |
| `getStartOfYear()` / `getStartOfMonth()` / `getStartOfWeek()` / `getStartOfDay()`               | Start of unit (new instance).                                                             |
| `getEndOfYear()` / `getEndOfMonth()` / `getEndOfWeek()` / `getEndOfDay()`                       | End of unit (new instance).                                                               |
| `format(str, options?)`                                                                         | Format with tokens above; options `{'calendar', 'persianDigits'}` or positional booleans. |
| `toISODate(calendar?)`                                                                          | `YYYY-MM-DD` in `'gregorian'` (default) or `'jalali'`.                                    |
| `clone()`                                                                                       | Copy with the same instant and timezone.                                                  |
| `__str__()` / `toString()` / `toDateString()` / `toLocaleDateString()` / `toLocaleTimeString()` | String views of the date/time.                                                            |
| `__repr__()`                                                                                    | Debug representation of the instance.                                                     |

## Links

- https://pypi.org/project/jalalix/
- https://jalalix.com
- https://github.com/jalalix/python
- [CHANGELOG.md](./CHANGELOG.md)

## License

MIT
