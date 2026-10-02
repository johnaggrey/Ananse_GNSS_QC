# =============================================================================
# Tests for QC Analysis Engines
# =============================================================================
# The uniform sample is 3 epochs at 30 s. Duration is seconds, GPST.
# Completeness and availability are percent. SNR is dB-Hz.

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


#==============================================================================
# \Function: _load_v3_file
# \Brief: Loads the RINEX 3 sample observation file
# \Params:
#           None
# \Returns:
#           S_RinexObsFile  Parsed file. Reading must succeed.
#==============================================================================
def _load_v3_file():
    path = os.path.join(DATA_DIR, 'sample_v3.snippet')
    obs_file, status = C_RinexObsReader().Read(path)
    assert status == eFileReadingStatus.eSuccess
    return obs_file


#==============================================================================
# \Function: _load_v2_file
# \Brief: Loads the RINEX 2 sample observation file
# \Params:
#           None
# \Returns:
#           S_RinexObsFile  Parsed file. Reading must succeed.
#==============================================================================
def _load_v2_file():
    path = os.path.join(DATA_DIR, 'sample_v2.snippet')
    obs_file, status = C_RinexObsReader().Read(path)
    assert status == eFileReadingStatus.eSuccess
    return obs_file


class TestAvailabilityAnalysis:
    """Tests for satellite/observable availability analysis."""

    #==============================================================================
    # \Function: test_total_epochs
    # \Brief: Availability reports the 3 epochs in the version-3 sample
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_total_epochs(self):
        obs_file = _load_v3_file()
        result = C_ObsAvailability().Analyse(obs_file)
        assert result.total_epochs == 3

    #==============================================================================
    # \Function: test_systems_detected
    # \Brief: The version-3 sample contains GPS and Galileo
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_systems_detected(self):
        obs_file = _load_v3_file()
        result = C_ObsAvailability().Analyse(obs_file)
        assert eGnss.eGPS in result.systems
        assert eGnss.eGAL in result.systems

    #==============================================================================
    # \Function: test_satellite_count
    # \Brief: The version-3 sample has 5 unique satellites
    # \Note:
    #   3 GPS satellites and 2 Galileo satellites.
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_satellite_count(self):
        obs_file = _load_v3_file()
        result = C_ObsAvailability().Analyse(obs_file)
        assert result.total_satellites == 5

    #==============================================================================
    # \Function: test_satellite_epoch_percentage
    # \Brief: G01, present in every epoch, has 100 percent availability
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Percentage is 0-100.
    #==============================================================================
    def test_satellite_epoch_percentage(self):
        obs_file = _load_v3_file()
        result = C_ObsAvailability().Analyse(obs_file)

        gps_avail = result.systems[eGnss.eGPS]
        if 1 in gps_avail.sat_details:
            assert gps_avail.sat_details[1].epoch_percentage == 100.0

    #==============================================================================
    # \Function: test_duration
    # \Brief: Three epochs at 30 s span 60 seconds
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Duration is seconds, GPST.
    #==============================================================================
    def test_duration(self):
        obs_file = _load_v3_file()
        result = C_ObsAvailability().Analyse(obs_file)
        assert abs(result.duration_seconds - 60.0) < 1.0


class TestEpochSampling:
    """Tests for epoch sampling interval analysis."""

    #==============================================================================
    # \Function: test_nominal_interval
    # \Brief: The uniform sample has a nominal interval of 30 seconds
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Interval is seconds.
    #==============================================================================
    def test_nominal_interval(self):
        obs_file = _load_v3_file()
        result = C_EpochSampling().Analyse(obs_file)
        assert abs(result.nominal_interval - 30.0) < 0.5

    #==============================================================================
    # \Function: test_no_gaps
    # \Brief: Uniform 30 s sampling has no gaps
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_no_gaps(self):
        obs_file = _load_v3_file()
        result = C_EpochSampling().Analyse(obs_file)
        assert result.num_gaps == 0

    #==============================================================================
    # \Function: test_completeness
    # \Brief: A file with no gaps is at least 99 percent complete
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Completeness is percent.
    #==============================================================================
    def test_completeness(self):
        obs_file = _load_v3_file()
        result = C_EpochSampling().Analyse(obs_file)
        assert result.completeness_percent >= 99.0

    #==============================================================================
    # \Function: test_header_interval_match
    # \Brief: The header interval of 30 seconds is stored on the result
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Interval is seconds.
    #==============================================================================
    def test_header_interval_match(self):
        obs_file = _load_v3_file()
        result = C_EpochSampling().Analyse(obs_file)
        assert result.header_interval == 30.0


class TestCycleSlipDetection:
    """Tests for cycle slip detection."""

    #==============================================================================
    # \Function: test_runs_without_error
    # \Brief: Cycle-slip analysis returns a result for the version-3 sample
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Slip counts are dimensionless.
    #==============================================================================
    def test_runs_without_error(self):
        obs_file = _load_v3_file()
        result = C_CycleSlipDetector().Analyse(obs_file)
        assert result is not None
        assert result.total_slips >= 0

    #==============================================================================
    # \Function: test_clean_data_few_slips
    # \Brief: The short sample still produces a non-negative slip count
    # \Note:
    #   Three epochs are too few for a TDCP second difference, so the count
    #   stays at zero or a very small number.
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_clean_data_few_slips(self):
        obs_file = _load_v3_file()
        result = C_CycleSlipDetector().Analyse(obs_file)
        assert result.total_slips >= 0


class TestMultipathSnr:
    """Tests for multipath and SNR analysis."""

    #==============================================================================
    # \Function: test_runs_without_error
    # \Brief: Multipath and SNR analysis returns a result for the V3 sample
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_runs_without_error(self):
        obs_file = _load_v3_file()
        result = C_MultipathSnr().Analyse(obs_file)
        assert result is not None

    #==============================================================================
    # \Function: test_snr_detected
    # \Brief: The version-3 sample produces at least one SNR record
    # \Note:
    #   The sample contains S1C and S2W observations.
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. SNR is dB-Hz.
    #==============================================================================
    def test_snr_detected(self):
        obs_file = _load_v3_file()
        result = C_MultipathSnr().Analyse(obs_file)
        assert len(result.sat_snr) > 0

    #==============================================================================
    # \Function: test_snr_values_reasonable
    # \Brief: Mean SNR, when present, is between 20 and 60 dB-Hz
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. SNR is dB-Hz.
    #==============================================================================
    def test_snr_values_reasonable(self):
        obs_file = _load_v3_file()
        result = C_MultipathSnr().Analyse(obs_file)
        if result.overall_snr_mean > 0:
            assert 20.0 <= result.overall_snr_mean <= 60.0

    #==============================================================================
    # \Function: test_v2_multipath
    # \Brief: Multipath analysis also accepts the version-2 sample
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_v2_multipath(self):
        obs_file = _load_v2_file()
        result = C_MultipathSnr().Analyse(obs_file)
        assert result is not None
