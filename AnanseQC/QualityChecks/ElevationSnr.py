# =============================================================================
# QC Engine: Elevation-Binned SNR
# =============================================================================
# Mean signal strength in 10-degree elevation bins from the horizon to zenith.
#
# Elevation is computed in degrees from the receiver ECEF approximate position
# (WGS84) and a broadcast ephemeris. Antenna height is not applied.
# Time system: GPST seconds stored on each epoch.
# SNR unit: dB-Hz, taken from observation descriptors that start with S.
# Each such observation has weight 1, so the bin value is a count-weighted mean.
# Bins with no observations stay empty: the mean is not a number.
# Special-event epochs (epoch flag greater than 1) are excluded.
# Elevations below the horizon are excluded. An elevation above 90 degrees,
# from a geometry residual, is placed in the zenith bin.

import math
from dataclasses import dataclass, field
from typing import List

from AnanseQC.Navigation.SatGeometry import C_SatGeometry
from AnanseQC.Readers.ObsTypes import S_RinexObsFile


# Elevation bin width, degrees. Nine bins cover 0 to 90.
BIN_WIDTH_DEG = 10.0
N_ELEVATION_BINS = 9
ZENITH_DEG = 90.0


#==============================================================================
# \Class: S_ElevationBin
# \Brief: Count-weighted mean SNR for one elevation interval
#==============================================================================
@dataclass
class S_ElevationBin:
    """One 10-degree elevation bin.

    Attributes:
        elev_min_deg (float): Lower edge, degrees, inclusive.
        elev_max_deg (float): Upper edge, degrees. The zenith bin includes 90.
        count (int): Number of S* observations in the bin.
        mean_dbhz (float): Count-weighted mean, dB-Hz. Not a number when empty.
    """
    elev_min_deg: float = 0.0
    elev_max_deg: float = 0.0
    count: int = 0
    mean_dbhz: float = float('nan')


#==============================================================================
# \Class: S_ElevationSnrResult
# \Brief: Mean SNR from the horizon to zenith
#==============================================================================
@dataclass
class S_ElevationSnrResult:
    """Nine elevation bins. Index 0 is 0-10 degrees. Index 8 is 80-90 degrees.

    Attributes:
        bins (list): S_ElevationBin rows, always nine entries.
    """
    bins: List[S_ElevationBin] = field(default_factory=list)


#==============================================================================
# \Class: C_ElevationSnr
# \Brief: Accumulates SNR observations into elevation bins
#==============================================================================
class C_ElevationSnr:
    """Elevation-binned mean SNR in dB-Hz."""

    def __init__(self):
        """Initializes the geometry helper used for each tracked satellite."""
        self._cGeometry = C_SatGeometry()

    def Reset(self):
        """Clears nothing held between calls. Analyse builds a new result."""
        return

    #==============================================================================
    # \Function: Analyse
    # \Brief: Mean SNR in 10-degree bins using broadcast elevation
    # \Params:
    #           obsFile         [in]    Parsed observation file
    #           keplerEph       [in]    Broadcast Kepler records
    # \Returns:
    #           S_ElevationSnrResult
    #==============================================================================
    def Analyse(self, obsFile: S_RinexObsFile, keplerEph) -> S_ElevationSnrResult:
        result = S_ElevationSnrResult()
        sums = []
        for binIndex in range(N_ELEVATION_BINS):
            elevMin = binIndex * BIN_WIDTH_DEG
            elevBin = S_ElevationBin()
            elevBin.elev_min_deg = elevMin
            elevBin.elev_max_deg = elevMin + BIN_WIDTH_DEG
            result.bins.append(elevBin)
            sums.append(0.0)
        # END for-loop over bin edges

        receiver = obsFile.header.approx_position
        for epoch in obsFile.epochs:
            if epoch.epoch_flag > 1:
                continue
            for sat in epoch.satellites:
                self._AddSatellite(
                    result,
                    sums,
                    keplerEph,
                    sat,
                    epoch.abs_gps_time,
                    receiver,
                )
            # END for-loop over satellites
        # END for-loop over epochs

        for binIndex in range(N_ELEVATION_BINS):
            count = result.bins[binIndex].count
            if count > 0:
                result.bins[binIndex].mean_dbhz = sums[binIndex] / count
        # END for-loop over bins
        return result

    #==============================================================================
    # \Function: _AddSatellite
    # \Brief: Adds every S* value at one satellite epoch into its elevation bin
    # \Params:
    #           result          [in,out]  Bin counts and means
    #           sums            [in,out]  Running SNR sums, dB-Hz
    #           keplerEph       [in]      Broadcast Kepler records
    #           sat             [in]      One tracked satellite
    #           tGpsts          [in]      Epoch time, GPST seconds
    #           receiver        [in]      Receiver ECEF, metres
    # \Returns:
    #           None
    #==============================================================================
    def _AddSatellite(self, result, sums, keplerEph, sat, tGpsts, receiver):
        angles = self._cGeometry.AzEl(
            keplerEph,
            sat.system,
            sat.prn,
            tGpsts,
            receiver,
        )
        if angles is None:
            return

        elevationDeg = angles[1]
        if elevationDeg < 0.0:
            return
        if elevationDeg > ZENITH_DEG:
            elevationDeg = ZENITH_DEG

        binIndex = int(elevationDeg / BIN_WIDTH_DEG)
        if binIndex >= N_ELEVATION_BINS:
            binIndex = N_ELEVATION_BINS - 1
        if binIndex < 0:
            return

        for obsType, value in sat.obs.items():
            if obsType.startswith('S') == False:
                continue
            sums[binIndex] = sums[binIndex] + value
            result.bins[binIndex].count = result.bins[binIndex].count + 1
        # END for-loop over observation types
