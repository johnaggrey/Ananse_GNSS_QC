# =============================================================================
# QC Engine: Cycle Slip Detection
# =============================================================================
# Detects cycle slips in carrier phase observations using two methods:
#
# 1. Time-Differenced Carrier Phase (TDCP)
#    - Computes epoch-to-epoch phase differences for each satellite
#    - Detects jumps exceeding a configurable threshold (in cycles)
#    - Simple, works with single-frequency data
#
# 2. Melbourne-Wübbena (MW) Combination
#    - Combines dual-frequency code and phase to form the widelane ambiguity
#    - MW = L_WL - N_NL  (widelane phase minus narrowlane code, in metres)
#    - Detects jumps in the MW time series (which should be constant)
#    - More robust than TDCP; requires dual-frequency data
#
# Reference:
#   Melbourne, W. (1985). The case for ranging in GPS-based geodetic systems.
#   Wübbena, G. (1985). Software developments for geodetic positioning with GPS.
#
# Units:
#   - Carrier phase: cycles (as stored in RINEX)
#   - Pseudorange: metres
#   - Frequencies: Hz (from constants module)
#   - Wavelengths: metres

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import math

from AnanseQC.Core.Enums import eGnss, SYSTEM_TO_CHAR
from AnanseQC.Core import Constants as C
from AnanseQC.Readers.ObsTypes import S_RinexObsFile, S_SatObs


# =============================================================================
# Configuration
# =============================================================================
# TDCP threshold: jumps exceeding this many cycles are flagged as slips
TDCP_THRESHOLD_CYCLES = 0.5

# MW threshold: jumps exceeding this many widelane cycles are flagged
MW_THRESHOLD_CYCLES = 1.0

# Minimum SNR for including a measurement in slip detection (dBHz)
MIN_SNR_FOR_SLIP = 0.0


#==============================================================================
# \Class: S_SlipEvent
# \Brief: One detected cycle slip
#==============================================================================
@dataclass
class S_SlipEvent:
    """Describes a single detected cycle slip event.

    Attributes:
        epoch_idx (int): Epoch index where the slip was detected.
        time (float): Absolute GPS time at the slip epoch.
        system (eGnss): GNSS constellation.
        prn (int): Satellite PRN.
        method (str): Detection method ('TDCP' or 'MW').
        obs_type (str): Observation descriptor involved (e.g. 'L1C', 'L2W').
        magnitude (float): Estimated slip magnitude in cycles.
    """
    epoch_idx: int = 0
    time: float = 0.0
    system: eGnss = eGnss.eUnknownSystem
    prn: int = 0
    method: str = ''
    obs_type: str = ''
    magnitude: float = 0.0


#==============================================================================
# \Class: S_SatSlipSummary
# \Brief: Cycle-slip summary for one satellite
#==============================================================================
@dataclass
class S_SatSlipSummary:
    """Cycle slip summary for a single satellite.

    Attributes:
        system (eGnss): GNSS constellation.
        prn (int): Satellite PRN.
        tdcp_slips (int): Number of TDCP-detected slips.
        mw_slips (int): Number of MW-detected slips.
        total_slips (int): Total unique slip events.
        slip_rate (float): Slips per hour of tracking.
        events (list): List of S_SlipEvent objects.
    """
    system: eGnss = eGnss.eUnknownSystem
    prn: int = 0
    tdcp_slips: int = 0
    mw_slips: int = 0
    total_slips: int = 0
    slip_rate: float = 0.0
    events: List[S_SlipEvent] = field(default_factory=list)


