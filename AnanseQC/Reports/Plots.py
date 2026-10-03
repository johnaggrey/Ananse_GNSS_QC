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
