# =============================================================================
# Satellite azimuth and elevation
# =============================================================================
# Topocentric angles from a broadcast ephemeris and a receiver ECEF position.
#
# Frame: receiver and satellite positions are ECEF metres, WGS84.
# The local frame is ENU. Azimuth is degrees clockwise from north.
# Elevation is degrees from the horizon, positive above it.
# Time: the epoch is absolute GPST seconds.
#
# The Kepler record whose toe is closest to the epoch is used, and only when
# that toe is inside the 14400-second fit window.
# One light-time iteration evaluates the satellite at receive time minus
# range over CLIGHT.
# A receiver at the ECEF origin has no angles.

import math

from AnanseQC.Core import Constants
from AnanseQC.Navigation.BroadcastOrbit import C_BroadcastOrbit, EPH_MAX_AGE_SEC

#==============================================================================
# \Class: C_SatGeometry
# \Brief: Computes azimuth and elevation from a Kepler ephemeris
#==============================================================================
class C_SatGeometry:
    #==============================================================================
    # \Function: __init__
    # \Brief: Creates the broadcast-orbit helper
    # \Params:
    #           None
    # \Returns:
    #           None
    #==============================================================================
    def __init__(self):
        self.c_Orbit = C_BroadcastOrbit()

    #==============================================================================
    # \Function: AzEl
    # \Brief: Computes azimuth and elevation of one satellite at one epoch
    # \Note:
    #   Azimuth is degrees clockwise from north, in [0, 360).
    #   Elevation is degrees from the horizon.
    #   The receiver position is ECEF metres. The origin returns no angles.
    # \Params:
    #           keplerEph       [in]    List of S_KeplerEph
    #           eSystem         [in]    eGnss constellation
    #           prn             [in]    Satellite PRN
    #           tGpsts          [in]    Absolute GPST seconds
    #           receiverXyz     [in]    Receiver ECEF (x, y, z), metres
    # \Returns:
    #           tuple or None   (azimuth degrees, elevation degrees)
    #==============================================================================
    def AzEl(self, keplerEph, eSystem, prn, tGpsts, receiverXyz):
        if self._IsOrigin(receiverXyz) == True:
            return None

        eph = self._SelectEph(keplerEph, eSystem, prn, tGpsts)
        if eph is None:
            return None

        satReceive = self.c_Orbit.Position(eph, tGpsts)
        if satReceive is None:
            return None

        dx = satReceive[0] - receiverXyz[0]
        dy = satReceive[1] - receiverXyz[1]
        dz = satReceive[2] - receiverXyz[2]
        rangeM = math.sqrt(dx * dx + dy * dy + dz * dz)
        if rangeM <= 0.0:
            return None

        # One light-time iteration. Transmit time is receive time minus tau.
        tau = rangeM / Constants.CLIGHT
        satTransmit = self.c_Orbit.Position(eph, tGpsts - tau)
        if satTransmit is None:
            return None

        geodetic = self._Geodetic(receiverXyz[0], receiverXyz[1], receiverXyz[2])
        if geodetic is None:
            return None

        dx = satTransmit[0] - receiverXyz[0]
        dy = satTransmit[1] - receiverXyz[1]
        dz = satTransmit[2] - receiverXyz[2]
        return self._AzElDeg(geodetic[0], geodetic[1], dx, dy, dz)

    #==============================================================================
    # \Function: _IsOrigin
    # \Brief: Reports whether the receiver ECEF position is the origin
    # \Params:
    #           receiverXyz     [in]    Receiver ECEF (x, y, z), metres
    # \Returns:
    #           bool
    #==============================================================================
    def _IsOrigin(self, receiverXyz):
        if receiverXyz[0] != 0.0:
            return False
        if receiverXyz[1] != 0.0:
            return False
        if receiverXyz[2] != 0.0:
            return False
        return True

    #==============================================================================
    # \Function: _SelectEph
    # \Brief: Selects the Kepler record closest to the epoch inside the fit window
    # \Params:
    #           keplerEph       [in]    List of S_KeplerEph
    #           eSystem         [in]    eGnss constellation
    #           prn             [in]    Satellite PRN
    #           tGpsts          [in]    Absolute GPST seconds
    # \Returns:
    #           S_KeplerEph or None
    #==============================================================================
    def _SelectEph(self, keplerEph, eSystem, prn, tGpsts):
        best = None
        bestDt = 0.0
        for eph in keplerEph:
            if eph.system != eSystem or eph.prn != prn:
                continue
            dt = abs(tGpsts - eph.toe_gpst)
            if dt > EPH_MAX_AGE_SEC:
                continue
            if best is None or dt < bestDt:
                best = eph
                bestDt = dt
        # END for-loop over Kepler records
        return best

    #==============================================================================
    # \Function: _Geodetic
    # \Brief: Converts ECEF metres to WGS84 geodetic latitude and longitude
    # \Params:
    #           x               [in]    ECEF X, metres
    #           y               [in]    ECEF Y, metres
    #           z               [in]    ECEF Z, metres
    # \Returns:
    #           tuple or None   (latitude radians, longitude radians)
    #==============================================================================
    def _Geodetic(self, x, y, z):
        semiMajor = Constants.WGS84_A
        flattening = Constants.WGS84_F
        semiMinor = semiMajor * (1.0 - flattening)
        ecc2 = flattening * (2.0 - flattening)
        secondEcc2 = (semiMajor * semiMajor - semiMinor * semiMinor) / (semiMinor * semiMinor)
        p = math.hypot(x, y)
        if p < Constants.EPSILON and abs(z) < Constants.EPSILON:
            return None

        theta = math.atan2(z * semiMajor, p * semiMinor)
        sinTheta = math.sin(theta)
        cosTheta = math.cos(theta)
        lat = math.atan2(
            z + secondEcc2 * semiMinor * sinTheta * sinTheta * sinTheta,
            p - ecc2 * semiMajor * cosTheta * cosTheta * cosTheta,
        )
        lon = math.atan2(y, x)
        return (lat, lon)

    #==============================================================================
    # \Function: _AzElDeg
    # \Brief: Converts an ECEF line of sight to azimuth and elevation
    # \Note:
    #   The rotation is ECEF to ENU. Azimuth is clockwise from north.
    # \Params:
    #           lat             [in]    Geodetic latitude, radians
    #           lon             [in]    Geodetic longitude, radians
    #           dx              [in]    ECEF X satellite minus receiver, metres
    #           dy              [in]    ECEF Y satellite minus receiver, metres
    #           dz              [in]    ECEF Z satellite minus receiver, metres
    # \Returns:
    #           tuple           (azimuth degrees, elevation degrees)
    #==============================================================================
    def _AzElDeg(self, lat, lon, dx, dy, dz):
        sinLat = math.sin(lat)
        cosLat = math.cos(lat)
        sinLon = math.sin(lon)
        cosLon = math.cos(lon)

        east = -sinLon * dx + cosLon * dy
        north = -sinLat * cosLon * dx - sinLat * sinLon * dy + cosLat * dz
        up = cosLat * cosLon * dx + cosLat * sinLon * dy + sinLat * dz

        azimuth = math.atan2(east, north)
        if azimuth < 0.0:
            azimuth = azimuth + 2.0 * Constants.PI
        elevation = math.atan2(up, math.hypot(east, north))
        return (azimuth * Constants.RAD2DEG, elevation * Constants.RAD2DEG)
