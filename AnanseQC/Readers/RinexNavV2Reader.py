# =============================================================================
# RINEX 2.x Navigation File Reader
# =============================================================================
# GPS navigation files are type N. GLONASS files are type G. GEO/SBAS files
# are type H. A RINEX 2 record has a PRN and no system character, so the
# constellation comes from the header.
#
# The epoch year is two digits: 00-79 is 2000-2079, 80-99 is 1980-1999.
# Continuation values start at column 4 (three leading spaces), then four
# 19-character fields.
#
# Time and units match the RINEX 3 reader:
#   Kepler toc_gpst and toe_gpst are absolute GPST seconds.
#   Galileo GST is stored as GPST. BeiDou BDT uses GPST = BDT + 14 seconds.
#   A GPS or QZSS week below 1024 is the 10-bit broadcast week. It is
#   expanded to the continuous week of the epoch before toe_gpst is formed.
#   GLONASS epochs are UTC plus the header leap seconds.
#   State vectors are converted from kilometres to ECEF metres.

import logging

from AnanseQC.Core import Constants
from AnanseQC.Core.Enums import (
    eFileReadingStatus,
    eGnss,
    eRinexObsVersion,
    RINEX_SYSTEM_CHAR,
)
from AnanseQC.Readers.NavTypes import S_KeplerEph, S_RinexNavFile, S_StateEph
from AnanseQC.Readers.RinexDetector import C_RinexVersionDetector
from AnanseQC.Readers.RinexNavV3Reader import (
    C_RinexNavReaderV3,
    KEPLER_LINE_COUNT,
    KM_TO_M,
    STATE_LINE_COUNT,
)

logger = logging.getLogger(__name__)

# Clock fields on the epoch line start after the 2-digit date and F5.1 seconds.
V2_CLOCK_COLUMN = 23

# Orbit lines are 3X,4D19.12. The first value starts at 0-based column 3.
V2_ORBIT_COLUMN = 3

# GPS and QZSS broadcast the week modulo 1024.
GPS_WEEK_ROLLOVER = 1024

NAV_V2_TYPES = ('N', 'G', 'H')


