# =============================================================================
# RINEX 2.x Observation File Reader
# =============================================================================
# Parses RINEX 2.x observation files (versions 2.00 through 2.11).
#
# RINEX 2.x key format characteristics:
#   - Epoch line: " YY MM DD HH MM SS.SSSSSSS  FLAG NUMSAT SAT_LIST"
#   - 2-digit year (80-99 => 1980-1999, 00-79 => 2000-2079)
#   - Satellite list in epoch line (up to 12 per line, continuation lines)
#   - Observation types defined once for all systems (# / TYPES OF OBSERV)
#   - Each observation value occupies 16 characters (14.3 value + 1 LLI + 1 SSI)
#   - Up to 5 observations per line; continuation lines for more
#
# Reference: RINEX 2.11 format specification (IGS/UNAVCO).

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

# Width of a single observation field in RINEX 2.x (value + LLI + SSI)
_OBS_FIELD_WIDTH = 16


#==============================================================================
# \Class: C_RinexObsReaderV2
# \Brief: Reads a RINEX 2.x observation file into S_RinexObsFile
#==============================================================================
class C_RinexObsReaderV2:
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
    # \Brief: Parse the RINEX 2.x header section
    #==============================================================================
    def _ParseHeader(self, file_handle):
        """Parse the RINEX 2.x header section.

        Reads lines until END OF HEADER is found and populates a
        S_RinexObsHeader dataclass.

        Args:
            file_handle: Open file handle positioned at the beginning of the file.

        Returns:
            tuple: (S_RinexObsHeader, list_of_obs_type_strings, eFileReadingStatus)
        """
        header = S_RinexObsHeader()
        header.version_enum = eRinexObsVersion.eRinexObsVersion_2
        obs_type_list = []  # Ordered list of observation type codes

        line = file_handle.readline()
        while line:
            label = self._Decode(line[60:80]) if len(line) >= 60 else ''

            # ---- RINEX VERSION / TYPE ----
            if 'RINEX VERSION / TYPE' in label:
                ver_str = self._Decode(line[0:9])
                try:
                    header.version = float(ver_str)
                except ValueError:
                    return header, obs_type_list, eFileReadingStatus.eFileFormatError
                if len(line) > 20:
                    header.file_type = self._Decode(line[20:21])
                if len(line) > 40:
                    header.satellite_system = self._Decode(line[40:41])
                    # RINEX 2.x with empty system defaults to GPS
                    if not header.satellite_system:
                        header.satellite_system = 'G'

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

            # ---- # / TYPES OF OBSERV ----
            elif '# / TYPES OF OBSERV' in label:
                count = self._SafeInt(line[0:6])
                if count is not None:
                    # First line of observation types (or continuation)
                    if len(obs_type_list) == 0:
                        # First occurrence: read all types
                        # Up to 9 types per line at columns 10-58 (6 chars each)
                        for i in range(min(count, 9)):
                            col_start = 10 + i * 6
                            ot = self._Decode(line[col_start:col_start + 6])
                            if ot:
                                obs_type_list.append(ot)

                        # If more than 9 types, read continuation lines
                        while len(obs_type_list) < count:
                            cont_line = file_handle.readline()
                            if not cont_line:
                                break
                            for i in range(min(count - len(obs_type_list), 9)):
                                col_start = 10 + i * 6
                                ot = self._Decode(cont_line[col_start:col_start + 6])
                                if ot:
                                    obs_type_list.append(ot)

                # In RINEX 2.x, obs types apply to all systems
                # We will assign them under the default system in header.obs_types later

            # ---- INTERVAL ----
            elif 'INTERVAL' in label:
                val = self._SafeFloat(line[0:10])
                if val is not None:
                    header.interval = val

            # ---- TIME OF FIRST OBS ----
            elif 'TIME OF FIRST OBS' in label:
                header.time_of_first_obs = self._ParseTimeHeaderLine(line)
                # Time system indicator at columns 48-51
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

            # ---- END OF HEADER ----
            elif 'END OF HEADER' in label:
                break

            line = file_handle.readline()

        # Assign the obs types to a default system (RINEX 2.x is single-system)
        default_sys = RINEX_SYSTEM_CHAR.get(header.satellite_system, eGnss.eGPS)
        header.obs_types[default_sys] = obs_type_list

        return header, obs_type_list, eFileReadingStatus.eSuccess


    #==============================================================================
    # \Function: _ParseTimeHeaderLine
    # \Brief: Parse a TIME OF FIRST/LAST OBS header line
    #==============================================================================
    def _ParseTimeHeaderLine(self, line):
        """Parse a TIME OF FIRST/LAST OBS header line.

        Format: 6 fields at columns 0-5, 6-11, 12-17, 18-23, 24-29, 30-42

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
    # \Function: _ParseV2Year
    # \Brief: Convert 2-digit year to 4-digit year per RINEX 2.x convention
    #==============================================================================
    def _ParseV2Year(self, year_2digit):
        """Convert 2-digit year to 4-digit year per RINEX 2.x convention.

        80-99 => 1980-1999 ; 00-79 => 2000-2079
        """
        if year_2digit >= 80:
            return 1900 + year_2digit
        return 2000 + year_2digit


    #==============================================================================
    # \Function: _ParseObsLine
    # \Brief: Parse observation values, LLI and SSI from one data line
    #==============================================================================
    def _ParseObsLine(self, line_str, obs_type_list, start_idx=0):
        """Parse observation values, LLI and SSI from one data line.

        RINEX 2.x places up to 5 observation fields per line, each 16 chars wide.

        Args:
            line_str (str): Decoded observation line.
            obs_type_list (list): Full ordered list of obs type descriptors.
            start_idx (int): Index into obs_type_list where this line starts.

        Returns:
            tuple: (obs_dict, lli_dict, ssi_dict, next_idx)
                obs_dict maps obs_type_str -> float value
                lli_dict maps obs_type_str -> int LLI (or omitted if absent)
                ssi_dict maps obs_type_str -> int SSI (or omitted if absent)
                next_idx is the index of the next unprocessed obs type
        """
        obs_dict = {}
        lli_dict = {}
        ssi_dict = {}
        idx = start_idx
        col = 0

        while idx < len(obs_type_list) and col + _OBS_FIELD_WIDTH <= len(line_str):
            field = line_str[col:col + _OBS_FIELD_WIDTH]
            value_str = field[0:14].strip()
            lli_char = field[14:15] if len(field) > 14 else ''
            ssi_char = field[15:16] if len(field) > 15 else ''

            ot = obs_type_list[idx]

            if value_str:
                try:
                    val = float(value_str)
                    obs_dict[ot] = val
                except ValueError:
                    pass

            if lli_char.strip() and lli_char.strip().isdigit():
                lli_dict[ot] = int(lli_char)

            if ssi_char.strip() and ssi_char.strip().isdigit():
                ssi_dict[ot] = int(ssi_char)

            idx += 1
            col += _OBS_FIELD_WIDTH

        # Handle short lines (incomplete field at end)
        if idx < len(obs_type_list) and col < len(line_str):
            remaining = line_str[col:]
            value_str = remaining[0:14].strip() if len(remaining) >= 14 else remaining.strip()
            if value_str:
                ot = obs_type_list[idx]
                try:
                    obs_dict[ot] = float(value_str)
                except ValueError:
                    pass
                idx += 1

        return obs_dict, lli_dict, ssi_dict, idx


    #==============================================================================
    # \Function: _DecodePreserveLeading
    # \Brief: Decode bytes to str, keeping leading whitespace (critical for RINEX 2.x
    #==============================================================================
    def _DecodePreserveLeading(self, raw):
        """Decode bytes to str, keeping leading whitespace (critical for RINEX 2.x
        fixed-column epoch lines). Only trailing whitespace is stripped."""
        if isinstance(raw, bytes):
            return raw.decode('utf-8', errors='replace').rstrip()
        if isinstance(raw, str):
            return raw.rstrip()
        return ''


    #==============================================================================
    # \Function: _ReadBody
    # \Brief: Parse all observation epochs from a RINEX 2.x file body
    #==============================================================================
    def _ReadBody(self, file_handle, obs_type_list):
        """Parse all observation epochs from a RINEX 2.x file body.

        Args:
            file_handle: File handle positioned right after END OF HEADER.
            obs_type_list (list): Ordered observation type descriptors from header.

        Returns:
            list: List of S_EpochRecord objects.
        """
        epochs = []

        while True:
            line = file_handle.readline()
            if not line:
                break

            line = line.rstrip(b'\r\n')
            # Preserve leading whitespace for fixed-column position parsing
            line_str = self._DecodePreserveLeading(line)

            # Skip blank or too-short lines
            if len(line_str) < 32:
                continue

            # Attempt to parse epoch line
            epoch_record = self._TryParseEpochLine(line_str)
            if epoch_record is None:
                continue

            num_sats = epoch_record.num_satellites

            # If more than 12 satellites, the satellite list continues on next line(s)
            # Satellite list in epoch line starts at column 32, 3 chars per satellite
            sat_ids = self._ParseSatelliteList(line_str[32:], num_sats)

            while len(sat_ids) < num_sats:
                cont_line = file_handle.readline()
                if not cont_line:
                    break
                cont_str = self._DecodePreserveLeading(cont_line.rstrip(b'\r\n'))
                # Continuation line has satellite list starting at column 32
                padded = cont_str.rjust(68) if len(cont_str) < 68 else cont_str
                sat_ids.extend(self._ParseSatelliteList(padded[32:], num_sats - len(sat_ids)))

            # If epoch flag > 1, this is a special event (e.g. header inline).
            # Skip observation lines for special event records.
            if epoch_record.epoch_flag > 1:
                # Skip 'num_sats' lines (they contain special event info, not obs)
                for _ in range(num_sats):
                    skip_line = file_handle.readline()
                    if not skip_line:
                        break
                epochs.append(epoch_record)
                continue

            # Read observations for each satellite
            for sat_idx in range(num_sats):
                # Build S_SatObs
                if sat_idx < len(sat_ids):
                    sys_char, prn = sat_ids[sat_idx]
                else:
                    sys_char, prn = 'G', 0

                sat_obs = S_SatObs()
                sat_obs.system = RINEX_SYSTEM_CHAR.get(sys_char, eGnss.eUnknownSystem)
                sat_obs.prn = prn

                # Read observation data lines for this satellite
                # RINEX 2.x: up to 5 obs per line, continuation lines if > 5 obs types
                obs_idx = 0
                first_obs_line = True

                while obs_idx < len(obs_type_list):
                    obs_line = file_handle.readline()
                    if not obs_line:
                        break
                    obs_line_str = obs_line.rstrip(b'\r\n')
                    obs_line_decoded = self._DecodePreserveLeading(obs_line_str)

                    obs_d, lli_d, ssi_d, obs_idx = self._ParseObsLine(
                        obs_line_decoded, obs_type_list, obs_idx
                    )

                    sat_obs.obs.update(obs_d)
                    sat_obs.lli.update(lli_d)
                    sat_obs.signal_strength.update(ssi_d)

                epoch_record.satellites.append(sat_obs)

            # Compute absolute GPS time for this epoch
            c_TimeUtils = C_TimeUtils()
            epoch_record.abs_gps_time = c_TimeUtils.YmdhmsToAbsGpsTime(
                epoch_record.year, epoch_record.month, epoch_record.day,
                epoch_record.hour, epoch_record.minute, epoch_record.second
            )

            epochs.append(epoch_record)

        return epochs


    #==============================================================================
    # \Function: _TryParseEpochLine
    # \Brief: Attempt to parse a RINEX 2.x epoch line
    #==============================================================================
    def _TryParseEpochLine(self, line_str):
        """Attempt to parse a RINEX 2.x epoch line.

        Format: " YY MM DD HH MM SS.SSSSSSS  F NN"
        Positions: 0-2 year, 3-5 month, 6-8 day, 9-11 hour, 12-14 minute,
                  15-26 second, 27-28 flag, 29-31 numsat

        Args:
            line_str (str): Decoded line to test.

        Returns:
            S_EpochRecord or None if line is not a valid epoch line.
        """
        try:
            year_2d = int(line_str[1:3])
            if year_2d < 0 or year_2d > 99:
                return None
            month = int(line_str[4:6])
            day = int(line_str[7:9])
            hour = int(line_str[10:12])
            minute = int(line_str[13:15])
            second = float(line_str[15:26])
            flag = int(line_str[26:29])
            num_sat = int(line_str[29:32])
        except (ValueError, IndexError):
            return None

        # Basic sanity checks
        if not (1 <= month <= 12 and 1 <= day <= 31
                and 0 <= hour <= 23 and 0 <= minute <= 59):
            return None

        epoch = S_EpochRecord()
        epoch.year = self._ParseV2Year(year_2d)
        epoch.month = month
        epoch.day = day
        epoch.hour = hour
        epoch.minute = minute
        epoch.second = second
        epoch.epoch_flag = flag
        epoch.num_satellites = num_sat

        # Check for receiver clock offset at the end of the line
        if len(line_str) >= 68:
            clk_str = line_str[68:80].strip() if len(line_str) >= 80 else ''
            if clk_str:
                try:
                    epoch.receiver_clock_offset = float(clk_str)
                except ValueError:
                    pass

        return epoch


    #==============================================================================
    # \Function: _ParseSatelliteList
    # \Brief: Parse satellite identifiers from the epoch line satellite list
    #==============================================================================
    def _ParseSatelliteList(self, sat_str, max_sats):
        """Parse satellite identifiers from the epoch line satellite list.

        Each satellite is 3 characters: system_char + 2-digit PRN.
        Example: "G01R05E12" -> [('G', 1), ('R', 5), ('E', 12)]

        Args:
            sat_str (str): Substring containing satellite identifiers.
            max_sats (int): Maximum number of satellites to read.

        Returns:
            list: List of (system_char, prn) tuples.
        """
        result = []
        for i in range(min(max_sats, len(sat_str) // 3)):
            chunk = sat_str[i * 3:(i + 1) * 3]
            sys_char = chunk[0:1].strip()
            prn_str = chunk[1:3].strip()

            # Default to GPS if system character is blank
            if not sys_char or sys_char == ' ':
                sys_char = 'G'

            try:
                prn = int(prn_str)
            except ValueError:
                continue

            result.append((sys_char, prn))

        return result


    # ============================================================================
    # Public API
    # ============================================================================

    #==============================================================================
    # \Function: Read
    # \Brief: Reads a RINEX 2.x observation header and body
    # \Params:
    #           filePath        [in]    Path to the RINEX 2.x observation file
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
                header, obs_type_list, status = self._ParseHeader(f)
                if status != eFileReadingStatus.eSuccess:
                    return result, status

                result.header = header

                # Parse body (file handle is now positioned after END OF HEADER)
                result.epochs = self._ReadBody(f, obs_type_list)

        except (IOError, OSError) as exc:
            logger.error("Failed to read file %s: %s", filePath, exc)
            return result, eFileReadingStatus.eFileOpenError

        logger.info("Read %d epochs from RINEX 2.x file: %s",
                    len(result.epochs), filePath)

        return result, eFileReadingStatus.eSuccess
