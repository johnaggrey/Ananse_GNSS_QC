# =============================================================================
# Tests for the missing-observable plot
# =============================================================================
# The figure is built with a non-interactive backend. No window is opened.
# Missing percent is 0-100 of that satellite's tracked epochs.

import matplotlib
matplotlib.use('Agg')

import os

from AnanseQC.Core.Enums import eFileReadingStatus, eGnss
from AnanseQC.QualityCheck import AnalyseFile
from AnanseQC.QualityChecks.MissingObservables import C_MissingObservables
from AnanseQC.Reports.Plots import C_QcPlots

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


class TestMissingPlot:
    """Missing header types as a percent of tracked epochs."""

    #==============================================================================
    # \Function: test_complete_sample_has_no_bars
    # \Brief: The complete version-3 sample draws axes and no missing-type bars
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_complete_sample_has_no_bars(self):
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obsFile, results, eStatus = AnalyseFile(path)
        assert eStatus == eFileReadingStatus.eSuccess
        assert obsFile is not None

        figure = C_QcPlots().PlotMissing(results['missingObs'])
        axes = figure.axes[0]
        assert axes.get_xlabel() == 'Percent of tracked epochs'
        assert len(axes.patches) == 0
        figure.clf()

    #==============================================================================
    # \Function: test_removed_type_is_fully_missing
    # \Brief: S2W removed from every GPS epoch is a bar at 100 percent
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Percent is 0-100.
    #==============================================================================
    def test_removed_type_is_fully_missing(self):
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obsFile, results, eStatus = AnalyseFile(path)
        assert eStatus == eFileReadingStatus.eSuccess

        for epoch in obsFile.epochs:
            for satObs in epoch.satellites:
                if satObs.system == eGnss.eGPS and 'S2W' in satObs.obs:
                    del satObs.obs['S2W']
            # END for-loop over satellites
        # END for-loop over epochs

        missingObs = C_MissingObservables().Analyse(obsFile)
        figure = C_QcPlots().PlotMissing(missingObs)
        axes = figure.axes[0]
        tickLabels = [tick.get_text() for tick in axes.get_yticklabels()]
        assert 'G01 S2W' in tickLabels
        assert len(axes.patches) == 3
        for patch in axes.patches:
            assert abs(patch.get_width() - 100.0) < 0.01
        figure.clf()
