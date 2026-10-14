# =============================================================================
# Broadcast Kepler orbit
# =============================================================================
# Satellite position from a GPS or QZSS broadcast ephemeris.
# QZSS uses the GPS gravity constant and Earth rotation rate.
#
# Frame: ECEF metres, WGS84 Earth rotation applied.
# Time: t_gpst and toe_gpst are absolute GPST seconds.
# The ephemeris is used only when abs(t_gpst - toe_gpst) <= 14400 s.
#
# Kepler's equation is solved by Newton iteration.
# Maximum iterations: 20.
# Convergence: the eccentric-anomaly correction is below 1e-12 rad.
# Failure: no convergence, non-positive semi-major axis, or a system other
# than GPS or QZSS. The caller receives no position.

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
# \Brief: Computes an ECEF position from a GPS or QZSS broadcast ephemeris
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
    #   half a GPS week. QZSS uses the GPS GM and Earth rate.
    # \Params:
    #           eph             [in]    S_KeplerEph
    #           tGpsts          [in]    Absolute GPST seconds
    # \Returns:
    #           tuple or None   (x, y, z) ECEF metres, or None on failure
    #==============================================================================
    def Position(self, eph, tGpsts):
        if eph.system != eGnss.eGPS and eph.system != eGnss.eQZSS:
            return None
        if abs(tGpsts - eph.toe_gpst) > EPH_MAX_AGE_SEC:
            return None
        if eph.sqrt_a <= 0.0:
            return None

        tk = tGpsts - eph.toe_gpst
        halfWeek = Constants.SECONDS_IN_WEEK * 0.5
        if tk > halfWeek:
            tk = tk - Constants.SECONDS_IN_WEEK
        elif tk < -halfWeek:
            tk = tk + Constants.SECONDS_IN_WEEK

        semiMajor = eph.sqrt_a * eph.sqrt_a
        meanMotion0 = math.sqrt(Constants.GPS_GM / (semiMajor * semiMajor * semiMajor))
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

        toeSow = self._SecondsOfWeek(eph.toe_gpst)
        node = (eph.omega0
                + (eph.omega_dot - Constants.GPS_OMEGA_E) * tk
                - Constants.GPS_OMEGA_E * toeSow)
        cosNode = math.cos(node)
        sinNode = math.sin(node)
        cosIncl = math.cos(incl)

        x = xOrb * cosNode - yOrb * cosIncl * sinNode
        y = xOrb * sinNode + yOrb * cosIncl * cosNode
        z = yOrb * math.sin(incl)
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
