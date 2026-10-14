# =============================================================================
# Tests for the RINEX 3 and 4 navigation reader
# =============================================================================
# The version-3 sample has one GPS Kepler record and one GLONASS state record.
# GPS time is GPST. GLONASS time in the file is UTC.
# Header leap seconds are 18, so GLONASS epoch_gpst is 18 seconds later.
# GLONASS position in the file is kilometres. Stored position is ECEF metres.
# The version-4 sample repeats those records and adds a STO block that must
# not become an ephemeris.

import os

from AnanseQC.Core.Enums import eFileReadingStatus, eGnss, eRinexObsVersion
from AnanseQC.Readers.RinexNavV3Reader import C_RinexNavReaderV3

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# 2024-07-15 00:00:00 GPST. GPS week 2323, seconds of week 86400.
TOC_GPST = 1405036800.0
LEAP_SECONDS = 18


class TestNavV3Reader:
    """RINEX 3 and 4 navigation records."""

    #==============================================================================
    # \Function: test_reads_gps_and_glonass
    # \Brief: Reads one GPS Kepler record and one GLONASS state record
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Times are GPST seconds.
    #                           GLONASS position is ECEF metres.
    #==============================================================================
    def test_reads_gps_and_glonass(self):
        path = os.path.join(DATA_DIR, 'sample_nav_v3.snippet')
        navFile, eStatus = C_RinexNavReaderV3().Read(path)
        assert eStatus == eFileReadingStatus.eSuccess
        assert navFile.header.version_enum == eRinexObsVersion.eRinexObsVersion_3
        assert abs(navFile.header.version - 3.04) < 0.001
        assert navFile.header.file_type == 'N'
        assert navFile.header.satellite_system == 'M'
        assert navFile.header.leap_seconds == LEAP_SECONDS
        assert len(navFile.header.comments) == 1
        assert len(navFile.kepler_eph) == 1
        assert len(navFile.state_eph) == 1

        gps = navFile.kepler_eph[0]
        assert gps.system == eGnss.eGPS
        assert gps.prn == 1
        assert abs(gps.af0 - 1.0e-4) < 1.0e-15
        assert abs(gps.crs - 10.0) < 1.0e-9
        assert abs(gps.e - 0.01) < 1.0e-12
        assert abs(gps.sqrt_a - 5153.0) < 1.0e-9
        assert abs(gps.omega_dot - (-1.0e-9)) < 1.0e-18
        assert gps.week == 2323
        assert gps.health == 0
        assert abs(gps.tgd - 1.0e-8) < 1.0e-18
        assert abs(gps.fit_interval - 4.0) < 1.0e-9
        assert abs(gps.toc_gpst - TOC_GPST) < 1.0e-6
        assert abs(gps.toe_gpst - TOC_GPST) < 1.0e-6

        glonass = navFile.state_eph[0]
        assert glonass.system == eGnss.eGLN
        assert glonass.prn == 1
        assert abs(glonass.x_m - 7000000.0) < 1.0e-3
        assert abs(glonass.y_m - (-7000000.0)) < 1.0e-3
        assert abs(glonass.z_m - 10000000.0) < 1.0e-3
        assert abs(glonass.vx_mps - 1000.0) < 1.0e-6
        assert abs(glonass.ax_mps2 - 0.001) < 1.0e-9
        assert glonass.frequency_slot == 1
        assert glonass.health == 0
        assert abs(glonass.clock_bias - (-1.0e-5)) < 1.0e-16
        assert abs(glonass.epoch_gpst - (TOC_GPST + LEAP_SECONDS)) < 1.0e-6

    #==============================================================================
    # \Function: test_rinex4_skips_non_ephemeris
    # \Brief: A RINEX 4 file keeps LNAV and FDMA and drops the STO block
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_rinex4_skips_non_ephemeris(self):
        path = os.path.join(DATA_DIR, 'sample_nav_v4.snippet')
        navFile, eStatus = C_RinexNavReaderV3().Read(path)
        assert eStatus == eFileReadingStatus.eSuccess
        assert navFile.header.version_enum == eRinexObsVersion.eRinexObsVersion_4
        assert len(navFile.kepler_eph) == 1
        assert navFile.kepler_eph[0].prn == 1
        assert navFile.kepler_eph[0].system == eGnss.eGPS
        assert len(navFile.state_eph) == 1
        assert navFile.state_eph[0].prn == 1
        assert navFile.state_eph[0].system == eGnss.eGLN
