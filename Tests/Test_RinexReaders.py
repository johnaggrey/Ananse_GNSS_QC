# =============================================================================
# Tests for RINEX Observation File Readers
# =============================================================================
# Sample files are observation files. Header interval is seconds.
# Positions in those files are ECEF metres.

import os
import pytest

from AnanseQC.Core.Enums import eFileReadingStatus, eRinexObsVersion, eGnss
from AnanseQC.Readers.RinexDetector import C_RinexVersionDetector
from AnanseQC.Readers.RinexV2Reader import C_RinexObsReaderV2
from AnanseQC.Readers.RinexV3Reader import C_RinexObsReaderV3
from AnanseQC.Readers.Reader import C_RinexObsReader

# Path to test data directory
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


class TestRinexDetector:
    """Tests for RINEX version detection."""

    #==============================================================================
    # \Function: test_detect_v2
    # \Brief: Detects RINEX 2.11 from the version-2 sample
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_detect_v2(self):
        path = os.path.join(DATA_DIR, 'sample_v2.snippet')
        version, ver_float, status = C_RinexVersionDetector().Detect(path)
        assert status == eFileReadingStatus.eSuccess
        assert version == eRinexObsVersion.eRinexObsVersion_2
        assert abs(ver_float - 2.11) < 0.01

    #==============================================================================
    # \Function: test_detect_v3
    # \Brief: Detects RINEX 3.05 from the version-3 sample
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_detect_v3(self):
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        version, ver_float, status = C_RinexVersionDetector().Detect(path)
        assert status == eFileReadingStatus.eSuccess
        assert version == eRinexObsVersion.eRinexObsVersion_3
        assert abs(ver_float - 3.05) < 0.01

    #==============================================================================
    # \Function: test_nonexistent_file
    # \Brief: A missing path returns file-not-found and an invalid version
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_nonexistent_file(self):
        version, _, status = C_RinexVersionDetector().Detect('/nonexistent/file.obs')
        assert status == eFileReadingStatus.eFileNotFound
        assert version == eRinexObsVersion.eRinexObsVersion_Invalid

    #==============================================================================
    # \Function: test_empty_path
    # \Brief: An empty path returns file-not-found
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_empty_path(self):
        version, _, status = C_RinexVersionDetector().Detect('')
        assert status == eFileReadingStatus.eFileNotFound


class TestRinexV2Reader:
    """Tests for RINEX 2.x reader."""

    #==============================================================================
    # \Function: test_read_header
    # \Brief: Reads marker, receiver, antenna, interval, and version from V2
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Interval is seconds.
    #==============================================================================
    def test_read_header(self):
        path = os.path.join(DATA_DIR, 'sample_v2.snippet')
        obs_file, status = C_RinexObsReaderV2().Read(path)

        assert status == eFileReadingStatus.eSuccess
        assert obs_file.header.marker_name == 'TEST'
        assert obs_file.header.marker_number == '0001'
        assert obs_file.header.receiver_type == 'LEICA GR25'
        assert 'LEIAR25.R4' in obs_file.header.antenna_type
        assert obs_file.header.interval == 30.0
        assert abs(obs_file.header.version - 2.11) < 0.01

    #==============================================================================
    # \Function: test_epoch_count
    # \Brief: The version-2 sample contains 3 observation epochs
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_epoch_count(self):
        path = os.path.join(DATA_DIR, 'sample_v2.snippet')
        obs_file, status = C_RinexObsReaderV2().Read(path)
        assert status == eFileReadingStatus.eSuccess
        assert len(obs_file.epochs) == 3

    #==============================================================================
    # \Function: test_satellite_count_per_epoch
    # \Brief: Each version-2 epoch tracks 4 satellites
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_satellite_count_per_epoch(self):
        path = os.path.join(DATA_DIR, 'sample_v2.snippet')
        obs_file, status = C_RinexObsReaderV2().Read(path)
        assert status == eFileReadingStatus.eSuccess
        for epoch in obs_file.epochs:
            assert len(epoch.satellites) == 4
        # END for-loop over epochs

    #==============================================================================
    # \Function: test_satellite_systems
    # \Brief: Every satellite in the version-2 sample is GPS
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_satellite_systems(self):
        path = os.path.join(DATA_DIR, 'sample_v2.snippet')
        obs_file, status = C_RinexObsReaderV2().Read(path)
        assert status == eFileReadingStatus.eSuccess
        for epoch in obs_file.epochs:
            for sat in epoch.satellites:
                assert sat.system == eGnss.eGPS
            # END for-loop over satellites
        # END for-loop over epochs

    #==============================================================================
    # \Function: test_observation_types_present
    # \Brief: The first GPS satellite has C1 and L1 values
    # \Note:
    #   Other descriptors depend on the sample field layout.
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Code is metres, phase is cycles.
    #==============================================================================
    def test_observation_types_present(self):
        path = os.path.join(DATA_DIR, 'sample_v2.snippet')
        obs_file, status = C_RinexObsReaderV2().Read(path)
        assert status == eFileReadingStatus.eSuccess
        first_sat = obs_file.epochs[0].satellites[0]
        assert len(first_sat.obs) > 0
        assert 'C1' in first_sat.obs
        assert 'L1' in first_sat.obs

    #==============================================================================
    # \Function: test_epoch_timestamps
    # \Brief: The first epoch is 2024-07-15 00:00 GPST
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_epoch_timestamps(self):
        path = os.path.join(DATA_DIR, 'sample_v2.snippet')
        obs_file, status = C_RinexObsReaderV2().Read(path)
        assert status == eFileReadingStatus.eSuccess

        e0 = obs_file.epochs[0]
        assert e0.year == 2024
        assert e0.month == 7
        assert e0.day == 15
        assert e0.hour == 0
        assert e0.minute == 0


