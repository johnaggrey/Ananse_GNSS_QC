# =============================================================================
# Tests for the RINEX 2 navigation reader
# =============================================================================
# The GPS sample is RINEX 2.11, file type N. The year is two digits (24).
# The week in the file is the 10-bit value 275, which expands to GPS week 2323.
# Times are absolute GPST seconds.
# The GLONASS sample is file type G. Position in the file is kilometres.
# Stored position is ECEF metres. The epoch is UTC plus 18 leap seconds.

import os

from AnanseQC.Core.Enums import eFileReadingStatus, eGnss, eRinexObsVersion
from AnanseQC.Readers.NavReader import C_RinexNavReader

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# 2024-07-15 00:00:00 GPST.
TOC_GPST = 1405036800.0
LEAP_SECONDS = 18


class TestNavV2Reader:
    """RINEX 2 navigation records and the version-selecting reader."""

    #==============================================================================
    # \Function: test_reads_gps_week_rollover
    # \Brief: A two-digit epoch and a 10-bit GPS week become absolute GPST
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Times are GPST seconds.
    #==============================================================================
    def test_reads_gps_week_rollover(self):
        path = os.path.join(DATA_DIR, 'sample_nav_v2.snippet')
        navFile, eStatus = C_RinexNavReader().Read(path)
        assert eStatus == eFileReadingStatus.eSuccess
        assert navFile.header.version_enum == eRinexObsVersion.eRinexObsVersion_2
        assert abs(navFile.header.version - 2.11) < 0.001
        assert navFile.header.file_type == 'N'
        assert navFile.header.satellite_system == 'G'
        assert len(navFile.kepler_eph) == 1
        assert len(navFile.state_eph) == 0

        gps = navFile.kepler_eph[0]
        assert gps.system == eGnss.eGPS
        assert gps.prn == 1
        assert gps.week == 2323
        assert abs(gps.af0 - 1.0e-4) < 1.0e-15
        assert abs(gps.sqrt_a - 5153.0) < 1.0e-9
        assert abs(gps.toc_gpst - TOC_GPST) < 1.0e-6
        assert abs(gps.toe_gpst - TOC_GPST) < 1.0e-6

    #==============================================================================
    # \Function: test_reads_glonass_state
    # \Brief: A RINEX 2 GLONASS file is stored as ECEF metres at GPST
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_reads_glonass_state(self):
        path = os.path.join(DATA_DIR, 'sample_nav_v2_glonass.snippet')
        navFile, eStatus = C_RinexNavReader().Read(path)
        assert eStatus == eFileReadingStatus.eSuccess
        assert navFile.header.file_type == 'G'
        assert len(navFile.kepler_eph) == 0
        assert len(navFile.state_eph) == 1

        glonass = navFile.state_eph[0]
        assert glonass.system == eGnss.eGLN
        assert glonass.prn == 1
        assert abs(glonass.x_m - 7000000.0) < 1.0e-3
        assert abs(glonass.vx_mps - 1000.0) < 1.0e-6
        assert glonass.frequency_slot == 1
        assert abs(glonass.epoch_gpst - (TOC_GPST + LEAP_SECONDS)) < 1.0e-6

    #==============================================================================
    # \Function: test_facade_reads_rinex3_and_rejects_observation
    # \Brief: The facade reads a RINEX 3 navigation file and rejects an observation file
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_facade_reads_rinex3_and_rejects_observation(self):
        navPath = os.path.join(DATA_DIR, 'sample_nav_v3.snippet')
        navFile, eStatus = C_RinexNavReader().Read(navPath)
        assert eStatus == eFileReadingStatus.eSuccess
        assert navFile.header.version_enum == eRinexObsVersion.eRinexObsVersion_3
        assert len(navFile.kepler_eph) == 1
        assert len(navFile.state_eph) == 1

        obsPath = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obsNav, eObsStatus = C_RinexNavReader().Read(obsPath)
        assert eObsStatus == eFileReadingStatus.eFileNotSupported
        assert len(obsNav.kepler_eph) == 0
