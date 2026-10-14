# =============================================================================
# Tests for the sky plot
# =============================================================================
# The figure is built with a non-interactive backend. No window is opened.
# North is at the top. Azimuth increases clockwise. Radius is 90 degrees
# minus elevation, so a satellite overhead is at the centre.
# The receiver is ECEF metres on the WGS84 equator at longitude 0.
# The epoch is absolute GPST seconds.

import matplotlib
matplotlib.use('Agg')

import math
import os

from AnanseQC.CommandLineInterface import C_QcCommand
from AnanseQC.Core import Constants
from AnanseQC.Core.Enums import eGnss
from AnanseQC.Readers.NavTypes import S_KeplerEph
from AnanseQC.Readers.ObsTypes import S_EpochRecord, S_RinexObsFile, S_SatObs
from AnanseQC.Reports.Plots import C_QcPlots

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# GPS week 2323 starts here, so toe seconds-of-week are 0.
TOE_GPST = 1404950400.0
SEMI_MAJOR = 26560000.0


def _OverheadFile():
    obsFile = S_RinexObsFile()
    obsFile.header.approx_position = (Constants.WGS84_A, 0.0, 0.0)

    epoch = S_EpochRecord()
    epoch.abs_gps_time = TOE_GPST
    epoch.epoch_flag = 0

    tracked = S_SatObs()
    tracked.system = eGnss.eGPS
    tracked.prn = 1
    epoch.satellites.append(tracked)

    # No ephemeris for this satellite, so it must not appear on the plot.
    omitted = S_SatObs()
    omitted.system = eGnss.eGPS
    omitted.prn = 2
    epoch.satellites.append(omitted)

    obsFile.epochs.append(epoch)
    return obsFile


def _EquatorialEph():
    eph = S_KeplerEph()
    eph.system = eGnss.eGPS
    eph.prn = 1
    eph.toe_gpst = TOE_GPST
    eph.toc_gpst = TOE_GPST
    eph.sqrt_a = math.sqrt(SEMI_MAJOR)
    eph.health = 0
    return eph


class TestSkyPlot:
    """Polar sky plot of azimuth and elevation."""

    #==============================================================================
    # \Function: test_overhead_satellite_is_near_the_centre
    # \Brief: North is up, azimuth is clockwise, and an overhead satellite is central
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Elevation is degrees.
    #==============================================================================
    def test_overhead_satellite_is_near_the_centre(self):
        figure = C_QcPlots().PlotSky(_OverheadFile(), [_EquatorialEph()])
        axes = figure.axes[0]
        assert axes.name == 'polar'
        assert axes.get_theta_direction() == -1
        assert abs(axes.get_theta_offset() - (math.pi * 0.5)) < 1.0e-6
        assert len(axes.collections) == 1
        offsets = axes.collections[0].get_offsets()
        assert len(offsets) == 1
        assert abs(float(offsets[0][1])) < 1.0
        labels = [text.get_text() for text in axes.get_legend().get_texts()]
        assert 'eGPS (G)' in labels
        figure.clf()

    #==============================================================================
    # \Function: test_failed_nav_does_not_plot
    # \Brief: A navigation path that cannot be read fails the run
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. No window is opened.
    #==============================================================================
    def test_failed_nav_does_not_plot(self):
        obsPath = os.path.join(DATA_DIR, 'sample_v3.snippet')
        exitCode = C_QcCommand().Run(
            filePath=obsPath,
            navPath=os.path.join(DATA_DIR, 'missing_nav.rnx'),
        )
        assert exitCode == 1
