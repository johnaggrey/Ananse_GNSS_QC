# =============================================================================
# Tests for RINEX Observation File Readers
# =============================================================================

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

    def test_detect_v2(self):
        """Detect RINEX 2.11 version from sample file."""
        path = os.path.join(DATA_DIR, 'sample_v2.snippet')
        version, ver_float, status = C_RinexVersionDetector().Detect(path)
        assert status == eFileReadingStatus.eSuccess
        assert version == eRinexObsVersion.eRinexObsVersion_2
        assert abs(ver_float - 2.11) < 0.01

    def test_detect_v3(self):
        """Detect RINEX 3.05 version from sample file."""
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        version, ver_float, status = C_RinexVersionDetector().Detect(path)
        assert status == eFileReadingStatus.eSuccess
        assert version == eRinexObsVersion.eRinexObsVersion_3
        assert abs(ver_float - 3.05) < 0.01

    def test_nonexistent_file(self):
        """Non-existent file should return FILE_NOT_FOUND."""
        version, _, status = C_RinexVersionDetector().Detect('/nonexistent/file.obs')
        assert status == eFileReadingStatus.eFileNotFound
        assert version == eRinexObsVersion.eRinexObsVersion_Invalid

    def test_empty_path(self):
        """Empty path should return FILE_NOT_FOUND."""
        version, _, status = C_RinexVersionDetector().Detect('')
        assert status == eFileReadingStatus.eFileNotFound


class TestRinexV2Reader:
    """Tests for RINEX 2.x reader."""

    def test_read_header(self):
        """Read RINEX 2.x header fields."""
        path = os.path.join(DATA_DIR, 'sample_v2.snippet')
        obs_file, status = C_RinexObsReaderV2().Read(path)

        assert status == eFileReadingStatus.eSuccess
        assert obs_file.header.marker_name == 'TEST'
        assert obs_file.header.marker_number == '0001'
        assert obs_file.header.receiver_type == 'LEICA GR25'
        assert 'LEIAR25.R4' in obs_file.header.antenna_type
        assert obs_file.header.interval == 30.0
        assert abs(obs_file.header.version - 2.11) < 0.01

    def test_epoch_count(self):
        """Verify correct number of epochs read."""
        path = os.path.join(DATA_DIR, 'sample_v2.snippet')
        obs_file, status = C_RinexObsReaderV2().Read(path)
        assert status == eFileReadingStatus.eSuccess
        assert len(obs_file.epochs) == 3

    def test_satellite_count_per_epoch(self):
        """Verify satellite count in each epoch."""
        path = os.path.join(DATA_DIR, 'sample_v2.snippet')
        obs_file, status = C_RinexObsReaderV2().Read(path)
        assert status == eFileReadingStatus.eSuccess
        for epoch in obs_file.epochs:
            assert len(epoch.satellites) == 4

    def test_satellite_systems(self):
        """All satellites should be GPS in the V2 sample."""
        path = os.path.join(DATA_DIR, 'sample_v2.snippet')
        obs_file, status = C_RinexObsReaderV2().Read(path)
        assert status == eFileReadingStatus.eSuccess
        for epoch in obs_file.epochs:
            for sat in epoch.satellites:
                assert sat.system == eGnss.eGPS

    def test_observation_types_present(self):
        """Check that expected observation types are present."""
        path = os.path.join(DATA_DIR, 'sample_v2.snippet')
        obs_file, status = C_RinexObsReaderV2().Read(path)
        assert status == eFileReadingStatus.eSuccess
        first_sat = obs_file.epochs[0].satellites[0]
        # Should have at least C1 and L1 parsed (exact obs depends on formatting)
        assert len(first_sat.obs) > 0
        assert 'C1' in first_sat.obs
        assert 'L1' in first_sat.obs

    def test_epoch_timestamps(self):
        """Verify epoch timestamps are parsed correctly."""
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

    def test_read_header(self):
        """Read RINEX 3.x header fields."""
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obs_file, status = C_RinexObsReaderV3().Read(path)

        assert status == eFileReadingStatus.eSuccess
        assert obs_file.header.marker_name == 'TEST'
        assert obs_file.header.receiver_type == 'LEICA GR25'
        assert obs_file.header.interval == 30.0
        assert abs(obs_file.header.version - 3.05) < 0.01

    def test_multi_system_obs_types(self):
        """Verify per-system observation types from header."""
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obs_file, status = C_RinexObsReaderV3().Read(path)
        assert status == eFileReadingStatus.eSuccess

        # GPS should have 6 obs types
        assert eGnss.eGPS in obs_file.header.obs_types
        assert len(obs_file.header.obs_types[eGnss.eGPS]) == 6

        # Galileo should have 4 obs types
        assert eGnss.eGAL in obs_file.header.obs_types
        assert len(obs_file.header.obs_types[eGnss.eGAL]) == 4

    def test_epoch_count(self):
        """Verify correct number of epochs read."""
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obs_file, status = C_RinexObsReaderV3().Read(path)
        assert status == eFileReadingStatus.eSuccess
        assert len(obs_file.epochs) == 3

    def test_mixed_constellations(self):
        """Verify both GPS and Galileo satellites are present."""
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obs_file, status = C_RinexObsReaderV3().Read(path)
        assert status == eFileReadingStatus.eSuccess

        systems = set()
        for epoch in obs_file.epochs:
            for sat in epoch.satellites:
                systems.add(sat.system)

        assert eGnss.eGPS in systems
        assert eGnss.eGAL in systems


class TestUnifiedReader:
    """Tests for the unified auto-detecting reader."""

    def test_auto_detect_v2(self):
        """Auto-detect and read RINEX 2.x file."""
        path = os.path.join(DATA_DIR, 'sample_v2.snippet')
        obs_file, status = C_RinexObsReader().Read(path)
        assert status == eFileReadingStatus.eSuccess
        assert obs_file.header.version_enum == eRinexObsVersion.eRinexObsVersion_2
        assert len(obs_file.epochs) == 3

    def test_auto_detect_v3(self):
        """Auto-detect and read RINEX 3.x file."""
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obs_file, status = C_RinexObsReader().Read(path)
        assert status == eFileReadingStatus.eSuccess
        assert obs_file.header.version_enum == eRinexObsVersion.eRinexObsVersion_3
        assert len(obs_file.epochs) == 3
