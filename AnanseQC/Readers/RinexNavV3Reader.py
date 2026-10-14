# =============================================================================
# RINEX 3.x / 4.x Navigation File Reader
# =============================================================================
# Reads mixed and single-system navigation files.
#
# RINEX 3 ephemeris records start with the system character and PRN.
# RINEX 4 puts a "> EPH" line in front of that same record. LNAV, INAV,
# FNAV, D1, D2, FDMA, and SBAS use the RINEX 3 field layout. Other RINEX 4
# messages (CNAV, STO, EOP, ION) are skipped.
#
# Time:
#   GPS, QZSS, and NavIC epochs are GPST.
#   Galileo GST is stored as GPST.
#   BeiDou epochs are BDT. Stored toc_gpst and toe_gpst use
#   GPST = BDT + 14 seconds. BDT week 0 is GPS week 1356.
#   GLONASS epochs are UTC. Stored epoch_gpst is UTC plus the header
#   leap seconds.
#   SBAS epochs are GPST.
#
# State vectors in the file are kilometres. Stored state is ECEF metres,
# metres/second, and metres/second^2. GLONASS coordinates are PZ-90.
# Unhealthy records are stored. Geometry code decides later whether to use them.

import logging

from AnanseQC.Core import Constants
from AnanseQC.Core.Enums import (
    eFileReadingStatus,
    eGnss,
    eRinexObsVersion,
    RINEX_SYSTEM_CHAR,
)
from AnanseQC.Core.TimeUtils import C_TimeUtils
from AnanseQC.Readers.NavTypes import (
    S_KeplerEph,
    S_RinexNavFile,
    S_StateEph,
)
from AnanseQC.Readers.RinexDetector import C_RinexVersionDetector

logger = logging.getLogger(__name__)

# Width of one navigation value. Four values follow the four leading spaces.
NAV_FIELD_WIDTH = 19

# Kepler broadcast body: epoch line plus seven orbit lines.
KEPLER_LINE_COUNT = 8

# GLONASS and SBAS body: epoch line plus three state lines.
STATE_LINE_COUNT = 4

# RINEX kilometres to stored metres.
KM_TO_M = 1000.0

# BDT week 0 begins at GPS week 1356. GPST = BDT + Constants.BDT_TO_GPST_SEC.
BDT_GPS_WEEK_OFFSET = 1356

# RINEX 4 ephemeris subtypes that still use the RINEX 3 orbit lines.
CLASSIC_EPH_MESSAGES = ('LNAV', 'INAV', 'FNAV', 'D1', 'D2', 'FDMA', 'SBAS')

KEPLER_CHARS = ('G', 'E', 'C', 'J', 'I')
STATE_CHARS = ('R', 'S')


