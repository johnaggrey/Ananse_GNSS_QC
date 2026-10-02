# =============================================================================
# QC Engine: Multipath Estimation and SNR Quality Analysis
# =============================================================================
# Computes standard multipath estimators and signal quality metrics:
#
# 1. Multipath (MP) Combinations
#    MP1 = P1 - L1 * λ1 - 2 * (f2²/(f1²-f2²)) * (L1*λ1 - L2*λ2)
#    MP2 = P2 - L2 * λ2 - 2 * (f1²/(f1²-f2²)) * (L1*λ1 - L2*λ2)
#
#    These combinations are geometry-free and ionosphere-free, isolating
#    pseudorange multipath + noise. Phase ambiguities create a constant
#    bias per tracking arc, which is removed by subtracting the arc mean.
#
# 2. SNR Quality Metrics
#    - Mean, min, max, standard deviation per satellite per observation type
#    - Distribution across signal strength categories (good/fair/poor)
#
# Reference:
#   Estey, L. & Meertens, C. (1999). TEQC: The Multi-Purpose Toolkit for
#   GPS/GLONASS Data. GPS Solutions.
#
# Units:
#   - Multipath: metres (RMS of MP combination after arc-mean removal)
#   - SNR: dBHz

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import math

from AnanseQC.Core.Enums import eGnss, SYSTEM_TO_CHAR
from AnanseQC.Core import Constants as C
from AnanseQC.Readers.ObsTypes import S_RinexObsFile, S_SatObs
from AnanseQC.QualityChecks.CycleSlips import C_CycleSlipDetector


# =============================================================================
# SNR Quality Thresholds (dBHz)
# =============================================================================
SNR_GOOD_THRESHOLD = 35.0      # Good signal quality
SNR_FAIR_THRESHOLD = 25.0      # Fair signal quality (below this = poor)


#==============================================================================
# \Class: S_SatMultipathResult
# \Brief: Multipath metrics for one satellite
#==============================================================================
@dataclass
class S_SatMultipathResult:
    """Multipath metrics for a single satellite.

    Attributes:
        system (eGnss): GNSS constellation.
        prn (int): Satellite PRN.
        mp1_rms (float): RMS of MP1 combination in metres (NaN if unavailable).
        mp2_rms (float): RMS of MP2 combination in metres (NaN if unavailable).
        mp1_mean (float): Mean of MP1 after arc-mean removal.
        mp2_mean (float): Mean of MP2 after arc-mean removal.
        mp1_epoch_count (int): Number of epochs used for MP1.
        mp2_epoch_count (int): Number of epochs used for MP2.
    """
    system: eGnss = eGnss.eUnknownSystem
    prn: int = 0
    mp1_rms: float = float('nan')
    mp2_rms: float = float('nan')
    mp1_mean: float = float('nan')
    mp2_mean: float = float('nan')
    mp1_epoch_count: int = 0
    mp2_epoch_count: int = 0


#==============================================================================
# \Class: S_SatSnrResult
# \Brief: SNR quality metrics for one satellite
#==============================================================================
@dataclass
class S_SatSnrResult:
    """SNR quality metrics for a single satellite.

    Attributes:
        system (eGnss): GNSS constellation.
        prn (int): Satellite PRN.
        obs_type_stats (dict): Maps obs_type -> dict with keys:
            'mean', 'std', 'min', 'max', 'count',
            'pct_good', 'pct_fair', 'pct_poor'
    """
    system: eGnss = eGnss.eUnknownSystem
    prn: int = 0
    obs_type_stats: Dict[str, dict] = field(default_factory=dict)


