# =============================================================================
# RINEX 3.x / 4.x Observation File Reader
# =============================================================================
# Parses RINEX 3.x (3.00 through 3.05) and RINEX 4.x observation files.
#
# RINEX 3.x/4.x key format characteristics:
#   - Epoch line starts with '>' character:
#     "> YYYY MM DD HH MM SS.SSSSSSS  FLAG NUMSAT"
#   - 4-digit year
#   - Observation types defined per satellite system (SYS / # / OBS TYPES)
#   - Each observation line starts with system char + 2-digit PRN
#   - Observation values: 16 chars each (14.3 value + 1 LLI + 1 SSI)
#   - 3-character observation descriptors (e.g., C1C, L1C, S1C)
#
# Reference: RINEX 3.05 format specification (IGS).

import os
import logging

from AnanseQC.Core.Enums import (
    eGnss,
    eFileReadingStatus,
    eRinexObsVersion,
    RINEX_SYSTEM_CHAR,
)
from AnanseQC.Core.TimeUtils import C_TimeUtils
from AnanseQC.Readers.ObsTypes import (
    S_RinexObsHeader,
    S_RinexObsFile,
    S_EpochRecord,
    S_SatObs,
)

logger = logging.getLogger(__name__)

# Width of a single observation field in RINEX 3.x (value + LLI + SSI)
_OBS_FIELD_WIDTH = 16


