"""Tests for JalaliX.normalizeQueryDate, Arabic-Indic digits, and dot-separator parsing."""

import math

from jalalix import JalaliX

class TestArabicDigits:
    def test_to_from_persian(self):
        assert JalaliX.toPersian("1403/12/07") == "۱۴۰۳/۱۲/۰۷"
        assert JalaliX.fromPersian("۱۴۰۳/۱۲/۰۷") == "1403/12/07"

    def test_from_arabic_indic(self):
        assert JalaliX.fromPersian("١٤٠٣/١٢/٠٧") == "1403/12/07"

    def test_from_mixed_persian_and_arabic_indic(self):
        assert JalaliX.fromPersian("۱٤۰٣/۱٢/۰٧") == "1403/12/07"

class TestParseJalaliDotSeparator:
    def test_dot_separator(self):
        assert JalaliX.parseJalali("1403.12.07").toISODate() == "2025-02-25"

class TestNormalizeQueryDateSentinels:
    def test_sentinels(self):
        assert JalaliX.normalizeQueryDate(None) is None
        assert JalaliX.normalizeQueryDate("null") is None
        assert JalaliX.normalizeQueryDate("") is None
        assert JalaliX.normalizeQueryDate("undefined") is None
        assert JalaliX.normalizeQueryDate("Invalid Date") is None
        assert JalaliX.normalizeQueryDate("NaN") is None
        assert JalaliX.normalizeQueryDate(float("nan")) is None
        assert JalaliX.normalizeQueryDate(0) is None
        assert JalaliX.normalizeQueryDate(-1) is None

    def test_unix_seconds_and_ms(self):
        seconds = 1740430800  # 2025-02-24 21:00:00 UTC / 2025-02-25 00:30:00 Tehran

        assert (
            JalaliX.normalizeQueryDate(seconds, {"timezone": "UTC"})
            == "2025-02-24 21:00:00"
        )
        assert (
            JalaliX.normalizeQueryDate(seconds * 1000, {"timezone": "Asia/Tehran"})
            == "2025-02-25 00:30:00"
        )
        assert (
            JalaliX.normalizeQueryDate(str(seconds), {"timezone": "UTC"})
            == "2025-02-24 21:00:00"
        )

class TestNormalizeQueryDateYearBand:
    def test_jalali_and_gregorian_detection(self):
        assert (
            JalaliX.normalizeQueryDate("1403/12/07", {"timezone": "UTC"})
            == "2025-02-25 00:00:00"
        )
        assert (
            JalaliX.normalizeQueryDate("۱۴۰۳-۱۲-۰۷ 14:30:00", {"timezone": "UTC"})
            == "2025-02-25 14:30:00"
        )
        assert JalaliX.normalizeQueryDate("2025.02.25") == "2025-02-25 00:00:00"
        assert (
            JalaliX.normalizeQueryDate("2025-02-25 12:30:45.123Z")
            == "2025-02-25 12:30:45"
        )
        assert JalaliX.normalizeQueryDate("not-a-date") == "not-a-date"

    def test_wider_default_band(self):
        assert (
            JalaliX.normalizeQueryDate("1200/01/01", {"timezone": "UTC"}) is not None
        )
        assert (
            JalaliX.normalizeQueryDate("1800/01/01", {"timezone": "UTC"}) is not None
        )

    def test_gregorian_years_stay_gregorian_unless_overridden(self):
        assert JalaliX.normalizeQueryDate("2025-01-01") == "2025-01-01 00:00:00"
        assert JalaliX.normalizeQueryDate(
            "2025-01-01",
            {"timezone": "UTC", "jalaliYearMin": 1, "jalaliYearMax": 3000},
        ) != "2025-01-01 00:00:00"

class TestNormalizeQueryDatePassthrough:
    def test_non_string_non_number_passes_through(self):
        obj = {"a": 1}
        arr = [1, 2, 3]

        assert JalaliX.normalizeQueryDate(obj) is obj
        assert JalaliX.normalizeQueryDate(arr) is arr
        assert JalaliX.normalizeQueryDate(True) is True
