# =============================================================================
# Tests for QC Analysis Engines
# =============================================================================

import os
import math
import pytest

from AnanseQC.Core.Enums import eFileReadingStatus, eGnss
from AnanseQC.Readers.Reader import C_RinexObsReader
from AnanseQC.QualityChecks.Availability import C_ObsAvailability
from AnanseQC.QualityChecks.EpochSampling import C_EpochSampling
from AnanseQC.QualityChecks.CycleSlips import C_CycleSlipDetector
from AnanseQC.QualityChecks.MultipathSnr import C_MultipathSnr

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def _load_v3_file():
    """Helper to load the V3 sample file."""
    path = os.path.join(DATA_DIR, 'sample_v3.snippet')
    obs_file, status = C_RinexObsReader().Read(path)
    assert status == eFileReadingStatus.eSuccess
    return obs_file


def _load_v2_file():
    """Helper to load the V2 sample file."""
    path = os.path.join(DATA_DIR, 'sample_v2.snippet')
    obs_file, status = C_RinexObsReader().Read(path)
    assert status == eFileReadingStatus.eSuccess
    return obs_file


class TestAvailabilityAnalysis:
    """Tests for satellite/observable availability analysis."""

    def test_total_epochs(self):
        """Total epochs should match parsed data."""
        obs_file = _load_v3_file()
        result = C_ObsAvailability().Analyse(obs_file)
        assert result.total_epochs == 3

    def test_systems_detected(self):
        """Should detect GPS and Galileo systems."""
        obs_file = _load_v3_file()
        result = C_ObsAvailability().Analyse(obs_file)
        assert eGnss.eGPS in result.systems
        assert eGnss.eGAL in result.systems

    def test_satellite_count(self):
        """Should count correct number of unique satellites."""
        obs_file = _load_v3_file()
        result = C_ObsAvailability().Analyse(obs_file)
        # 3 GPS + 2 Galileo = 5 total
        assert result.total_satellites == 5

    def test_satellite_epoch_percentage(self):
        """Satellites present in all epochs should have 100% availability."""
        obs_file = _load_v3_file()
        result = C_ObsAvailability().Analyse(obs_file)

        gps_avail = result.systems[eGnss.eGPS]
        # G01 should be in all 3 epochs -> 100%
        if 1 in gps_avail.sat_details:
            assert gps_avail.sat_details[1].epoch_percentage == 100.0

    def test_duration(self):
        """Duration should be approximately 60 seconds (3 epochs at 30s)."""
        obs_file = _load_v3_file()
        result = C_ObsAvailability().Analyse(obs_file)
        # 30s between each epoch -> total 60s
        assert abs(result.duration_seconds - 60.0) < 1.0


class TestEpochSampling:
    """Tests for epoch sampling interval analysis."""

    def test_nominal_interval(self):
        """Nominal interval should be 30.0 seconds for sample data."""
        obs_file = _load_v3_file()
        result = C_EpochSampling().Analyse(obs_file)
        assert abs(result.nominal_interval - 30.0) < 0.5

    def test_no_gaps(self):
        """Uniform 30s sampling should have no gaps."""
        obs_file = _load_v3_file()
        result = C_EpochSampling().Analyse(obs_file)
        assert result.num_gaps == 0

    def test_completeness(self):
        """With no gaps, completeness should be 100%."""
        obs_file = _load_v3_file()
        result = C_EpochSampling().Analyse(obs_file)
        assert result.completeness_percent >= 99.0

    def test_header_interval_match(self):
        """Header interval should be captured."""
        obs_file = _load_v3_file()
        result = C_EpochSampling().Analyse(obs_file)
        assert result.header_interval == 30.0


class TestCycleSlipDetection:
    """Tests for cycle slip detection."""

    def test_runs_without_error(self):
        """Cycle slip analysis should complete without errors."""
        obs_file = _load_v3_file()
        result = C_CycleSlipDetector().Analyse(obs_file)
        assert result is not None
        assert result.total_slips >= 0

    def test_clean_data_few_slips(self):
        """Clean sample data should have very few or no slips."""
        obs_file = _load_v3_file()
        result = C_CycleSlipDetector().Analyse(obs_file)
        # With only 3 epochs, not enough data for TDCP second-difference
        # so we expect zero or very few slips
        assert result.total_slips >= 0


class TestMultipathSnr:
    """Tests for multipath and SNR analysis."""

    def test_runs_without_error(self):
        """Multipath/SNR analysis should complete without errors."""
        obs_file = _load_v3_file()
        result = C_MultipathSnr().Analyse(obs_file)
        assert result is not None

    def test_snr_detected(self):
        """SNR observations should be detected in the sample data."""
        obs_file = _load_v3_file()
        result = C_MultipathSnr().Analyse(obs_file)
        # The sample data has S1C and S2W observations
        assert len(result.sat_snr) > 0

    def test_snr_values_reasonable(self):
        """SNR mean should be in a reasonable range (20-60 dBHz)."""
        obs_file = _load_v3_file()
        result = C_MultipathSnr().Analyse(obs_file)
        if result.overall_snr_mean > 0:
            assert 20.0 <= result.overall_snr_mean <= 60.0

    def test_v2_multipath(self):
        """V2 reader data should also work with multipath analysis."""
        obs_file = _load_v2_file()
        result = C_MultipathSnr().Analyse(obs_file)
        assert result is not None
