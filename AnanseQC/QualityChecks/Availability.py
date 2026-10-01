# =============================================================================
# QC Engine: Observation Availability Analysis
# =============================================================================
# Analyses satellite and observable availability from parsed RINEX data.
#
# Metrics computed:
#   - Per-satellite epoch count and percentage of total epochs
#   - Per-system satellite count over time
#   - Observable completeness (which obs types present per satellite)
#   - Data completeness ratio (actual vs expected observations)
#   - Observation windows (continuous tracking arcs)
#   - Loss-of-lock events (LLI flag transitions)

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from AnanseQC.Core.Enums import eGnss, SYSTEM_TO_CHAR
from AnanseQC.Readers.ObsTypes import S_RinexObsFile


#==============================================================================
# \Class: S_SatAvailability
# \Brief: Availability metrics for one satellite
#==============================================================================
@dataclass
class S_SatAvailability:
    """Availability metrics for a single satellite.

    Attributes:
        system (eGnss): GNSS constellation.
        prn (int): Satellite PRN.
        epoch_count (int): Number of epochs where this satellite was observed.
        epoch_percentage (float): Percentage of total epochs (0-100).
        obs_types_present (set): Set of observation descriptors seen at least once.
        obs_completeness (dict): Maps obs_type -> count of epochs with that observable.
        tracking_arcs (list): List of (start_epoch_idx, end_epoch_idx, duration_epochs).
        gaps (list): List of (start_epoch_idx, end_epoch_idx, gap_epochs).
        lli_events (int): Number of Loss-of-Lock Indicator transitions detected.
        first_epoch_idx (int): Index of first epoch with this satellite.
        last_epoch_idx (int): Index of last epoch with this satellite.
    """
    system: eGnss = eGnss.eUnknownSystem
    prn: int = 0
    epoch_count: int = 0
    epoch_percentage: float = 0.0
    obs_types_present: set = field(default_factory=set)
    obs_completeness: Dict[str, int] = field(default_factory=dict)
    tracking_arcs: List[Tuple[int, int, int]] = field(default_factory=list)
    gaps: List[Tuple[int, int, int]] = field(default_factory=list)
    lli_events: int = 0
    first_epoch_idx: int = -1
    last_epoch_idx: int = -1


#==============================================================================
# \Class: S_SystemAvailability
# \Brief: Availability summary for one GNSS constellation
#==============================================================================
@dataclass
class S_SystemAvailability:
    """Availability summary for one GNSS constellation.

    Attributes:
        system (eGnss): GNSS constellation.
        total_sats_observed (int): Total unique satellites observed.
        sat_details (dict): Maps PRN -> S_SatAvailability.
        sats_per_epoch (list): Number of satellites tracked at each epoch index.
        mean_sats_per_epoch (float): Average satellite count per epoch.
        min_sats_per_epoch (int): Minimum satellite count in any epoch.
        max_sats_per_epoch (int): Maximum satellite count in any epoch.
    """
    system: eGnss = eGnss.eUnknownSystem
    total_sats_observed: int = 0
    sat_details: Dict[int, S_SatAvailability] = field(default_factory=dict)
    sats_per_epoch: List[int] = field(default_factory=list)
    mean_sats_per_epoch: float = 0.0
    min_sats_per_epoch: int = 0
    max_sats_per_epoch: int = 0


#==============================================================================
# \Class: S_AvailabilityResult
# \Brief: Complete satellite and observable availability result
#==============================================================================
@dataclass
class S_AvailabilityResult:
    """Complete availability analysis result.

    Attributes:
        total_epochs (int): Total number of observation epochs.
        total_satellites (int): Total unique satellites observed across all systems.
        systems (dict): Maps eGnss -> S_SystemAvailability.
        obs_type_summary (dict): Maps obs_type_descriptor -> total epochs with that obs.
        duration_seconds (float): Observation duration in seconds.
        first_epoch_time (float): Absolute GPS time of first epoch.
        last_epoch_time (float): Absolute GPS time of last epoch.
    """
    total_epochs: int = 0
    total_satellites: int = 0
    systems: Dict[eGnss, S_SystemAvailability] = field(default_factory=dict)
    obs_type_summary: Dict[str, int] = field(default_factory=dict)
    duration_seconds: float = 0.0
    first_epoch_time: float = 0.0
    last_epoch_time: float = 0.0


