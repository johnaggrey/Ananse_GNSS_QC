#==============================================================================
# QC plots
#==============================================================================
# Figures use the QC results already computed by the engines.
# Time axes are hours from the first epoch, in GPST.
# Satellite count is dimensionless.

import os

from AnanseQC.Core.Enums import SYSTEM_TO_CHAR

# Seconds in one hour. Used to convert absolute GPST seconds to hours.
SECONDS_PER_HOUR = 3600.0


#==============================================================================
# \Class: C_QcPlots
# \Brief: Builds matplotlib figures for a QC run
#==============================================================================
class C_QcPlots:
    #==============================================================================
    # \Function: PlotSatellites
    # \Brief: Plots satellites tracked versus time, one line per constellation
    # \Note:
    #   X values are hours from the first epoch, GPST. Y values are the
    #   satellite count in sats_per_epoch, aligned with obsFile.epochs.
    # \Params:
    #           obsFile         [in]    Parsed RINEX observation file
    #           availability    [in]    S_AvailabilityResult
    # \Returns:
    #           matplotlib.figure.Figure
    #==============================================================================
    def PlotSatellites(self, obsFile, availability):
        import matplotlib.pyplot as plt

        figure, axes = plt.subplots(figsize=(8.0, 4.5))
        axes.set_xlabel('Time from first epoch (hours, GPST)')
        axes.set_ylabel('Satellites tracked')
        axes.set_title('Satellites versus time')
        axes.grid(True, linestyle=':', linewidth=0.6)

        if len(obsFile.epochs) == 0 or availability.total_epochs == 0:
            axes.text(
                0.5,
                0.5,
                'No epochs',
                transform=axes.transAxes,
                ha='center',
                va='center',
            )
            figure.tight_layout()
            return figure

        firstTime = obsFile.epochs[0].abs_gps_time
        hours = []
        for epoch in obsFile.epochs:
            hours.append((epoch.abs_gps_time - firstTime) / SECONDS_PER_HOUR)
        # END for-loop over epochs

        systems = sorted(availability.systems.keys(), key=lambda item: item.value)
        for eSystem in systems:
            counts = availability.systems[eSystem].sats_per_epoch
            nPoints = min(len(hours), len(counts))
            if nPoints == 0:
                continue
            sysChar = SYSTEM_TO_CHAR.get(eSystem, '?')
            label = f"{eSystem.name} ({sysChar})"
            axes.plot(hours[:nPoints], counts[:nPoints], label=label)
        # END for-loop over constellations

        if len(axes.lines) > 0:
            axes.legend(loc='best')
        axes.set_ylim(bottom=0.0)
        figure.tight_layout()
        return figure

    #==============================================================================
    # \Function: PlotAvailability
    # \Brief: Plots each satellite's availability as a percent of epochs
    # \Note:
    #   Bars are grouped by constellation, then by PRN. The percent uses the
    #   satellite's tracked epochs over the file length.
    # \Params:
    #           availability    [in]    S_AvailabilityResult
    # \Returns:
    #           matplotlib.figure.Figure
    #==============================================================================
    def PlotAvailability(self, availability):
        import matplotlib.pyplot as plt

        labels = []
        percents = []
        systems = sorted(availability.systems.keys(), key=lambda item: item.value)
        for eSystem in systems:
            sysChar = SYSTEM_TO_CHAR.get(eSystem, '?')
            details = availability.systems[eSystem].sat_details
            for prn in sorted(details.keys()):
                labels.append(f"{sysChar}{prn:02d}")
                percents.append(details[prn].epoch_percentage)
            # END for-loop over satellites
        # END for-loop over constellations

        # Draw the first satellite at the top of the horizontal bars.
        labels.reverse()
        percents.reverse()

        barHeight = 0.28
        figureHeight = max(4.5, barHeight * len(labels) + 1.2)
        figure, axes = plt.subplots(figsize=(8.0, figureHeight))
        axes.set_xlabel('Percent of epochs')
        axes.set_ylabel('Satellite')
        axes.set_title('Satellite availability')
        axes.set_xlim(0.0, 100.0)
        axes.grid(True, axis='x', linestyle=':', linewidth=0.6)

        if len(labels) == 0:
            axes.text(
                0.5,
                0.5,
                'No satellites',
                transform=axes.transAxes,
                ha='center',
                va='center',
            )
        else:
            axes.barh(labels, percents)

        figure.tight_layout()
        return figure

    #==============================================================================
    # \Function: PlotIntervals
    # \Brief: Plots inter-epoch interval versus time and marks data gaps
    # \Note:
    #   X values are hours from the first normal epoch, GPST. Y values are
    #   the interval to the previous epoch, in seconds. A gap is an interval
    #   already recorded on the sampling result. The nominal interval is a
    #   horizontal reference line, in seconds.
    # \Params:
    #           obsFile         [in]    Parsed RINEX observation file
    #           sampling        [in]    S_EpochSamplingResult
    # \Returns:
    #           matplotlib.figure.Figure
    #==============================================================================
    def PlotIntervals(self, obsFile, sampling):
        import matplotlib.pyplot as plt

        figure, axes = plt.subplots(figsize=(8.0, 4.5))
        axes.set_xlabel('Time from first epoch (hours, GPST)')
        axes.set_ylabel('Interval (seconds)')
        axes.set_title('Epoch interval and gaps')
        axes.grid(True, linestyle=':', linewidth=0.6)

        timestamps = []
        for epoch in obsFile.epochs:
            if epoch.epoch_flag <= 1:
                timestamps.append(epoch.abs_gps_time)
        # END for-loop over epochs

        if len(timestamps) < 2:
            axes.text(
                0.5,
                0.5,
                'Not enough epochs',
                transform=axes.transAxes,
                ha='center',
                va='center',
            )
            figure.tight_layout()
            return figure

        firstTime = timestamps[0]
        intervalHours = []
        intervalSeconds = []
        gapHours = []
        gapSeconds = []
        for idx in range(1, len(timestamps)):
            dt = timestamps[idx] - timestamps[idx - 1]
            hour = (timestamps[idx] - firstTime) / SECONDS_PER_HOUR
            bGap = self._IsRecordedGap(timestamps[idx], dt, sampling.gaps)
            if bGap == True:
                gapHours.append(hour)
                gapSeconds.append(dt)
            intervalHours.append(hour)
            intervalSeconds.append(dt)
        # END for-loop over intervals

        axes.plot(
            intervalHours,
            intervalSeconds,
            label='Interval',
        )
        if len(gapHours) > 0:
            axes.scatter(
                gapHours,
                gapSeconds,
                marker='o',
                zorder=3,
                label='Gap',
            )
        if sampling.nominal_interval > 0.0:
            axes.axhline(
                sampling.nominal_interval,
                linestyle='--',
                linewidth=1.0,
                label='Nominal interval',
            )
        axes.legend(loc='best')
        axes.set_ylim(bottom=0.0)
        figure.tight_layout()
        return figure

    #==============================================================================
    # \Function: _IsRecordedGap
    # \Brief: Reports whether an inter-epoch step matches a recorded gap
    # \Params:
    #           endTime         [in]    Absolute GPS time of the later epoch, seconds
    #           interval_s      [in]    Interval length, seconds
    #           gaps            [in]    List of S_GapRecord
    # \Returns:
    #           bool            True when the step is one of the recorded gaps
    #==============================================================================
    def _IsRecordedGap(self, endTime, interval_s, gaps):
        for gap in gaps:
            bSameEnd = abs(gap.end_time - endTime) < 0.05
            bSameLength = abs(gap.duration_seconds - interval_s) < 0.05
            if bSameEnd == True and bSameLength == True:
                return True
        # END for-loop over gaps
        return False

    #==============================================================================
    # \Function: PlotMissing
    # \Brief: Plots missing percent for each satellite and header observation type
    # \Note:
    #   The percent uses that satellite's tracked epochs, not the file length.
    #   Satellites with a complete set of header types are omitted.
    # \Params:
    #           missingObs      [in]    S_MissingObsResult
    # \Returns:
    #           matplotlib.figure.Figure
    #==============================================================================
    def PlotMissing(self, missingObs):
        import matplotlib.pyplot as plt

        labels = []
        percents = []
        satKeys = sorted(
            missingObs.satellites.keys(),
            key=lambda satKey: (satKey[0].value, satKey[1]),
        )
        for satKey in satKeys:
            satResult = missingObs.satellites[satKey]
            sysChar = SYSTEM_TO_CHAR.get(satResult.system, '?')
            satName = f"{sysChar}{satResult.prn:02d}"
            for typeGap in satResult.missing_types:
                labels.append(f"{satName} {typeGap.obs_type}")
                percents.append(typeGap.missing_percent)
            # END for-loop over observation types
        # END for-loop over satellites

        labels.reverse()
        percents.reverse()

        barHeight = 0.28
        figureHeight = max(4.5, barHeight * max(len(labels), 1) + 1.2)
        figure, axes = plt.subplots(figsize=(8.0, figureHeight))
        axes.set_xlabel('Percent of tracked epochs')
        axes.set_ylabel('Satellite and type')
        axes.set_title('Missing observables')
        axes.set_xlim(0.0, 100.0)
        axes.grid(True, axis='x', linestyle=':', linewidth=0.6)

        if len(labels) == 0:
            axes.text(
                0.5,
                0.5,
                'No missing observables',
                transform=axes.transAxes,
                ha='center',
                va='center',
            )
        else:
            axes.barh(labels, percents)

        figure.tight_layout()
        return figure

    #==============================================================================
    # \Function: PlotSlips
    # \Brief: Plots each cycle slip against time and satellite
    # \Note:
    #   X values are hours from the first epoch, GPST. Y values are satellite
    #   ids. TDCP uses an x marker. Melbourne-Wubbena uses a circle. An empty
    #   event list still draws the axes.
    # \Params:
    #           obsFile         [in]    Parsed RINEX observation file
    #           slips           [in]    S_CycleSlipResult
    # \Returns:
    #           matplotlib.figure.Figure
    #==============================================================================
    def PlotSlips(self, obsFile, slips):
        import matplotlib.pyplot as plt

        satNames = []
        for event in slips.all_events:
            sysChar = SYSTEM_TO_CHAR.get(event.system, '?')
            satName = f"{sysChar}{event.prn:02d}"
            if satName not in satNames:
                satNames.append(satName)
        # END for-loop over slip events
        satNames.sort()

        barHeight = 0.35
        figureHeight = max(4.5, barHeight * max(len(satNames), 1) + 1.4)
        figure, axes = plt.subplots(figsize=(8.0, figureHeight))
        axes.set_xlabel('Time from first epoch (hours, GPST)')
        axes.set_ylabel('Satellite')
        axes.set_title('Cycle slips')
        axes.grid(True, linestyle=':', linewidth=0.6)

        if len(slips.all_events) == 0 or len(obsFile.epochs) == 0:
            axes.text(
                0.5,
                0.5,
                'No cycle slips',
                transform=axes.transAxes,
                ha='center',
                va='center',
            )
            figure.tight_layout()
            return figure

        firstTime = obsFile.epochs[0].abs_gps_time
        yIndex = {}
        for idx, satName in enumerate(satNames):
            yIndex[satName] = idx

        tdcpHours = []
        tdcpY = []
        mwHours = []
        mwY = []
        for event in slips.all_events:
            sysChar = SYSTEM_TO_CHAR.get(event.system, '?')
            satName = f"{sysChar}{event.prn:02d}"
            hour = (event.time - firstTime) / SECONDS_PER_HOUR
            if event.method == 'TDCP':
                tdcpHours.append(hour)
                tdcpY.append(yIndex[satName])
            elif event.method == 'MW':
                mwHours.append(hour)
                mwY.append(yIndex[satName])
        # END for-loop over slip events

        if len(tdcpHours) > 0:
            axes.scatter(tdcpHours, tdcpY, marker='x', label='TDCP', zorder=3)
        if len(mwHours) > 0:
            axes.scatter(
                mwHours,
                mwY,
                marker='o',
                label='Melbourne-Wubbena',
                zorder=3,
            )
        axes.set_yticks(list(range(len(satNames))))
        axes.set_yticklabels(satNames)
        if len(axes.collections) > 0:
            axes.legend(loc='best')
        figure.tight_layout()
        return figure

    #==============================================================================
    # \Function: Show
    # \Brief: Displays one figure on screen and blocks until it is closed
    # \Params:
    #           figure          [in]    matplotlib figure from a plot method
    # \Returns:
    #           None
    #==============================================================================
    def Show(self, figure):
        import matplotlib.pyplot as plt

        figure.show()
        plt.show()

    #==============================================================================
    # \Function: SaveBeside
    # \Brief: Saves a figure as a PNG next to the report file
    # \Note:
    #   report.json and plot name satellites become report_satellites.png
    #   in the same directory.
    # \Params:
    #           figure          [in]    matplotlib figure
    #           outputFile      [in]    Report path given by the user
    #           plotName        [in]    Short name used in the PNG file name
    # \Returns:
    #           str             Path of the written PNG
    #==============================================================================
    def SaveBeside(self, figure, outputFile, plotName):
        folder = os.path.dirname(outputFile)
        if folder == '':
            folder = '.'
        stem = os.path.splitext(os.path.basename(outputFile))[0]
        pngPath = os.path.join(folder, f"{stem}_{plotName}.png")
        figure.savefig(pngPath, dpi=120, bbox_inches='tight')
        return pngPath
