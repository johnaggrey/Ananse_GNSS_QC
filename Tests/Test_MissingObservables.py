# =============================================================================
# Tests for missing observation types versus the RINEX header
# =============================================================================

import os

from AnanseQC.Core.Enums import eFileReadingStatus, eGnss
from AnanseQC.QualityChecks.MissingObservables import C_MissingObservables
from AnanseQC.Readers.Reader import C_RinexObsReader

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def _load_v3_file():
    path = os.path.join(DATA_DIR, 'sample_v3.snippet')
    obsFile, eStatus = C_RinexObsReader().Read(path)
    assert eStatus == eFileReadingStatus.eSuccess
    return obsFile


def _gap_for(satResult, obsType):
    for typeGap in satResult.missing_types:
        if typeGap.obs_type == obsType:
            return typeGap
    return None


class TestMissingObservables:
    """Header observation types compared with the observation body."""

    def test_complete_sample_has_no_missing_types(self):
        """The V3 snippet carries every type declared in its header."""
        result = C_MissingObservables().Analyse(_load_v3_file())
        assert len(result.satellites) == 0
        assert len(result.absent_header_types) == 0
        assert result.total_missing_records == 0

    def test_header_type_never_present(self):
        """A declared GPS type removed from every epoch is fully absent."""
        obsFile = _load_v3_file()
        for epoch in obsFile.epochs:
            for satObs in epoch.satellites:
                if satObs.system == eGnss.eGPS and 'S2W' in satObs.obs:
                    del satObs.obs['S2W']
            # END for-loop over satellites
        # END for-loop over epochs

        result = C_MissingObservables().Analyse(obsFile)

        assert 'S2W' in result.absent_header_types[eGnss.eGPS]
        satResult = result.satellites[(eGnss.eGPS, 1)]
        typeGap = _gap_for(satResult, 'S2W')
        assert typeGap is not None
        assert typeGap.epochs_present == 0
        assert typeGap.epochs_missing == 3
        assert typeGap.missing_percent == 100.0
        assert (eGnss.eGAL, 1) not in result.satellites

    def test_partial_missing_percent(self):
        """One missing epoch out of three is about 33.3 percent."""
        obsFile = _load_v3_file()
        bRemoved = False
        for epoch in obsFile.epochs:
            if bRemoved == True:
                break
            for satObs in epoch.satellites:
                if satObs.system == eGnss.eGPS and satObs.prn == 1:
                    del satObs.obs['S2W']
                    bRemoved = True
                    break
            # END for-loop over satellites
        # END for-loop over epochs

        assert bRemoved == True
        result = C_MissingObservables().Analyse(obsFile)
        assert eGnss.eGPS not in result.absent_header_types

        satResult = result.satellites[(eGnss.eGPS, 1)]
        typeGap = _gap_for(satResult, 'S2W')
        assert typeGap.epochs_present == 2
        assert typeGap.epochs_missing == 1
        assert abs(typeGap.missing_percent - (100.0 / 3.0)) < 0.001
