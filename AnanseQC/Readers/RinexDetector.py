# =============================================================================
# RINEX File Version Detector
# =============================================================================
# Detects the RINEX observation file version by examining the first line
# of the file. Supports RINEX 2.x, 3.x, and 4.x formats.
#
# RINEX first-line format:
#   Columns 0-8:   Version number (e.g. "     2.11", "     3.05")
#   Column  20:    File type ('O' for observation)
#   Columns 60-79: "RINEX VERSION / TYPE"

import os

from AnanseQC.Core.Enums import eFileReadingStatus, eRinexObsVersion


#==============================================================================
# \Class: C_RinexVersionDetector
# \Brief: Detects the RINEX observation version from the first header line
#==============================================================================
class C_RinexVersionDetector:
    #==============================================================================
    # \Function: Detect
    # \Brief: Detects the RINEX observation version from the first header line
    # \Params:
    #           filePath        [in]    Path to the RINEX observation file
    # \Returns:
    #           eRinexObsVersion, float, eFileReadingStatus
    #           The float is the precise version (2.11, 3.05, 4.00), or 0.0
    #==============================================================================
    def Detect(self, filePath):
        # Validate input
        if not filePath:
            return eRinexObsVersion.eRinexObsVersion_Invalid, 0.0, eFileReadingStatus.eFileNotFound

        if not os.path.exists(filePath):
            return eRinexObsVersion.eRinexObsVersion_Invalid, 0.0, eFileReadingStatus.eFileNotFound

        try:
            with open(filePath, 'rb') as f:
                first_line = f.readline()
        except (IOError, OSError):
            return eRinexObsVersion.eRinexObsVersion_Invalid, 0.0, eFileReadingStatus.eFileOpenError

        if not first_line:
            return eRinexObsVersion.eRinexObsVersion_Invalid, 0.0, eFileReadingStatus.eEmptyFile

        # Ensure line is long enough for RINEX format
        if len(first_line) < 60:
            return eRinexObsVersion.eRinexObsVersion_Invalid, 0.0, eFileReadingStatus.eFileFormatError

        # Check for the RINEX header marker at columns 60-79
        marker_bytes = first_line[60:80] if len(first_line) >= 80 else first_line[60:]
        marker_str = marker_bytes.decode('utf-8', errors='ignore').strip()

        if 'RINEX VERSION / TYPE' not in marker_str:
            return eRinexObsVersion.eRinexObsVersion_Invalid, 0.0, eFileReadingStatus.eFileFormatError

        # Extract version number from columns 0-8
        version_str = first_line[0:9].decode('utf-8', errors='ignore').strip()

        try:
            version_float = float(version_str)
        except ValueError:
            return eRinexObsVersion.eRinexObsVersion_Invalid, 0.0, eFileReadingStatus.eFileFormatError

        # Check file type indicator at column 20
        if len(first_line) > 20:
            file_type_char = chr(first_line[20]) if isinstance(first_line[20], int) else first_line[20]
            # Accept 'O' for observation files (case insensitive)
            if file_type_char.upper() not in ('O',):
                # Not an observation file, but still a valid RINEX file
                pass

        # Classify into version enum
        major_version = int(version_float)

        if major_version == 2:
            return eRinexObsVersion.eRinexObsVersion_2, version_float, eFileReadingStatus.eSuccess
        elif major_version == 3:
            return eRinexObsVersion.eRinexObsVersion_3, version_float, eFileReadingStatus.eSuccess
        elif major_version == 4:
            return eRinexObsVersion.eRinexObsVersion_4, version_float, eFileReadingStatus.eSuccess
        else:
            return eRinexObsVersion.eRinexObsVersion_Unknown, version_float, eFileReadingStatus.eFileNotSupported
