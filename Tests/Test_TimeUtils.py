# =============================================================================
# Tests for GPS Time Conversion Utilities
# =============================================================================

import math
import pytest
from AnanseQC.Core import Constants as C
from AnanseQC.Core.TimeUtils import C_TimeUtils

c_TimeUtils = C_TimeUtils()


class TestCalendarToJulian:
    """Tests for calendar_to_julian()."""

    def test_gps_epoch(self):
        """GPS epoch (1980-01-06) should give the known Julian date."""
        jd = c_TimeUtils.CalendarToJulianDate(1980, 1, 6)
        assert abs(jd - C.JULIAN_DATE_AT_GPS_EPOCH) < 0.001

    def test_known_date(self):
        """Test a well-known reference date (2000-01-01.5 = JD 2451545.0)."""
        jd = c_TimeUtils.CalendarToJulianDate(2000, 1, 1.5)
        assert abs(jd - 2451545.0) < 0.001

    def test_invalid_month(self):
        """Invalid month should return INVALID."""
        assert c_TimeUtils.CalendarToJulianDate(2024, 13, 1) == C.INVALID
        assert c_TimeUtils.CalendarToJulianDate(2024, 0, 1) == C.INVALID

    def test_invalid_day(self):
        """Invalid day should return INVALID."""
        assert c_TimeUtils.CalendarToJulianDate(2024, 1, 0) == C.INVALID
        assert c_TimeUtils.CalendarToJulianDate(2024, 1, 32) == C.INVALID


class TestJulianToCalendar:
    """Tests for julian_to_calendar()."""

    def test_roundtrip(self):
        """Calendar -> Julian -> Calendar should round-trip."""
        jd = c_TimeUtils.CalendarToJulianDate(2024, 7, 15)
        y, m, d = c_TimeUtils.JulianDateToCalendar(jd)
        assert y == 2024
        assert m == 7
        assert abs(d - 15.0) < 0.001

    def test_negative_jd(self):
        """Negative Julian date should return INVALID."""
        y, m, d = c_TimeUtils.JulianDateToCalendar(-1.0)
        assert y == C.INVALID


class TestGpsWeekSow:
    """Tests for GPS week and seconds-of-week conversions."""

    def test_gps_epoch_is_week_zero(self):
        """GPS epoch (1980-01-06 00:00:00) should be week 0, SOW 0."""
        week, sow = c_TimeUtils.YmdhmsToGpsWeekSec(1980, 1, 6, 0, 0, 0.0)
        assert week == 0
        assert abs(sow) < 0.01

    def test_known_gps_week(self):
        """Test a known GPS date: 2024-01-01 00:00:00 = GPS week 2295."""
        week, sow = c_TimeUtils.YmdhmsToGpsWeekSec(2024, 1, 1, 0, 0, 0.0)
        # GPS week 2295 started on 2023-12-31 (Sunday)
        # 2024-01-01 is Monday => SOW = 1 * 86400 = 86400
        assert week == 2295
        assert abs(sow - 86400.0) < 1.0

    def test_roundtrip(self):
        """ymdhms -> week/sow -> ymdhms should round-trip."""
        week, sow = c_TimeUtils.YmdhmsToGpsWeekSec(2024, 6, 15, 12, 30, 45.0)
        y, m, d, h, mi, s = c_TimeUtils.GpsWeekSecToYmdhms(week, sow)
        assert y == 2024
        assert m == 6
        assert d == 15
        assert h == 12
        assert mi == 30
        assert abs(s - 45.0) < 0.01


class TestAbsGpsTime:
    """Tests for absolute GPS time conversions."""

    def test_gps_epoch_abs_zero(self):
        """GPS epoch should have absolute time near 0."""
        abs_time = c_TimeUtils.YmdhmsToAbsGpsTime(1980, 1, 6, 0, 0, 0.0)
        assert abs(abs_time) < 0.01

    def test_abs_to_week_sow(self):
        """Absolute time -> week/sow should be consistent."""
        abs_time = c_TimeUtils.GpsWeekSecToAbsGpsTime(2295, 86400.0)
        week, sow = c_TimeUtils.AbsGpsTimeToGpsWeekSec(abs_time)
        assert week == 2295
        assert abs(sow - 86400.0) < 0.01


class TestLeapYear:
    """Tests for is_leap_year()."""

    def test_common_year(self):
        assert c_TimeUtils.IsLeapYear(2023) is False

    def test_leap_year(self):
        assert c_TimeUtils.IsLeapYear(2024) is True

    def test_century_not_leap(self):
        assert c_TimeUtils.IsLeapYear(1900) is False

    def test_400_year_leap(self):
        assert c_TimeUtils.IsLeapYear(2000) is True