# =============================================================================
# Tests for missing observation types versus the RINEX header
# =============================================================================
# Missing counts are epochs. Missing percent is 0-100 of the satellite's
# tracked epochs. Time stays GPST on the parsed epochs.

import os

from AnanseQC.Core.Enums import eFileReadingStatus, eGnss
from AnanseQC.QualityChecks.MissingObservables import C_MissingObservables
from AnanseQC.Readers.Reader import C_RinexObsReader

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


#==============================================================================
# \Function: _load_v3_file
# \Brief: Loads the RINEX 3 sample used as a complete observation file
# \Params:
#           None
# \Returns:
#           S_RinexObsFile  Parsed file. Reading must succeed.
#==============================================================================
def _load_v3_file():
    path = os.path.join(DATA_DIR, 'sample_v3.snippet')
    obsFile, eStatus = C_RinexObsReader().Read(path)
    assert eStatus == eFileReadingStatus.eSuccess
    return obsFile


#==============================================================================
# \Function: _gap_for
# \Brief: Returns the missing-type row for one observation descriptor
# \Params:
#           satResult       [in]    S_SatMissingObs for one satellite
#           obsType         [in]    RINEX descriptor, for example S2W
# \Returns:
#           S_ObsTypeGap or None
#==============================================================================
def _gap_for(satResult, obsType):
    for typeGap in satResult.missing_types:
        if typeGap.obs_type == obsType:
            return typeGap
    return None


class TestMissingObservables:
    """Header observation types compared with the observation body."""

    #==============================================================================
    # \Function: test_complete_sample_has_no_missing_types
    # \Brief: The version-3 sample has every header type in the body
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_complete_sample_has_no_missing_types(self):
        result = C_MissingObservables().Analyse(_load_v3_file())
        assert len(result.satellites) == 0
        assert len(result.absent_header_types) == 0
        assert result.total_missing_records == 0

    #==============================================================================
    # \Function: test_header_type_never_present
    # \Brief: S2W removed from every GPS epoch is fully absent
    # \Note:
    #   Galileo does not declare S2W, so E01 is not reported.
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Missing percent is 0-100.
    #==============================================================================
    def test_header_type_never_present(self):
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

    #==============================================================================
    # \Function: test_partial_missing_percent
    # \Brief: One missing S2W epoch out of three is about 33.3 percent
    # \Note:
    #   The type is still observed on other epochs, so it is not an absent
    #   header type.
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Counts are epochs.
    #==============================================================================
    def test_partial_missing_percent(self):
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
