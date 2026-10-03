# =============================================================================
# Tests for the satellites-versus-time plot
# =============================================================================
# The figure is built with a non-interactive backend. No window is opened.
# Time is hours from the first epoch, GPST. Y values are satellite counts.

import matplotlib
matplotlib.use('Agg')

import os
import tempfile

from AnanseQC.Core.Enums import eFileReadingStatus
from AnanseQC.QualityCheck import AnalyseFile
from AnanseQC.Reports.Plots import C_QcPlots

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


class TestSatellitePlot:
    """Satellites tracked versus GPST."""

    #==============================================================================
    # \Function: test_constellation_lines
    # \Brief: The version-3 sample draws one line for GPS and one for Galileo
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_constellation_lines(self):
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obsFile, results, eStatus = AnalyseFile(path)
        assert eStatus == eFileReadingStatus.eSuccess

        figure = C_QcPlots().PlotSatellites(obsFile, results['availability'])
        axes = figure.axes[0]
        assert axes.get_xlabel() == 'Time from first epoch (hours, GPST)'
        assert axes.get_ylabel() == 'Satellites tracked'
        assert len(axes.lines) == 2
        labels = [line.get_label() for line in axes.lines]
        assert 'eGPS (G)' in labels
        assert 'eGAL (E)' in labels
        figure.clf()

    #==============================================================================
    # \Function: test_save_beside_report
    # \Brief: A report path report.json saves report_satellites.png beside it
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_save_beside_report(self):
        path = os.path.join(DATA_DIR, 'sample_v3.snippet')
        obsFile, results, eStatus = AnalyseFile(path)
        assert eStatus == eFileReadingStatus.eSuccess
        figure = C_QcPlots().PlotSatellites(obsFile, results['availability'])

        with tempfile.TemporaryDirectory() as folder:
            reportPath = os.path.join(folder, 'report.json')
            pngPath = C_QcPlots().SaveBeside(figure, reportPath, 'satellites')
            assert os.path.basename(pngPath) == 'report_satellites.png'
            assert os.path.isfile(pngPath) == True
        figure.clf()
