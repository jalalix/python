"""Tests for JalaliX (Python port)."""

from datetime import date, datetime, timezone

import pytest

from jalalix import JalaliX

class TestGolden:
    def test_create_format_jalali(self):
        assert JalaliX.create("2025-02-25").format("YYYY/MM/DD") == "1403/12/07"

    def test_parse_jalali_to_iso(self):
        assert JalaliX.parseJalali("1403/12/07").toISODate() == "2025-02-25"

class TestCreate:
    def test_from_ms(self):
        ms = 1740441600000  # approx 2025-02-25 UTC
        d = JalaliX.create(ms)
        assert d.getTime() == ms

    def test_from_datetime(self):
        dt = datetime(2025, 2, 25, 12, 0, 0, tzinfo=timezone.utc)
        d = JalaliX.create(dt)
        assert d.format("YYYY/MM/DD") == "1403/12/07"

    def test_from_date(self):
        d = JalaliX.create(date(2025, 2, 25))
        assert d.format("YYYY/MM/DD") == "1403/12/07"

    def test_iso_with_offset(self):
        # Midday UTC stays on 2025-02-25 for both local and UTC day-walk
        d = JalaliX.create("2025-02-25T12:00:00+00:00")
        assert d.toISODate("jalali") == "1403-12-07"
        assert d.format("YYYY/MM/DD") == "1403/12/07"

        # parseJalali -> local calendar date (portable across timezones)
        assert JalaliX.parseJalali("1403/12/07").toISODate() == "2025-02-25"

class TestParseJalali:
    def test_slash_and_dash(self):
        a = JalaliX.parseJalali("1403/12/07")
        b = JalaliX.parseJalali("1403-12-07")
        assert a.toISODate() == b.toISODate() == "2025-02-25"

    def test_persian_digits_and_time(self):
        d = JalaliX.parseJalali("۱۴۰۳-۱۲-۰۷ 14:30")
        assert d.format("YYYY/MM/DD") == "1403/12/07"
        assert d.getHours() == 14
        assert d.getMinutes() == 30

    def test_invalid(self):
        with pytest.raises(ValueError):
            JalaliX.parseJalali("not-a-date")

class TestFormat:
    def test_persian_digits_options(self):
        d = JalaliX.create("2025-02-25")
        assert d.format("YYYY/MM/DD", {"persianDigits": True}) == "۱۴۰۳/۱۲/۰۷"

    def test_gregorian_calendar(self):
        d = JalaliX.create("2025-02-25")
        assert "February" in d.format("DD MMM YYYY", {"calendar": "gregorian"})

    def test_positional_api(self):
        d = JalaliX.create("2025-02-25")
        assert d.format("YYYY/MM/DD", True) == "۱۴۰۳/۱۲/۰۷"

class TestPersianHelpers:
    def test_to_from_persian(self):
        assert JalaliX.toPersian("1403/12/07") == "۱۴۰۳/۱۲/۰۷"
        assert JalaliX.fromPersian("۱۴۰۳/۱۲/۰۷") == "1403/12/07"

class TestMonthQuirk:
    def test_get_month_1_based_set_0_based(self):
        d = JalaliX.create("2025-02-25")
        d.setFullYear(1404, 0, 1)
        assert d.getMonth() == 1
        assert d.getDate() == 1
        assert d.getFullYear() == 1404

    def test_set_month(self):
        d = JalaliX.parseJalali("1403/01/15")
        d.setMonth(11)  # Esfand (0-based)
        assert d.getMonth() == 12

class TestMutating:
    def test_add_and_start_chain(self):
        result = (
            JalaliX.create("2025-02-25")
            .addMonths(1)
            .getStartOfMonth()
            .format("YYYY/MM/DD")
        )

        assert result == "1404/01/01"

    def test_setters_return_self(self):
        d = JalaliX.create("2025-02-25")
        assert d.setHours(10, 20, 30, 0) is d
        assert d.getHours() == 10
        assert d.getMinutes() == 20
        assert d.getSeconds() == 30

    def test_clone(self):
        a = JalaliX.create("2025-02-25")
        b = a.clone()
        assert a.getTime() == b.getTime()
        assert a is not b
        b.addDays(1)
        assert a.getTime() != b.getTime()

class TestCompareAndValid:
    def test_compare(self):
        a = JalaliX.create("2025-02-25")
        b = JalaliX.create("2025-02-26")
        assert JalaliX.compare(a, b) is True
        assert JalaliX.compare(b, a) is False

    def test_is_valid_date(self):
        assert JalaliX.isValidDate(datetime.now()) is True
        assert JalaliX.isValidDate(date.today()) is True
        assert JalaliX.isValidDate(JalaliX.create("2025-02-25")) is True
        assert JalaliX.isValidDate("2025-02-25") is False
        assert JalaliX.isValidDate(None) is False

class TestRoundTrip:
    def test_several_dates(self):
        samples = [
            ("2024-03-20", "1403/01/01"),
            ("2025-02-25", "1403/12/07"),
            ("2025-03-21", "1404/01/01"),
        ]
        for iso, jalali in samples:
            assert JalaliX.create(iso).format("YYYY/MM/DD") == jalali
            assert JalaliX.parseJalali(jalali).toISODate() == iso

class TestTimezone:
    """Golden cases from testdata/timezone.json (instant-preserving contract)."""

    MS = 1740430800000  # 2025-02-25T00:30:00+03:30
    MS_NOON = 1740484800000  # 2025-02-25T12:00:00Z

    def test_tehran_offset_instant(self):
        d = JalaliX.create(self.MS).setTimezone("Asia/Tehran")
        assert d.getTime() == self.MS
        assert d.getTimezone() == "Asia/Tehran"
        assert d.format("YYYY/MM/DD") == "1403/12/07"
        assert d.format("HH:mm:ss") == "00:30:00"
        assert d.toISODate() == "2025-02-25"
        assert d.toISODate("jalali") == "1403-12-07"

    def test_same_instant_utc(self):
        d = JalaliX.create(self.MS).setTimezone("UTC")
        assert d.getTime() == self.MS
        assert d.format("YYYY/MM/DD") == "1403/12/06"
        assert d.format("HH:mm:ss") == "21:00:00"
        assert d.toISODate() == "2025-02-24"

    def test_utc_noon_tehran(self):
        d = JalaliX.create(self.MS_NOON).setTimezone("Asia/Tehran")
        assert d.format("YYYY/MM/DD") == "1403/12/07"
        assert d.format("HH:mm:ss") == "15:30:00"

    def test_alias_utc(self):
        d = JalaliX.create(self.MS_NOON).setTimezone("utc")
        assert d.getTimezone() == "UTC"

    def test_instant_preserving_and_invalid(self):
        d = JalaliX.create(self.MS)
        tehran = d.setTimezone("Asia/Tehran")
        utc = d.setTimezone("UTC")
        assert d.getTime() == tehran.getTime() == utc.getTime()
        assert tehran.format("YYYY/MM/DD") != utc.format("YYYY/MM/DD")
        with pytest.raises(ValueError):
            d.setTimezone("Mars/Olympus")

    def test_clone_keeps_timezone(self):
        a = JalaliX.create(self.MS).setTimezone("Asia/Tehran")
        b = a.clone()
        assert b.getTimezone() == "Asia/Tehran"
        assert b.format("HH:mm:ss") == "00:30:00"
