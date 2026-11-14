"""Shared golden parity tests (fixtures/golden.json -> testdata/golden.json)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jalalix import JalaliX

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = ROOT / "testdata" / "golden.json"

def load_golden() -> dict:
    with GOLDEN_PATH.open(encoding="utf-8") as f:
        return json.load(f)

def create_from(spec: dict) -> JalaliX:
    if "unixMs" in spec:
        d = JalaliX.create(spec["unixMs"])
        if spec.get("timezone"):
            d = d.setTimezone(spec["timezone"])
        return d
    return JalaliX.create(spec["isoDate"])

@pytest.fixture(scope="module")
def golden() -> dict:
    data = load_golden()
    assert data.get("version") == 1
    return data

class TestGoldenCalendar:
    def test_calendar_cases(self, golden: dict) -> None:
        for case in golden["calendar"]:
            d = create_from(case["create"])
            expect = case["expect"]
            assert d.format("YYYY/MM/DD") == expect["formatYYYYMMDD"], case["id"]
            assert d.toISODate() == expect["toISODateGregorian"], case["id"]
            assert d.toISODate("jalali") == expect["toISODateJalali"], case["id"]

class TestGoldenParse:
    def test_parse_cases(self, golden: dict) -> None:
        for case in golden["parse"]:
            d = JalaliX.parseJalali(case["input"])
            expect = case["expect"]
            assert d.toISODate() == expect["toISODateGregorian"], case["id"]
            if "formatYYYYMMDD" in expect:
                assert d.format("YYYY/MM/DD") == expect["formatYYYYMMDD"], case["id"]

class TestGoldenFormat:
    def test_format_cases(self, golden: dict) -> None:
        for case in golden["format"]:
            if "toPersian" in case:
                assert JalaliX.toPersian(case["toPersian"]["input"]) == case["toPersian"]["expect"]
                assert (
                    JalaliX.fromPersian(case["fromPersian"]["input"])
                    == case["fromPersian"]["expect"]
                )
                continue
            d = create_from(case["create"])
            assert d.format(case["pattern"], case.get("options")) == case["expect"], case["id"]

class TestGoldenTimezone:
    def test_timezone_cases(self, golden: dict) -> None:
        for case in golden["timezone"]:
            if "setTimezoneAlias" in case:
                d = JalaliX.create(case["unixMs"]).setTimezone(case["setTimezoneAlias"])
                assert d.getTimezone() == case["expectTimezone"], case["id"]
                continue
            d = JalaliX.create(case["unixMs"]).setTimezone(case["withTimezone"])
            expect = case["expect"]
            assert d.format("YYYY/MM/DD") == expect["jalaliSlash"], case["id"]
            if "jalaliIso" in expect:
                assert d.toISODate("jalali") == expect["jalaliIso"], case["id"]
            if "wallGregorian" in expect:
                assert d.toISODate() == expect["wallGregorian"], case["id"]
            if "wallTime" in expect:
                assert d.format("HH:mm:ss") == expect["wallTime"], case["id"]
            assert d.getHours() == expect["hours"], case["id"]
            assert d.getMinutes() == expect["minutes"], case["id"]
            if "getTime" in expect:
                assert d.getTime() == expect["getTime"], case["id"]

class TestGoldenMutations:
    def test_mutation_cases(self, golden: dict) -> None:
        for case in golden["mutations"]:
            d = create_from(case["create"])
            if "setFullYear" in case:
                sfy = case["setFullYear"]
                d.setFullYear(sfy["year"], sfy["month0"], sfy["day"])
                assert d.getMonth() == case["expect"]["getMonth"], case["id"]
                assert d.format("YYYY/MM/DD") == case["expect"]["formatYYYYMMDD"], case["id"]
                continue
            for op in case["ops"]:
                if op.startswith("addMonths:"):
                    d = d.addMonths(int(op.split(":")[1]))
                elif op == "getStartOfMonth":
                    d = d.getStartOfMonth()
            assert d.format("YYYY/MM/DD") == case["expect"]["formatYYYYMMDD"], case["id"]