#==============================================================================
# \Class: S_MultipathSnrResult
# \Brief: Complete multipath and SNR analysis result
#==============================================================================
@dataclass
class S_MultipathSnrResult:
    """Complete multipath and SNR analysis result.

    Attributes:
        overall_mp1_rms (float): Overall MP1 RMS across all satellites (metres).
        overall_mp2_rms (float): Overall MP2 RMS across all satellites (metres).
        sat_multipath (dict): Maps (eGnss, prn) -> S_SatMultipathResult.
        sat_snr (dict): Maps (eGnss, prn) -> S_SatSnrResult.
        overall_snr_mean (float): Mean SNR across all observations (dBHz).
        pct_good_snr (float): Percentage of observations with SNR >= 35 dBHz.
        pct_fair_snr (float): Percentage with 25 <= SNR < 35 dBHz.
        pct_poor_snr (float): Percentage with SNR < 25 dBHz.
    """
    overall_mp1_rms: float = float('nan')
    overall_mp2_rms: float = float('nan')
    sat_multipath: Dict[Tuple[eGnss, int], S_SatMultipathResult] = field(
        default_factory=dict)
    sat_snr: Dict[Tuple[eGnss, int], S_SatSnrResult] = field(
        default_factory=dict)
    overall_snr_mean: float = 0.0
    pct_good_snr: float = 0.0
    pct_fair_snr: float = 0.0
    pct_poor_snr: float = 0.0


# =============================================================================
# Multipath Computation
# =============================================================================

