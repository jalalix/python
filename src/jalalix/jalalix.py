"""JalaliX — Jalali (Persian / Shamsi) calendar for Python."""

from __future__ import annotations

import math
import os
import re
import zoneinfo
from datetime import date, datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any, Dict, Optional, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DateInput = Union[int, float, str, datetime, date, "JalaliX"]

_ZONEINFO_DIR = Path(__file__).resolve().parent / "zoneinfo"

def _ensure_vendored_tzpath() -> None:
    """Prepend package zoneinfo so Windows works without PyPI tzdata."""
    vendored = str(_ZONEINFO_DIR)
    current = list(zoneinfo.TZPATH)
    if vendored not in current:
        zoneinfo.reset_tzpath((vendored, *current))

_ensure_vendored_tzpath()

class JalaliX:
    """Jalali calendar wrapper around a millisecond Unix timestamp + IANA zone."""

    persianNumbers = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"]

    def __init__(self, ms: Optional[int] = None) -> None:
        """Create a JalaliX instance from an optional millisecond timestamp.

        Args:
            ms: Unix timestamp in milliseconds. If None, uses the current time.

        Returns:
            None.
        """
        if ms is None:
            self._ms = int(datetime.now().timestamp() * 1000)
        else:
            self._ms = int(ms)

        # Default zone is UTC (portable; matches Rust/C). Use setTimezone for others.
        self._timezone: str = "UTC"

        local = self._local_dt()
        self._jalali: Dict[str, Any] = {
            "year": 1348,
            "month": 10,
            "day": 11,
            "hours": local.hour,
            "min": local.minute,
            "sec": local.second,
            "ms": local.microsecond // 1000,
            "isLeapYear": False,
        }
        self._is_converted = False
        self._leap_year_division = 0.24219858156
        self._first_day_of_week = 6
        self._date_length = 86400000
        self._week_days_names = [
            "شنبه",
            "یکشنبه",
            "دوشنبه",
            "سه شنبه",
            "چهار شنبه",
            "پنج شنبه",
            "جمعه",
        ]
        self._week_days_letters = ["ش", "ی", "د", "س", "چ", "پ", "ج"]
        self._week_days_gregorian_names = [
            "Sunday",
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
        ]
        self._week_days_gregorian_letters = ["S", "M", "T", "W", "T", "F", "S"]
        self._months_names = [
            "فروردین",
            "اردیبهشت",
            "خرداد",
            "تیر",
            "مرداد",
            "شهریور",
            "مهر",
            "آبان",
            "آذر",
            "دی",
            "بهمن",
            "اسفند",
        ]
        self._months_gregorian_names = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        self._am = "ق.ظ."
        self._pm = "ب.ظ."
        self._am_gregorian = "AM"
        self._pm_gregorian = "PM"

    @staticmethod
    def _host_local_iana() -> str:
        """Return the host local IANA timezone id when detectable, else UTC."""
        try:
            tz = datetime.now().astimezone().tzinfo
            key = getattr(tz, "key", None)
            if key:
                return str(key)
        except Exception:
            pass
        env_tz = os.environ.get("TZ")
        if env_tz:
            return env_tz
        return "UTC"

    @staticmethod
    def _zoneinfo_for(tz_name: str) -> tzinfo:
        """Resolve an IANA id to a tzinfo, searching the vendored path first.

        Args:
            tz_name: Canonical IANA timezone id (e.g. ``Asia/Tehran``).

        Returns:
            A ``ZoneInfo`` or ``timezone.utc`` instance.

        Raises:
            ValueError: If the zone cannot be resolved.
        """
        if tz_name.upper() == "UTC":
            return timezone.utc
        _ensure_vendored_tzpath()
        try:
            return ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            # Explicit package-file fallback (some platforms ignore TZPATH).
            zone_path = _ZONEINFO_DIR / tz_name
            if zone_path.is_file():
                with zone_path.open("rb") as fh:
                    return ZoneInfo.from_file(fh, key=tz_name)
            raise ValueError(f"invalid timezone: {tz_name}") from None

    def _tzinfo(self) -> tzinfo:
        """Return tzinfo for the active instance timezone."""
        return self._zoneinfo_for(self._timezone)

    def _local_dt(self) -> datetime:
        """Convert the internal timestamp to wall time in the active timezone.

        Returns:
            An aware datetime in the instance timezone.
        """
        return datetime.fromtimestamp(self._ms / 1000.0, tz=self._tzinfo())

    def _wall_ms(self) -> int:
        """UTC instant shifted by zone offset -> civil 'as-if-UTC' milliseconds."""
        offset = self._local_dt().utcoffset()
        offset_ms = int(offset.total_seconds() * 1000) if offset is not None else 0
        return self._ms + offset_ms

    def _js_day(self) -> int:
        """Return the JavaScript-style day of week (Sunday = 0 … Saturday = 6).

        Returns:
            Day of week as used by JavaScript ``Date.getDay()``.
        """
        return (self._local_dt().weekday() + 1) % 7

    def _js_timezone_offset(self) -> int:
        """Return the JavaScript-style timezone offset in minutes.

        Returns:
            Minutes to add to local time to get UTC (``getTimezoneOffset()``).
        """
        offset = self._local_dt().utcoffset()
        if offset is None:
            return 0
        return -int(offset.total_seconds() / 60)

    def _to_jalali(self) -> Dict[str, Any]:
        """Convert the current date to Jalali (Persian) calendar date.

        Returns:
            The Jalali date dict with year, month, day, hours, minutes,
            seconds, milliseconds, and isLeapYear.
        """
        if not self._is_converted:
            # Civil day walk uses wall time in the active timezone (instant-preserving).
            wall = self._wall_ms()
            diff_days = math.floor(wall / self._date_length)
            self._jalali["year"] = 1348
            self._jalali["month"] = 10
            self._jalali["day"] = 11

            if diff_days > 0:
                for _ in range(diff_days):
                    self._jalali["day"] += 1

                    if self._jalali["month"] < 7 and self._jalali["day"] > 31:
                        self._jalali["month"] += 1
                        self._jalali["day"] = 1
                    elif self._jalali["month"] > 6 and self._jalali["month"] < 12 and self._jalali["day"] > 30:
                        self._jalali["month"] += 1
                        self._jalali["day"] = 1
                    elif self._jalali["month"] == 12:
                        is_leap = self._check_leap_year(self._jalali["year"])
                        if is_leap and self._jalali["day"] > 30:
                            self._jalali["year"] += 1
                            self._jalali["month"] = 1
                            self._jalali["day"] = 1
                        elif not is_leap and self._jalali["day"] > 29:
                            self._jalali["year"] += 1
                            self._jalali["month"] = 1
                            self._jalali["day"] = 1
            elif diff_days < 0:
                for _ in range(-diff_days):
                    self._jalali["day"] -= 1

                    if self._jalali["day"] < 1:
                        if self._jalali["month"] == 1:
                            self._jalali["year"] -= 1
                            self._jalali["month"] = 12
                            is_leap = self._check_leap_year(self._jalali["year"])
                            self._jalali["day"] = 30 if is_leap else 29
                        elif self._jalali["month"] < 8:
                            self._jalali["month"] -= 1
                            self._jalali["day"] = 31
                        elif self._jalali["month"] < 13:
                            self._jalali["month"] -= 1
                            self._jalali["day"] = 30

            self._jalali["isLeapYear"] = self._check_leap_year(self._jalali["year"])
            self._is_converted = True

        # Keep wall-clock fields in sync with the timestamp
        local = self._local_dt()
        self._jalali["hours"] = local.hour
        self._jalali["min"] = local.minute
        self._jalali["sec"] = local.second
        self._jalali["ms"] = local.microsecond // 1000

        return self._jalali

    def _to_gregorian(self, j_date: Dict[str, Any]) -> int:
        """Convert a Jalali date to a Gregorian timestamp.

        Args:
            j_date: The Jalali date object to convert.

        Returns:
            The timestamp in milliseconds.
        """
        jalali = {
            "year": 1348,
            "month": 10,
            "day": 11,
            "hours": self.getHours(),
            "min": self.getMinutes(),
            "sec": self.getSeconds(),
            "ms": self.getMilliseconds(),
            "isLeapYear": False,
        }

        diff_days = 0
        jy, jm, jd = j_date["year"], j_date["month"], j_date["day"]

        # Match TypeScript conditions exactly (including redundant clauses).
        after_or_equal = (
            jy > 1348
            or (jy == 1348 and jm >= 10)
            or (jy == 1348 and jm == 10 and jd >= 11)
        )
        before = (
            jy < 1348
            or (jy == 1348 and jm < 10)
            or (jy == 1348 and jm == 10 and jd < 11)
        )

        if after_or_equal:
            while True:
                if jalali["year"] == jy and jalali["month"] == jm and jalali["day"] == jd:
                    break
                diff_days += 1
                jalali["day"] += 1

                if jalali["month"] < 7 and jalali["day"] > 31:
                    jalali["month"] += 1
                    jalali["day"] = 1
                elif jalali["month"] > 6 and jalali["month"] < 12 and jalali["day"] > 30:
                    jalali["month"] += 1
                    jalali["day"] = 1
                elif jalali["month"] == 12:
                    is_leap = self._check_leap_year(jalali["year"])
                    if is_leap and jalali["day"] > 30:
                        jalali["year"] += 1
                        jalali["month"] = 1
                        jalali["day"] = 1
                    elif not is_leap and jalali["day"] > 29:
                        jalali["year"] += 1
                        jalali["month"] = 1
                        jalali["day"] = 1
        elif before:
            while True:
                if jalali["year"] == jy and jalali["month"] == jm and jalali["day"] == jd:
                    break
                diff_days -= 1
                jalali["day"] -= 1

                if jalali["day"] < 1:
                    if jalali["month"] == 1:
                        jalali["year"] -= 1
                        jalali["month"] = 12
                        is_leap = self._check_leap_year(jalali["year"])
                        jalali["day"] = 30 if is_leap else 29
                    elif jalali["month"] < 8:
                        jalali["month"] -= 1
                        jalali["day"] = 31
                    elif jalali["month"] < 13:
                        jalali["month"] -= 1
                        jalali["day"] = 30

        local = self._local_dt()
        output_time = (
            diff_days * self._date_length
            + (
                local.hour * 3600
                + (local.minute + self._js_timezone_offset()) * 60
                + local.second
            )
            * 1000
            + local.microsecond // 1000
        )
        return output_time

    def _check_leap_year(self, year: int) -> bool:
        """Check if the given Jalali year is a leap year.

        Args:
            year: The Jalali year to check.

        Returns:
            True if the year is a leap year, false otherwise.
        """
        if year > 0:
            check_year = (year + 2346) * self._leap_year_division
            return check_year - int(check_year) < self._leap_year_division
        return False

    def _reset(self) -> Dict[str, Any]:
        """Reset the Jalali conversion state and recalculate from the base date.

        Returns:
            The recalculated Jalali date.
        """
        self._is_converted = False
        self._jalali["year"] = 1348
        self._jalali["month"] = 10
        self._jalali["day"] = 11
        return self._to_jalali()

    def _add_zero(self, number: int) -> str:
        """Pad a number with a leading zero if it is a single digit.

        Args:
            number: The number to pad.

        Returns:
            The padded string (e.g., "05" for 5).
        """
        return f"{'0' if -1 < number < 10 else ''}{number}"

    def _get_jalali_month(self, number: int) -> str:
        """Return the Persian name of a Jalali month.

        Args:
            number: The month number (1-12).

        Returns:
            The Persian month name (e.g., "فروردین").
        """
        return self._months_names[number - 1]

    def _get_gregorian_month(self, number: int) -> str:
        """Return the English name of a Gregorian month.

        Args:
            number: The month number (1-12).

        Returns:
            The English month name (e.g., "January").
        """
        return self._months_gregorian_names[number - 1]

    def _get_gregorian_day_of_year(self) -> int:
        """Return the day of the year (1-366) in the Gregorian calendar.

        Returns:
            The day of the year.
        """
        local = self._local_dt()
        # Match JS: new Date(year, 0, 0) is Dec 31 of previous year
        start_ms = datetime(local.year, 1, 1).timestamp() * 1000 - self._date_length
        return math.ceil((self._ms - start_ms) / self._date_length)

    def _get_gregorian_week_of_year(self) -> int:
        """Return the ISO week number of the year in the Gregorian calendar.

        Returns:
            The week number (1-53).
        """
        local = self._local_dt()
        d = datetime(local.year, local.month, local.day, tzinfo=timezone.utc)
        # ISO-like week: Thursday of current week
        iso_day = d.isoweekday()  # Mon=1 … Sun=7
        d = d + timedelta(days=4 - iso_day)
        year_start = datetime(d.year, 1, 1, tzinfo=timezone.utc)
        return math.ceil(((d.timestamp() - year_start.timestamp()) * 1000 / self._date_length + 1) / 7)

    def _get_gregorian_week_day_name(self) -> str:
        """Return the English name of the day of the week.

        Returns:
            The day name (e.g., "Monday").
        """
        return self._week_days_gregorian_names[self._js_day()]

    def _get_gregorian_week_day_letter(self) -> str:
        """Return the first letter of the day of the week in English.

        Returns:
            The day letter (e.g., "M" for Monday).
        """
        return self._week_days_gregorian_letters[self._js_day()]

    def _get_week_day_name(self) -> str:
        """Return the Persian name of the day of the week.

        Returns:
            The Persian day name (e.g., "شنبه").
        """
        return self._week_days_names[(self.getDay() + self._first_day_of_week) % 7]

    def _get_week_day_letter(self) -> str:
        """Return the first letter of the day of the week in Persian.

        Returns:
            The Persian day letter (e.g., "ش" for شنبه).
        """
        return self._week_days_letters[(self.getDay() + self._first_day_of_week) % 7]

    def _get_utc_timezone(self) -> str:
        """Extract and return the UTC timezone string from the date.

        Returns:
            The timezone string (e.g., " GMT+0330").
        """
        offset = -self._js_timezone_offset()
        sign = "+" if offset >= 0 else "-"
        abs_offset = abs(offset)
        hours = abs_offset // 60
        mins = abs_offset % 60
        return f" GMT{sign}{hours:02d}{mins:02d}"

    def _normalize_date(self, days: int) -> int:
        """Adjust the date by adding the specified number of days.

        Args:
            days: The number of days to add (can be negative).

        Returns:
            The updated timestamp in milliseconds.
        """
        local = self._local_dt()
        new_local = local + timedelta(days=days)
        self._ms = int(new_local.timestamp() * 1000)
        return self._ms

    def _normalize_jalali(self, j_date: Dict[str, Any], year: int, month: int, day: int) -> int:
        """Normalize Jalali date components and set the internal timestamp.

        Args:
            j_date: The current Jalali date object.
            year: The target year.
            month: The target month (1-12).
            day: The target day of month.

        Returns:
            The updated timestamp in milliseconds.
        """
        if month < 1:
            year_diff = math.ceil((1 - month) / 12)
            year -= year_diff
            month = 12 * year_diff + month
        elif month > 12:
            year_diff = math.floor((month - 1) / 12)
            year += year_diff
            month = month - 12 * year_diff

        if month > 6 and month < 12 and day > 30:
            day = 30
        elif month == 12:
            is_leap = self._check_leap_year(year)
            if is_leap and day > 30:
                day = 30
            elif not is_leap and day > 29:
                day = 29

        updated = dict(j_date)
        updated.update({"year": year, "month": month, "day": day})
        self._ms = self._to_gregorian(updated)
        return self._ms

    def _normalize_timezone(self, tz: Optional[str]) -> str:
        """Normalize a timezone string to a canonical IANA id.

        Args:
            tz: The timezone string (e.g., "UTC", "local", "Asia/Tehran").

        Returns:
            The normalized timezone string.

        Raises:
            ValueError: If ``tz`` is empty or not a known zone.
        """
        if tz is None:
            return self.getTimezone()
        trimmed = tz.strip()
        if not trimmed:
            raise ValueError("invalid timezone: empty")
        lowered = trimmed.lower()
        if lowered in ("default", "local", "system"):
            return self._host_local_iana()
        if lowered in ("utc", "gmt"):
            return "UTC"
        # Preserve IANA casing; validate via ZoneInfo / vendored TZif.
        self._zoneinfo_for(trimmed)
        return trimmed

    def _get_gregorian_meridiem(self) -> str:
        """Return AM or PM based on the hour in 12-hour format.

        Returns:
            "AM" or "PM".
        """
        return self._pm_gregorian if self.getHours() >= 12 else self._am_gregorian

    @staticmethod
    def _parse_input(value: DateInput) -> int:
        """Parse a date input into a millisecond Unix timestamp.

        Args:
            value: The date value (timestamp ms, ISO string, datetime, date, or JalaliX).

        Returns:
            Unix timestamp in milliseconds.
        """
        if isinstance(value, JalaliX):
            return value.getTime()
        if isinstance(value, bool):
            raise TypeError("JalaliX.create: invalid date")
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, datetime):
            if value.tzinfo is not None:
                return int(value.timestamp() * 1000)
            return int(value.timestamp() * 1000)
        if isinstance(value, date):
            dt = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        if isinstance(value, str):
            return JalaliX._parse_iso_string(value)
        raise TypeError(f"JalaliX.create: unsupported date type {type(value)!r}")

    @staticmethod
    def _parse_iso_string(value: str) -> int:
        """Parse an ISO date/time string into a millisecond Unix timestamp.

        Args:
            value: ISO date or datetime string.

        Returns:
            Unix timestamp in milliseconds.
        """
        s = value.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"

        # Date-only YYYY-MM-DD -> UTC midnight (JS Date behaviour)
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            y, m, d = (int(p) for p in s.split("-"))
            dt = datetime(y, m, d, tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)

        try:
            dt = datetime.fromisoformat(s)
        except ValueError as exc:
            raise ValueError(f"JalaliX.create: invalid date string {value!r}") from exc

        if dt.tzinfo is not None:
            return int(dt.timestamp() * 1000)
        # Naive datetime with time -> local (JS behaviour for non-Z ISO)
        return int(dt.timestamp() * 1000)

    @staticmethod
    def create(date: DateInput, options: Optional[Dict[str, Any]] = None) -> "JalaliX":
        """Create a JalaliX instance from a Gregorian date value.

        Args:
            date: The date value (timestamp ms, ISO string, datetime, or date).
            options: Optional dict with timezone key.

        Returns:
            A new JalaliX instance.
        """
        output = JalaliX(JalaliX._parse_input(date))
        if options and options.get("timezone"):
            output = output.setTimezone(options["timezone"])
        return output

    @staticmethod
    def parseJalali(value: str, options: Optional[Dict[str, Any]] = None) -> "JalaliX":
        """Parse a Jalali date string into a JalaliX instance.

        Accepts ``YYYY/MM/DD`` or ``YYYY-MM-DD``, optional time
        (``HH:mm`` / ``HH:mm:ss``), and Persian digits.

        Args:
            value: Jalali date string (e.g. "1403/12/07", "۱۴۰۳-۱۲-۰۷ 14:30").
            options: Optional dict with timezone key.

        Returns:
            A new JalaliX instance.
        """
        normalized = JalaliX.fromPersian(str(value)).strip()
        match = re.match(
            r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})(?:[ T](\d{1,2}):(\d{1,2})(?::(\d{1,2}))?)?$",
            normalized,
        )
        if not match:
            raise ValueError(f'JalaliX.parseJalali: invalid Jalali date "{value}"')

        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        hours = int(match.group(4) or 0)
        minutes = int(match.group(5) or 0)
        seconds = int(match.group(6) or 0)

        if month < 1 or month > 12 or day < 1 or day > 31:
            raise ValueError(f'JalaliX.parseJalali: invalid Jalali date "{value}"')

        output = JalaliX.create(datetime.now(), options)
        output.setFullYear(year, month - 1, day)
        output.setHours(hours, minutes, seconds, 0)
        return output

    @staticmethod
    def isValidDate(value: Any) -> bool:
        """Check if the given value is a valid date.

        Args:
            value: The value to check.

        Returns:
            True if valid date, false otherwise.
        """
        if isinstance(value, JalaliX):
            return True
        if isinstance(value, datetime):
            return True
        if isinstance(value, date):
            return True
        return False

    @classmethod
    def toPersian(cls, s: str) -> str:
        """Convert Western numerals (0-9) to Persian numerals (۰-۹) in a string.

        Args:
            s: The string containing numerals to convert.

        Returns:
            The string with Persian numerals.
        """
        out = s
        for i in range(10):
            out = out.replace(str(i), cls.persianNumbers[i])
        return out

    @classmethod
    def fromPersian(cls, s: str) -> str:
        """Convert Persian numerals (۰-۹) to Western numerals (0-9) in a string.

        Args:
            s: The string containing Persian numerals.

        Returns:
            The string with Western numerals.
        """
        out = s
        for i in range(10):
            out = out.replace(cls.persianNumbers[i], str(i))
        return out

    @staticmethod
    def compare(a: "JalaliX", b: "JalaliX") -> bool:
        """Compare two JalaliX dates.

        Args:
            a: The first date to compare.
            b: The second date to compare against.

        Returns:
            True if a is before b, false otherwise.
        """
        return a.getTime() < b.getTime()

    def toString(self) -> str:
        """Return a string representation of a date in Jalali format.

        Returns:
            Full date string with weekday, day, month, year, and time.
        """
        j = self._to_jalali()
        return (
            f"{self._get_week_day_name()} {self._add_zero(j['day'])} "
            f"{self._get_jalali_month(j['month'])} {self._add_zero(j['year'])} "
            f"{j['hours']}:{self._add_zero(j['min'])}:{self._add_zero(j['sec'])}"
            f"{self._get_utc_timezone()}"
        )

    def toDateString(self) -> str:
        """Return a date as a string value (without time).

        Returns:
            Date string with weekday, day, month, and year.
        """
        j = self._to_jalali()
        return (
            f"{self._get_week_day_name()} {self._add_zero(j['day'])} "
            f"{self._get_jalali_month(j['month'])} {self._add_zero(j['year'])}"
        )

    def toLocaleDateString(self) -> str:
        """Return a date as a string value in locale format (YYYY/MM/DD).

        Returns:
            Locale-formatted date string.
        """
        j = self._to_jalali()
        return f"{self._add_zero(j['year'])}/{self._add_zero(j['month'])}/{self._add_zero(j['day'])}"

    def toLocaleTimeString(self) -> str:
        """Return a time as a string value with meridiem.

        Returns:
            Time string (e.g., "10:30:45 ق.ظ.").
        """
        j = self._to_jalali()
        return f"{j['hours'] % 12}:{self._add_zero(j['min'])}:{self._add_zero(j['sec'])} {self.getMeridiem()}"

    def __str__(self) -> str:
        """Return the Jalali string representation of this instance.

        Returns:
            Same as :meth:`toString`.
        """
        return self.toString()

    def __repr__(self) -> str:
        """Return an unambiguous representation of this instance.

        Returns:
            A string like ``JalaliX(<timestamp>)``.
        """
        return f"JalaliX({self.getTime()})"

    def getFullYear(self) -> int:
        """Get the Jalali year.

        Returns:
            The year (e.g., 1403).
        """
        return self._to_jalali()["year"]

    def getMonth(self) -> int:
        """Get the Jalali month (1-12).

        Returns:
            The month number.
        """
        return self._to_jalali()["month"]

    def getDate(self) -> int:
        """Get the day of the month in Jalali calendar (1-31).

        Returns:
            The day of the month.
        """
        return self._to_jalali()["day"]

    def getDay(self) -> int:
        """Get the day of the week (1=Saturday, 7=Friday in Jalali).

        Returns:
            The day number (1-7).
        """
        return (self._js_day() - self._first_day_of_week + 7 + 1) % 7

    def getHours(self) -> int:
        """Get the hours value using local time.

        Returns:
            The hour (0-23).
        """
        return self._local_dt().hour

    def getMinutes(self) -> int:
        """Get the minutes value using local time.

        Returns:
            The minutes (0-59).
        """
        return self._local_dt().minute

    def getSeconds(self) -> int:
        """Get the seconds value using local time.

        Returns:
            The seconds (0-59).
        """
        return self._local_dt().second

    def getMilliseconds(self) -> int:
        """Get the milliseconds value using local time.

        Returns:
            The milliseconds (0-999).
        """
        return self._local_dt().microsecond // 1000

    def getTime(self) -> int:
        """Get the timestamp in milliseconds since Unix epoch.

        Returns:
            The elapsed milliseconds since midnight, January 1, 1970 GMT.
        """
        return self._ms

    def getWeekOfYear(self) -> int:
        """Get the week number of the year in Jalali calendar.

        Returns:
            The week number (1-53).
        """
        day_of_year = self.getDayOfYear()
        day_of_week = JalaliX(self._ms).getStartOfYear().getDayISO()
        return math.ceil((day_of_year + day_of_week - 1) / 7)

    def getDayOfYear(self) -> int:
        """Get the day of the year in Jalali calendar (1-366).

        Returns:
            The day of the year.
        """
        j = self._to_jalali()
        if j["month"] < 7:
            return j["day"] + (j["month"] - 1) * 31
        if j["month"] < 12:
            return j["day"] + 186 + (j["month"] - 7) * 30
        return j["day"] + 336

    def getDayISO(self) -> int:
        """Get the ISO day of the week (1=Monday, 7=Sunday).

        Returns:
            The ISO day number (1-7).
        """
        return ((self.getDay() + 6) % 7) + 1

    def getHoursISO(self) -> int:
        """Get the hour in 12-hour format (1-12).

        Returns:
            The hour in 12-hour format.
        """
        hours = self.getHours()
        return hours - 12 if hours > 12 else hours

    def getMeridiem(self) -> str:
        """Get the meridiem (AM/PM) in Persian.

        Returns:
            "ق.ظ." (before noon) or "ب.ظ." (after noon).
        """
        j = self._to_jalali()
        return self._pm if j["hours"] > 12 else self._am

    def getTimezone(self) -> str:
        """Get the IANA timezone id of this instance.

        Returns:
            The IANA timezone string (e.g., "Asia/Tehran").
        """
        return self._timezone

    def setTime(self, time: int) -> "JalaliX":
        """Set the date and time value.

        Args:
            time: Elapsed milliseconds since midnight, January 1, 1970 GMT.

        Returns:
            This instance.
        """
        self._ms = int(time)
        self._reset()
        return self

    def setMilliseconds(self, ms: int) -> "JalaliX":
        """Set the milliseconds value using local time.

        Args:
            ms: A numeric value equal to the millisecond value.

        Returns:
            This instance.
        """
        local = self._local_dt().replace(microsecond=int(ms) * 1000)
        self._ms = int(local.timestamp() * 1000)
        self._jalali["ms"] = ms
        return self

    def setSeconds(self, sec: int, ms: Optional[int] = None) -> "JalaliX":
        """Set the seconds value using local time.

        Args:
            sec: A numeric value equal to the seconds value.
            ms: Optional numeric value equal to the milliseconds value.

        Returns:
            This instance.
        """
        local = self._local_dt()
        kwargs: Dict[str, int] = {"second": int(sec)}
        if ms is not None:
            kwargs["microsecond"] = int(ms) * 1000
        local = local.replace(**kwargs)
        self._ms = int(local.timestamp() * 1000)
        self._jalali["sec"] = sec
        if ms:
            self._jalali["ms"] = ms
        return self

    def setMinutes(
        self, min: int, sec: Optional[int] = None, ms: Optional[int] = None
    ) -> "JalaliX":
        """Set the minutes value using local time.

        Args:
            min: A numeric value equal to the minutes value.
            sec: Optional numeric value equal to the seconds value.
            ms: Optional numeric value equal to the milliseconds value.

        Returns:
            This instance.
        """
        local = self._local_dt()
        kwargs: Dict[str, int] = {"minute": int(min)}
        if sec is not None:
            kwargs["second"] = int(sec)
        if ms is not None:
            kwargs["microsecond"] = int(ms) * 1000
        local = local.replace(**kwargs)
        self._ms = int(local.timestamp() * 1000)
        self._jalali["min"] = min
        if sec:
            self._jalali["sec"] = sec
        if ms:
            self._jalali["ms"] = ms
        return self

    def setHours(
        self,
        hours: int,
        min: Optional[int] = None,
        sec: Optional[int] = None,
        ms: Optional[int] = None,
    ) -> "JalaliX":
        """Set the hour value using local time.

        Args:
            hours: A numeric value equal to the hours value.
            min: Optional numeric value equal to the minutes value.
            sec: Optional numeric value equal to the seconds value.
            ms: Optional numeric value equal to the milliseconds value.

        Returns:
            This instance.
        """
        local = self._local_dt()
        kwargs: Dict[str, int] = {"hour": int(hours)}
        if min is not None:
            kwargs["minute"] = int(min)
        if sec is not None:
            kwargs["second"] = int(sec)
        if ms is not None:
            kwargs["microsecond"] = int(ms) * 1000
        local = local.replace(**kwargs)
        self._ms = int(local.timestamp() * 1000)
        self._jalali["hours"] = hours
        if min:
            self._jalali["min"] = min
        if sec:
            self._jalali["sec"] = sec
        if ms:
            self._jalali["ms"] = ms
        return self

    def setDate(self, date: int) -> "JalaliX":
        """Set the numeric day-of-the-month value using local time.

        Args:
            date: A numeric value equal to the day of the month.

        Returns:
            This instance.
        """
        j = self._to_jalali()
        self._normalize_date(date - j["day"])
        return self

    def setMonth(self, month: int, date: Optional[int] = None) -> "JalaliX":
        """Set the month value using local time.

        Args:
            month: Zero-based month (0 for Farvardin); other months follow consecutively.
            date: Optional day of the month; defaults to the current day via getDate.

        Returns:
            This instance.
        """
        j = self._to_jalali()
        self._normalize_jalali(j, j["year"], month + 1, j["day"])
        self._reset()
        if date is not None:
            j = self._to_jalali()
            self._normalize_date(date - j["day"])
            self._reset()
        return self

    def setFullYear(
        self, year: int, month: Optional[int] = None, date: Optional[int] = None
    ) -> "JalaliX":
        """Set the year using local time.

        Args:
            year: A numeric value for the year.
            month: Optional zero-based month (0 for Farvardin, 11 for Esfand).
            date: Optional day of the month.

        Returns:
            This instance.
        """
        j = self._to_jalali()
        self._normalize_jalali(
            j, year, month + 1 if month is not None else j["month"], j["day"]
        )
        self._reset()
        if date is not None:
            j = self._to_jalali()
            self._normalize_date(date - j["day"])
            self._reset()
        return self

    def addYears(self, year: int) -> "JalaliX":
        """Add the specified number of years to the date.

        Args:
            year: The number of years to add (can be negative).

        Returns:
            This instance modified.
        """
        j = self._to_jalali()
        self._normalize_jalali(j, j["year"] + year, j["month"], j["day"])
        self._reset()
        return self

    def addMonths(self, month: int) -> "JalaliX":
        """Add the specified number of months to the date.

        Args:
            month: The number of months to add (can be negative).

        Returns:
            This instance modified.
        """
        j = self._to_jalali()
        self._normalize_jalali(j, j["year"], j["month"] + month, j["day"])
        self._reset()
        return self

    def addWeeks(self, weeks: int) -> "JalaliX":
        """Add the specified number of weeks to the date.

        Args:
            weeks: The number of weeks to add (can be negative).

        Returns:
            This instance modified.
        """
        self._normalize_date(weeks * 7)
        self._reset()
        return self

    def addDays(self, days: int) -> "JalaliX":
        """Add the specified number of days to the date.

        Args:
            days: The number of days to add (can be negative).

        Returns:
            This instance modified.
        """
        self._normalize_date(days)
        self._reset()
        return self

    def getStartOfYear(self) -> "JalaliX":
        """Set this instance to the start of the Jalali year.

        Returns:
            This instance modified to the first moment of the year.
        """
        return self.addDays(-1 * self.getDayOfYear() + 1).getStartOfDay()

    def getStartOfMonth(self) -> "JalaliX":
        """Set this instance to the start of the current month.

        Returns:
            This instance modified to the first moment of the month.
        """
        return self.addDays(-1 * self.getDate() + 1).getStartOfDay()

    def getStartOfWeek(self) -> "JalaliX":
        """Set this instance to the start of the current week (Monday).

        Returns:
            This instance modified to the first moment of the week.
        """
        return self.addDays(-1 * self.getDayISO() + 1).getStartOfDay()

    def getStartOfDay(self) -> "JalaliX":
        """Set this instance to the start of the current day (00:00:00.000).

        Returns:
            This instance modified to midnight.
        """
        self.setHours(0, 0, 0, 0)
        return self

    def getEndOfYear(self) -> "JalaliX":
        """Set this instance to the end of the Jalali year (23:59:59.999).

        Returns:
            This instance modified to the last moment of the year.
        """
        j = self._to_jalali()
        last_day = 366 if j["isLeapYear"] else 365
        return self.addDays(last_day - self.getDayOfYear()).getEndOfDay()

    def getEndOfMonth(self) -> "JalaliX":
        """Set this instance to the end of the current month.

        Returns:
            This instance modified to the last moment of the month.
        """
        j = self._to_jalali()
        last_day = 31
        if j["month"] > 6 and j["month"] < 12:
            last_day = 30
        elif j["month"] == 12:
            last_day = 30 if j["isLeapYear"] else 29
        return self.addDays(last_day - self.getDate()).getEndOfDay()

    def getEndOfWeek(self) -> "JalaliX":
        """Set this instance to the end of the current week (Sunday).

        Returns:
            This instance modified to the last moment of the week.
        """
        return self.addDays(7 - self.getDayISO()).getEndOfDay()

    def getEndOfDay(self) -> "JalaliX":
        """Set this instance to the end of the current day (23:59:59.999).

        Returns:
            This instance modified to the last moment of the day.
        """
        self.setHours(23, 59, 59, 999)
        return self

    def clone(self) -> "JalaliX":
        """Create a copy of this JalaliX instance.

        Returns:
            A new JalaliX instance with the same timestamp and timezone.
        """
        out = JalaliX(self._ms)
        out._timezone = self._timezone
        return out

    def setTimezone(self, timezone_name: Optional[str] = None) -> "JalaliX":
        """Create a new JalaliX with the same UTC instant in a different timezone.

        Instant-preserving: ``getTime()`` is unchanged; wall clock / Jalali day
        may change.

        Args:
            timezone_name: IANA id (e.g. ``Asia/Tehran``), or alias
                ``local`` / ``system`` / ``default``, ``UTC`` / ``GMT``.
                ``None`` keeps the current zone.

        Returns:
            A new JalaliX instance in the specified timezone.

        Raises:
            ValueError: If the zone cannot be resolved.
        """
        tz_name = self._normalize_timezone(timezone_name)
        out = JalaliX(self._ms)
        out._timezone = tz_name
        return out

    def toISODate(self, calendar: str = "gregorian") -> str:
        """Return a calendar date string using local getters (no UTC shift).

        Args:
            calendar: ``"gregorian"`` (default) -> ``YYYY-MM-DD`` Gregorian;
                ``"jalali"`` -> Jalali ``YYYY-MM-DD``.

        Returns:
            Date string in ``YYYY-MM-DD`` form.
        """
        if calendar == "jalali":
            return self.format("YYYY-MM-DD")
        local = self._local_dt()
        return f"{local.year}-{self._add_zero(local.month)}-{self._add_zero(local.day)}"

    def format(
        self,
        s: str,
        persianOrOptions: Union[bool, Dict[str, Any], None] = None,
        gregorian: Optional[bool] = None,
    ) -> str:
        """Format the date according to the specified format string.

        Prefer ``format(str, { calendar, persianDigits })``. Positional
        booleans remain supported: ``format(str, persianDigits?, gregorian?)``.

        Args:
            s: The format string (e.g., "YYYY/MM/DD", "DD MMM YYYY").
            persianOrOptions: Persian digits flag, or options dict.
            gregorian: If true, uses Gregorian calendar (positional API only).

        Returns:
            The formatted date string.
        """
        persian = False
        use_gregorian = False

        if isinstance(persianOrOptions, dict):
            persian = bool(persianOrOptions.get("persianDigits"))
            use_gregorian = persianOrOptions.get("calendar") == "gregorian"
        else:
            persian = bool(persianOrOptions)
            use_gregorian = bool(gregorian)

        placeholders: list = []

        def ph(val: str) -> str:
            i = len(placeholders)
            placeholders.append(val)
            return f"\ue000{i}\ue001"

        output = s
        local = self._local_dt()

        year = local.year if use_gregorian else self.getFullYear()
        month = (local.month) if use_gregorian else self.getMonth()
        week_of_year = (
            self._get_gregorian_week_of_year() if use_gregorian else self.getWeekOfYear()
        )
        day_of_year = (
            self._get_gregorian_day_of_year() if use_gregorian else self.getDayOfYear()
        )
        date_n = local.day if use_gregorian else self.getDate()
        month_name = (
            self._get_gregorian_month(month)
            if use_gregorian
            else self._get_jalali_month(month)
        )
        week_day_name = (
            self._get_gregorian_week_day_name()
            if use_gregorian
            else self._get_week_day_name()
        )
        week_day_letter = (
            self._get_gregorian_week_day_letter()
            if use_gregorian
            else self._get_week_day_letter()
        )
        meridiem = (
            self._get_gregorian_meridiem() if use_gregorian else self.getMeridiem()
        )
        year_str = str(year)

        if re.search(r"YYYY", output):
            output = re.sub(r"YYYY", lambda _: ph(year_str), output)
        if re.search(r"YYY", output):
            output = re.sub(r"YYY", lambda _: ph(year_str[-3:]), output)
        if re.search(r"YY", output):
            output = re.sub(r"YY", lambda _: ph(year_str[-2:]), output)
        if re.search(r"Y", output):
            output = re.sub(r"Y", lambda _: ph(year_str[-1:]), output)

        if re.search(r"MMM", output):
            output = re.sub(r"MMM", lambda _: ph(month_name), output)
        if re.search(r"MM", output):
            output = re.sub(r"MM", lambda _: ph(self._add_zero(month)), output)
        if re.search(r"M", output):
            output = re.sub(r"M", lambda _: ph(str(month)), output)

        if re.search(r"W", output):
            output = re.sub(r"W", lambda _: ph(self._add_zero(week_of_year)), output)
        if re.search(r"w", output):
            output = re.sub(r"w", lambda _: ph(str(week_of_year)), output)

        if re.search(r"DW", output):
            output = re.sub(r"DW", lambda _: ph(str(self.getDayISO())), output)
        if re.search(r"dw", output):
            dw = (self._js_day() or 7) if use_gregorian else self.getDay()
            output = re.sub(r"dw", lambda _: ph(str(dw)), output)
        if re.search(r"WN", output):
            output = re.sub(r"WN", lambda _: ph(week_day_name), output)
        if re.search(r"wn", output):
            output = re.sub(r"wn", lambda _: ph(week_day_name), output)
        if re.search(r"WL", output):
            output = re.sub(r"WL", lambda _: ph(week_day_letter), output)
        if re.search(r"wl", output):
            output = re.sub(r"wl", lambda _: ph(week_day_letter), output)

        if re.search(r"DDDD", output):
            output = re.sub(r"DDDD", lambda _: ph(self._add_zero(day_of_year)), output)
        if re.search(r"DDD", output):
            output = re.sub(r"DDD", lambda _: ph(str(day_of_year)), output)

        if re.search(r"DD", output):
            output = re.sub(r"DD", lambda _: ph(self._add_zero(date_n)), output)
        if re.search(r"D", output):
            output = re.sub(r"D", lambda _: ph(str(date_n)), output)

        hours = self.getHours()
        if re.search(r"HH", output):
            output = re.sub(r"HH", lambda _: ph(self._add_zero(hours)), output)
        if re.search(r"H", output):
            output = re.sub(r"H", lambda _: ph(str(hours)), output)

        hours_iso = hours - 12 if hours > 12 else (12 if hours == 0 else hours)
        if re.search(r"hh", output):
            output = re.sub(r"hh", lambda _: ph(self._add_zero(hours_iso)), output)
        if re.search(r"h", output):
            output = re.sub(r"h", lambda _: ph(str(hours_iso)), output)

        if re.search(r"mm", output):
            output = re.sub(r"mm", lambda _: ph(self._add_zero(self.getMinutes())), output)
        if re.search(r"m", output):
            output = re.sub(r"m", lambda _: ph(str(self.getMinutes())), output)

        if re.search(r"ss", output):
            output = re.sub(r"ss", lambda _: ph(self._add_zero(self.getSeconds())), output)
        if re.search(r"s", output):
            output = re.sub(r"s", lambda _: ph(str(self.getSeconds())), output)

        if re.search(r"sss", output):
            output = re.sub(r"sss", lambda _: ph(str(self.getMilliseconds())), output)
        if re.search(r"SSS", output):
            output = re.sub(r"SSS", lambda _: ph(str(self.getMilliseconds())), output)

        if re.search(r"A", output):
            output = re.sub(r"A", lambda _: ph(meridiem), output)
        if re.search(r"a", output):
            output = re.sub(r"a", lambda _: ph(meridiem), output)

        if re.search(r"X", output):
            output = re.sub(r"X", lambda _: ph(str(math.floor(self.getTime() / 1000))), output)
        if re.search(r"x", output):
            output = re.sub(r"x", lambda _: ph(str(self.getTime())), output)

        for i, val in enumerate(placeholders):
            output = output.replace(f"\ue000{i}\ue001", val)

        return JalaliX.toPersian(output) if persian else output
