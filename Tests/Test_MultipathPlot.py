# =============================================================================
# Tests for the multipath plot
# =============================================================================
# The figure is built with a non-interactive backend. No window is opened.
# MP1 and MP2 RMS are metres.

import matplotlib
matplotlib.use('Agg')

import os

from AnanseQC.Core.Enums import eFileReadingStatus
from AnanseQC.QualityCheck import AnalyseFile
from AnanseQC.Reports.Plots import C_QcPlots

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


class TestMultipathPlot:
    """MP1 and MP2 RMS bars per satellite."""

    #==============================================================================
    # \Function: test_sample_has_mp1_and_mp2
    # \Brief: The version-3 sample draws MP1 and MP2 bars in metres
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. RMS is metres.
    #==============================================================================
    def test_sample_has_mp1_and_mp2(self):
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obsFile, results, eStatus = AnalyseFile(path)
        assert eStatus == eFileReadingStatus.eSuccess
        assert obsFile is not None

        figure = C_QcPlots().PlotMultipath(results['multipathSnr'])
        axes = figure.axes[0]
        assert axes.get_xlabel() == 'RMS (metres)'
        assert axes.get_ylabel() == 'Satellite'
        legend = axes.get_legend()
        assert legend is not None
        legendText = [item.get_text() for item in legend.get_texts()]
        assert 'MP1' in legendText
        assert 'MP2' in legendText
        tickLabels = [tick.get_text() for tick in axes.get_yticklabels()]
        assert 'G01' in tickLabels
        assert len(axes.patches) > 0
        for patch in axes.patches:
            assert patch.get_width() >= 0.0
        figure.clf()
