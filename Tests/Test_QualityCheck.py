# =============================================================================
# Tests for the single-call QC entry point used by a web application
# =============================================================================
# RunQualityCheck returns a JSON report, a text report, and eFileReadingStatus.
# Times in the report are GPST. Positions are ECEF metres. SNR is dB-Hz.

import os

from AnanseQC.Core.Enums import eFileReadingStatus
from AnanseQC.QualityCheck import RunQualityCheck
from AnanseQC.Reports.QualityCheckReport import SCHEMA_VERSION

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


class TestRunQualityCheck:
    """RunQualityCheck returns a versioned JSON report and a text report."""

    #==============================================================================
    # \Function: test_sample_report_keys
    # \Brief: A readable file returns the sections a web client needs
    # \Note:
    #   schema_version is the response contract. The complete sample has no
    #   missing observables.
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_sample_report_keys(self):
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        reportDict, textReport, eStatus = RunQualityCheck(path)

        assert eStatus == eFileReadingStatus.eSuccess
        assert reportDict['schema_version'] == SCHEMA_VERSION
        assert 'ANANSE GNSS QC REPORT' in textReport
        assert 'MISSING OBSERVABLES' in textReport

        expectedKeys = (
            'schema_version',
            'version',
            'file_info',
            'availability',
            'missing_observables',
            'epoch_sampling',
            'cycle_slips',
            'multipath_snr',
        )
        for key in expectedKeys:
            assert key in reportDict

        assert reportDict['file_info']['marker_name'] == 'TEST'
        assert reportDict['availability']['total_epochs'] == 3
        assert reportDict['missing_observables']['satellites'] == []

    #==============================================================================
    # \Function: test_missing_file
    # \Brief: A missing path returns an empty report and file-not-found
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_missing_file(self):
        reportDict, textReport, eStatus = RunQualityCheck(
            os.path.join(DATA_DIR, 'does_not_exist.rnx')
        )
        assert eStatus == eFileReadingStatus.eFileNotFound
        assert reportDict == {}
        assert textReport == ''
