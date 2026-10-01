# =============================================================================
# QC Engine: Epoch Sampling and Gap Analysis
# =============================================================================
# Analyses the temporal distribution of observation epochs to detect:
#   - Nominal sampling interval (mode of inter-epoch intervals)
#   - Irregular intervals and their distribution
#   - Data gaps (missing epochs beyond a tolerance)
#   - Observation completeness as a ratio of expected vs actual epochs
#   - Epoch statistics (total, expected, missing)
#
# Units: All time values are in seconds (GPST).

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from collections import Counter
import math

from AnanseQC.Readers.ObsTypes import S_RinexObsFile


#==============================================================================
# \Class: S_GapRecord
# \Brief: One data gap in the observation timeline
#==============================================================================
@dataclass
class S_GapRecord:
    """Describes a single data gap in the observation timeline.

    Attributes:
        start_epoch_idx (int): Index of the epoch before the gap.
        end_epoch_idx (int): Index of the epoch after the gap.
        start_time (float): Absolute GPS time at start of gap (seconds).
        end_time (float): Absolute GPS time at end of gap (seconds).
        duration_seconds (float): Gap duration in seconds.
        missing_epochs (int): Estimated number of missing epochs based on
                              nominal interval.
    """
    start_epoch_idx: int = 0
    end_epoch_idx: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    duration_seconds: float = 0.0
    missing_epochs: int = 0


#==============================================================================
# \Class: S_EpochSamplingResult
# \Brief: Epoch interval, completeness, and gap result
#==============================================================================
@dataclass
class S_EpochSamplingResult:
    """Complete epoch sampling analysis result.

    Attributes:
        total_epochs (int): Total observed epochs.
        expected_epochs (int): Expected epochs based on duration and nominal interval.
        missing_epochs (int): Estimated number of missing epochs (expected - actual).
        completeness_percent (float): Data completeness as percentage (0-100).
        nominal_interval (float): Detected nominal sampling interval in seconds.
        header_interval (float): Interval from RINEX header (0 if not specified).
        mean_interval (float): Mean inter-epoch interval in seconds.
        std_interval (float): Standard deviation of inter-epoch intervals in seconds.
        min_interval (float): Minimum inter-epoch interval in seconds.
        max_interval (float): Maximum inter-epoch interval in seconds.
        interval_histogram (dict): Maps interval_seconds -> count.
        gaps (list): List of S_GapRecord for gaps exceeding 1.5x nominal interval.
        total_gap_duration (float): Sum of all gap durations in seconds.
        num_gaps (int): Number of detected gaps.
        duration_seconds (float): Total observation span in seconds.
        first_epoch_time (float): Absolute GPS time of first epoch.
        last_epoch_time (float): Absolute GPS time of last epoch.
    """
    total_epochs: int = 0
    expected_epochs: int = 0
    missing_epochs: int = 0
    completeness_percent: float = 0.0
    nominal_interval: float = 0.0
    header_interval: float = 0.0
    mean_interval: float = 0.0
    std_interval: float = 0.0
    min_interval: float = 0.0
    max_interval: float = 0.0
    interval_histogram: Dict[float, int] = field(default_factory=dict)
    gaps: List[S_GapRecord] = field(default_factory=list)
    total_gap_duration: float = 0.0
    num_gaps: int = 0
    duration_seconds: float = 0.0
    first_epoch_time: float = 0.0
    last_epoch_time: float = 0.0


#==============================================================================
# \Class: C_EpochSampling
# \Brief: Analyses epoch sampling intervals and data gaps
#==============================================================================
class C_EpochSampling:
    #==============================================================================
    # \Function: Analyse
    # \Brief: Analyses epoch sampling intervals and data gaps
    # \Note:
    #   Time system is GPST. A gap is an inter-epoch interval greater than
    #   1.5 times the nominal interval. Durations are in seconds.
    # \Params:
    #           obsFile         [in]    Parsed RINEX observation file
    # \Returns:
    #           S_EpochSamplingResult
    #==============================================================================
    def Analyse(self, obsFile):
        # Nominal interval is the most common inter-epoch spacing.
        result = S_EpochSamplingResult()
        result.header_interval = obsFile.header.interval

        # Filter to normal observation epochs (flag <= 1)
        timestamps = []
        epoch_indices = []
        for idx, epoch in enumerate(obsFile.epochs):
            if epoch.epoch_flag <= 1:
                timestamps.append(epoch.abs_gps_time)
                epoch_indices.append(idx)

        result.total_epochs = len(timestamps)

        if result.total_epochs < 2:
            # Not enough data to compute intervals
            if result.total_epochs == 1:
                result.first_epoch_time = timestamps[0]
                result.last_epoch_time = timestamps[0]
            return result

        result.first_epoch_time = timestamps[0]
        result.last_epoch_time = timestamps[-1]
        result.duration_seconds = timestamps[-1] - timestamps[0]

        # Compute inter-epoch intervals
        intervals = []
        for i in range(1, len(timestamps)):
            dt = timestamps[i] - timestamps[i - 1]
            intervals.append(dt)

        # Detect nominal interval (mode of intervals, rounded to 0.1 s)
        rounded_intervals = [round(dt, 1) for dt in intervals]
        interval_counter = Counter(rounded_intervals)
        result.interval_histogram = dict(interval_counter)
        nominal_interval = interval_counter.most_common(1)[0][0]

        # If header specifies interval and it matches the mode, prefer it
        if result.header_interval > 0:
            header_rounded = round(result.header_interval, 1)
            if header_rounded in interval_counter:
                nominal_interval = header_rounded

        result.nominal_interval = nominal_interval

        # Interval statistics
        result.mean_interval = sum(intervals) / len(intervals)
        result.min_interval = min(intervals)
        result.max_interval = max(intervals)

        # Standard deviation
        variance = sum((dt - result.mean_interval) ** 2 for dt in intervals) / len(intervals)
        result.std_interval = math.sqrt(variance)

        # Expected epochs and completeness
        if nominal_interval > 0:
            result.expected_epochs = int(round(result.duration_seconds / nominal_interval)) + 1
        else:
            result.expected_epochs = result.total_epochs

        result.missing_epochs = max(0, result.expected_epochs - result.total_epochs)

        if result.expected_epochs > 0:
            result.completeness_percent = (
                100.0 * result.total_epochs / result.expected_epochs
            )
        else:
            result.completeness_percent = 100.0

        # Detect gaps (intervals > 1.5 * nominal)
        gap_threshold = 1.5 * nominal_interval if nominal_interval > 0 else float('inf')

        for i, dt in enumerate(intervals):
            if dt > gap_threshold:
                gap = S_GapRecord()
                gap.start_epoch_idx = epoch_indices[i]
                gap.end_epoch_idx = epoch_indices[i + 1]
                gap.start_time = timestamps[i]
                gap.end_time = timestamps[i + 1]
                gap.duration_seconds = dt

                if nominal_interval > 0:
                    gap.missing_epochs = int(round(dt / nominal_interval)) - 1
                else:
                    gap.missing_epochs = 0

                result.gaps.append(gap)

        result.num_gaps = len(result.gaps)
        result.total_gap_duration = sum(g.duration_seconds for g in result.gaps)

        return result
