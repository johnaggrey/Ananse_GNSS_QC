# =============================================================================
# QC Report Generator
# =============================================================================
# Produces human-readable text and machine-readable JSON reports from the
# combined QC analysis results.
#
# The report aggregates results from all QC engines:
#   - Observation availability
#   - Epoch sampling / gap analysis
#   - Cycle slip detection
#   - Multipath and SNR quality
#
# Output formats:
#   - Plain text (for terminal display and log files)
#   - JSON (for web API responses and programmatic consumption)

import json
import math
from datetime import datetime
from typing import Optional

from AnanseQC.Core.Enums import SYSTEM_TO_CHAR, eGnss
from AnanseQC.Core.TimeUtils import C_TimeUtils
from AnanseQC.Readers.ObsTypes import S_RinexObsFile
from AnanseQC.QualityChecks.Availability import S_AvailabilityResult
from AnanseQC.QualityChecks.EpochSampling import S_EpochSamplingResult
from AnanseQC.QualityChecks.CycleSlips import S_CycleSlipResult
from AnanseQC.QualityChecks.MultipathSnr import S_MultipathSnrResult


#==============================================================================
# \Class: C_QcReport
# \Brief: Builds text and JSON quality-control reports
#==============================================================================
class C_QcReport:
    #==============================================================================
    # \Function: _FormatGpsTime
    # \Brief: Format absolute GPS time as a human-readable string
    #==============================================================================
    def _FormatGpsTime(self, abs_gps_time):
        """Format absolute GPS time as a human-readable string."""
        if abs_gps_time <= 0:
            return 'N/A'
        c_TimeUtils = C_TimeUtils()
        gpsWeek, sow = c_TimeUtils.AbsGpsTimeToGpsWeekSec(abs_gps_time)
        y, m, d, hh, mm, ss = c_TimeUtils.GpsWeekSecToYmdhms(gpsWeek, sow)
        return f"{y:04d}-{m:02d}-{int(d):02d} {hh:02d}:{mm:02d}:{ss:05.2f} GPST"


    #==============================================================================
    # \Function: _FormatDuration
    # \Brief: Format a duration in seconds as HH:MM:SS
    #==============================================================================
    def _FormatDuration(self, seconds):
        """Format a duration in seconds as HH:MM:SS."""
        if seconds <= 0:
            return '00:00:00'
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:05.2f}"


    #==============================================================================
    # \Function: _SafeNan
    # \Brief: Convert NaN to None for JSON serialisation
    #==============================================================================
    def _SafeNan(self, val):
        """Convert NaN to None for JSON serialisation."""
        if isinstance(val, float) and math.isnan(val):
            return None
        return val


    # =============================================================================
    # Text Report
    # =============================================================================

    #==============================================================================
    # \Function: GenerateText
    # \Brief: Builds a human-readable QC report
    # \Params:
    #           obsFile         [in]    Parsed RINEX observation file
    #           availability    [in]    S_AvailabilityResult, or None
    #           sampling        [in]    S_EpochSamplingResult, or None
    #           slips           [in]    S_CycleSlipResult, or None
    #           multipathSnr    [in]    S_MultipathSnrResult, or None
    # \Returns:
    #           str             Formatted text report
    #==============================================================================
    def GenerateText(self, obsFile,
                     availability=None,
                     sampling=None,
                     slips=None,
                     multipathSnr=None):
        lines = []
        sep = '=' * 78
        thin_sep = '-' * 78

        lines.append(sep)
        lines.append('  ANANSE GNSS QC REPORT')
        lines.append(sep)
        lines.append('')

        # --- File Information ---
        h = obsFile.header
        lines.append('FILE INFORMATION')
        lines.append(thin_sep)
        lines.append(f"  File:             {obsFile.file_path}")
        lines.append(f"  RINEX Version:    {h.version}")
        lines.append(f"  Marker Name:      {h.marker_name}")
        lines.append(f"  Marker Number:    {h.marker_number}")
        lines.append(f"  Receiver:         {h.receiver_type} (s/n {h.receiver_number})")
        lines.append(f"  Antenna:          {h.antenna_type} (s/n {h.antenna_number})")
        lines.append(f"  Approx Position:  X={h.approx_position[0]:.4f}  "
                     f"Y={h.approx_position[1]:.4f}  Z={h.approx_position[2]:.4f} m (ECEF)")
        lines.append(f"  Antenna Delta:    H={h.antenna_delta[0]:.4f}  "
                     f"E={h.antenna_delta[1]:.4f}  N={h.antenna_delta[2]:.4f} m")
        lines.append('')

        # --- Observation Summary ---
        if availability is not None:
            lines.append('OBSERVATION SUMMARY')
            lines.append(thin_sep)
            lines.append(f"  Total Epochs:     {availability.total_epochs}")
            lines.append(f"  Duration:         {self._FormatDuration(availability.duration_seconds)}")
            lines.append(f"  First Epoch:      {self._FormatGpsTime(availability.first_epoch_time)}")
            lines.append(f"  Last Epoch:       {self._FormatGpsTime(availability.last_epoch_time)}")
            lines.append(f"  Total Satellites: {availability.total_satellites}")
            lines.append('')

            # Per-system summary
            for sys_enum in sorted(availability.systems.keys(), key=lambda s: s.value):
                sys_avail = availability.systems[sys_enum]
                sys_char = SYSTEM_TO_CHAR.get(sys_enum, '?')
                sys_name = sys_enum.name
                lines.append(f"  {sys_name} ({sys_char}): {sys_avail.total_sats_observed} satellites, "
                             f"avg {sys_avail.mean_sats_per_epoch:.1f}/epoch "
                             f"(min {sys_avail.min_sats_per_epoch}, max {sys_avail.max_sats_per_epoch})")

                # Top-level satellite list with epoch counts
                sorted_sats = sorted(sys_avail.sat_details.items())
                for prn, sat_detail in sorted_sats:
                    lines.append(f"    {sys_char}{prn:02d}: {sat_detail.epoch_count} epochs "
                                 f"({sat_detail.epoch_percentage:.1f}%), "
                                 f"{len(sat_detail.tracking_arcs)} arc(s), "
                                 f"{sat_detail.lli_events} LLI events")

            lines.append('')

        # --- Epoch Sampling ---
        if sampling is not None:
            lines.append('EPOCH SAMPLING')
            lines.append(thin_sep)
            lines.append(f"  Nominal Interval: {sampling.nominal_interval:.1f} s")
            lines.append(f"  Header Interval:  {sampling.header_interval:.1f} s")
            lines.append(f"  Mean Interval:    {sampling.mean_interval:.2f} s "
                         f"(std: {sampling.std_interval:.3f} s)")
            lines.append(f"  Interval Range:   {sampling.min_interval:.2f} - "
                         f"{sampling.max_interval:.2f} s")
            lines.append(f"  Expected Epochs:  {sampling.expected_epochs}")
            lines.append(f"  Actual Epochs:    {sampling.total_epochs}")
            lines.append(f"  Missing Epochs:   {sampling.missing_epochs}")
            lines.append(f"  Completeness:     {sampling.completeness_percent:.1f}%")
            lines.append(f"  Data Gaps:        {sampling.num_gaps}")
            if sampling.num_gaps > 0:
                lines.append(f"  Total Gap Time:   {self._FormatDuration(sampling.total_gap_duration)}")
                for i, gap in enumerate(sampling.gaps[:20], 1):
                    lines.append(f"    Gap {i:3d}: {self._FormatDuration(gap.duration_seconds)} "
                                 f"({gap.missing_epochs} missing epochs) at epoch {gap.start_epoch_idx}")
                if sampling.num_gaps > 20:
                    lines.append(f"    ... and {sampling.num_gaps - 20} more gaps")
            lines.append('')

        # --- Cycle Slips ---
        if slips is not None:
            lines.append('CYCLE SLIPS')
            lines.append(thin_sep)
            lines.append(f"  TDCP Slips:       {slips.total_tdcp_slips}")
            lines.append(f"  MW Slips:         {slips.total_mw_slips}")
            lines.append(f"  Total Slips:      {slips.total_slips}")
            lines.append(f"  Mean Slip Rate:   {slips.mean_slip_rate:.2f} slips/hour")

            if slips.satellites:
                lines.append('')
                lines.append('  Satellite        TDCP  MW   Total  Rate(/hr)')
                lines.append('  ' + '-' * 50)
                for sat_key in sorted(slips.satellites.keys(),
                                       key=lambda k: (k[0].value, k[1])):
                    summary = slips.satellites[sat_key]
                    sys_char = SYSTEM_TO_CHAR.get(summary.system, '?')
                    lines.append(f"  {sys_char}{summary.prn:02d}             "
                                 f"{summary.tdcp_slips:5d} {summary.mw_slips:4d} "
                                 f"{summary.total_slips:6d}  {summary.slip_rate:8.2f}")
            lines.append('')

        # --- Multipath & SNR ---
        if multipathSnr is not None:
            lines.append('MULTIPATH & SIGNAL QUALITY')
            lines.append(thin_sep)
            mp1_str = (f"{multipathSnr.overall_mp1_rms:.4f} m"
                       if not math.isnan(multipathSnr.overall_mp1_rms) else "N/A")
            mp2_str = (f"{multipathSnr.overall_mp2_rms:.4f} m"
                       if not math.isnan(multipathSnr.overall_mp2_rms) else "N/A")
            lines.append(f"  Overall MP1 RMS:  {mp1_str}")
            lines.append(f"  Overall MP2 RMS:  {mp2_str}")
            lines.append(f"  Mean SNR:         {multipathSnr.overall_snr_mean:.1f} dBHz")
            lines.append(f"  SNR Good (>=35):  {multipathSnr.pct_good_snr:.1f}%")
            lines.append(f"  SNR Fair (25-35): {multipathSnr.pct_fair_snr:.1f}%")
            lines.append(f"  SNR Poor (<25):   {multipathSnr.pct_poor_snr:.1f}%")

            if multipathSnr.sat_multipath:
                lines.append('')
                lines.append('  Satellite   MP1 RMS(m)  MP2 RMS(m)  Epochs')
                lines.append('  ' + '-' * 50)
                for sat_key in sorted(multipathSnr.sat_multipath.keys(),
                                       key=lambda k: (k[0].value, k[1])):
                    mp = multipathSnr.sat_multipath[sat_key]
                    sys_char = SYSTEM_TO_CHAR.get(mp.system, '?')
                    mp1 = f"{mp.mp1_rms:.4f}" if not math.isnan(mp.mp1_rms) else "  N/A "
                    mp2 = f"{mp.mp2_rms:.4f}" if not math.isnan(mp.mp2_rms) else "  N/A "
                    lines.append(f"  {sys_char}{mp.prn:02d}        "
                                 f"{mp1:>10s}  {mp2:>10s}  {mp.mp1_epoch_count:6d}")
            lines.append('')

        lines.append(sep)
        lines.append(f"  Report generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        lines.append(f"  Ananse GNSS QC v0.1.0")
        lines.append(sep)

        return '\n'.join(lines)


    # =============================================================================
    # JSON Report
    # =============================================================================

    #==============================================================================
    # \Function: GenerateJson
    # \Brief: Builds a machine-readable QC report dictionary
    # \Params:
    #           obsFile         [in]    Parsed RINEX observation file
    #           availability    [in]    S_AvailabilityResult, or None
    #           sampling        [in]    S_EpochSamplingResult, or None
    #           slips           [in]    S_CycleSlipResult, or None
    #           multipathSnr    [in]    S_MultipathSnrResult, or None
    # \Returns:
    #           dict            JSON-serialisable report
    #==============================================================================
    def GenerateJson(self, obsFile,
                     availability=None,
                     sampling=None,
                     slips=None,
                     multipathSnr=None):
        h = obsFile.header
        report = {
            'version': '0.1.0',
            'generated_utc': datetime.utcnow().isoformat(),
            'file_info': {
                'file_path': obsFile.file_path,
                'rinex_version': h.version,
                'marker_name': h.marker_name,
                'marker_number': h.marker_number,
                'receiver_type': h.receiver_type,
                'receiver_number': h.receiver_number,
                'antenna_type': h.antenna_type,
                'antenna_number': h.antenna_number,
                'approx_position_ecef_m': list(h.approx_position),
                'antenna_delta_hen_m': list(h.antenna_delta),
            },
        }

        if availability is not None:
            sys_data = {}
            for sys_enum, sys_avail in availability.systems.items():
                sys_char = SYSTEM_TO_CHAR.get(sys_enum, '?')
                sat_list = []
                for prn, sat_d in sorted(sys_avail.sat_details.items()):
                    sat_list.append({
                        'prn': prn,
                        'epoch_count': sat_d.epoch_count,
                        'epoch_percentage': round(sat_d.epoch_percentage, 2),
                        'tracking_arcs': len(sat_d.tracking_arcs),
                        'lli_events': sat_d.lli_events,
                        'obs_types': sorted(list(sat_d.obs_types_present)),
                    })
                sys_data[sys_char] = {
                    'name': sys_enum.name,
                    'total_satellites': sys_avail.total_sats_observed,
                    'mean_sats_per_epoch': round(sys_avail.mean_sats_per_epoch, 2),
                    'min_sats_per_epoch': sys_avail.min_sats_per_epoch,
                    'max_sats_per_epoch': sys_avail.max_sats_per_epoch,
                    'satellites': sat_list,
                }

            report['availability'] = {
                'total_epochs': availability.total_epochs,
                'total_satellites': availability.total_satellites,
                'duration_seconds': round(availability.duration_seconds, 2),
                'first_epoch_gpst': self._FormatGpsTime(availability.first_epoch_time),
                'last_epoch_gpst': self._FormatGpsTime(availability.last_epoch_time),
                'systems': sys_data,
            }

        if sampling is not None:
            gap_list = []
            for gap in sampling.gaps:
                gap_list.append({
                    'start_epoch_idx': gap.start_epoch_idx,
                    'end_epoch_idx': gap.end_epoch_idx,
                    'duration_seconds': round(gap.duration_seconds, 2),
                    'missing_epochs': gap.missing_epochs,
                })

            report['epoch_sampling'] = {
                'nominal_interval_s': sampling.nominal_interval,
                'header_interval_s': sampling.header_interval,
                'mean_interval_s': round(sampling.mean_interval, 3),
                'std_interval_s': round(sampling.std_interval, 4),
                'min_interval_s': round(sampling.min_interval, 3),
                'max_interval_s': round(sampling.max_interval, 3),
                'total_epochs': sampling.total_epochs,
                'expected_epochs': sampling.expected_epochs,
                'missing_epochs': sampling.missing_epochs,
                'completeness_percent': round(sampling.completeness_percent, 2),
                'num_gaps': sampling.num_gaps,
                'total_gap_duration_s': round(sampling.total_gap_duration, 2),
                'gaps': gap_list,
            }

        if slips is not None:
            sat_slips = []
            for sat_key in sorted(slips.satellites.keys(),
                                   key=lambda k: (k[0].value, k[1])):
                s = slips.satellites[sat_key]
                sys_char = SYSTEM_TO_CHAR.get(s.system, '?')
                sat_slips.append({
                    'satellite': f"{sys_char}{s.prn:02d}",
                    'tdcp_slips': s.tdcp_slips,
                    'mw_slips': s.mw_slips,
                    'total_slips': s.total_slips,
                    'slip_rate_per_hour': round(s.slip_rate, 3),
                })

            report['cycle_slips'] = {
                'total_tdcp_slips': slips.total_tdcp_slips,
                'total_mw_slips': slips.total_mw_slips,
                'total_slips': slips.total_slips,
                'mean_slip_rate_per_hour': round(slips.mean_slip_rate, 3),
                'satellites': sat_slips,
            }

        if multipathSnr is not None:
            sat_mp_list = []
            for sat_key in sorted(multipathSnr.sat_multipath.keys(),
                                   key=lambda k: (k[0].value, k[1])):
                mp = multipathSnr.sat_multipath[sat_key]
                sys_char = SYSTEM_TO_CHAR.get(mp.system, '?')
                sat_mp_list.append({
                    'satellite': f"{sys_char}{mp.prn:02d}",
                    'mp1_rms_m': self._SafeNan(round(mp.mp1_rms, 5) if not math.isnan(mp.mp1_rms) else float('nan')),
                    'mp2_rms_m': self._SafeNan(round(mp.mp2_rms, 5) if not math.isnan(mp.mp2_rms) else float('nan')),
                    'epoch_count': mp.mp1_epoch_count,
                })

            report['multipath_snr'] = {
                'overall_mp1_rms_m': self._SafeNan(multipathSnr.overall_mp1_rms),
                'overall_mp2_rms_m': self._SafeNan(multipathSnr.overall_mp2_rms),
                'overall_snr_mean_dbhz': round(multipathSnr.overall_snr_mean, 2),
                'pct_good_snr': round(multipathSnr.pct_good_snr, 2),
                'pct_fair_snr': round(multipathSnr.pct_fair_snr, 2),
                'pct_poor_snr': round(multipathSnr.pct_poor_snr, 2),
                'satellites': sat_mp_list,
            }

        return report


    #==============================================================================
    # \Function: ToJsonString
    # \Brief: Serialises a report dictionary to a JSON string
    # \Params:
    #           reportDict      [in]    Dictionary from GenerateJson
    #           indent          [in]    JSON indentation, spaces
    # \Returns:
    #           str             JSON text
    #==============================================================================
    def ToJsonString(self, reportDict, indent=2):
        return json.dumps(reportDict, indent=indent, default=str)
