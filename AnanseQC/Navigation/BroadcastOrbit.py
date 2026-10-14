# =============================================================================
# Broadcast Kepler orbit
# =============================================================================
# Satellite position from a GPS, QZSS, Galileo, BeiDou, or NavIC ephemeris.
# QZSS uses the GPS gravity constant and Earth rotation rate.
# Galileo GST and NavIC time are treated as GPST.
# BeiDou toe is BDT. Stored toe_gpst is already GPST, so the Earth-rotation
# term uses toe_gpst minus 14 seconds, wrapped into the BDT week.
# BeiDou GEO PRNs are 1-5 and 59-63. They use the ICD 5-degree rotation.
# MEO and IGSO use the standard Kepler result.
#
# Frame: ECEF metres.
# Time: t_gpst and toe_gpst are absolute GPST seconds.
# The ephemeris is used only when health is 0 and
# abs(t_gpst - toe_gpst) <= 14400 s.
#
# Kepler's equation is solved by Newton iteration.
# Maximum iterations: 20.
# Convergence: the eccentric-anomaly correction is below 1e-12 rad.
# Failure: no convergence, non-positive semi-major axis, unhealthy record,
# or GLONASS, SBAS, or an unknown system. The caller receives no position.

import math

from AnanseQC.Core import Constants
from AnanseQC.Core.Enums import eGnss

# Fit interval used when the record does not supply a tighter limit.
# Units: seconds.
EPH_MAX_AGE_SEC = 14400.0

# Newton solution of Ek - e*sin(Ek) = Mk.
MAX_KEPLER_ITER = 20
KEPLER_TOL_RAD = 1.0e-12


