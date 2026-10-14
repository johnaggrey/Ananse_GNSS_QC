# =============================================================================
# Tests for elevation-binned SNR
# =============================================================================
# The figure is built with a non-interactive backend. No window is opened.
# The receiver is ECEF metres on the WGS84 equator at longitude 0.
# Epoch times are absolute GPST seconds.
# SNR values are dB-Hz. Elevation bins are 10 degrees wide from 0 to 90.
# An equatorial GPS broadcast orbit is overhead at the ephemeris epoch and
# near 45 degrees of elevation 8400 seconds later.

import matplotlib
matplotlib.use('Agg')

import math

from AnanseQC.Core import Constants
from AnanseQC.Core.Enums import eGnss
from AnanseQC.QualityChecks.ElevationSnr import C_ElevationSnr
from AnanseQC.Readers.NavTypes import S_KeplerEph
from AnanseQC.Readers.ObsTypes import S_EpochRecord, S_RinexObsFile, S_SatObs
from AnanseQC.Reports.Plots import C_QcPlots

# GPS week 2323 starts here, so toe seconds-of-week are 0.
TOE_GPST = 1404950400.0
SEMI_MAJOR = 26560000.0

# Elapsed seconds that place the equatorial satellite near 45 degrees.
MID_ELEVATION_OFFSET = 8400.0

# 40-50 degree bin and 80-90 degree bin.
MID_BIN = 4
ZENITH_BIN = 8


def _PassFile():
    obsFile = S_RinexObsFile()
    obsFile.header.approx_position = (Constants.WGS84_A, 0.0, 0.0)

    overhead = S_EpochRecord()
    overhead.abs_gps_time = TOE_GPST
    overhead.epoch_flag = 0
    tracked = S_SatObs()
    tracked.system = eGnss.eGPS
    tracked.prn = 1
    tracked.obs['S1C'] = 40.0
    tracked.obs['S2W'] = 20.0
    tracked.obs['C1C'] = 22000000.0
    overhead.satellites.append(tracked)
    omitted = S_SatObs()
    omitted.system = eGnss.eGPS
    omitted.prn = 2
    omitted.obs['S1C'] = 50.0
    overhead.satellites.append(omitted)
    obsFile.epochs.append(overhead)

    mid = S_EpochRecord()
    mid.abs_gps_time = TOE_GPST + MID_ELEVATION_OFFSET
    mid.epoch_flag = 0
    lower = S_SatObs()
    lower.system = eGnss.eGPS
    lower.prn = 1
    lower.obs['S1C'] = 44.0
    mid.satellites.append(lower)
    obsFile.epochs.append(mid)
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


class TestElevationSnr:
    """Mean SNR in 10-degree elevation bins."""

    #==============================================================================
    # \Function: test_two_bins_hold_count_weighted_means
    # \Brief: Two S* samples average in the zenith bin, and one sample fills 40-50
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Means are dB-Hz. Elevation is degrees.
    #==============================================================================
    def test_two_bins_hold_count_weighted_means(self):
        result = C_ElevationSnr().Analyse(_PassFile(), [_EquatorialEph()])
        assert len(result.bins) == 9

        zenith = result.bins[ZENITH_BIN]
        assert zenith.elev_min_deg == 80.0
        assert zenith.elev_max_deg == 90.0
        assert zenith.count == 2
        assert abs(zenith.mean_dbhz - 30.0) < 1.0e-9

        mid = result.bins[MID_BIN]
        assert mid.elev_min_deg == 40.0
        assert mid.elev_max_deg == 50.0
        assert mid.count == 1
        assert abs(mid.mean_dbhz - 44.0) < 1.0e-9

        empty = result.bins[0]
        assert empty.count == 0
        assert math.isnan(empty.mean_dbhz) == True

    #==============================================================================
    # \Function: test_figure_labels_elevation_and_snr
    # \Brief: The axes name elevation in degrees and SNR in dB-Hz, with 25 and 35 lines
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. No window is opened.
    #==============================================================================
    def test_figure_labels_elevation_and_snr(self):
        result = C_ElevationSnr().Analyse(_PassFile(), [_EquatorialEph()])
        figure = C_QcPlots().PlotSnrElevation(result)
        axes = figure.axes[0]
        assert axes.get_xlabel() == 'Elevation (degrees)'
        assert axes.get_ylabel() == 'Mean SNR (dB-Hz)'

        levels = []
        for line in axes.get_lines():
            yData = line.get_ydata()
            if len(yData) > 0 and yData[0] == yData[-1]:
                levels.append(yData[0])
        # END for-loop over lines
        assert 25.0 in levels
        assert 35.0 in levels

        centres = list(axes.get_lines()[-1].get_xdata())
        assert centres == [45.0, 85.0]
