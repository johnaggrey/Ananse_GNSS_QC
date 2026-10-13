# =============================================================================
# Tests for navigation-file detection
# =============================================================================
# The sample header is a RINEX 3.04 mixed navigation file.
# File type N is navigation. System character M is mixed.
# The observation reader must reject it.

import os

from AnanseQC.Core.Enums import eFileReadingStatus, eRinexObsVersion
from AnanseQC.Readers.Reader import C_RinexObsReader
from AnanseQC.Readers.RinexDetector import C_RinexVersionDetector

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


class TestNavDetector:
    """Navigation headers are identified and kept out of the observation reader."""

    #==============================================================================
    # \Function: test_detects_navigation_header
    # \Brief: A RINEX 3.04 navigation header is type N and system M
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_detects_navigation_header(self):
        path = os.path.join(DATA_DIR, 'sample_nav_header.snippet')
        fileId = C_RinexVersionDetector().Detect(path)
        assert fileId.status == eFileReadingStatus.eSuccess
        assert fileId.version_enum == eRinexObsVersion.eRinexObsVersion_3
        assert abs(fileId.version_float - 3.04) < 0.001
        assert fileId.file_type == 'N'
        assert fileId.system_char == 'M'

    #==============================================================================
    # \Function: test_observation_reader_rejects_navigation
    # \Brief: The observation reader returns not-supported for a navigation file
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_observation_reader_rejects_navigation(self):
        path = os.path.join(DATA_DIR, 'sample_nav_header.snippet')
        obsFile, eStatus = C_RinexObsReader().Read(path)
        assert eStatus == eFileReadingStatus.eFileNotSupported
        assert len(obsFile.epochs) == 0
