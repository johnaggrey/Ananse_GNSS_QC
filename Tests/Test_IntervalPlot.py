# =============================================================================
# Tests for the epoch-interval and gap plot
# =============================================================================
# The figure is built with a non-interactive backend. No window is opened.
# Intervals are seconds. Time is hours from the first epoch, GPST.
# sample_v3_gap.snippet has one 90 s gap and a 30 s nominal interval.

import matplotlib
matplotlib.use('Agg')

import os

from AnanseQC.Core.Enums import eFileReadingStatus
from AnanseQC.QualityCheck import AnalyseFile
from AnanseQC.Reports.Plots import C_QcPlots

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


class TestIntervalPlot:
    """Inter-epoch interval versus GPST, with gaps marked."""

    #==============================================================================
    # \Function: test_uniform_sample_has_no_gap_markers
    # \Brief: The uniform 30 s sample draws the interval line and no gap markers
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Interval is seconds.
    #==============================================================================
    def test_uniform_sample_has_no_gap_markers(self):
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obsFile, results, eStatus = AnalyseFile(path)
        assert eStatus == eFileReadingStatus.eSuccess

        figure = C_QcPlots().PlotIntervals(obsFile, results['sampling'])
        axes = figure.axes[0]
        assert axes.get_ylabel() == 'Interval (seconds)'
        assert axes.get_xlabel() == 'Time from first epoch (hours, GPST)'
        assert len(axes.lines) >= 1
        assert len(axes.collections) == 0
        figure.clf()

    #==============================================================================
    # \Function: test_gap_file_marks_one_gap
    # \Brief: The gapped sample marks one gap and draws the 30 s nominal line
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Gap duration is seconds.
    #==============================================================================
    def test_gap_file_marks_one_gap(self):
        path = os.path.join(DATA_DIR, 'sample_v3_gap.snippet')
        obsFile, results, eStatus = AnalyseFile(path)
        assert eStatus == eFileReadingStatus.eSuccess

        figure = C_QcPlots().PlotIntervals(obsFile, results['sampling'])
        axes = figure.axes[0]
        assert len(axes.collections) == 1
        gapPoints = axes.collections[0].get_offsets()
        assert len(gapPoints) == 1
        assert abs(gapPoints[0][1] - 90.0) < 0.05
        figure.clf()
