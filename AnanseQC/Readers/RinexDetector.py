# =============================================================================
# RINEX File Version Detector
# =============================================================================
# Detects the RINEX version and file type from the first header line.
# Supports RINEX 2.x, 3.x, and 4.x observation and navigation files.
#
# RINEX first-line format (columns are 1-based in the standard):
#   Columns 1-9:   Version number (e.g. "     2.11", "     3.04")
#   Column  21:    File type ('O' observation, 'N' navigation)
#   Column  41:    Satellite system ('G', 'M', 'R', and so on)
#   Columns 61-80: "RINEX VERSION / TYPE"

import os
from dataclasses import dataclass

from AnanseQC.Core.Enums import eFileReadingStatus, eRinexObsVersion


#==============================================================================
# \Class: S_RinexFileId
# \Brief: Version, file type, and system character from the first header line
#==============================================================================
@dataclass
class S_RinexFileId:
    """Identity of a RINEX file taken from the first header line.

    Attributes:
        version_enum (eRinexObsVersion): Coarse version category.
        version_float (float): Precise version (2.11, 3.04, 4.00), or 0.0.
        file_type (str): 'O' or 'N'. Empty when the column is not a letter.
        system_char (str): Satellite system character. Empty when absent.
        status (eFileReadingStatus): eSuccess when the header line is valid.
    """
    version_enum: eRinexObsVersion = eRinexObsVersion.eRinexObsVersion_Invalid
    version_float: float = 0.0
    file_type: str = ''
    system_char: str = ''
    status: eFileReadingStatus = eFileReadingStatus.eUnknownError


#==============================================================================
# \Class: C_RinexVersionDetector
# \Brief: Detects the RINEX version and file type from the first header line
#==============================================================================
class C_RinexVersionDetector:
    #==============================================================================
    # \Function: Detect
    # \Brief: Reads the version, file type, and system character
    # \Params:
    #           filePath        [in]    Path to a RINEX observation or navigation file
    # \Returns:
    #           S_RinexFileId   version_float is 0.0 when detection fails
    #==============================================================================
    def Detect(self, filePath):
        if filePath is None or filePath == '':
            return self._Failed(eFileReadingStatus.eFileNotFound)

        if os.path.exists(filePath) == False:
            return self._Failed(eFileReadingStatus.eFileNotFound)

        try:
            with open(filePath, 'rb') as fileHandle:
                firstLine = fileHandle.readline()
        except (IOError, OSError):
            return self._Failed(eFileReadingStatus.eFileOpenError)

        if firstLine is None or len(firstLine) == 0:
            return self._Failed(eFileReadingStatus.eEmptyFile)

        if len(firstLine) < 60:
            return self._Failed(eFileReadingStatus.eFileFormatError)

        if len(firstLine) >= 80:
            markerBytes = firstLine[60:80]
        else:
            markerBytes = firstLine[60:]
        marker = markerBytes.decode('utf-8', errors='ignore').strip()

        if 'RINEX VERSION / TYPE' not in marker:
            return self._Failed(eFileReadingStatus.eFileFormatError)

        versionText = firstLine[0:9].decode('utf-8', errors='ignore').strip()
        try:
            versionFloat = float(versionText)
        except ValueError:
            return self._Failed(eFileReadingStatus.eFileFormatError)

        fileType = self._LetterAt(firstLine, 20)
        systemChar = self._LetterAt(firstLine, 40)
        majorVersion = int(versionFloat)

        if majorVersion == 2:
            versionEnum = eRinexObsVersion.eRinexObsVersion_2
            status = eFileReadingStatus.eSuccess
        elif majorVersion == 3:
            versionEnum = eRinexObsVersion.eRinexObsVersion_3
            status = eFileReadingStatus.eSuccess
        elif majorVersion == 4:
            versionEnum = eRinexObsVersion.eRinexObsVersion_4
            status = eFileReadingStatus.eSuccess
        else:
            versionEnum = eRinexObsVersion.eRinexObsVersion_Unknown
            status = eFileReadingStatus.eFileNotSupported

        return S_RinexFileId(
            version_enum=versionEnum,
            version_float=versionFloat,
            file_type=fileType,
            system_char=systemChar,
            status=status,
        )

    #==============================================================================
    # \Function: _Failed
    # \Brief: Builds a failed identity with an empty file type
    # \Params:
    #           eStatus         [in]    eFileReadingStatus
    # \Returns:
    #           S_RinexFileId
    #==============================================================================
    def _Failed(self, eStatus):
        return S_RinexFileId(
            version_enum=eRinexObsVersion.eRinexObsVersion_Invalid,
            version_float=0.0,
            file_type='',
            system_char='',
            status=eStatus,
        )

    #==============================================================================
    # \Function: _LetterAt
    # \Brief: Returns the uppercase letter at a 0-based column, or empty
    # \Params:
    #           lineBytes       [in]    First header line, bytes
    #           index           [in]    0-based column
    # \Returns:
    #           str             One uppercase letter, or ''
    #==============================================================================
    def _LetterAt(self, lineBytes, index):
        if len(lineBytes) <= index:
            return ''
        raw = lineBytes[index]
        if isinstance(raw, int) == True:
            char = chr(raw)
        else:
            char = raw
        if char.isalpha() == False:
            return ''
        return char.upper()
