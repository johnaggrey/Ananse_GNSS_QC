# =============================================================================
# Tests for the GPS and QZSS broadcast orbit
# =============================================================================
# The ephemeris is circular and has no harmonic corrections.
# Time is absolute GPST seconds. Position is ECEF metres.
# At the ephemeris epoch, with the node and Earth angle at zero, the
# equatorial satellite is on the X axis. A polar satellite with mean
# anomaly 90 degrees is on the Z axis.
# The fit window is 14400 seconds.

import math

from AnanseQC.Core import Constants
from AnanseQC.Core.Enums import eGnss
from AnanseQC.Navigation.BroadcastOrbit import C_BroadcastOrbit
from AnanseQC.Readers.NavTypes import S_KeplerEph

# GPS week 2323 starts at this absolute GPST second, so toe seconds-of-week is 0.
TOE_GPST = 1404950400.0
SEMI_MAJOR = 26560000.0


def _CircularEph(eSystem, meanAnomaly, inclination):
    eph = S_KeplerEph()
    eph.system = eSystem
    eph.prn = 1
    eph.toe_gpst = TOE_GPST
    eph.toc_gpst = TOE_GPST
    eph.sqrt_a = math.sqrt(SEMI_MAJOR)
    eph.e = 0.0
    eph.m0 = meanAnomaly
    eph.i0 = inclination
    eph.omega = 0.0
    eph.omega0 = 0.0
    eph.omega_dot = 0.0
    eph.delta_n = 0.0
    eph.idot = 0.0
    return eph


class TestBroadcastOrbitGps:
    """GPS and QZSS ECEF positions from a zero-harmonic ephemeris."""

    #==============================================================================
    # \Function: test_equatorial_at_toe_is_on_x_axis
    # \Brief: A circular equatorial GPS satellite at toe is at (A, 0, 0)
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Position is ECEF metres.
    #==============================================================================
    def test_equatorial_at_toe_is_on_x_axis(self):
        eph = _CircularEph(eGnss.eGPS, 0.0, 0.0)
        position = C_BroadcastOrbit().Position(eph, TOE_GPST)
        assert position is not None
        assert abs(position[0] - SEMI_MAJOR) < 1.0
        assert abs(position[1]) < 1.0
        assert abs(position[2]) < 1.0

    #==============================================================================
    # \Function: test_qzss_uses_gps_constants
    # \Brief: The same elements for QZSS match the GPS ECEF position
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Position is ECEF metres.
    #==============================================================================
    def test_qzss_uses_gps_constants(self):
        gps = C_BroadcastOrbit().Position(_CircularEph(eGnss.eGPS, 0.0, 0.0), TOE_GPST)
        qzss = C_BroadcastOrbit().Position(_CircularEph(eGnss.eQZSS, 0.0, 0.0), TOE_GPST)
        assert gps is not None
        assert qzss is not None
        assert abs(qzss[0] - gps[0]) < 1.0e-6
        assert abs(qzss[1] - gps[1]) < 1.0e-6
        assert abs(qzss[2] - gps[2]) < 1.0e-6

    #==============================================================================
    # \Function: test_polar_mean_anomaly_is_on_z_axis
    # \Brief: Inclination 90 degrees and mean anomaly 90 degrees put the satellite on Z
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Position is ECEF metres.
    #==============================================================================
    def test_polar_mean_anomaly_is_on_z_axis(self):
        eph = _CircularEph(eGnss.eGPS, Constants.PI * 0.5, Constants.PI * 0.5)
        position = C_BroadcastOrbit().Position(eph, TOE_GPST)
        assert position is not None
        assert abs(position[0]) < 1.0
        assert abs(position[1]) < 1.0
        assert abs(position[2] - SEMI_MAJOR) < 1.0

    #==============================================================================
    # \Function: test_outside_fit_interval_has_no_position
    # \Brief: A time more than 14400 seconds from toe returns no position
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_outside_fit_interval_has_no_position(self):
        eph = _CircularEph(eGnss.eGPS, 0.0, 0.0)
        position = C_BroadcastOrbit().Position(eph, TOE_GPST + 14401.0)
        assert position is None