#==============================================================================
# \Class: C_MultipathSnr
# \Brief: Estimates MP1/MP2 multipath and SNR quality
#==============================================================================
class C_MultipathSnr:
    #==============================================================================
    # \Function: _FindCodePhasePair
    # \Brief: Find code and phase values for a specific band
    #==============================================================================
    def _FindCodePhasePair(self, sat_obs, band, system):
        """Find code and phase values for a specific band.

        Args:
            sat_obs (S_SatObs): Satellite observations.
            band (int): RINEX band number (1, 2, 5, etc.).
            system (eGnss): GNSS constellation.

        Returns:
            tuple: (code_value_m, phase_value_cycles, phase_obs_type) or (None, None, None).
        """
        code_val = None
        phase_val = None
        phase_type = None

        for obs_type, value in sat_obs.obs.items():
            if len(obs_type) < 2:
                continue
            try:
                obs_band = int(obs_type[1])
            except ValueError:
                continue

            if obs_band != band:
                continue

            if obs_type.startswith('C') or obs_type.startswith('P'):
                if code_val is None:
                    code_val = value
            elif obs_type.startswith('L'):
                if phase_val is None:
                    phase_val = value
                    phase_type = obs_type

        return code_val, phase_val, phase_type


    #==============================================================================
    # \Function: _ComputeMultipath
    # \Brief: Compute MP1 and MP2 multipath combinations for all satellites
    #==============================================================================
    def _ComputeMultipath(self, obs_file):
        """Compute MP1 and MP2 multipath combinations for all satellites.

        MP1 = P1 - L1*λ1 - 2*(f2²/(f1²-f2²)) * (L1*λ1 - L2*λ2)
        MP2 = P2 - L2*λ2 - 2*(f1²/(f1²-f2²)) * (L1*λ1 - L2*λ2)

        These are computed epoch-by-epoch and the RMS is taken after
        removing the per-arc mean (to account for phase ambiguity bias).

        Args:
            obs_file (S_RinexObsFile): Parsed RINEX observation data.

        Returns:
            dict: Maps (eGnss, prn) -> S_SatMultipathResult.
        """
        # Collect MP values per satellite
        # sat_key -> {'mp1': [values], 'mp2': [values]}
        sat_mp_values = defaultdict(lambda: {'mp1': [], 'mp2': []})

        for idx, epoch in enumerate(obs_file.epochs):
            if epoch.epoch_flag > 1:
                continue

            for sat in epoch.satellites:
                sat_key = (sat.system, sat.prn)

                # Determine primary frequency bands for this system
                bands = self._GetPrimaryBands(sat.system)
                if bands is None or len(bands) < 2:
                    continue

                band1, band2 = bands[0], bands[1]

                # Get code and phase for both bands
                P1, L1, L1_type = self._FindCodePhasePair(sat, band1, sat.system)
                P2, L2, L2_type = self._FindCodePhasePair(sat, band2, sat.system)

                if P1 is None or L1 is None or P2 is None or L2 is None:
                    continue

                # Get frequencies and wavelengths
                c_Freq = C_CycleSlipDetector()
                f1 = c_Freq._GetFrequencyHz(sat.system, f'L{band1}C')
                f2 = c_Freq._GetFrequencyHz(sat.system, f'L{band2}C')
                if f1 is None or f2 is None or f1 == f2:
                    continue

                lambda1 = c_Freq._Wavelength(f1)
                lambda2 = c_Freq._Wavelength(f2)
                if lambda1 is None or lambda2 is None:
                    continue

                # Compute f² ratio terms
                f1_sq = f1 * f1
                f2_sq = f2 * f2
                denom = f1_sq - f2_sq

                if abs(denom) < 1e-6:
                    continue

                # Geometry-free phase combination in metres
                gf_phase_m = L1 * lambda1 - L2 * lambda2

                # MP1 combination (metres)
                mp1 = P1 - L1 * lambda1 - 2.0 * (f2_sq / denom) * gf_phase_m

                # MP2 combination (metres)
                mp2 = P2 - L2 * lambda2 - 2.0 * (f1_sq / denom) * gf_phase_m

                sat_mp_values[sat_key]['mp1'].append(mp1)
                sat_mp_values[sat_key]['mp2'].append(mp2)

        # Compute RMS after removing mean (arc-mean approximation)
        results = {}
        for sat_key, mp_dict in sat_mp_values.items():
            system, prn = sat_key
            result = S_SatMultipathResult(system=system, prn=prn)

            # MP1 RMS
            mp1_vals = mp_dict['mp1']
            if len(mp1_vals) > 0:
                mean1 = sum(mp1_vals) / len(mp1_vals)
                rms1 = math.sqrt(sum((v - mean1) ** 2 for v in mp1_vals) / len(mp1_vals))
                result.mp1_rms = rms1
                result.mp1_mean = mean1
                result.mp1_epoch_count = len(mp1_vals)

            # MP2 RMS
            mp2_vals = mp_dict['mp2']
            if len(mp2_vals) > 0:
                mean2 = sum(mp2_vals) / len(mp2_vals)
                rms2 = math.sqrt(sum((v - mean2) ** 2 for v in mp2_vals) / len(mp2_vals))
                result.mp2_rms = rms2
                result.mp2_mean = mean2
                result.mp2_epoch_count = len(mp2_vals)

            results[sat_key] = result

        return results


    #==============================================================================
    # \Function: _GetPrimaryBands
    # \Brief: Get the primary dual-frequency band numbers for a GNSS system
    #==============================================================================
    def _GetPrimaryBands(self, system):
        """Get the primary dual-frequency band numbers for a GNSS system.

        Args:
            system (eGnss): GNSS constellation.

        Returns:
            list or None: [band1, band2] for the two primary frequencies.
        """
        band_map = {
            eGnss.eGPS: [1, 2],        # L1, L2
            eGnss.eGLN: [1, 2],    # G1, G2
            eGnss.eGAL: [1, 5],    # E1, E5a
            eGnss.eBDS: [2, 7],     # B1I, B2b (BDS-2) or [1, 5] for BDS-3
            eGnss.eQZSS: [1, 2],       # L1, L2
            eGnss.eSBAS: [1, 5],       # L1, L5
            eGnss.eNavIC: [5, 9],      # L5, S
        }
        return band_map.get(system)


    # =============================================================================
    # SNR Analysis
    # =============================================================================

    #==============================================================================
    # \Function: _ComputeSnrStats
    # \Brief: Compute SNR quality statistics for all satellites
    #==============================================================================
    def _ComputeSnrStats(self, obs_file):
        """Compute SNR quality statistics for all satellites.

        Args:
            obs_file (S_RinexObsFile): Parsed RINEX observation data.

        Returns:
            tuple: (dict of per-sat SNR results, overall stats dict)
        """
        # Collect SNR values: sat_key -> {obs_type -> [values]}
        sat_snr_values = defaultdict(lambda: defaultdict(list))
        all_snr_values = []

        for epoch in obs_file.epochs:
            if epoch.epoch_flag > 1:
                continue

            for sat in epoch.satellites:
                sat_key = (sat.system, sat.prn)
                for obs_type, value in sat.obs.items():
                    # SNR observations start with 'S'
                    if obs_type.startswith('S'):
                        sat_snr_values[sat_key][obs_type].append(value)
                        all_snr_values.append(value)

        # Compute per-satellite, per-obs-type statistics
        sat_results = {}
        for sat_key, obs_dict in sat_snr_values.items():
            system, prn = sat_key
            sat_result = S_SatSnrResult(system=system, prn=prn)

            for obs_type, values in obs_dict.items():
                if not values:
                    continue

                n = len(values)
                mean_val = sum(values) / n
                min_val = min(values)
                max_val = max(values)
                variance = sum((v - mean_val) ** 2 for v in values) / n
                std_val = math.sqrt(variance)

                good_count = sum(1 for v in values if v >= SNR_GOOD_THRESHOLD)
                fair_count = sum(1 for v in values
                                 if SNR_FAIR_THRESHOLD <= v < SNR_GOOD_THRESHOLD)
                poor_count = sum(1 for v in values if v < SNR_FAIR_THRESHOLD)

                sat_result.obs_type_stats[obs_type] = {
                    'mean': mean_val,
                    'std': std_val,
                    'min': min_val,
                    'max': max_val,
                    'count': n,
                    'pct_good': 100.0 * good_count / n,
                    'pct_fair': 100.0 * fair_count / n,
                    'pct_poor': 100.0 * poor_count / n,
                }

            sat_results[sat_key] = sat_result

        # Overall SNR statistics
        overall = {}
        if all_snr_values:
            n = len(all_snr_values)
            overall['mean'] = sum(all_snr_values) / n
            overall['pct_good'] = 100.0 * sum(1 for v in all_snr_values
                                               if v >= SNR_GOOD_THRESHOLD) / n
            overall['pct_fair'] = 100.0 * sum(1 for v in all_snr_values
                                               if SNR_FAIR_THRESHOLD <= v < SNR_GOOD_THRESHOLD) / n
            overall['pct_poor'] = 100.0 * sum(1 for v in all_snr_values
                                               if v < SNR_FAIR_THRESHOLD) / n

        return sat_results, overall


    # =============================================================================
    # Public API
    # =============================================================================

    #==============================================================================
    # \Function: Analyse
    # \Brief: Estimates multipath and SNR quality
    # \Note:
    #   MP1 and MP2 are reported as RMS after arc-mean removal, in metres.
    #   SNR is in dB-Hz. Good is at least 35, fair is 25 to 35, poor is below 25.
    # \Params:
    #           obsFile         [in]    Parsed RINEX observation file
    # \Returns:
    #           S_MultipathSnrResult
    #==============================================================================
    def Analyse(self, obsFile):
        result = S_MultipathSnrResult()

        # Compute multipath
        result.sat_multipath = self._ComputeMultipath(obsFile)

        # Compute overall MP1/MP2 RMS (weighted average by epoch count)
        total_mp1_sum_sq = 0.0
        total_mp1_count = 0
        total_mp2_sum_sq = 0.0
        total_mp2_count = 0

        for sat_key, mp_result in result.sat_multipath.items():
            if not math.isnan(mp_result.mp1_rms) and mp_result.mp1_epoch_count > 0:
                total_mp1_sum_sq += mp_result.mp1_rms ** 2 * mp_result.mp1_epoch_count
                total_mp1_count += mp_result.mp1_epoch_count
            if not math.isnan(mp_result.mp2_rms) and mp_result.mp2_epoch_count > 0:
                total_mp2_sum_sq += mp_result.mp2_rms ** 2 * mp_result.mp2_epoch_count
                total_mp2_count += mp_result.mp2_epoch_count

        if total_mp1_count > 0:
            result.overall_mp1_rms = math.sqrt(total_mp1_sum_sq / total_mp1_count)
        if total_mp2_count > 0:
            result.overall_mp2_rms = math.sqrt(total_mp2_sum_sq / total_mp2_count)

        # Compute SNR statistics
        sat_snr_results, overall_snr = self._ComputeSnrStats(obsFile)
        result.sat_snr = sat_snr_results

        if overall_snr:
            result.overall_snr_mean = overall_snr.get('mean', 0.0)
            result.pct_good_snr = overall_snr.get('pct_good', 0.0)
            result.pct_fair_snr = overall_snr.get('pct_fair', 0.0)
            result.pct_poor_snr = overall_snr.get('pct_poor', 0.0)

        return result