class TestRinexV3Reader:
    """Tests for RINEX 3.x reader."""

    #==============================================================================
    # \Function: test_read_header
    # \Brief: Reads marker, receiver, interval, and version from V3
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Interval is seconds.
    #==============================================================================
    def test_read_header(self):
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obs_file, status = C_RinexObsReaderV3().Read(path)

        assert status == eFileReadingStatus.eSuccess
        assert obs_file.header.marker_name == 'TEST'
        assert obs_file.header.receiver_type == 'LEICA GR25'
        assert obs_file.header.interval == 30.0
        assert abs(obs_file.header.version - 3.05) < 0.01

    #==============================================================================
    # \Function: test_multi_system_obs_types
    # \Brief: The V3 header lists 6 GPS types and 4 Galileo types
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_multi_system_obs_types(self):
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obs_file, status = C_RinexObsReaderV3().Read(path)
        assert status == eFileReadingStatus.eSuccess

        assert eGnss.eGPS in obs_file.header.obs_types
        assert len(obs_file.header.obs_types[eGnss.eGPS]) == 6

        assert eGnss.eGAL in obs_file.header.obs_types
        assert len(obs_file.header.obs_types[eGnss.eGAL]) == 4

    #==============================================================================
    # \Function: test_epoch_count
    # \Brief: The version-3 sample contains 3 observation epochs
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_epoch_count(self):
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obs_file, status = C_RinexObsReaderV3().Read(path)
        assert status == eFileReadingStatus.eSuccess
        assert len(obs_file.epochs) == 3

    #==============================================================================
    # \Function: test_mixed_constellations
    # \Brief: The version-3 sample contains GPS and Galileo satellites
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_mixed_constellations(self):
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obs_file, status = C_RinexObsReaderV3().Read(path)
        assert status == eFileReadingStatus.eSuccess

        systems = set()
        for epoch in obs_file.epochs:
            for sat in epoch.satellites:
                systems.add(sat.system)
            # END for-loop over satellites
        # END for-loop over epochs

        assert eGnss.eGPS in systems
        assert eGnss.eGAL in systems


class TestUnifiedReader:
    """Tests for the unified auto-detecting reader."""

    #==============================================================================
    # \Function: test_auto_detect_v2
    # \Brief: The unified reader selects the version-2 path and reads 3 epochs
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_auto_detect_v2(self):
        path = os.path.join(DATA_DIR, 'sample_v2.snippet')
        obs_file, status = C_RinexObsReader().Read(path)
        assert status == eFileReadingStatus.eSuccess
        assert obs_file.header.version_enum == eRinexObsVersion.eRinexObsVersion_2
        assert len(obs_file.epochs) == 3

    #==============================================================================
    # \Function: test_auto_detect_v3
    # \Brief: The unified reader selects the version-3 path and reads 3 epochs
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_auto_detect_v3(self):
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obs_file, status = C_RinexObsReader().Read(path)
        assert status == eFileReadingStatus.eSuccess
        assert obs_file.header.version_enum == eRinexObsVersion.eRinexObsVersion_3
        assert len(obs_file.epochs) == 3
