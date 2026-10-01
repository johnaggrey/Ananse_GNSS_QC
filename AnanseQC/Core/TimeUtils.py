#==============================================================================
# System imported libraries
#==============================================================================
import math

import AnanseQC.Core.Constants as Constants

#==============================================================================
# \Class: C_TimeUtils
# \Brief: Converts between calendar dates, Julian dates, and GPS time
# \Note:
#   Time system is GPST, continuous since 1980-01-06 00:00:00.
#   Time values are seconds unless a function states otherwise.
#   Julian-date algorithm follows Montenbruck (1989).
#==============================================================================
class C_TimeUtils:
    #==============================================================================
    # \Function: __init__
    # \Brief: Initialises the time record to the empty state
    # \Params:
    #           None
    # \Returns:
    #           None
    #==============================================================================
    def __init__(self):
        self.Reset()

    #==============================================================================
    # \Function: Reset
    # \Brief: Resets the C_TimeUtils record to its empty state
    # \Params:
    #           None
    # \Returns:
    #           None
    #==============================================================================
    def Reset(self):
        self.year = Constants.INVALID
        self.month = Constants.INVALID
        self.day = Constants.INVALID
        self.hour = Constants.INVALID
        self.minute = Constants.INVALID
        self.seconds = Constants.INVALID
        self.gpsWeek = Constants.INVALID
        self.gpsSecondsOfWeek = Constants.INVALID
        self.absGpsTime = Constants.INVALID
        self.julianDate = Constants.INVALID
        self.dayOfWeek = Constants.INVALID
        self.dayOfYear = Constants.INVALID
        self.bIsLeapYear = False

    #==============================================================================
    # \Function: CalendarToJulianDate
    # \Brief: Converts a calendar date to a Julian date
    # \Params:
    #           year            [in]    Calendar year, 4 digits
    #           month           [in]    Calendar month [1..12]
    #           day             [in]    Calendar day, fractional part allowed
    # \Returns:
    #           float           Julian date, or Constants.INVALID on bad input
    #==============================================================================
    def CalendarToJulianDate(self, year, month, day):
        monthsWithLessThan31Days = [4, 6, 9, 11]
        self.julianDate = Constants.INVALID

        if (month < 1) or (month > 12):
            return self.julianDate

        if (day < 1.0) or (day > 31.0):
            return self.julianDate

        if ((month == 2) and (day > 29)) or \
           ((month in monthsWithLessThan31Days) and (day > 30)):
            return self.julianDate

        # January and February are treated as months 13 and 14 of the previous year.
        if month > 2:
            tempYear = year
            tempMonth = month
        else:
            tempYear = year - 1
            tempMonth = month + 12

        lastJulian = 4 + 31 * (10 + 12 * 1582)
        firstGregorian = 15 + 31 * (10 + 12 * 1582)
        dateKey = day + 31 * (month + 12 * year)

        if dateKey <= lastJulian:
            bCorr = -2
        elif dateKey >= firstGregorian:
            bCorr = math.floor(tempYear / 400) - math.floor(tempYear / 100)
        else:
            return self.julianDate

        if tempYear > 0:
            self.julianDate = (math.floor(365.25 * tempYear)
                               + math.floor(30.6001 * (tempMonth + 1))
                               + bCorr + 1720996.5 + day)
        else:
            self.julianDate = (math.floor(365.25 * tempYear - 0.75)
                               + math.floor(30.6001 * (tempMonth + 1))
                               + bCorr + 1720996.5 + day)

        return self.julianDate

    #==============================================================================
    # \Function: JulianDateToCalendar
    # \Brief: Converts a Julian date to a calendar date
    # \Params:
    #           julianDate      [in]    Julian date, including the fractional day
    # \Returns:
    #           year, month, day
    #           day keeps the fractional part. Invalid input returns INVALID.
    #==============================================================================
    def JulianDateToCalendar(self, julianDate):
        self.year = Constants.INVALID
        self.month = Constants.INVALID
        self.day = Constants.INVALID

        if julianDate < 0:
            return self.year, self.month, self.day

        a = math.floor(julianDate + 0.5)

        if a < 2299161:
            c = a + 1524
        else:
            b = math.floor((a - 1867216.25) / 36524.25)
            c = a + b - math.floor(b / 4) + 1525

        d = math.floor((c - 122.1) / 365.25)
        e = math.floor(365.25 * d)
        f = math.floor((c - e) / 30.6001)

        self.day = c - e - math.floor(30.6001 * f) + (julianDate + 0.5) - a
        self.month = int(f - 1 - 12 * math.floor(f / 14))
        self.year = int(d - 4715 - math.floor((7 + self.month) / 10))

        return self.year, self.month, self.day

    #==============================================================================
    # \Function: JulianDateToDow
    # \Brief: Converts a Julian date to the day of week
    # \Params:
    #           julianDate      [in]    Julian date
    # \Returns:
    #           int             Day of week, 0 = Sunday. INVALID on bad input.
    #==============================================================================
    def JulianDateToDow(self, julianDate):
        if julianDate < 0:
            self.dayOfWeek = Constants.INVALID
            return self.dayOfWeek

        self.dayOfWeek = math.floor(julianDate + 1.5) % 7
        return self.dayOfWeek

    #==============================================================================
    # \Function: JulianDateToDoy
    # \Brief: Converts a Julian date to year and day of year
    # \Params:
    #           julianDate      [in]    Julian date
    # \Returns:
    #           year, dayOfYear
    #==============================================================================
    def JulianDateToDoy(self, julianDate):
        if julianDate < 0:
            return Constants.INVALID, Constants.INVALID

        self.year, _, _ = self.JulianDateToCalendar(julianDate)
        jdJan0 = self.CalendarToJulianDate(self.year, 1, 0)
        self.dayOfYear = julianDate - jdJan0
        return self.year, self.dayOfYear

    #==============================================================================
    # \Function: YmdhmsToGpsWeekSec
    # \Brief: Converts a calendar date and time to GPS week and seconds of week
    # \Params:
    #           year            [in]    Calendar year
    #           month           [in]    Calendar month [1..12]
    #           day             [in]    Calendar day [1..31]
    #           hour            [in]    Hour [0..23]
    #           minute          [in]    Minute [0..59]
    #           seconds         [in]    Seconds [0..61)
    # \Returns:
    #           gpsWeek, gpsSecondsOfWeek
    #           Time system: GPST. Units: week number and seconds.
    #==============================================================================
    def YmdhmsToGpsWeekSec(self, year, month, day, hour, minute, seconds):
        self.gpsWeek = Constants.INVALID
        self.gpsSecondsOfWeek = Constants.INVALID

        bValid = True
        if (year < 1980) or (month < 1) or (month > 12):
            bValid = False
        if (day < 1) or (day > 31):
            bValid = False
        if (hour < 0) or (hour > 23):
            bValid = False
        if (minute < 0) or (minute > 59):
            bValid = False
        if (seconds < 0.0) or (seconds >= 61.0):
            bValid = False

        if bValid == False:
            return self.gpsWeek, self.gpsSecondsOfWeek

        julianDate = self.CalendarToJulianDate(year, month, day)
        if julianDate == Constants.INVALID:
            return self.gpsWeek, self.gpsSecondsOfWeek

        fracDay = (hour * Constants.SECONDS_IN_HOUR
                   + minute * Constants.SECONDS_IN_MINUTE
                   + seconds) / Constants.SECONDS_IN_DAY
        deltaJulianDate = julianDate - Constants.JULIAN_DATE_AT_GPS_EPOCH

        if deltaJulianDate < 0:
            return self.gpsWeek, self.gpsSecondsOfWeek

        self.gpsWeek = int(math.floor(deltaJulianDate / 7.0))
        self.gpsSecondsOfWeek = ((deltaJulianDate % 7) + fracDay) * Constants.SECONDS_IN_DAY
        return self.gpsWeek, self.gpsSecondsOfWeek

    #==============================================================================
    # \Function: GpsWeekSecToAbsGpsTime
    # \Brief: Converts GPS week and seconds of week to absolute GPS time
    # \Params:
    #           gpsWeek         [in]    GPS week number
    #           gpsSecondsOfWeek [in]   Seconds of week [0..604800]
    # \Returns:
    #           float           Seconds since the GPS epoch, or INVALID
    #==============================================================================
    def GpsWeekSecToAbsGpsTime(self, gpsWeek, gpsSecondsOfWeek):
        self.absGpsTime = Constants.INVALID

        if gpsWeek < 0:
            return self.absGpsTime
        if (gpsSecondsOfWeek < 0.0) or (gpsSecondsOfWeek > Constants.SECONDS_IN_WEEK):
            return self.absGpsTime

        self.absGpsTime = gpsWeek * Constants.SECONDS_IN_WEEK + gpsSecondsOfWeek
        return self.absGpsTime

    #==============================================================================
    # \Function: AbsGpsTimeToGpsWeekSec
    # \Brief: Converts absolute GPS time to GPS week and seconds of week
    # \Params:
    #           absGpsTime      [in]    Seconds since the GPS epoch
    # \Returns:
    #           gpsWeek, gpsSecondsOfWeek
    #==============================================================================
    def AbsGpsTimeToGpsWeekSec(self, absGpsTime):
        if absGpsTime < 0.0:
            return Constants.INVALID, Constants.INVALID

        self.gpsWeek = int(math.floor(absGpsTime / Constants.SECONDS_IN_WEEK))
        self.gpsSecondsOfWeek = absGpsTime - self.gpsWeek * Constants.SECONDS_IN_WEEK
        self.absGpsTime = absGpsTime
        return self.gpsWeek, self.gpsSecondsOfWeek

    #==============================================================================
    # \Function: YmdhmsToAbsGpsTime
    # \Brief: Converts a calendar date and time to absolute GPS time
    # \Params:
    #           year            [in]    Calendar year
    #           month           [in]    Calendar month
    #           day             [in]    Calendar day
    #           hour            [in]    Hour
    #           minute          [in]    Minute
    #           seconds         [in]    Seconds
    # \Returns:
    #           float           Seconds since the GPS epoch, or INVALID
    #==============================================================================
    def YmdhmsToAbsGpsTime(self, year, month, day, hour, minute, seconds):
        gpsWeek, gpsSecondsOfWeek = self.YmdhmsToGpsWeekSec(
            year, month, day, hour, minute, seconds)
        if gpsWeek == Constants.INVALID:
            return Constants.INVALID

        return self.GpsWeekSecToAbsGpsTime(gpsWeek, gpsSecondsOfWeek)

    #==============================================================================
    # \Function: GpsWeekSecToYmdhms
    # \Brief: Converts GPS week and seconds of week to a calendar date and time
    # \Params:
    #           gpsWeek         [in]    GPS week number
    #           gpsSecondsOfWeek [in]   Seconds of week
    # \Returns:
    #           year, month, day, hour, minute, seconds
    #==============================================================================
    def GpsWeekSecToYmdhms(self, gpsWeek, gpsSecondsOfWeek):
        if (gpsWeek < 0) or (gpsSecondsOfWeek < 0) or \
           (gpsSecondsOfWeek > Constants.SECONDS_IN_WEEK):
            return (Constants.INVALID, Constants.INVALID, Constants.INVALID,
                    Constants.INVALID, Constants.INVALID, Constants.INVALID)

        julianDate = (Constants.JULIAN_DATE_AT_GPS_EPOCH
                      + gpsWeek * 7.0
                      + gpsSecondsOfWeek / Constants.SECONDS_IN_DAY)
        year, month, dayFrac = self.JulianDateToCalendar(julianDate)

        day = int(math.floor(dayFrac))
        frac = dayFrac - day
        totalSeconds = frac * Constants.SECONDS_IN_DAY
        hour = int(math.floor(totalSeconds / Constants.SECONDS_IN_HOUR))
        minute = int(math.floor((totalSeconds - hour * Constants.SECONDS_IN_HOUR)
                                / Constants.SECONDS_IN_MINUTE))
        seconds = (totalSeconds
                   - hour * Constants.SECONDS_IN_HOUR
                   - minute * Constants.SECONDS_IN_MINUTE)

        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.seconds = seconds
        return year, month, day, hour, minute, seconds

    #==============================================================================
    # \Function: SowToHms
    # \Brief: Extracts hour, minute, and second from GPS seconds of week
    # \Params:
    #           gpsSecondsOfWeek [in]   Seconds of week [0..604800]
    # \Returns:
    #           hour, minute, seconds
    #==============================================================================
    def SowToHms(self, gpsSecondsOfWeek):
        if (gpsSecondsOfWeek < 0) or (gpsSecondsOfWeek > Constants.SECONDS_IN_WEEK):
            return Constants.INVALID, Constants.INVALID, Constants.INVALID

        secondsOfDay = gpsSecondsOfWeek % Constants.SECONDS_IN_DAY
        self.hour = int(math.floor(secondsOfDay / Constants.SECONDS_IN_HOUR))
        self.minute = int(math.floor(
            (secondsOfDay - self.hour * Constants.SECONDS_IN_HOUR)
            / Constants.SECONDS_IN_MINUTE))
        self.seconds = (secondsOfDay
                        - self.hour * Constants.SECONDS_IN_HOUR
                        - self.minute * Constants.SECONDS_IN_MINUTE)
        return self.hour, self.minute, self.seconds

    #==============================================================================
    # \Function: DoyToMonthDay
    # \Brief: Converts a day of year to month and day
    # \Params:
    #           year            [in]    Calendar year
    #           dayOfYear       [in]    Day of year [1..366]
    # \Returns:
    #           month, day
    #==============================================================================
    def DoyToMonthDay(self, year, dayOfYear):
        if (dayOfYear < 1) or (dayOfYear > 366):
            return Constants.INVALID, Constants.INVALID

        julianDate = self.CalendarToJulianDate(year, 1, 0) + dayOfYear
        _, month, dayFrac = self.JulianDateToCalendar(julianDate)
        return month, int(math.floor(dayFrac))

    #==============================================================================
    # \Function: IsLeapYear
    # \Brief: Reports whether a calendar year is a leap year
    # \Params:
    #           year            [in]    Calendar year
    # \Returns:
    #           bool            True when the year is a leap year
    #==============================================================================
    def IsLeapYear(self, year):
        self.bIsLeapYear = ((year % 4 == 0) and (year % 100 != 0)) or (year % 400 == 0)
        return self.bIsLeapYear