#==============================================================================
# \Class: S_CycleSlipResult
# \Brief: Complete cycle-slip analysis result
#==============================================================================
@dataclass
class S_CycleSlipResult:
    """Complete cycle slip analysis result.

    Attributes:
        total_tdcp_slips (int): Total TDCP-detected slips across all satellites.
        total_mw_slips (int): Total MW-detected slips across all satellites.
        total_slips (int): Total slip events across all satellites.
        mean_slip_rate (float): Average slips per hour across all satellites.
        satellites (dict): Maps (eGnss, prn) -> S_SatSlipSummary.
        all_events (list): Chronological list of all S_SlipEvent objects.
    """
    total_tdcp_slips: int = 0
    total_mw_slips: int = 0
    total_slips: int = 0
    mean_slip_rate: float = 0.0
    satellites: Dict[Tuple[eGnss, int], S_SatSlipSummary] = field(default_factory=dict)
    all_events: List[S_SlipEvent] = field(default_factory=list)


# =============================================================================
# Frequency / Wavelength Helpers
# =============================================================================

#==============================================================================
# \Class: C_CycleSlipDetector
# \Brief: Detects carrier-phase cycle slips with TDCP and Melbourne-Wubbena
#==============================================================================
class C_CycleSlipDetector:
    #==============================================================================
    # \Function: _GetFrequencyHz
    # \Brief: Get the carrier frequency in Hz for a given obs descriptor
    #==============================================================================
    def _GetFrequencyHz(self, system, obs_descriptor):
        """Get the carrier frequency in Hz for a given obs descriptor.

        Determines the frequency from the RINEX band number (second character
        of a 3-character descriptor like 'L1C', 'L2W', etc.).

        Args:
            system (eGnss): Satellite constellation.
            obs_descriptor (str): 3-character observation descriptor (e.g. 'L1C').

        Returns:
            float or None: Frequency in Hz, or None if unknown.
        """
        if len(obs_descriptor) < 2:
            return None

        try:
            band = int(obs_descriptor[1])
        except ValueError:
            return None

        freq_map = {
            eGnss.eGPS: {1: C.GPS_L1, 2: C.GPS_L2, 5: C.GPS_L5},
            eGnss.eGLN: {1: C.GLN_BASEFREQ_G1, 2: C.GLN_BASEFREQ_G2, 3: C.GLN_G3},
            eGnss.eGAL: {1: C.GAL_E1, 5: C.GAL_E5A, 6: C.GAL_E6,
                                 7: C.GAL_E5B, 8: C.GAL_E5},
            eGnss.eBDS: {1: C.BDS3_B1C, 2: C.BDS2_B1, 5: C.BDS3_B2A,
                                6: C.BDS3_B3, 7: C.BDS3_B2B, 8: C.BDS3_B2AB},
            eGnss.eQZSS: {1: C.QZSS_L1, 2: C.QZSS_L2, 5: C.QZSS_L5,
                              6: C.QZSS_L6},
            eGnss.eSBAS: {1: C.SBAS_L1, 5: C.SBAS_L5},
            eGnss.eNavIC: {1: C.NAVIC_L1, 5: C.NAVIC_L5, 9: C.NAVIC_S},
        }

        sys_freqs = freq_map.get(system)
        if sys_freqs is None:
            return None

        return sys_freqs.get(band)


    #==============================================================================
    # \Function: _Wavelength
    # \Brief: Compute wavelength in metres from frequency in Hz
    #==============================================================================
    def _Wavelength(self, freq_hz):
        """Compute wavelength in metres from frequency in Hz."""
        if freq_hz is None or freq_hz == 0.0:
            return None
        return C.CLIGHT / freq_hz


    # =============================================================================
    # Time-Differenced Carrier Phase (TDCP) Detection
    # =============================================================================

    #==============================================================================
    # \Function: _DetectTdcpSlips
    # \Brief: Detect cycle slips using Time-Differenced Carrier Phase
    #==============================================================================
    def _DetectTdcpSlips(self, obs_file, threshold_cycles=TDCP_THRESHOLD_CYCLES):
        """Detect cycle slips using Time-Differenced Carrier Phase.

        For each satellite and carrier phase observable, computes the epoch-to-epoch
        difference. Jumps exceeding the threshold are flagged as slips.

        Args:
            obs_file (S_RinexObsFile): Parsed RINEX observation data.
            threshold_cycles (float): Slip detection threshold in cycles.

        Returns:
            list: List of S_SlipEvent objects.
        """
        events = []

        # Build per-satellite phase time series
        # sat_key = (eGnss, prn)
        # phase_series[sat_key][obs_type] = [(epoch_idx, abs_time, phase_cycles), ...]
        phase_series = defaultdict(lambda: defaultdict(list))

        for idx, epoch in enumerate(obs_file.epochs):
            if epoch.epoch_flag > 1:
                continue

            for sat in epoch.satellites:
                sat_key = (sat.system, sat.prn)
                for obs_type, value in sat.obs.items():
                    # Only process carrier phase observations (L*)
                    if obs_type.startswith('L') and len(obs_type) >= 2:
                        phase_series[sat_key][obs_type].append(
                            (idx, epoch.abs_gps_time, value)
                        )

        # Detect slips in each time series
        for sat_key, obs_dict in phase_series.items():
            system, prn = sat_key

            for obs_type, series in obs_dict.items():
                if len(series) < 2:
                    continue

                for i in range(1, len(series)):
                    prev_idx, prev_time, prev_phase = series[i - 1]
                    curr_idx, curr_time, curr_phase = series[i]

                    # Skip if time gap is too large (> 120 seconds => likely re-acquisition)
                    dt = curr_time - prev_time
                    if dt > 120.0:
                        continue

                    # Compute phase difference in cycles
                    dphase = curr_phase - prev_phase

                    # For slip detection, we look at the *fractional* part
                    # since the integer part changes due to satellite motion.
                    # However, TDCP is really delta-phase minus expected range-rate.
                    # Without range rate, we check if the change is "too large"
                    # relative to typical values.
                    # A simpler approach: check if |dphase - median_dphase| > threshold
                    # For now, we flag using a threshold on the second difference
                    # (acceleration-like metric).

                    if i >= 2:
                        prev2_idx, prev2_time, prev2_phase = series[i - 2]
                        dt2 = prev_time - prev2_time
                        if dt2 > 0 and dt > 0 and dt2 < 120.0:
                            dphase_prev = prev_phase - prev2_phase
                            # Second difference (change in phase rate)
                            ddphase = dphase - dphase_prev
                            if abs(ddphase) > threshold_cycles:
                                event = S_SlipEvent()
                                event.epoch_idx = curr_idx
                                event.time = curr_time
                                event.system = system
                                event.prn = prn
                                event.method = 'TDCP'
                                event.obs_type = obs_type
                                event.magnitude = ddphase
                                events.append(event)

        return events


    # =============================================================================
    # Melbourne-Wübbena Detection
    # =============================================================================

    #==============================================================================
    # \Function: _FindDualFreqPairs
    # \Brief: Find matching dual-frequency code+phase pairs for MW combination
    #==============================================================================
    def _FindDualFreqPairs(self, sat_obs, system):
        """Find matching dual-frequency code+phase pairs for MW combination.

        Looks for pairs of (L_f1, L_f2, P_f1, P_f2) where f1 and f2 are
        different frequencies for the same satellite.

        Args:
            sat_obs (S_SatObs): Satellite observations for one epoch.
            system (eGnss): GNSS constellation.

        Returns:
            list: List of dicts with keys 'L1','L2','P1','P2','f1','f2','band1','band2'.
        """
        # Collect available phase and code observations by band number
        phases = {}   # band -> (obs_type, value)
        codes = {}    # band -> (obs_type, value)

        for obs_type, value in sat_obs.obs.items():
            if len(obs_type) < 2:
                continue
            try:
                band = int(obs_type[1])
            except ValueError:
                continue

            if obs_type.startswith('L'):
                if band not in phases:
                    phases[band] = (obs_type, value)
            elif obs_type.startswith('C') or obs_type.startswith('P'):
                if band not in codes:
                    codes[band] = (obs_type, value)

        # Find all valid dual-frequency pairs
        pairs = []
        band_list = sorted(set(phases.keys()) & set(codes.keys()))

        for i in range(len(band_list)):
            for j in range(i + 1, len(band_list)):
                b1 = band_list[i]
                b2 = band_list[j]

                f1 = self._GetFrequencyHz(system, phases[b1][0])
                f2 = self._GetFrequencyHz(system, phases[b2][0])

                if f1 is not None and f2 is not None and f1 != f2:
                    pairs.append({
                        'L1_type': phases[b1][0], 'L1_val': phases[b1][1],
                        'L2_type': phases[b2][0], 'L2_val': phases[b2][1],
                        'P1_type': codes[b1][0], 'P1_val': codes[b1][1],
                        'P2_type': codes[b2][0], 'P2_val': codes[b2][1],
                        'f1': f1, 'f2': f2,
                        'band1': b1, 'band2': b2,
                    })

        return pairs


    #==============================================================================
    # \Function: _ComputeMw
    # \Brief: Compute the Melbourne-Wübbena combination
    #==============================================================================
    def _ComputeMw(self, L1_cycles, L2_cycles, P1_m, P2_m, f1, f2):
        """Compute the Melbourne-Wübbena combination.

        MW = L_WL - P_NL  (in metres, then converted to widelane cycles)

        Where:
            L_WL = (f1*L1 - f2*L2) / (f1 - f2)  [widelane phase in metres]
            P_NL = (f1*P1 + f2*P2) / (f1 + f2)  [narrowlane code in metres]

        The result is expressed in widelane wavelengths (cycles).

        Args:
            L1_cycles (float): Phase on frequency 1 in cycles.
            L2_cycles (float): Phase on frequency 2 in cycles.
            P1_m (float): Pseudorange on frequency 1 in metres.
            P2_m (float): Pseudorange on frequency 2 in metres.
            f1 (float): Frequency 1 in Hz.
            f2 (float): Frequency 2 in Hz.

        Returns:
            float: MW combination in widelane cycles.
        """
        # Wavelengths in metres
        lambda1 = C.CLIGHT / f1
        lambda2 = C.CLIGHT / f2
        lambda_wl = C.CLIGHT / (f1 - f2)  # Widelane wavelength

        # Convert phase from cycles to metres
        L1_m = L1_cycles * lambda1
        L2_m = L2_cycles * lambda2

        # Widelane phase combination (metres)
        L_wl = (f1 * L1_m - f2 * L2_m) / (f1 - f2)

        # Narrowlane code combination (metres)
        P_nl = (f1 * P1_m + f2 * P2_m) / (f1 + f2)

        # MW in widelane cycles
        mw_cycles = (L_wl - P_nl) / lambda_wl

        return mw_cycles


    #==============================================================================
    # \Function: _DetectMwSlips
    # \Brief: Detect cycle slips using the Melbourne-Wübbena combination
    #==============================================================================
    def _DetectMwSlips(self, obs_file, threshold_cycles=MW_THRESHOLD_CYCLES):
        """Detect cycle slips using the Melbourne-Wübbena combination.

        Computes MW for each satellite and dual-frequency pair across epochs,
        then detects jumps in the MW time series.

        Args:
            obs_file (S_RinexObsFile): Parsed RINEX observation data.
            threshold_cycles (float): Slip detection threshold in widelane cycles.

        Returns:
            list: List of S_SlipEvent objects.
        """
        events = []

        # Build per-satellite MW time series
        # mw_key = (eGnss, prn, band1, band2)
        mw_series = defaultdict(list)  # mw_key -> [(epoch_idx, abs_time, mw_val)]

        for idx, epoch in enumerate(obs_file.epochs):
            if epoch.epoch_flag > 1:
                continue

            for sat in epoch.satellites:
                pairs = self._FindDualFreqPairs(sat, sat.system)
                for pair in pairs:
                    mw_val = self._ComputeMw(
                        pair['L1_val'], pair['L2_val'],
                        pair['P1_val'], pair['P2_val'],
                        pair['f1'], pair['f2']
                    )
                    mw_key = (sat.system, sat.prn, pair['band1'], pair['band2'])
                    mw_series[mw_key].append((idx, epoch.abs_gps_time, mw_val))

        # Detect jumps in MW time series
        for mw_key, series in mw_series.items():
            system, prn, band1, band2 = mw_key

            if len(series) < 2:
                continue

            for i in range(1, len(series)):
                prev_idx, prev_time, prev_mw = series[i - 1]
                curr_idx, curr_time, curr_mw = series[i]

                # Skip large time gaps
                dt = curr_time - prev_time
                if dt > 120.0:
                    continue

                dmw = curr_mw - prev_mw
                if abs(dmw) > threshold_cycles:
                    event = S_SlipEvent()
                    event.epoch_idx = curr_idx
                    event.time = curr_time
                    event.system = system
                    event.prn = prn
                    event.method = 'MW'
                    event.obs_type = f'L{band1}-L{band2}'
                    event.magnitude = dmw
                    events.append(event)

        return events


    # =============================================================================
    # Public API
    # =============================================================================

    #==============================================================================
    # \Function: Analyse
    # \Brief: Detects carrier-phase cycle slips with TDCP and Melbourne-Wubbena
    # \Note:
    #   TDCP uses a second difference of carrier phase, in cycles.
    #   Melbourne-Wubbena uses the widelane combination, in widelane cycles.
    # \Params:
    #           obsFile         [in]    Parsed RINEX observation file
    #           tdcpThreshold   [in]    TDCP slip threshold, cycles
    #           mwThreshold     [in]    Melbourne-Wubbena threshold, widelane cycles
    # \Returns:
    #           S_CycleSlipResult
    #==============================================================================
    def Analyse(self, obsFile,
                tdcpThreshold=TDCP_THRESHOLD_CYCLES,
                mwThreshold=MW_THRESHOLD_CYCLES):
        result = S_CycleSlipResult()

        # Run both detection methods
        tdcp_events = self._DetectTdcpSlips(obsFile, tdcpThreshold)
        mw_events = self._DetectMwSlips(obsFile, mwThreshold)

        result.total_tdcp_slips = len(tdcp_events)
        result.total_mw_slips = len(mw_events)

        # Merge all events and sort chronologically
        all_events = tdcp_events + mw_events
        all_events.sort(key=lambda e: (e.epoch_idx, e.system.value, e.prn))
        result.all_events = all_events
        result.total_slips = len(all_events)

        # Build per-satellite summaries
        sat_summaries = {}
        for event in all_events:
            sat_key = (event.system, event.prn)
            if sat_key not in sat_summaries:
                sat_summaries[sat_key] = S_SatSlipSummary(
                    system=event.system, prn=event.prn
                )
            summary = sat_summaries[sat_key]
            summary.events.append(event)

            if event.method == 'TDCP':
                summary.tdcp_slips += 1
            elif event.method == 'MW':
                summary.mw_slips += 1

        # Compute slip rates (slips per hour)
        if len(obsFile.epochs) >= 2:
            total_duration_hours = (
                (obsFile.epochs[-1].abs_gps_time - obsFile.epochs[0].abs_gps_time)
                / C.SECONDS_IN_HOUR
            )
        else:
            total_duration_hours = 0.0

        total_slip_rates = []
        for sat_key, summary in sat_summaries.items():
            summary.total_slips = summary.tdcp_slips + summary.mw_slips
            if total_duration_hours > 0:
                summary.slip_rate = summary.total_slips / total_duration_hours
            total_slip_rates.append(summary.slip_rate)

        result.satellites = sat_summaries

        if total_slip_rates:
            result.mean_slip_rate = sum(total_slip_rates) / len(total_slip_rates)

        return result
