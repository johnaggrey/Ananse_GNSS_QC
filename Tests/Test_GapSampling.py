# =============================================================================
# Tests for observation span, gaps, and completeness
# =============================================================================
# sample_v3_gap.snippet is the V3 sample with the third epoch moved from
# 00:01:00 to 00:02:00 GPST. Header interval is 30 s.
# Span is 120 s. The 90 s step is one gap of two missing epochs.
# Expected epochs over that span: 5. Observed epochs: 3. Completeness: 60%.

import os

from AnanseQC.Core.Enums import eFileReadingStatus
from AnanseQC.QualityChecks.Availability import C_ObsAvailability
from AnanseQC.QualityChecks.EpochSampling import C_EpochSampling
from AnanseQC.Readers.Reader import C_RinexObsReader

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def _load_gap_file():
    path = os.path.join(DATA_DIR, 'sample_v3_gap.snippet')
    obsFile, eStatus = C_RinexObsReader().Read(path)
    assert eStatus == eFileReadingStatus.eSuccess
    return obsFile


class TestGapSampling:
    """Duration and gap figures for a file with one known interval break."""

    def test_duration_seconds(self):
        """Span from the first epoch to the last epoch is 120 seconds."""
        obsFile = _load_gap_file()
        availability = C_ObsAvailability().Analyse(obsFile)
        sampling = C_EpochSampling().Analyse(obsFile)
        assert abs(availability.duration_seconds - 120.0) < 0.01
        assert abs(sampling.duration_seconds - 120.0) < 0.01

    def test_nominal_interval(self):
        """Nominal interval stays 30 seconds from the header and the short step."""
        sampling = C_EpochSampling().Analyse(_load_gap_file())
        assert abs(sampling.nominal_interval - 30.0) < 0.01
        assert abs(sampling.header_interval - 30.0) < 0.01

    def test_gap_and_completeness(self):
        """One 90 second gap removes two epochs and leaves 60 percent completeness."""
        sampling = C_EpochSampling().Analyse(_load_gap_file())
        assert sampling.total_epochs == 3
        assert sampling.expected_epochs == 5
        assert sampling.missing_epochs == 2
        assert abs(sampling.completeness_percent - 60.0) < 0.01
        assert sampling.num_gaps == 1
        assert abs(sampling.gaps[0].duration_seconds - 90.0) < 0.01
        assert sampling.gaps[0].missing_epochs == 2
        assert abs(sampling.total_gap_duration - 90.0) < 0.01