#==============================================================================
# \Class: C_ObsAvailability
# \Brief: Analyses satellite and observable availability
#==============================================================================
class C_ObsAvailability:
    #==============================================================================
    # \Function: Analyse
    # \Brief: Analyses satellite and observable availability
    # \Note:
    #   Counts epochs, observation types, tracking arcs, gaps, and LLI events
    #   for each satellite and constellation.
    # \Params:
    #           obsFile         [in]    Parsed RINEX observation file
    # \Returns:
    #           S_AvailabilityResult
    #==============================================================================
    def Analyse(self, obsFile):
        result = S_AvailabilityResult()
        result.total_epochs = len(obsFile.epochs)

        if result.total_epochs == 0:
            return result

        # Set time bounds
        result.first_epoch_time = obsFile.epochs[0].abs_gps_time
        result.last_epoch_time = obsFile.epochs[-1].abs_gps_time
        result.duration_seconds = result.last_epoch_time - result.first_epoch_time

        # Intermediate structures
        # sat_key = (eGnss, prn)
        sat_epoch_indices = defaultdict(list)       # sat_key -> [epoch_idx, ...]
        sat_obs_types = defaultdict(lambda: defaultdict(int))  # sat_key -> {obs_type: count}
        sat_lli_prev = {}                           # sat_key -> previous LLI state (any obs)
        sat_lli_count = defaultdict(int)            # sat_key -> LLI transition count
        sys_epoch_counts = defaultdict(lambda: defaultdict(int))  # eGnss -> {epoch_idx: count}
        obs_type_global = defaultdict(int)          # obs_type -> total count across all sats

        # Scan all epochs
        for epoch_idx, epoch in enumerate(obsFile.epochs):
            # Skip special event epochs
            if epoch.epoch_flag > 1:
                continue

            for sat_obs in epoch.satellites:
                sat_key = (sat_obs.system, sat_obs.prn)

                # Track which epochs this satellite appears in
                sat_epoch_indices[sat_key].append(epoch_idx)

                # Count per-system satellites per epoch
                sys_epoch_counts[sat_obs.system][epoch_idx] = (
                    sys_epoch_counts[sat_obs.system].get(epoch_idx, 0) + 1
                )

                # Track observable completeness
                for obs_type in sat_obs.obs:
                    sat_obs_types[sat_key][obs_type] += 1
                    obs_type_global[obs_type] += 1

                # Track LLI transitions
                current_lli = self._GetLliState(sat_obs)
                prev_lli = sat_lli_prev.get(sat_key)
                if prev_lli is not None and current_lli is not None:
                    if prev_lli != current_lli:
                        sat_lli_count[sat_key] += 1
                if current_lli is not None:
                    sat_lli_prev[sat_key] = current_lli

        # Build per-satellite results
        total_unique_sats = 0

        for sat_key, epoch_list in sat_epoch_indices.items():
            sys_enum, prn = sat_key

            sat_avail = S_SatAvailability()
            sat_avail.system = sys_enum
            sat_avail.prn = prn
            sat_avail.epoch_count = len(epoch_list)
            sat_avail.epoch_percentage = (
                100.0 * len(epoch_list) / result.total_epochs
                if result.total_epochs > 0 else 0.0
            )
            sat_avail.obs_types_present = set(sat_obs_types[sat_key].keys())
            sat_avail.obs_completeness = dict(sat_obs_types[sat_key])
            sat_avail.lli_events = sat_lli_count.get(sat_key, 0)
            sat_avail.first_epoch_idx = epoch_list[0]
            sat_avail.last_epoch_idx = epoch_list[-1]

            # Compute tracking arcs and gaps
            sat_avail.tracking_arcs, sat_avail.gaps = self._ComputeArcsAndGaps(epoch_list)

            # Add to system-level results
            if sys_enum not in result.systems:
                result.systems[sys_enum] = S_SystemAvailability(system=sys_enum)

            result.systems[sys_enum].sat_details[prn] = sat_avail
            total_unique_sats += 1

        # Build per-system summaries
        for sys_enum, sys_avail in result.systems.items():
            sys_avail.total_sats_observed = len(sys_avail.sat_details)

            # Compute sats-per-epoch for this system
            epoch_sat_counts = sys_epoch_counts.get(sys_enum, {})
            sats_per_epoch = []
            for epoch_idx in range(result.total_epochs):
                sats_per_epoch.append(epoch_sat_counts.get(epoch_idx, 0))

            sys_avail.sats_per_epoch = sats_per_epoch
            if sats_per_epoch:
                sys_avail.mean_sats_per_epoch = sum(sats_per_epoch) / len(sats_per_epoch)
                sys_avail.min_sats_per_epoch = min(sats_per_epoch)
                sys_avail.max_sats_per_epoch = max(sats_per_epoch)

        result.total_satellites = total_unique_sats
        result.obs_type_summary = dict(obs_type_global)

        return result


    #==============================================================================
    # \Function: _GetLliState
    # \Brief: Extract a single LLI state value from a S_SatObs for transition detection
    #==============================================================================
    def _GetLliState(self, sat_obs):
        """Extract a single LLI state value from a S_SatObs for transition detection.

        Uses a bitwise OR of all LLI values present to create a composite state.

        Args:
            sat_obs (S_SatObs): Satellite observation data.

        Returns:
            int or None: Composite LLI state, or None if no LLI data available.
        """
        if not sat_obs.lli:
            return None

        composite = 0
        for lli_val in sat_obs.lli.values():
            composite |= lli_val

        return composite


    #==============================================================================
    # \Function: _ComputeArcsAndGaps
    # \Brief: Compute continuous tracking arcs and gaps from sorted epoch index list
    #==============================================================================
    def _ComputeArcsAndGaps(self, epoch_list):
        """Compute continuous tracking arcs and gaps from sorted epoch index list.

        A tracking arc is a contiguous sequence of epoch indices. A gap is the
        break between two arcs.

        Args:
            epoch_list (list): Sorted list of epoch indices where satellite was observed.

        Returns:
            tuple: (arcs, gaps) where:
                arcs: list of (start_idx, end_idx, length)
                gaps: list of (arc_end_idx, next_arc_start_idx, gap_length)
        """
        if not epoch_list:
            return [], []

        arcs = []
        gaps = []

        arc_start = epoch_list[0]
        prev_idx = epoch_list[0]

        for i in range(1, len(epoch_list)):
            curr_idx = epoch_list[i]

            if curr_idx == prev_idx + 1:
                # Contiguous - extend current arc
                prev_idx = curr_idx
            else:
                # Gap detected - end current arc, record gap
                arc_length = prev_idx - arc_start + 1
                arcs.append((arc_start, prev_idx, arc_length))

                gap_length = curr_idx - prev_idx - 1
                gaps.append((prev_idx, curr_idx, gap_length))

                # Start new arc
                arc_start = curr_idx
                prev_idx = curr_idx

        # Close the final arc
        arc_length = prev_idx - arc_start + 1
        arcs.append((arc_start, prev_idx, arc_length))

        return arcs, gaps
