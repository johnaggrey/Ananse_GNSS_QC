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
        versionEnum, versionFloat, detectStatus = self.c_Detector.Detect(filePath)

        if detectStatus != eFileReadingStatus.eSuccess:
            logger.error("Version detection failed for %s: %s", filePath, detectStatus)
            return S_RinexObsFile(), detectStatus

        logger.info("Detected RINEX version %.2f (%s) for file: %s",
                    versionFloat, versionEnum.name, filePath)

        if versionEnum == eRinexObsVersion.eRinexObsVersion_2:
            return self.c_ReaderV2.Read(filePath)

        if versionEnum in (eRinexObsVersion.eRinexObsVersion_3,
                           eRinexObsVersion.eRinexObsVersion_4):
            return self.c_ReaderV3.Read(filePath)

        logger.error("Unsupported RINEX version: %.2f", versionFloat)
        return S_RinexObsFile(), eFileReadingStatus.eFileNotSupported