#==============================================================================
# \Class: C_BroadcastOrbit
# \Brief: Computes an ECEF position from a Kepler broadcast ephemeris
#==============================================================================
class C_BroadcastOrbit:
    #==============================================================================
    # \Function: __init__
    # \Brief: Creates the orbit helper
    # \Params:
    #           None
    # \Returns:
    #           None
    #==============================================================================
    def __init__(self):
        pass

    #==============================================================================
    # \Function: Position
    # \Brief: Computes ECEF position at one GPST epoch
    # \Note:
    #   Harmonic corrections are applied. tk is wrapped to plus or minus
    #   half a GPS week. Health 0 is usable. GLONASS and SBAS return None.
    # \Params:
    #           eph             [in]    S_KeplerEph
    #           tGpsts          [in]    Absolute GPST seconds
    # \Returns:
    #           tuple or None   (x, y, z) ECEF metres, or None on failure
    #==============================================================================
    def Position(self, eph, tGpsts):
        broadcast = self._BroadcastConstants(eph.system)
        if broadcast is None:
            return None
        if eph.health != 0:
            return None
        if abs(tGpsts - eph.toe_gpst) > EPH_MAX_AGE_SEC:
            return None
        if eph.sqrt_a <= 0.0:
            return None

        gm, omegaE = broadcast
        tk = tGpsts - eph.toe_gpst
        halfWeek = Constants.SECONDS_IN_WEEK * 0.5
        if tk > halfWeek:
            tk = tk - Constants.SECONDS_IN_WEEK
        elif tk < -halfWeek:
            tk = tk + Constants.SECONDS_IN_WEEK

        bGeo = False
        if eph.system == eGnss.eBDS:
            toeSow = self._SecondsOfWeek(eph.toe_gpst - Constants.BDT_TO_GPST_SEC)
            bGeo = self._IsBdsGeo(eph.prn)
        else:
            toeSow = self._SecondsOfWeek(eph.toe_gpst)

        semiMajor = eph.sqrt_a * eph.sqrt_a
        meanMotion0 = math.sqrt(gm / (semiMajor * semiMajor * semiMajor))
        meanMotion = meanMotion0 + eph.delta_n
        meanAnomaly = eph.m0 + meanMotion * tk

        eccAnomaly = self._EccentricAnomaly(meanAnomaly, eph.e)
        if eccAnomaly is None:
            return None

        sinE = math.sin(eccAnomaly)
        cosE = math.cos(eccAnomaly)
        oneMinusE2 = 1.0 - eph.e * eph.e
        if oneMinusE2 < 0.0:
            return None

        trueAnomaly = math.atan2(
            math.sqrt(oneMinusE2) * sinE,
            cosE - eph.e,
        )
        argLat = trueAnomaly + eph.omega
        sin2 = math.sin(2.0 * argLat)
        cos2 = math.cos(2.0 * argLat)

        corrU = eph.cus * sin2 + eph.cuc * cos2
        corrR = eph.crs * sin2 + eph.crc * cos2
        corrI = eph.cis * sin2 + eph.cic * cos2

        u = argLat + corrU
        radius = semiMajor * (1.0 - eph.e * cosE) + corrR
        incl = eph.i0 + corrI + eph.idot * tk

        xOrb = radius * math.cos(u)
        yOrb = radius * math.sin(u)

        # GEO keeps the node rate. Other orbits remove Earth rotation from it.
        if bGeo == True:
            nodeRate = eph.omega_dot
        else:
            nodeRate = eph.omega_dot - omegaE
        node = eph.omega0 + nodeRate * tk - omegaE * toeSow
        cosNode = math.cos(node)
        sinNode = math.sin(node)
        cosIncl = math.cos(incl)

        x = xOrb * cosNode - yOrb * cosIncl * sinNode
        y = xOrb * sinNode + yOrb * cosIncl * cosNode
        z = yOrb * math.sin(incl)
        if bGeo == True:
            return self._RotateBdsGeo(x, y, z, omegaE * tk)
        return (x, y, z)

    #==============================================================================
    # \Function: _BroadcastConstants
    # \Brief: Returns the broadcast GM and Earth rate for a Kepler system
    # \Params:
    #           eSystem         [in]    eGnss constellation
    # \Returns:
    #           tuple or None   (GM m^3/s^2, Earth rate rad/s)
    #==============================================================================
    def _BroadcastConstants(self, eSystem):
        if eSystem == eGnss.eGPS or eSystem == eGnss.eQZSS:
            return (Constants.GPS_GM, Constants.GPS_OMEGA_E)
        if eSystem == eGnss.eGAL:
            return (Constants.GAL_GM, Constants.GAL_OMEGA_E)
        if eSystem == eGnss.eBDS:
            return (Constants.BDS_GM, Constants.BDS_OMEGA_E)
        if eSystem == eGnss.eNavIC:
            return (Constants.NAVIC_GM, Constants.NAVIC_OMEGA_E)
        return None

    #==============================================================================
    # \Function: _IsBdsGeo
    # \Brief: Reports whether a BeiDou PRN uses the GEO coordinate rotation
    # \Params:
    #           prn             [in]    BeiDou PRN
    # \Returns:
    #           bool            True for PRNs 1-5 and 59-63
    #==============================================================================
    def _IsBdsGeo(self, prn):
        if prn >= 1 and prn <= 5:
            return True
        if prn >= 59 and prn <= 63:
            return True
        return False

    #==============================================================================
    # \Function: _RotateBdsGeo
    # \Brief: Applies the BeiDou GEO 5-degree coordinate rotation
    # \Note:
    #   ICD matrix, with theta = Earth rate * tk and a = -5 degrees:
    #   [ cos(theta)   sin(theta)cos(a)   sin(theta)sin(a) ]
    #   [-sin(theta)   cos(theta)cos(a)   cos(theta)sin(a) ]
    #   [ 0           -sin(a)             cos(a)           ]
    #   sin(-5 deg) = -sin(5 deg). cos(-5 deg) = cos(5 deg).
    # \Params:
    #           xGk             [in]    ECEF X before the GEO rotation, metres
    #           yGk             [in]    ECEF Y before the GEO rotation, metres
    #           zGk             [in]    ECEF Z before the GEO rotation, metres
    #           theta           [in]    Earth rotation over tk, radians
    # \Returns:
    #           tuple           (x, y, z) ECEF metres
    #==============================================================================
    def _RotateBdsGeo(self, xGk, yGk, zGk, theta):
        cosTheta = math.cos(theta)
        sinTheta = math.sin(theta)
        cos5 = math.cos(Constants.BDS_GEO_ROT_RAD)
        sin5 = math.sin(Constants.BDS_GEO_ROT_RAD)
        x = xGk * cosTheta + yGk * sinTheta * cos5 - zGk * sinTheta * sin5
        y = -xGk * sinTheta + yGk * cosTheta * cos5 - zGk * cosTheta * sin5
        z = yGk * sin5 + zGk * cos5
        return (x, y, z)

    #==============================================================================
    # \Function: _EccentricAnomaly
    # \Brief: Solves Kepler's equation by Newton iteration
    # \Note:
    #   Stops when the correction is below 1e-12 rad, or after 20 iterations.
    # \Params:
    #           meanAnomaly     [in]    Mean anomaly, radians
    #           ecc             [in]    Eccentricity, dimensionless
    # \Returns:
    #           float or None   Eccentric anomaly, radians
    #==============================================================================
    def _EccentricAnomaly(self, meanAnomaly, ecc):
        eccAnomaly = meanAnomaly
        bConverged = False
        for _iIter in range(MAX_KEPLER_ITER):
            sinE = math.sin(eccAnomaly)
            cosE = math.cos(eccAnomaly)
            denom = 1.0 - ecc * cosE
            if abs(denom) < Constants.EPSILON:
                return None
            deltaE = (eccAnomaly - ecc * sinE - meanAnomaly) / denom
            eccAnomaly = eccAnomaly - deltaE
            if abs(deltaE) < KEPLER_TOL_RAD:
                bConverged = True
                break
        # END Kepler iteration
        if bConverged == False:
            return None
        return eccAnomaly

    #==============================================================================
    # \Function: _SecondsOfWeek
    # \Brief: Converts absolute GPST seconds to seconds of the GPS week
    # \Params:
    #           tGpsts          [in]    Absolute GPST seconds
    # \Returns:
    #           float           Seconds of week, [0, 604800)
    #==============================================================================
    def _SecondsOfWeek(self, tGpsts):
        week = math.floor(tGpsts / Constants.SECONDS_IN_WEEK)
        return tGpsts - week * Constants.SECONDS_IN_WEEK
