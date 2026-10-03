# =============================================================================
# Tests for the satellite availability plot
# =============================================================================
# The figure is built with a non-interactive backend. No window is opened.
# Availability is percent of epochs. Satellite ids use the RINEX system letter.

import matplotlib
matplotlib.use('Agg')

import os

from AnanseQC.Core.Enums import eFileReadingStatus
from AnanseQC.QualityCheck import AnalyseFile
from AnanseQC.Reports.Plots import C_QcPlots

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


class TestAvailabilityPlot:
    """Per-satellite availability as a percent of epochs."""

    #==============================================================================
    # \Function: test_sample_bars
    # \Brief: The version-3 sample draws one bar for each of its five satellites
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Percent is 0-100.
    #==============================================================================
    def test_sample_bars(self):
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obsFile, results, eStatus = AnalyseFile(path)
        assert eStatus == eFileReadingStatus.eSuccess
        assert obsFile is not None

        figure = C_QcPlots().PlotAvailability(results['availability'])
        axes = figure.axes[0]
        assert axes.get_xlabel() == 'Percent of epochs'
        assert axes.get_ylabel() == 'Satellite'
        assert len(axes.patches) == 5
        tickLabels = [tick.get_text() for tick in axes.get_yticklabels()]
        assert 'G01' in tickLabels
        assert 'E01' in tickLabels
        figure.clf()
