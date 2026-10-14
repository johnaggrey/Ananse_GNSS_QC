# =============================================================================
# Tests for Galileo, BeiDou, and NavIC broadcast orbits
# =============================================================================
# Positions are ECEF metres. Epochs are absolute GPST seconds.
# Galileo GST and NavIC time are treated as GPST.
# BeiDou toe_gpst is GPST, which is BDT plus 14 seconds. The Earth-rotation
# term must use the BDT seconds of week, or an equatorial satellite at toe
# is tens of kilometres off the X axis.
# GEO PRN 1 applies the 5-degree rotation. MEO PRN 11 does not.
# An unhealthy record and GLONASS or SBAS return no position.

import math

from AnanseQC.Core import Constants
from AnanseQC.Core.Enums import eGnss
from AnanseQC.Navigation.BroadcastOrbit import C_BroadcastOrbit
from AnanseQC.Readers.NavTypes import S_KeplerEph

# GPS week 2323 starts here, so GPST seconds of week are 0.
WEEK_START_GPST = 1404950400.0
SEMI_MAJOR = 26560000.0


def _CircularEph(eSystem, prn, toeGpsts):
    eph = S_KeplerEph()
    eph.system = eSystem
    eph.prn = prn
    eph.toe_gpst = toeGpsts
    eph.toc_gpst = toeGpsts
    eph.sqrt_a = math.sqrt(SEMI_MAJOR)
    eph.e = 0.0
    eph.m0 = 0.0
    eph.i0 = 0.0
    eph.omega = 0.0
    eph.omega0 = 0.0
    eph.omega_dot = 0.0
    eph.delta_n = 0.0
    eph.idot = 0.0
    eph.health = 0
    return eph


def _EquatorialAfter(gm, omegaE, tk):
    # Closed form for a circular equatorial orbit with zero node and zero toe
    # seconds of week. Mean anomaly grows with n*tk. Earth rotation is -omegaE*tk.
    meanMotion = math.sqrt(gm / (SEMI_MAJOR * SEMI_MAJOR * SEMI_MAJOR))
    angle = (meanMotion - omegaE) * tk
    x = SEMI_MAJOR * math.cos(angle)
    y = SEMI_MAJOR * math.sin(angle)
    return (x, y, 0.0)


class TestBroadcastOrbitOther:
    """Galileo, BeiDou, and NavIC ECEF positions."""

    #==============================================================================
    # \Function: test_galileo_matches_its_gm
    # \Brief: A Galileo satellite 14400 s after toe matches the Galileo closed form
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Position is ECEF metres.
    #                           GST is treated as GPST.
    #==============================================================================
    def test_galileo_matches_its_gm(self):
        tk = 14400.0
        eph = _CircularEph(eGnss.eGAL, 1, WEEK_START_GPST)
        position = C_BroadcastOrbit().Position(eph, WEEK_START_GPST + tk)
        expected = _EquatorialAfter(Constants.GAL_GM, Constants.GAL_OMEGA_E, tk)
        assert position is not None
        assert abs(position[0] - expected[0]) < 1.0
        assert abs(position[1] - expected[1]) < 1.0
        assert abs(position[2] - expected[2]) < 1.0

    #==============================================================================
    # \Function: test_beidou_meo_uses_bdt_toe
    # \Brief: BeiDou MEO at a BDT week boundary sits on the ECEF X axis
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Position is ECEF metres.
    #                           toe_gpst is BDT plus 14 seconds.
    #==============================================================================
    def test_beidou_meo_uses_bdt_toe(self):
        toeGpsts = WEEK_START_GPST + Constants.BDT_TO_GPST_SEC
        eph = _CircularEph(eGnss.eBDS, 11, toeGpsts)
        position = C_BroadcastOrbit().Position(eph, toeGpsts)
        assert position is not None
        assert abs(position[0] - SEMI_MAJOR) < 1.0
        assert abs(position[1]) < 1.0
        assert abs(position[2]) < 1.0

    #==============================================================================
    # \Function: test_beidou_geo_rotation
    # \Brief: BeiDou GEO PRN 1 applies the 5-degree rotation after 1000 s
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Position is ECEF metres.
    #==============================================================================
    def test_beidou_geo_rotation(self):
        tk = 1000.0
        toeGpsts = WEEK_START_GPST + Constants.BDT_TO_GPST_SEC
        eph = _CircularEph(eGnss.eBDS, 1, toeGpsts)
        position = C_BroadcastOrbit().Position(eph, toeGpsts + tk)
        assert position is not None

        meanMotion = math.sqrt(
            Constants.BDS_GM / (SEMI_MAJOR * SEMI_MAJOR * SEMI_MAJOR)
        )
        argLat = meanMotion * tk
        xGk = SEMI_MAJOR * math.cos(argLat)
        yGk = SEMI_MAJOR * math.sin(argLat)
        zGk = 0.0
        theta = Constants.BDS_OMEGA_E * tk
        cosTheta = math.cos(theta)
        sinTheta = math.sin(theta)
        cos5 = math.cos(Constants.BDS_GEO_ROT_RAD)
        sin5 = math.sin(-Constants.BDS_GEO_ROT_RAD)
        expectedX = xGk * cosTheta + yGk * sinTheta * cos5 + zGk * sinTheta * sin5
        expectedY = -xGk * sinTheta + yGk * cosTheta * cos5 + zGk * cosTheta * sin5
        expectedZ = -yGk * sin5 + zGk * cos5
        assert abs(position[0] - expectedX) < 1.0
        assert abs(position[1] - expectedY) < 1.0
        assert abs(position[2] - expectedZ) < 1.0
        assert abs(position[2]) > 1.0

    #==============================================================================
    # \Function: test_navic_matches_its_gm
    # \Brief: A NavIC satellite 14400 s after toe matches the NavIC closed form
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only. Position is ECEF metres.
    #                           NavIC time is treated as GPST.
    #==============================================================================
    def test_navic_matches_its_gm(self):
        tk = 14400.0
        eph = _CircularEph(eGnss.eNavIC, 1, WEEK_START_GPST)
        position = C_BroadcastOrbit().Position(eph, WEEK_START_GPST + tk)
        expected = _EquatorialAfter(Constants.NAVIC_GM, Constants.NAVIC_OMEGA_E, tk)
        assert position is not None
        assert abs(position[0] - expected[0]) < 1.0
        assert abs(position[1] - expected[1]) < 1.0
        assert abs(position[2] - expected[2]) < 1.0

    #==============================================================================
    # \Function: test_unhealthy_glonass_and_sbas_have_no_position
    # \Brief: Health other than 0, GLONASS, and SBAS return no position
    # \Params:
    #           self            [in]    Test case instance
    # \Returns:
    #           None            Assertions only
    #==============================================================================
    def test_unhealthy_glonass_and_sbas_have_no_position(self):
        unhealthy = _CircularEph(eGnss.eGAL, 1, WEEK_START_GPST)
        unhealthy.health = 1
        assert C_BroadcastOrbit().Position(unhealthy, WEEK_START_GPST) is None

        glonass = _CircularEph(eGnss.eGLN, 1, WEEK_START_GPST)
        assert C_BroadcastOrbit().Position(glonass, WEEK_START_GPST) is None

        sbas = _CircularEph(eGnss.eSBAS, 120, WEEK_START_GPST)
        assert C_BroadcastOrbit().Position(sbas, WEEK_START_GPST) is None
