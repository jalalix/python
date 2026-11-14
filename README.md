# JalaliX

Jalali (Persian / Shamsi) calendar for Python. Pure Python 3.9+, no runtime dependencies.

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

`toISODate()` uses local calendar getters. Prefer it when you need a calendar date string without UTC shift surprises.

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
```

### toISODate

```python
d = JalaliX.create('2025-02-25')

d.toISODate()          # 2025-02-25  (local Gregorian getters)
d.toISODate('jalali')  # 1403-12-07
```

### add / start / end

```python
JalaliX.create('2025-02-25').addMonths(1).getStartOfMonth().format('YYYY/MM/DD')
```

### Persian digits

```python
JalaliX.toPersian('1403/12/07')   # ۱۴۰۳/۱۲/۰۷
JalaliX.fromPersian('۱۴۰۳/۱۲/۰۷')  # 1403/12/07
```

## Months

This is easy to get wrong:

- `getMonth()` -> 1..12 (Farvardin = 1)
- `setMonth(m)` / `setFullYear(y, m)` -> 0..11, same as JS `Date` (Farvardin = 0)

```python
d = JalaliX.create(datetime.now())
d.setFullYear(1404, 0, 1)  # 1 Farvardin 1404
d.getMonth()  # 1
```

## Timezone

Internal storage is a **UTC Unix millisecond instant** plus an IANA timezone id. `setTimezone` is **instant-preserving**: the timestamp stays the same; wall clock / Jalali day may change.

```python
d = JalaliX.create(1740430800000)
tehran = d.setTimezone("Asia/Tehran")
tehran.format("YYYY/MM/DD")  # 1403/12/07
tehran.format("HH:mm:ss")    # 00:30:00

utc = d.setTimezone("UTC")
utc.format("YYYY/MM/DD")  # 1403/12/06
utc.format("HH:mm:ss")    # 21:00:00
```

- **Aliases:** `utc` / `gmt` -> `UTC`; `local` / `default` / `system` -> host IANA zone when detectable, else `UTC`.
- **Invalid zone** -> `ValueError`.
- Offsets use stdlib `zoneinfo`, with a **vendored** TZif set under `jalalix/zoneinfo/` (`UTC`, `Etc/UTC`, `Asia/Tehran`, `Asia/Tokyo`, `Europe/London`, `America/New_York`) so Windows works without the PyPI `tzdata` package.

## Format tokens

| Token               |                                 |
| ------------------- | ------------------------------- |
| `YYYY` `YY`         | year                            |
| `MMM` `MM` `M`      | month name / number             |
| `DD` `D`            | day                             |
| `HH` `hh` `mm` `ss` | time                            |
| `A` `a`             | meridiem (ق.ظ. / ب.ظ. or AM/PM) |
| `WN` `WL`           | weekday name / letter           |
| `w` `DDD`           | week of year / day of year      |
| `X` `x`             | unix seconds / ms               |

```python
date.format('YYYY/MM/DD')
date.format('YYYY/MM/DD', {'persianDigits': True})
date.format('DD MMM YYYY', {'calendar': 'gregorian'})
```

## API

Static:

- `create(date, options?)` — timestamp (ms), ISO string, `datetime`, or `date`
- `parseJalali(str, options?)`
- `isValidDate(value)`
- `toPersian(str)` / `fromPersian(str)`
- `compare(a, b)` — true if `a` is before `b`

`options` is `{'timezone': str}` (e.g. `'Asia/Tehran'`).

Instance (main ones):

- `format(...)`, `toISODate(calendar?)`
- `toString()`, `toDateString()`, `toLocaleDateString()`, `toLocaleTimeString()`
- `getFullYear()`, `getMonth()`, `getDate()`, `getDay()`, …
- `setFullYear`, `setMonth`, `setDate`, `setHours`, … (mutate and return `self`)
- `addYears`, `addMonths`, `addWeeks`, `addDays`
- `getStartOfYear` / `Month` / `Week` / `Day` and matching `getEndOf*`
- `clone()`, `setTimezone(tz)`, `getTimezone()`

Method names match the TypeScript package (camelCase).

## Links

- https://pypi.org/project/jalalix/
- https://jalalix.com
- https://github.com/jalalix/python
- [CHANGELOG.md](./CHANGELOG.md)

## License

MIT
