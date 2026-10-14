#==============================================================================
# System imported libraries
#==============================================================================
# Selects the RINEX 2 or RINEX 3/4 navigation reader from the header.
# Observation files are rejected.

import logging

from AnanseQC.Core.Enums import eFileReadingStatus, eRinexObsVersion
from AnanseQC.Readers.NavTypes import S_RinexNavFile
from AnanseQC.Readers.RinexDetector import C_RinexVersionDetector
from AnanseQC.Readers.RinexNavV2Reader import C_RinexNavReaderV2, NAV_V2_TYPES
from AnanseQC.Readers.RinexNavV3Reader import C_RinexNavReaderV3

logger = logging.getLogger(__name__)


#==============================================================================
# \Class: C_RinexNavReader
# \Brief: Reads a RINEX navigation file after detecting its version
# \Note:
#   RINEX 2 accepts file types N, G, and H.
#   RINEX 3 and 4 accept file type N. RINEX 4 uses the version-3 reader.
#==============================================================================
class C_RinexNavReader:
    #==============================================================================
    # \Function: __init__
    # \Brief: Creates the version detector and the version-specific readers
    # \Params:
    #           None
    # \Returns:
    #           None
    #==============================================================================
    def __init__(self):
        self.c_Detector = C_RinexVersionDetector()
        self.c_ReaderV2 = C_RinexNavReaderV2()
        self.c_ReaderV3 = C_RinexNavReaderV3()

    #==============================================================================
    # \Function: Read
    # \Brief: Reads a RINEX navigation file with automatic version detection
    # \Params:
    #           filePath        [in]    Path to the navigation file
    # \Returns:
    #           S_RinexNavFile, eFileReadingStatus
    #           Kepler times are absolute GPST seconds.
    #           State positions are ECEF metres.
    #==============================================================================
    def Read(self, filePath):
        fileId = self.c_Detector.Detect(filePath)

        if fileId.status != eFileReadingStatus.eSuccess:
            logger.error("Version detection failed for %s: %s", filePath, fileId.status)
            return S_RinexNavFile(), fileId.status

        if fileId.file_type not in NAV_V2_TYPES:
            logger.error(
                "Not a navigation file: %s (type '%s')",
                filePath,
                fileId.file_type,
            )
            return S_RinexNavFile(), eFileReadingStatus.eFileNotSupported

        logger.info(
            "Detected RINEX navigation version %.2f (%s) for file: %s",
            fileId.version_float,
            fileId.version_enum.name,
            filePath,
        )

        if fileId.version_enum == eRinexObsVersion.eRinexObsVersion_2:
            return self.c_ReaderV2.Read(filePath)

        if fileId.version_enum in (
            eRinexObsVersion.eRinexObsVersion_3,
            eRinexObsVersion.eRinexObsVersion_4,
        ):
            return self.c_ReaderV3.Read(filePath)

        logger.error("Unsupported navigation version: %.2f", fileId.version_float)
        return S_RinexNavFile(), eFileReadingStatus.eFileNotSupported
