#==============================================================================
# System imported libraries
#==============================================================================
import logging

from AnanseQC.Core.Enums import eFileReadingStatus, eRinexObsVersion
from AnanseQC.Readers.RinexDetector import C_RinexVersionDetector
from AnanseQC.Readers.RinexV2Reader import C_RinexObsReaderV2
from AnanseQC.Readers.RinexV3Reader import C_RinexObsReaderV3
from AnanseQC.Readers.ObsTypes import S_RinexObsFile

logger = logging.getLogger(__name__)

#==============================================================================
# \Class: C_RinexObsReader
# \Brief: Reads a RINEX observation file after detecting its version
# \Note:
#   Supported versions are RINEX 2.x, 3.x, and 4.x observation files.
#   A navigation file (type N) is rejected.
#   The returned record is always S_RinexObsFile.
#==============================================================================
class C_RinexObsReader:
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
        self.c_ReaderV2 = C_RinexObsReaderV2()
        self.c_ReaderV3 = C_RinexObsReaderV3()

    #==============================================================================
    # \Function: Read
    # \Brief: Reads a RINEX observation file with automatic version detection
    # \Params:
    #           filePath        [in]    Path to the RINEX observation file
    # \Returns:
    #           S_RinexObsFile, eFileReadingStatus
    #==============================================================================
    def Read(self, filePath):
        fileId = self.c_Detector.Detect(filePath)

        if fileId.status != eFileReadingStatus.eSuccess:
            logger.error("Version detection failed for %s: %s", filePath, fileId.status)
            return S_RinexObsFile(), fileId.status

        if fileId.file_type != 'O':
            logger.error(
                "Not an observation file: %s (type '%s')",
                filePath,
                fileId.file_type,
            )
            return S_RinexObsFile(), eFileReadingStatus.eFileNotSupported

        logger.info("Detected RINEX version %.2f (%s) for file: %s",
                    fileId.version_float, fileId.version_enum.name, filePath)

        if fileId.version_enum == eRinexObsVersion.eRinexObsVersion_2:
            return self.c_ReaderV2.Read(filePath)

        if fileId.version_enum in (eRinexObsVersion.eRinexObsVersion_3,
                                   eRinexObsVersion.eRinexObsVersion_4):
            return self.c_ReaderV3.Read(filePath)

        logger.error("Unsupported RINEX version: %.2f", fileId.version_float)
        return S_RinexObsFile(), eFileReadingStatus.eFileNotSupported