#==============================================================================
# \Class: C_RinexNavReaderV3
# \Brief: Reads a RINEX 3.x or 4.x navigation file into S_RinexNavFile
#==============================================================================
class C_RinexNavReaderV3:
    #==============================================================================
    # \Function: __init__
    # \Brief: Creates the time converter used for ephemeris epochs
    # \Params:
    #           None
    # \Returns:
    #           None
    #==============================================================================
    def __init__(self):
        self.c_Time = C_TimeUtils()
        self.leapSeconds = 0

    #==============================================================================
    # \Function: Read
    # \Brief: Reads one RINEX 3 or 4 navigation file
    # \Params:
    #           filePath        [in]    Path to the navigation file
    # \Returns:
    #           S_RinexNavFile, eFileReadingStatus
    #           Kepler times are absolute GPST seconds.
    #           State positions are ECEF metres.
    #==============================================================================
    def Read(self, filePath):
        navFile = S_RinexNavFile()
        navFile.file_path = filePath if filePath is not None else ''
        self.leapSeconds = 0

        fileId = C_RinexVersionDetector().Detect(filePath)
        if fileId.status != eFileReadingStatus.eSuccess:
            logger.error("Navigation detection failed for %s: %s", filePath, fileId.status)
            return navFile, fileId.status

        if fileId.file_type != 'N':
            logger.error("Not a navigation file: %s (type '%s')", filePath, fileId.file_type)
            return navFile, eFileReadingStatus.eFileNotSupported

        if fileId.version_enum not in (
            eRinexObsVersion.eRinexObsVersion_3,
            eRinexObsVersion.eRinexObsVersion_4,
        ):
            logger.error("Unsupported navigation version: %.2f", fileId.version_float)
            return navFile, eFileReadingStatus.eFileNotSupported

        navFile.header.version = fileId.version_float
        navFile.header.version_enum = fileId.version_enum
        navFile.header.file_type = fileId.file_type
        navFile.header.satellite_system = fileId.system_char

        try:
            with open(filePath, 'r', encoding='utf-8', errors='replace') as fileHandle:
                lines = fileHandle.readlines()
        except (IOError, OSError) as exc:
            logger.error("Failed to read navigation file %s: %s", filePath, exc)
            return navFile, eFileReadingStatus.eFileOpenError

        bodyIndex, eStatus = self._ParseHeader(lines, navFile)
        if eStatus != eFileReadingStatus.eSuccess:
            return navFile, eStatus

        eStatus = self._ReadBody(lines, bodyIndex, navFile)
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
    # \Function: _ParseHeader
    # \Brief: Reads leap seconds and comments, and finds the body start
    # \Note:
    #   Ionosphere and time-system header lines are skipped.
    # \Params:
    #           lines           [in]    All file lines
    #           navFile         [in,out] S_RinexNavFile
    # \Returns:
    #           int, eFileReadingStatus
    #           The int is the index of the first body line.
    #==============================================================================
    def _ParseHeader(self, lines, navFile):
        for index, rawLine in enumerate(lines):
            line = rawLine.rstrip('\r\n')
            if len(line) >= 60:
                label = line[60:].strip()
            else:
                label = ''

            if label == 'END OF HEADER':
                return index + 1, eFileReadingStatus.eSuccess

            if label.startswith('LEAP SECONDS') == True:
                leapText = line[0:6].strip()
                if leapText != '':
                    navFile.header.leap_seconds = int(float(leapText))
                    self.leapSeconds = navFile.header.leap_seconds
            elif label == 'COMMENT':
                navFile.header.comments.append(line[0:60].strip())
        # END for-loop over header lines

        logger.error("Navigation header has no END OF HEADER in %s", navFile.file_path)
        return 0, eFileReadingStatus.eInvalidHeader

    #==============================================================================
    # \Function: _ReadBody
    # \Brief: Parses Kepler and state records after the header
    # \Params:
    #           lines           [in]    All file lines
    #           start           [in]    Index of the first body line
    #           navFile         [in,out] S_RinexNavFile
    # \Returns:
    #           eFileReadingStatus
    #==============================================================================
    def _ReadBody(self, lines, start, navFile):
        index = start
        nLine = len(lines)
        while index < nLine:
            line = lines[index].rstrip('\r\n')
            if line.strip() == '':
                index += 1
                continue

            if line.startswith('>') == True:
                index = self._NextAfterMarker(lines, index)
                continue

            if len(line) < 3:
                index += 1
                continue

            systemChar = line[0].upper()
            if systemChar in KEPLER_CHARS:
                record, index = self._Take(lines, index, KEPLER_LINE_COUNT)
                if record is None:
                    return eFileReadingStatus.eFileFormatError
                eph = self._ParseKepler(record)
                if eph is None:
                    return eFileReadingStatus.eFileFormatError
                navFile.kepler_eph.append(eph)
            elif systemChar in STATE_CHARS:
                record, index = self._Take(lines, index, STATE_LINE_COUNT)
                if record is None:
                    return eFileReadingStatus.eFileFormatError
                state = self._ParseState(record, systemChar)
                if state is None:
                    return eFileReadingStatus.eFileFormatError
                navFile.state_eph.append(state)
            else:
                index += 1
        # END while-loop over navigation records
        return eFileReadingStatus.eSuccess

    #==============================================================================
    # \Function: _NextAfterMarker
    # \Brief: Steps past a RINEX 4 record marker to the next usable line
    # \Note:
    #   A classic EPH marker is followed by a RINEX 3 ephemeris record.
    #   Every other marker is skipped through to the next '>' line.
    # \Params:
    #           lines           [in]    All file lines
    #           index           [in]    Index of the '>' line
    # \Returns:
    #           int             Index of the next line to parse
    #==============================================================================
    def _NextAfterMarker(self, lines, index):
        line = lines[index].rstrip('\r\n')
        parts = line[1:].split()
        bClassicEph = False
        if len(parts) >= 1 and parts[0] == 'EPH':
            message = ''
            if len(parts) >= 3:
                message = parts[2]
            if message in CLASSIC_EPH_MESSAGES:
                bClassicEph = True

        if bClassicEph == True:
            return index + 1

        index += 1
        nLine = len(lines)
        while index < nLine:
            if lines[index].startswith('>') == True:
                return index
            index += 1
        # END while-loop skipping a non-ephemeris RINEX 4 block
        return index

    #==============================================================================
    # \Function: _Take
    # \Brief: Copies a fixed number of record lines
    # \Params:
    #           lines           [in]    All file lines
    #           index           [in]    First line of the record
    #           count           [in]    Number of lines in the record
    # \Returns:
    #           list or None, int
    #           None when the record runs past the end of the file.
    #==============================================================================
    def _Take(self, lines, index, count):
        end = index + count
        if end > len(lines):
            return None, index
        record = []
        for iLine in range(index, end):
            record.append(lines[iLine].rstrip('\r\n'))
        # END for-loop copying one navigation record
        return record, end

    #==============================================================================
    # \Function: _ParseKepler
    # \Brief: Fills one S_KeplerEph from an eight-line broadcast record
    # \Params:
    #           record          [in]    Epoch line plus seven orbit lines
    # \Returns:
    #           S_KeplerEph or None
    #==============================================================================
    def _ParseKepler(self, record):
        epoch = self._ParseEpoch(record[0])
        if epoch is None:
            return None

        systemChar, prn, year, month, day, hour, minute, second, af0, af1, af2 = epoch
        eSystem = RINEX_SYSTEM_CHAR.get(systemChar, eGnss.eUnknownSystem)
        orbit1 = self._Fields(record[1], 4, 4)
        orbit2 = self._Fields(record[2], 4, 4)
        orbit3 = self._Fields(record[3], 4, 4)
        orbit4 = self._Fields(record[4], 4, 4)
        orbit5 = self._Fields(record[5], 4, 4)
        orbit6 = self._Fields(record[6], 4, 4)
        orbit7 = self._Fields(record[7], 4, 4)

        week = int(round(orbit5[2]))
        toeSow = orbit3[0]
        tocGpsts, toeGpsts = self._TocAndToe(
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
    # \Brief: Fills one S_StateEph from a four-line GLONASS or SBAS record
    # \Note:
    #   File units are kilometres. Stored units are metres.
    #   GLONASS epoch is UTC plus leap seconds. SBAS epoch is GPST.
    # \Params:
    #           record          [in]    Epoch line plus three state lines
    #           systemChar      [in]    'R' or 'S'
    # \Returns:
    #           S_StateEph or None
    #==============================================================================
    def _ParseState(self, record, systemChar):
        epoch = self._ParseEpoch(record[0])
        if epoch is None:
            return None

        systemChar, prn, year, month, day, hour, minute, second, clockBias, freqBias, _frame = epoch
        eSystem = RINEX_SYSTEM_CHAR.get(systemChar, eGnss.eUnknownSystem)
        epochGpsts = self.c_Time.YmdhmsToAbsGpsTime(year, month, day, hour, minute, second)
        if epochGpsts == Constants.INVALID:
            return None

        if systemChar == 'R':
            epochGpsts = epochGpsts + float(self.leapSeconds)

        lineX = self._Fields(record[1], 4, 4)
        lineY = self._Fields(record[2], 4, 4)
        lineZ = self._Fields(record[3], 4, 4)

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
        if systemChar == 'R':
            state.frequency_slot = int(round(lineY[3]))
        else:
            state.frequency_slot = 0
        return state

    #==============================================================================
    # \Function: _ParseEpoch
    # \Brief: Reads the satellite id, calendar epoch, and three clock fields
    # \Params:
    #           line            [in]    First line of a navigation record
    # \Returns:
    #           tuple or None   system char, prn, calendar, and three floats
    #==============================================================================
    def _ParseEpoch(self, line):
        if len(line) < 23:
            return None
        systemChar = line[0].upper()
        prnText = line[1:3]
        if prnText.isdigit() == False:
            return None
        try:
            prn = int(prnText)
            year = int(line[4:8])
            month = int(line[9:11])
            day = int(line[12:14])
            hour = int(line[15:17])
            minute = int(line[18:20])
            second = float(line[21:23])
        except ValueError:
            return None

        af0, af1, af2 = self._Fields(line, 3, 23)
        return (systemChar, prn, year, month, day, hour, minute, second, af0, af1, af2)

    #==============================================================================
    # \Function: _Fields
    # \Brief: Parses fixed 19-character navigation values
    # \Params:
    #           line            [in]    One record line
    #           nFields         [in]    Number of values
    #           start           [in]    0-based index of the first value
    # \Returns:
    #           list            Floats. A blank field is 0.
    #==============================================================================
    def _Fields(self, line, nFields, start):
        needed = start + nFields * NAV_FIELD_WIDTH
        padded = line
        if len(padded) < needed:
            padded = padded + (' ' * (needed - len(padded)))

        values = []
        for iField in range(nFields):
            begin = start + iField * NAV_FIELD_WIDTH
            chunk = padded[begin:begin + NAV_FIELD_WIDTH]
            values.append(self._ParseFloat(chunk))
        # END for-loop over navigation fields
        return values

    #==============================================================================
    # \Function: _ParseFloat
    # \Brief: Parses one RINEX value, accepting a Fortran D exponent
    # \Params:
    #           text            [in]    Field text
    # \Returns:
    #           float           0 when the field is blank or not numeric
    #==============================================================================
    def _ParseFloat(self, text):
        cleaned = text.strip().replace('D', 'E').replace('d', 'e')
        if cleaned == '':
            return 0.0
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    #==============================================================================
    # \Function: _TocAndToe
    # \Brief: Converts a broadcast clock epoch and toe into absolute GPST
    # \Note:
    #   BeiDou week and seconds are BDT. The stored times are GPST.
    #   toe is moved by one week when that puts it closer to toc.
    # \Params:
    #           eSystem         [in]    Constellation
    #           year            [in]    Epoch year
    #           month           [in]    Epoch month
    #           day             [in]    Epoch day
    #           hour            [in]    Epoch hour
    #           minute          [in]    Epoch minute
    #           second          [in]    Epoch second
    #           week            [in]    Broadcast week number
    #           toeSow          [in]    Time of ephemeris, seconds of week
    # \Returns:
    #           toc_gpst, toe_gpst
    #           None, None when the calendar epoch is invalid.
    #==============================================================================
    def _TocAndToe(self, eSystem, year, month, day, hour, minute, second, week, toeSow):
        tocCalendar = self.c_Time.YmdhmsToAbsGpsTime(year, month, day, hour, minute, second)
        if tocCalendar == Constants.INVALID:
            return None, None

        if eSystem == eGnss.eBDS:
            tocGpsts = tocCalendar + Constants.BDT_TO_GPST_SEC
            toeGpsts = ((week + BDT_GPS_WEEK_OFFSET) * Constants.SECONDS_IN_WEEK
                        + toeSow
                        + Constants.BDT_TO_GPST_SEC)
        else:
            tocGpsts = tocCalendar
            toeGpsts = week * Constants.SECONDS_IN_WEEK + toeSow

        halfWeek = Constants.SECONDS_IN_WEEK * 0.5
        delta = tocGpsts - toeGpsts
        if delta > halfWeek:
            toeGpsts = toeGpsts + Constants.SECONDS_IN_WEEK
        elif delta < -halfWeek:
            toeGpsts = toeGpsts - Constants.SECONDS_IN_WEEK
        return tocGpsts, toeGpsts
       