#==============================================================================
# \Class: C_RinexObsReaderV3
# \Brief: Reads a RINEX 3.x or 4.x observation file into S_RinexObsFile
#==============================================================================
class C_RinexObsReaderV3:
    #==============================================================================
    # \Function: _Decode
    # \Brief: Decode bytes to str, stripping whitespace
    #==============================================================================
    def _Decode(self, raw, fallback=''):
        """Decode bytes to str, stripping whitespace."""
        if isinstance(raw, bytes):
            return raw.decode('utf-8', errors='replace').strip()
        if isinstance(raw, str):
            return raw.strip()
        return fallback


    #==============================================================================
    # \Function: _SafeFloat
    # \Brief: Parse a float from text, returning None on failure or blank input
    #==============================================================================
    def _SafeFloat(self, text):
        """Parse a float from text, returning None on failure or blank input."""
        s = text.strip() if isinstance(text, str) else self._Decode(text)
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None


    #==============================================================================
    # \Function: _SafeInt
    # \Brief: Parse an int from text, returning None on failure or blank input
    #==============================================================================
    def _SafeInt(self, text):
        """Parse an int from text, returning None on failure or blank input."""
        s = text.strip() if isinstance(text, str) else self._Decode(text)
        if not s:
            return None
        try:
            return int(s)
        except ValueError:
            return None


    # ============================================================================
    # Header Parsing
    # ============================================================================

    #==============================================================================
    # \Function: _ParseHeader
    # \Brief: Parse the RINEX 3.x/4.x header section
    #==============================================================================
    def _ParseHeader(self, file_handle):
        """Parse the RINEX 3.x/4.x header section.

        Reads lines until END OF HEADER is found and populates a
        S_RinexObsHeader dataclass. Unlike RINEX 2.x, observation types
        are defined per satellite system.

        Args:
            file_handle: Open file handle positioned at the beginning of the file.

        Returns:
            tuple: (S_RinexObsHeader, dict_of_obs_types_per_system, eFileReadingStatus)
                dict_of_obs_types_per_system maps system_char -> list of obs descriptors
        """
        header = S_RinexObsHeader()
        sys_obs_types = {}  # Maps system character -> list of 3-char obs type strings

        line = file_handle.readline()
        while line:
            label = self._Decode(line[60:80]) if len(line) >= 60 else ''

            # ---- RINEX VERSION / TYPE ----
            if 'RINEX VERSION / TYPE' in label:
                ver_str = self._Decode(line[0:9])
                try:
                    header.version = float(ver_str)
                except ValueError:
                    return header, sys_obs_types, eFileReadingStatus.eFileFormatError

                major = int(header.version)
                if major == 3:
                    header.version_enum = eRinexObsVersion.eRinexObsVersion_3
                elif major == 4:
                    header.version_enum = eRinexObsVersion.eRinexObsVersion_4
                else:
                    header.version_enum = eRinexObsVersion.eRinexObsVersion_Unknown

                if len(line) > 20:
                    header.file_type = self._Decode(line[20:21])
                if len(line) > 40:
                    header.satellite_system = self._Decode(line[40:41])

            # ---- COMMENT ----
            elif 'COMMENT' in label:
                header.comments.append(self._Decode(line[0:60]))

            # ---- MARKER NAME ----
            elif 'MARKER NAME' in label:
                header.marker_name = self._Decode(line[0:60])

            # ---- MARKER NUMBER ----
            elif 'MARKER NUMBER' in label:
                header.marker_number = self._Decode(line[0:20])

            # ---- OBSERVER / AGENCY ----
            elif 'OBSERVER / AGENCY' in label:
                header.observer = self._Decode(line[0:20])
                header.agency = self._Decode(line[20:60])

            # ---- REC # / TYPE / VERS ----
            elif 'REC # / TYPE / VERS' in label:
                header.receiver_number = self._Decode(line[0:20])
                header.receiver_type = self._Decode(line[20:40])
                header.receiver_version = self._Decode(line[40:60])

            # ---- ANT # / TYPE ----
            elif 'ANT # / TYPE' in label:
                header.antenna_number = self._Decode(line[0:20])
                header.antenna_type = self._Decode(line[20:40])

            # ---- APPROX POSITION XYZ ----
            elif 'APPROX POSITION XYZ' in label:
                x = self._SafeFloat(line[0:14])
                y = self._SafeFloat(line[14:28])
                z = self._SafeFloat(line[28:42])
                if x is not None and y is not None and z is not None:
                    header.approx_position = (x, y, z)

            # ---- ANTENNA: DELTA H/E/N ----
            elif 'ANTENNA: DELTA H/E/N' in label:
                h = self._SafeFloat(line[0:14])
                e = self._SafeFloat(line[14:28])
                n = self._SafeFloat(line[28:42])
                if h is not None and e is not None and n is not None:
                    header.antenna_delta = (h, e, n)

            # ---- SYS / # / OBS TYPES (RINEX 3.x/4.x per-system obs types) ----
            elif 'SYS / # / OBS TYPES' in label:
                sys_char = self._Decode(line[0:1])
                count = self._SafeInt(line[3:6])

                if sys_char and count is not None:
                    obs_list = []
                    # First line: up to 13 obs types starting at column 7, 4 chars each
                    self._ExtractObsTypesFromLine(line, obs_list, count)

                    # Continuation lines if more than 13 obs types
                    while len(obs_list) < count:
                        cont_line = file_handle.readline()
                        if not cont_line:
                            break
                        self._ExtractObsTypesFromLine(cont_line, obs_list, count)

                    sys_obs_types[sys_char] = obs_list

                    # Also store in header.obs_types keyed by eGnss enum
                    sys_enum = RINEX_SYSTEM_CHAR.get(sys_char, None)
                    if sys_enum is not None:
                        header.obs_types[sys_enum] = obs_list

            # ---- INTERVAL ----
            elif 'INTERVAL' in label:
                val = self._SafeFloat(line[0:10])
                if val is not None:
                    header.interval = val

            # ---- TIME OF FIRST OBS ----
            elif 'TIME OF FIRST OBS' in label:
                header.time_of_first_obs = self._ParseTimeHeaderLine(line)
                ts = self._Decode(line[48:51])
                if ts:
                    header.time_system = ts

            # ---- TIME OF LAST OBS ----
            elif 'TIME OF LAST OBS' in label:
                header.time_of_last_obs = self._ParseTimeHeaderLine(line)

            # ---- LEAP SECONDS ----
            elif 'LEAP SECONDS' in label:
                val = self._SafeInt(line[0:6])
                if val is not None:
                    header.leap_seconds = val

            # ---- # OF SATELLITES ----
            elif '# OF SATELLITES' in label:
                val = self._SafeInt(line[0:6])
                if val is not None:
                    header.num_satellites = val

            # ---- GLONASS SLOT / FRQ # ----
            elif 'GLONASS SLOT / FRQ #' in label:
                num_slots = self._SafeInt(line[0:3])
                if num_slots is not None:
                    for i in range(min(num_slots, 8)):
                        slot_start = 4 + i * 7
                        prn_str = self._Decode(line[slot_start:slot_start + 3])
                        freq_str = self._Decode(line[slot_start + 3:slot_start + 7])
                        if prn_str and freq_str:
                            prn_val = self._SafeInt(prn_str.lstrip('R'))
                            freq_val = self._SafeInt(freq_str)
                            if prn_val is not None and freq_val is not None:
                                header.glonass_slots[prn_val] = freq_val

            # ---- GLONASS COD/PHS/BIS ----
            elif 'GLONASS COD/PHS/BIS' in label:
                # Store raw for potential future use; not critical for QC
                pass

            # ---- END OF HEADER ----
            elif 'END OF HEADER' in label:
                break

            line = file_handle.readline()

        return header, sys_obs_types, eFileReadingStatus.eSuccess


    #==============================================================================
    # \Function: _ExtractObsTypesFromLine
    # \Brief: Extract 3-character observation type descriptors from a header line
    #==============================================================================
    def _ExtractObsTypesFromLine(self, line, obs_list, total_count):
        """Extract 3-character observation type descriptors from a header line.

        In RINEX 3.x, obs types start at column 7, each 4 characters wide (3 chars
        for the descriptor + 1 space), up to 13 per line.

        Args:
            line: Raw line (bytes or str).
            obs_list (list): List to append extracted obs type strings to.
            total_count (int): Total number of obs types to extract (across all lines).
        """
        remaining = total_count - len(obs_list)
        for i in range(min(13, remaining)):
            col_start = 7 + i * 4
            col_end = col_start + 3
            if len(line) >= col_end:
                ot = self._Decode(line[col_start:col_end])
                if ot:
                    obs_list.append(ot)


    #==============================================================================
    # \Function: _ParseTimeHeaderLine
    # \Brief: Parse a TIME OF FIRST/LAST OBS header line
    #==============================================================================
    def _ParseTimeHeaderLine(self, line):
        """Parse a TIME OF FIRST/LAST OBS header line.

        Returns:
            tuple: (year, month, day, hour, minute, second) or None.
        """
        try:
            year = int(self._Decode(line[0:6]))
            month = int(self._Decode(line[6:12]))
            day = int(self._Decode(line[12:18]))
            hour = int(self._Decode(line[18:24]))
            minute = int(self._Decode(line[24:30]))
            second = float(self._Decode(line[30:43]))
            return (year, month, day, hour, minute, second)
        except (ValueError, IndexError):
            return None


    # ============================================================================
    # Epoch / Body Parsing
    # ============================================================================

    #==============================================================================
    # \Function: _ReadBody
    # \Brief: Parse all observation epochs from a RINEX 3.x/4.x file body
    #==============================================================================
    def _ReadBody(self, file_handle, sys_obs_types):
        """Parse all observation epochs from a RINEX 3.x/4.x file body.

        RINEX 3.x epoch structure:
            > YYYY MM DD HH MM SS.SSSSSSS  FLAG NUMSAT   (epoch line)
            GPRN obs1 obs2 obs3 ...                      (satellite lines)
            GPRN obs1 obs2 obs3 ...
            ...

        Args:
            file_handle: File handle positioned right after END OF HEADER.
            sys_obs_types (dict): Maps system char -> list of obs type descriptors.

        Returns:
            list: List of S_EpochRecord objects.
        """
        epochs = []
        current_epoch = None

        for raw_line in file_handle:
            line = raw_line.rstrip(b'\r\n')
            if not line:
                continue

            # Check for epoch line (starts with '>')
            if line[0:1] == b'>':
                # Store previous epoch if it exists
                if current_epoch is not None:
                    epochs.append(current_epoch)

                # Parse new epoch line
                current_epoch = self._TryParseEpochLine(line)
                if current_epoch is None:
                    # Failed to parse epoch line; will skip until next valid epoch
                    logger.warning("Failed to parse epoch line: %s", self._Decode(line))
                continue

            # If we don't have a valid current epoch, skip observation lines
            if current_epoch is None:
                continue

            # Parse satellite observation line
            sat_obs = self._ParseSatObsLine(line, sys_obs_types)
            if sat_obs is not None:
                current_epoch.satellites.append(sat_obs)

        # Don't forget the last epoch
        if current_epoch is not None:
            epochs.append(current_epoch)

        return epochs


    #==============================================================================
    # \Function: _TryParseEpochLine
    # \Brief: Parse a RINEX 3.x/4.x epoch line
    #==============================================================================
    def _TryParseEpochLine(self, line):
        """Parse a RINEX 3.x/4.x epoch line.

        Format: "> YYYY MM DD HH MM SS.SSSSSSS  FLAG NUMSAT  [receiver_clk_offset]"
        Positions:  2-5  7-8  10-11 13-14 16-17 19-28  29-31  32-34

        Args:
            line: Raw bytes line starting with '>'.

        Returns:
            S_EpochRecord or None.
        """
        line_str = self._Decode(line)

        if len(line_str) < 35:
            return None

        try:
            year = int(line_str[2:6])
            month = int(line_str[7:9])
            day = int(line_str[10:12])
            hour = int(line_str[13:15])
            minute = int(line_str[16:18])
            second = float(line_str[19:29])
            flag = int(line_str[29:32])
            num_sat = int(line_str[32:35])
        except (ValueError, IndexError):
            return None

        # Basic sanity checks
        if not (1 <= month <= 12 and 1 <= day <= 31
                and 0 <= hour <= 23 and 0 <= minute <= 59):
            return None

        epoch = S_EpochRecord()
        epoch.year = year
        epoch.month = month
        epoch.day = day
        epoch.hour = hour
        epoch.minute = minute
        epoch.second = second
        epoch.epoch_flag = flag
        epoch.num_satellites = num_sat

        # Receiver clock offset (optional, columns 41-56)
        if len(line_str) >= 56:
            clk_str = line_str[41:56].strip()
            if clk_str:
                try:
                    epoch.receiver_clock_offset = float(clk_str)
                except ValueError:
                    pass

        # Compute absolute GPS time
        c_TimeUtils = C_TimeUtils()
        epoch.abs_gps_time = c_TimeUtils.YmdhmsToAbsGpsTime(
            year, month, day, hour, minute, second
        )

        return epoch


    #==============================================================================
    # \Function: _ParseSatObsLine
    # \Brief: Parse a satellite observation line
    #==============================================================================
    def _ParseSatObsLine(self, line, sys_obs_types):
        """Parse a satellite observation line.

        Format: "Gnn ooooooooooooo.ooo LI ooooooooooooo.ooo LI ..."
        - Column 0: System character
        - Columns 1-2: PRN
        - Columns 3+: Observation fields, each 16 chars wide

        Args:
            line: Raw bytes line.
            sys_obs_types (dict): Maps system char -> list of obs type descriptors.

        Returns:
            S_SatObs or None on parse failure.
        """
        if len(line) < 3:
            return None

        line_str = line.decode('utf-8', errors='replace') if isinstance(line, bytes) else line

        sys_char = line_str[0:1]
        prn_str = line_str[1:3].strip()

        if not sys_char or not prn_str:
            return None

        try:
            prn = int(prn_str)
        except ValueError:
            return None

        # Look up observation types for this system
        obs_type_list = sys_obs_types.get(sys_char, [])
        if not obs_type_list:
            # System not defined in header - skip satellite
            return None

        sat = S_SatObs()
        sat.system = RINEX_SYSTEM_CHAR.get(sys_char, eGnss.eUnknownSystem)
        sat.prn = prn

        # Parse each observation field
        for obs_idx, obs_descriptor in enumerate(obs_type_list):
            col_start = 3 + obs_idx * _OBS_FIELD_WIDTH
            col_end = col_start + _OBS_FIELD_WIDTH

            if col_start >= len(line_str):
                break

            field = line_str[col_start:col_end]

            # Extract 14-char value
            value_str = field[0:14].strip() if len(field) >= 14 else field.strip()

            if value_str:
                try:
                    sat.obs[obs_descriptor] = float(value_str)
                except ValueError:
                    pass

            # Extract LLI (column 14 of the field)
            if len(field) > 14:
                lli_char = field[14:15].strip()
                if lli_char and lli_char.isdigit():
                    sat.lli[obs_descriptor] = int(lli_char)

            # Extract SSI (column 15 of the field)
            if len(field) > 15:
                ssi_char = field[15:16].strip()
                if ssi_char and ssi_char.isdigit():
                    sat.signal_strength[obs_descriptor] = int(ssi_char)

        return sat


    # ============================================================================
    # Public API
    # ============================================================================

    #==============================================================================
    # \Function: Read
    # \Brief: Reads a RINEX 3.x or 4.x observation header and body
    # \Params:
    #           filePath        [in]    Path to the RINEX 3.x or 4.x observation file
    # \Returns:
    #           S_RinexObsFile, eFileReadingStatus
    #==============================================================================
    def Read(self, filePath):
        result = S_RinexObsFile()
        result.file_path = filePath

        if not filePath or not os.path.exists(filePath):
            return result, eFileReadingStatus.eFileNotFound

        try:
            with open(filePath, 'rb') as f:
                # Parse header
                header, sys_obs_types, status = self._ParseHeader(f)
                if status != eFileReadingStatus.eSuccess:
                    return result, status

                result.header = header

                # Parse body (file handle positioned after END OF HEADER)
                result.epochs = self._ReadBody(f, sys_obs_types)

        except (IOError, OSError) as exc:
            logger.error("Failed to read file %s: %s", filePath, exc)
            return result, eFileReadingStatus.eFileOpenError

        logger.info("Read %d epochs from RINEX %s file: %s",
                    len(result.epochs),
                    "3.x" if header.version_enum == eRinexObsVersion.eRinexObsVersion_3 else "4.x",
                    filePath)

        return result, eFileReadingStatus.eSuccess
