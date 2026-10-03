# =============================================================================
# Tests for the SNR plot
# =============================================================================
# The figure is built with a non-interactive backend. No window is opened.
# Mean SNR is dB-Hz. The fair boundary is 25 dB-Hz. The good boundary is
# 35 dB-Hz.

import matplotlib
matplotlib.use('Agg')

import os

from AnanseQC.Core.Enums import eFileReadingStatus
from AnanseQC.QualityCheck import AnalyseFile
from AnanseQC.Reports.Plots import C_QcPlots

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


class TestSnrPlot:
    """Mean SNR per satellite, with the class boundaries."""

    #==============================================================================
    # \Function: test_sample_draws_boundaries
    # \Brief: The version-3 sample draws SNR bars and the 25 and 35 dB-Hz lines
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. SNR is dB-Hz.
    #==============================================================================
    def test_sample_draws_boundaries(self):
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obsFile, results, eStatus = AnalyseFile(path)
        assert eStatus == eFileReadingStatus.eSuccess
        assert obsFile is not None

        figure = C_QcPlots().PlotSnr(results['multipathSnr'])
        axes = figure.axes[0]
        assert axes.get_xlabel() == 'Mean SNR (dB-Hz)'
        assert axes.get_ylabel() == 'Satellite'
        lineValues = []
        for line in axes.lines:
            xData = line.get_xdata()
            if len(xData) > 0:
                lineValues.append(float(xData[0]))
        assert 25.0 in lineValues
        assert 35.0 in lineValues
        tickLabels = [tick.get_text() for tick in axes.get_yticklabels()]
        assert 'G01' in tickLabels
        assert len(axes.patches) > 0
        figure.clf()
