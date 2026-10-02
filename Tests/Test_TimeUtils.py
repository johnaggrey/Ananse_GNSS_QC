# =============================================================================
# Tests for GPS Time Conversion Utilities
# =============================================================================
# Time system: GPST. Julian dates are days. Seconds of week and absolute GPS
# time are seconds.

import math
import pytest
from AnanseQC.Core import Constants as C
from AnanseQC.Core.TimeUtils import C_TimeUtils

c_TimeUtils = C_TimeUtils()


class TestCalendarToJulian:
    """Tests for calendar_to_julian()."""

    #==============================================================================
    # \Function: test_gps_epoch
    # \Brief: GPS epoch 1980-01-06 has the known Julian date
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Julian date is in days.
    #==============================================================================
    def test_gps_epoch(self):
        jd = c_TimeUtils.CalendarToJulianDate(1980, 1, 6)
        assert abs(jd - C.JULIAN_DATE_AT_GPS_EPOCH) < 0.001

    #==============================================================================
    # \Function: test_known_date
    # \Brief: 2000-01-01.5 is Julian date 2451545.0
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Julian date is in days.
    #==============================================================================
    def test_known_date(self):
        jd = c_TimeUtils.CalendarToJulianDate(2000, 1, 1.5)
        assert abs(jd - 2451545.0) < 0.001

    #==============================================================================
    # \Function: test_invalid_month
    # \Brief: A month outside 1..12 returns INVALID
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_invalid_month(self):
        assert c_TimeUtils.CalendarToJulianDate(2024, 13, 1) == C.INVALID
        assert c_TimeUtils.CalendarToJulianDate(2024, 0, 1) == C.INVALID

    #==============================================================================
    # \Function: test_invalid_day
    # \Brief: A day outside 1..31 returns INVALID
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_invalid_day(self):
        assert c_TimeUtils.CalendarToJulianDate(2024, 1, 0) == C.INVALID
        assert c_TimeUtils.CalendarToJulianDate(2024, 1, 32) == C.INVALID


class TestJulianToCalendar:
    """Tests for julian_to_calendar()."""

    #==============================================================================
    # \Function: test_roundtrip
    # \Brief: Calendar date 2024-07-15 survives a Julian-date round trip
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Day fraction is in days.
    #==============================================================================
    def test_roundtrip(self):
        jd = c_TimeUtils.CalendarToJulianDate(2024, 7, 15)
        y, m, d = c_TimeUtils.JulianDateToCalendar(jd)
        assert y == 2024
        assert m == 7
        assert abs(d - 15.0) < 0.001

    #==============================================================================
    # \Function: test_negative_jd
    # \Brief: A negative Julian date returns INVALID
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_negative_jd(self):
        y, m, d = c_TimeUtils.JulianDateToCalendar(-1.0)
        assert y == C.INVALID


class TestGpsWeekSow:
    """Tests for GPS week and seconds-of-week conversions."""

    #==============================================================================
    # \Function: test_gps_epoch_is_week_zero
    # \Brief: GPS epoch is week 0 and 0 seconds of week
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Seconds of week are seconds.
    #==============================================================================
    def test_gps_epoch_is_week_zero(self):
        week, sow = c_TimeUtils.YmdhmsToGpsWeekSec(1980, 1, 6, 0, 0, 0.0)
        assert week == 0
        assert abs(sow) < 0.01

    #==============================================================================
    # \Function: test_known_gps_week
    # \Brief: 2024-01-01 00:00:00 GPST is GPS week 2295 and SOW 86400 s
    # \Note:
    #   GPS week 2295 started on 2023-12-31. 2024-01-01 is the next day.
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. SOW is seconds.
    #==============================================================================
    def test_known_gps_week(self):
        week, sow = c_TimeUtils.YmdhmsToGpsWeekSec(2024, 1, 1, 0, 0, 0.0)
        assert week == 2295
        assert abs(sow - 86400.0) < 1.0

    #==============================================================================
    # \Function: test_roundtrip
    # \Brief: 2024-06-15 12:30:45 GPST survives a week and SOW round trip
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Seconds are GPST seconds.
    #==============================================================================
    def test_roundtrip(self):
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

    #==============================================================================
    # \Function: test_gps_epoch_abs_zero
    # \Brief: The GPS epoch has absolute GPS time of 0 seconds
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Absolute time is seconds.
    #==============================================================================
    def test_gps_epoch_abs_zero(self):
        abs_time = c_TimeUtils.YmdhmsToAbsGpsTime(1980, 1, 6, 0, 0, 0.0)
        assert abs(abs_time) < 0.01

    #==============================================================================
    # \Function: test_abs_to_week_sow
    # \Brief: Week 2295 and SOW 86400 s convert back from absolute GPS time
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. SOW is seconds.
    #==============================================================================
    def test_abs_to_week_sow(self):
        abs_time = c_TimeUtils.GpsWeekSecToAbsGpsTime(2295, 86400.0)
        week, sow = c_TimeUtils.AbsGpsTimeToGpsWeekSec(abs_time)
        assert week == 2295
        assert abs(sow - 86400.0) < 0.01


class TestLeapYear:
    """Tests for is_leap_year()."""

    #==============================================================================
    # \Function: test_common_year
    # \Brief: A common year is not a leap year
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_common_year(self):
        assert c_TimeUtils.IsLeapYear(2023) is False

    #==============================================================================
    # \Function: test_leap_year
    # \Brief: A year divisible by 4 is a leap year
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_leap_year(self):
        assert c_TimeUtils.IsLeapYear(2024) is True

    #==============================================================================
    # \Function: test_century_not_leap
    # \Brief: A century year is not a leap year unless divisible by 400
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_century_not_leap(self):
        assert c_TimeUtils.IsLeapYear(1900) is False

    #==============================================================================
    # \Function: test_400_year_leap
    # \Brief: A year divisible by 400 is a leap year
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_400_year_leap(self):
        assert c_TimeUtils.IsLeapYear(2000) is True