#==============================================================================
# \Class: C_RinexNavReaderV2
# \Brief: Reads a RINEX 2 navigation file into S_RinexNavFile
#==============================================================================
class C_RinexNavReaderV2:
    #==============================================================================
    # \Function: __init__
    # \Brief: Creates the detector and the shared time conversion helper
    # \Params:
    #           None
    # \Returns:
    #           None
    #==============================================================================
    def __init__(self):
        self.c_Detector = C_RinexVersionDetector()
        self.c_V3 = C_RinexNavReaderV3()

    #==============================================================================
    # \Function: Read
    # \Brief: Reads one RINEX 2 navigation file
    # \Params:
    #           filePath        [in]    Path to a type N, G, or H navigation file
    # \Returns:
    #           S_RinexNavFile, eFileReadingStatus
    #           Kepler times are absolute GPST seconds.
    #           State positions are ECEF metres.
    #==============================================================================
    def Read(self, filePath):
        navFile = S_RinexNavFile()
        navFile.file_path = filePath if filePath is not None else ''

        fileId = self.c_Detector.Detect(filePath)
        if fileId.status != eFileReadingStatus.eSuccess:
            logger.error("Navigation detection failed for %s: %s", filePath, fileId.status)
            return navFile, fileId.status

        if fileId.version_enum != eRinexObsVersion.eRinexObsVersion_2:
            logger.error("Not a RINEX 2 navigation file: %s", filePath)
            return navFile, eFileReadingStatus.eFileNotSupported

        if fileId.file_type not in NAV_V2_TYPES:
            logger.error("Not a RINEX 2 navigation file: %s (type '%s')", filePath, fileId.file_type)
            return navFile, eFileReadingStatus.eFileNotSupported

        eSystem = self._System(fileId)
        if eSystem == eGnss.eUnknownSystem:
            logger.error("Unknown RINEX 2 navigation system in %s", filePath)
            return navFile, eFileReadingStatus.eFileNotSupported

        navFile.header.version = fileId.version_float
        navFile.header.version_enum = fileId.version_enum
        navFile.header.file_type = fileId.file_type
        navFile.header.satellite_system = self._SystemChar(fileId, eSystem)

        try:
            with open(filePath, 'r', encoding='utf-8', errors='replace') as fileHandle:
                lines = fileHandle.readlines()
        except (IOError, OSError) as exc:
            logger.error("Failed to read navigation file %s: %s", filePath, exc)
            return navFile, eFileReadingStatus.eFileOpenError

        bodyIndex, eStatus = self.c_V3._ParseHeader(lines, navFile)
        if eStatus != eFileReadingStatus.eSuccess:
            return navFile, eStatus

        eStatus = self._ReadBody(lines, bodyIndex, navFile, eSystem)
        if eStatus != eFileReadingStatus.eSuccess:
            return navFile, eStatus

        logger.info(
            "Read %d Kepler and %d state records from %s",
            len(navFile.kepler_eph),
            len(navFile.state_eph),
            filePath,
        )
        return navFile, eFileReadingStatus.eSuccess

    #==============================================================================
    # \Function: _System
    # \Brief: Chooses the constellation from the RINEX 2 file type and system character
    # \Params:
    #           fileId          [in]    S_RinexFileId
    # \Returns:
    #           eGnss           eGPS when a type-N file has no system character
    #==============================================================================
    def _System(self, fileId):
        if fileId.file_type == 'G':
            return eGnss.eGLN
        if fileId.file_type == 'H':
            return eGnss.eSBAS
        if fileId.system_char in RINEX_SYSTEM_CHAR:
            return RINEX_SYSTEM_CHAR[fileId.system_char]
        if fileId.file_type == 'N':
            return eGnss.eGPS
        return eGnss.eUnknownSystem

    #==============================================================================
    # \Function: _SystemChar
    # \Brief: Returns the header system character, filling a blank GPS type-N file
    # \Params:
    #           fileId          [in]    S_RinexFileId
    #           eSystem         [in]    Constellation chosen for the file
    # \Returns:
    #           str
    #==============================================================================
    def _SystemChar(self, fileId, eSystem):
        if fileId.system_char != '':
            return fileId.system_char
        if eSystem == eGnss.eGPS:
            return 'G'
        if eSystem == eGnss.eGLN:
            return 'R'
        if eSystem == eGnss.eSBAS:
            return 'S'
        return ''

    #==============================================================================
    # \Function: _ReadBody
    # \Brief: Parses every record as Kepler or state, using the file constellation
    # \Params:
    #           lines           [in]    All file lines
    #           start           [in]    Index of the first body line
    #           navFile         [in,out] S_RinexNavFile
    #           eSystem         [in]    Constellation for every record in the file
    # \Returns:
    #           eFileReadingStatus
    #==============================================================================
    def _ReadBody(self, lines, start, navFile, eSystem):
        if eSystem in (eGnss.eGLN, eGnss.eSBAS):
            lineCount = STATE_LINE_COUNT
            bState = True
        else:
            lineCount = KEPLER_LINE_COUNT
            bState = False

        index = start
        nLine = len(lines)
        while index < nLine:
            if lines[index].strip() == '':
                index += 1
                continue

            record, index = self.c_V3._Take(lines, index, lineCount)
            if record is None:
                return eFileReadingStatus.eFileFormatError

            if bState == True:
                state = self._ParseState(record, eSystem)
                if state is None:
                    return eFileReadingStatus.eFileFormatError
                navFile.state_eph.append(state)
            else:
                eph = self._ParseKepler(record, eSystem)
                if eph is None:
                    return eFileReadingStatus.eFileFormatError
                navFile.kepler_eph.append(eph)
        # END while-loop over RINEX 2 navigation records
        return eFileReadingStatus.eSuccess

    #==============================================================================
    # \Function: _ParseKepler
    # \Brief: Fills one S_KeplerEph from an eight-line RINEX 2 record
    # \Params:
    #           record          [in]    Epoch line plus seven orbit lines
    #           eSystem         [in]    Constellation from the header
    # \Returns:
    #           S_KeplerEph or None
    #==============================================================================
    def _ParseKepler(self, record, eSystem):
        epoch = self._ParseEpoch(record[0])
        if epoch is None:
            return None

        prn, year, month, day, hour, minute, second, af0, af1, af2 = epoch
        orbit1 = self.c_V3._Fields(record[1], 4, V2_ORBIT_COLUMN)
        orbit2 = self.c_V3._Fields(record[2], 4, V2_ORBIT_COLUMN)
        orbit3 = self.c_V3._Fields(record[3], 4, V2_ORBIT_COLUMN)
        orbit4 = self.c_V3._Fields(record[4], 4, V2_ORBIT_COLUMN)
        orbit5 = self.c_V3._Fields(record[5], 4, V2_ORBIT_COLUMN)
        orbit6 = self.c_V3._Fields(record[6], 4, V2_ORBIT_COLUMN)
        orbit7 = self.c_V3._Fields(record[7], 4, V2_ORBIT_COLUMN)

        rawWeek = int(round(orbit5[2]))
        week = self._ExpandGpsWeek(eSystem, rawWeek, year, month, day, hour, minute, second)
        toeSow = orbit3[0]
        tocGpsts, toeGpsts = self.c_V3._TocAndToe(
            eSystem,
            year,
            month,
            day,
            hour,
            minute,
            second,
            week,
            toeSow,
        )
        if tocGpsts is None:
            return None

        eph = S_KeplerEph()
        eph.system = eSystem
        eph.prn = prn
        eph.toc_gpst = tocGpsts
        eph.toe_gpst = toeGpsts
        eph.week = week
        eph.af0 = af0
        eph.af1 = af1
        eph.af2 = af2
        eph.iode = orbit1[0]
        eph.crs = orbit1[1]
        eph.delta_n = orbit1[2]
        eph.m0 = orbit1[3]
        eph.cuc = orbit2[0]
        eph.e = orbit2[1]
        eph.cus = orbit2[2]
        eph.sqrt_a = orbit2[3]
        eph.cic = orbit3[1]
        eph.omega0 = orbit3[2]
        eph.cis = orbit3[3]
        eph.i0 = orbit4[0]
        eph.crc = orbit4[1]
        eph.omega = orbit4[2]
        eph.omega_dot = orbit4[3]
        eph.idot = orbit5[0]
        eph.health = int(round(orbit6[1]))
        eph.tgd = orbit6[2]

        if eSystem == eGnss.eGAL:
            eph.codes = orbit5[1]
            eph.iodc = 0.0
            eph.fit_interval = 0.0
        elif eSystem == eGnss.eBDS:
            eph.codes = 0.0
            eph.iodc = orbit7[1]
            eph.fit_interval = 0.0
        else:
            eph.codes = orbit5[1]
            eph.iodc = orbit6[3]
            eph.fit_interval = orbit7[1]
        return eph

    #==============================================================================
    # \Function: _ParseState
    # \Brief: Fills one S_StateEph from a four-line RINEX 2 GLONASS or SBAS record
    # \Note:
    #   File units are kilometres. Stored units are metres.
    #   GLONASS epoch is UTC plus leap seconds. SBAS epoch is GPST.
    # \Params:
    #           record          [in]    Epoch line plus three state lines
    #           eSystem         [in]    eGLN or eSBAS
    # \Returns:
    #           S_StateEph or None
    #==============================================================================
    def _ParseState(self, record, eSystem):
        epoch = self._ParseEpoch(record[0])
        if epoch is None:
            return None

        prn, year, month, day, hour, minute, second, clockBias, freqBias, _frame = epoch
        epochGpsts = self.c_V3.c_Time.YmdhmsToAbsGpsTime(year, month, day, hour, minute, second)
        if epochGpsts == Constants.INVALID:
            return None

        if eSystem == eGnss.eGLN:
            epochGpsts = epochGpsts + float(self.c_V3.leapSeconds)

        lineX = self.c_V3._Fields(record[1], 4, V2_ORBIT_COLUMN)
        lineY = self.c_V3._Fields(record[2], 4, V2_ORBIT_COLUMN)
        lineZ = self.c_V3._Fields(record[3], 4, V2_ORBIT_COLUMN)

        state = S_StateEph()
        state.system = eSystem
        state.prn = prn
        state.epoch_gpst = epochGpsts
        state.x_m = lineX[0] * KM_TO_M
        state.y_m = lineY[0] * KM_TO_M
        state.z_m = lineZ[0] * KM_TO_M
        state.vx_mps = lineX[1] * KM_TO_M
        state.vy_mps = lineY[1] * KM_TO_M
        state.vz_mps = lineZ[1] * KM_TO_M
        state.ax_mps2 = lineX[2] * KM_TO_M
        state.ay_mps2 = lineY[2] * KM_TO_M
        state.az_mps2 = lineZ[2] * KM_TO_M
        state.clock_bias = clockBias
        state.frequency_bias = freqBias
        state.health = int(round(lineX[3]))
        if eSystem == eGnss.eGLN:
            state.frequency_slot = int(round(lineY[3]))
        else:
            state.frequency_slot = 0
        return state

    #==============================================================================
    # \Function: _ParseEpoch
    # \Brief: Reads the PRN, two-digit calendar epoch, and three clock fields
    # \Params:
    #           line            [in]    First line of a RINEX 2 navigation record
    # \Returns:
    #           tuple or None   PRN, full year, calendar, and three floats
    #==============================================================================
    def _ParseEpoch(self, line):
        if len(line) < V2_CLOCK_COLUMN:
            return None
        try:
            prn = int(line[0:2])
            yearTwo = int(line[3:5])
            month = int(line[6:8])
            day = int(line[9:11])
            hour = int(line[12:14])
            minute = int(line[15:17])
            second = float(line[18:23])
        except ValueError:
            return None

        year = self._FullYear(yearTwo)
        af0, af1, af2 = self.c_V3._Fields(line, 3, V2_CLOCK_COLUMN)
        return (prn, year, month, day, hour, minute, second, af0, af1, af2)

    #==============================================================================
    # \Function: _FullYear
    # \Brief: Expands a RINEX 2 two-digit year
    # \Params:
    #           yearTwo         [in]    Year as written in the file
    # \Returns:
    #           int             00-79 becomes 2000-2079. 80-99 becomes 1980-1999.
    #==============================================================================
    def _FullYear(self, yearTwo):
        if yearTwo >= 100:
            return yearTwo
        if yearTwo < 80:
            return 2000 + yearTwo
        return 1900 + yearTwo

    #==============================================================================
    # \Function: _ExpandGpsWeek
    # \Brief: Expands a 10-bit GPS or QZSS week to the week of the epoch
    # \Params:
    #           eSystem         [in]    Constellation
    #           rawWeek         [in]    Week number from the record
    #           year            [in]    Full epoch year
    #           month           [in]    Epoch month
    #           day             [in]    Epoch day
    #           hour            [in]    Epoch hour
    #           minute          [in]    Epoch minute
    #           second          [in]    Epoch second
    # \Returns:
    #           int             Continuous week. Other systems are unchanged.
    #==============================================================================
    def _ExpandGpsWeek(self, eSystem, rawWeek, year, month, day, hour, minute, second):
        if eSystem not in (eGnss.eGPS, eGnss.eQZSS):
            return rawWeek
        if rawWeek >= GPS_WEEK_ROLLOVER:
            return rawWeek

        toc = self.c_V3.c_Time.YmdhmsToAbsGpsTime(year, month, day, hour, minute, second)
        if toc == Constants.INVALID:
            return rawWeek

        tocWeek = int(toc // Constants.SECONDS_IN_WEEK)
        nCycle = int(round((tocWeek - rawWeek) / float(GPS_WEEK_ROLLOVER)))
        return rawWeek + nCycle * GPS_WEEK_ROLLOVER
