# =============================================================================
# Tests for the cycle-slip plot
# =============================================================================
# The figure is built with a non-interactive backend. No window is opened.
# Time is hours from the first epoch, GPST. Marker shape separates TDCP
# from Melbourne-Wubbena.

import matplotlib
matplotlib.use('Agg')

import os

from AnanseQC.Core.Enums import eFileReadingStatus
from AnanseQC.QualityCheck import AnalyseFile
from AnanseQC.Reports.Plots import C_QcPlots

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


class TestSlipPlot:
    """Cycle-slip markers versus GPST."""

    #==============================================================================
    # \Function: test_axes_are_labelled
    # \Brief: The slip figure names GPST time and the satellite axis
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_axes_are_labelled(self):
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obsFile, results, eStatus = AnalyseFile(path)
        assert eStatus == eFileReadingStatus.eSuccess

        figure = C_QcPlots().PlotSlips(obsFile, results['slips'])
        axes = figure.axes[0]
        assert axes.get_xlabel() == 'Time from first epoch (hours, GPST)'
        assert axes.get_ylabel() == 'Satellite'
        figure.clf()

    #==============================================================================
    # \Function: test_marker_counts_match_events
    # \Brief: TDCP and Melbourne-Wubbena markers match the event counts
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Counts are slip events.
    #==============================================================================
    def test_marker_counts_match_events(self):
        path = os.path.join(DATA_DIR, 'sample_v3_gap.snippet')
        obsFile, results, eStatus = AnalyseFile(path)
        assert eStatus == eFileReadingStatus.eSuccess
        slips = results['slips']

        figure = C_QcPlots().PlotSlips(obsFile, slips)
        axes = figure.axes[0]
        nMarkers = 0
        for collection in axes.collections:
            nMarkers += len(collection.get_offsets())
        assert nMarkers == slips.total_tdcp_slips + slips.total_mw_slips
        if nMarkers == 0:
            notes = [text.get_text() for text in axes.texts]
            assert 'No cycle slips' in notes
        figure.clf()
