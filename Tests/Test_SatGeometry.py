# =============================================================================
# Tests for azimuth and elevation
# =============================================================================
# The receiver is on the WGS84 equator at longitude 0, ECEF metres.
# A polar broadcast orbit puts the satellite on the Z axis, due north of
# that receiver. Elevation is negative because the zenith there is +X.
# An equatorial orbit puts the satellite on the X axis, overhead.
# Angles are degrees. The epoch is absolute GPST seconds.
# One light-time iteration moves the satellite by a fraction of a degree.

import math

from AnanseQC.Core import Constants
from AnanseQC.Core.Enums import eGnss
from AnanseQC.Navigation.SatGeometry import C_SatGeometry
from AnanseQC.Readers.NavTypes import S_KeplerEph

# GPS week 2323 starts here, so toe seconds-of-week are 0.
TOE_GPST = 1404950400.0
SEMI_MAJOR = 26560000.0

# Receiver on the equator, longitude 0. Zenith is +X. North is +Z.
RECEIVER_XYZ = (Constants.WGS84_A, 0.0, 0.0)


def _CircularEph(meanAnomaly, inclination, toeGpsts):
    eph = S_KeplerEph()
    eph.system = eGnss.eGPS
    eph.prn = 1
    eph.toe_gpst = toeGpsts
    eph.toc_gpst = toeGpsts
    eph.sqrt_a = math.sqrt(SEMI_MAJOR)
    eph.e = 0.0
    eph.m0 = meanAnomaly
    eph.i0 = inclination
    eph.omega = 0.0
    eph.omega0 = 0.0
    eph.omega_dot = 0.0
    eph.delta_n = 0.0
    eph.idot = 0.0
    eph.health = 0
    return eph


class TestSatGeometry:
    """Azimuth and elevation from a receiver ECEF position."""

    #==============================================================================
    # \Function: test_polar_satellite_is_due_north
    # \Brief: A Z-axis satellite has azimuth near 0 and a known elevation
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Angles are degrees.
    #                           Receiver and satellite are ECEF metres.
    #==============================================================================
    def test_polar_satellite_is_due_north(self):
        eph = _CircularEph(Constants.PI * 0.5, Constants.PI * 0.5, TOE_GPST)
        angles = C_SatGeometry().AzEl([eph], eGnss.eGPS, 1, TOE_GPST, RECEIVER_XYZ)
        expectedEl = math.atan2(-Constants.WGS84_A, SEMI_MAJOR) * Constants.RAD2DEG
        assert angles is not None
        assert abs(angles[0] - 0.0) < 0.05
        assert abs(angles[1] - expectedEl) < 0.05

    #==============================================================================
    # \Function: test_equatorial_satellite_is_overhead
    # \Brief: An X-axis satellite has elevation near 90 degrees
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Elevation is degrees.
    #==============================================================================
    def test_equatorial_satellite_is_overhead(self):
        eph = _CircularEph(0.0, 0.0, TOE_GPST)
        angles = C_SatGeometry().AzEl([eph], eGnss.eGPS, 1, TOE_GPST, RECEIVER_XYZ)
        assert angles is not None
        assert abs(angles[1] - 90.0) < 0.05

    #==============================================================================
    # \Function: test_closer_toe_is_selected
    # \Brief: Two records inside the fit window use the toe closest to the epoch
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Elevation is degrees.
    #==============================================================================
    def test_closer_toe_is_selected(self):
        overhead = _CircularEph(0.0, 0.0, TOE_GPST)
        north = _CircularEph(Constants.PI * 0.5, Constants.PI * 0.5, TOE_GPST + 1000.0)
        angles = C_SatGeometry().AzEl(
            [north, overhead],
            eGnss.eGPS,
            1,
            TOE_GPST,
            RECEIVER_XYZ,
        )
        assert angles is not None
        assert abs(angles[1] - 90.0) < 0.05

    #==============================================================================
    # \Function: test_origin_and_stale_ephemeris_have_no_angles
    # \Brief: The ECEF origin and a toe outside 14400 seconds return no angles
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_origin_and_stale_ephemeris_have_no_angles(self):
        eph = _CircularEph(0.0, 0.0, TOE_GPST)
        assert C_SatGeometry().AzEl([eph], eGnss.eGPS, 1, TOE_GPST, (0.0, 0.0, 0.0)) is None

        stale = _CircularEph(0.0, 0.0, TOE_GPST + 20000.0)
        assert C_SatGeometry().AzEl([stale], eGnss.eGPS, 1, TOE_GPST, RECEIVER_XYZ) is None
