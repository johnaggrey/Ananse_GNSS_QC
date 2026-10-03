#==============================================================================
# System imported libraries
#==============================================================================
import argparse
import logging
import os
import sys

from AnanseQC import __version__
from AnanseQC.Core.Enums import eFileReadingStatus
from AnanseQC.QualityCheck import AnalyseFile
from AnanseQC.Reports.Plots import C_QcPlots
from AnanseQC.Reports.QualityCheckReport import C_QcReport

#==============================================================================
# \Class: C_QcCommand
# \Brief: Command-line entry point for a RINEX observation QC run
#==============================================================================
class C_QcCommand:
    #==============================================================================
    # \Function: _SetupLogging
    # \Brief: Configures logging for a quiet or verbose run
    # \Params:
    #           bVerbose        [in]    True enables debug logging
    # \Returns:
    #           None
    #==============================================================================
    def _SetupLogging(self, bVerbose):
        if bVerbose == True:
            level = logging.DEBUG
        else:
            level = logging.WARNING

        logging.basicConfig(
            level=level,
            format='%(asctime)s %(name)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S',
        )

    #==============================================================================
    # \Function: Run
    # \Brief: Reads one RINEX file, runs the QC engines, and writes the report
    # \Params:
    #           filePath        [in]    Path to the RINEX observation file
    #           outputFormat    [in]    'text' or 'json'
    #           outputFile      [in]    Report path, or None to print the report
    #           bVerbose        [in]    True enables debug logging
    # \Returns:
    #           int             0 on success, 1 on error
    #==============================================================================
    def Run(self, filePath, outputFormat='text', outputFile=None, bVerbose=False):
        self._SetupLogging(bVerbose)

        if os.path.exists(filePath) == False:
            print(f"Error: File not found: {filePath}", file=sys.stderr)
            return 1

        print(f"Reading RINEX file: {filePath}")
        obsFile, results, eStatus = AnalyseFile(filePath)

        if eStatus != eFileReadingStatus.eSuccess:
            print(f"Error: Failed to read file (status: {eStatus.name})", file=sys.stderr)
            return 1

        nEpoch = results['availability'].total_epochs
        print(f"  RINEX version {obsFile.header.version}, "
              f"{nEpoch} epochs, "
              f"station: {obsFile.header.marker_name}")

        print("QC checks completed:")
        print("  - Satellite/observable availability")
        print("  - Missing observables")
        print("  - Epoch sampling and gap detection")
        print("  - Cycle slip detection")
        print("  - Multipath and SNR analysis")
        print("Generating report...")
        c_Report = C_QcReport()
        availability = results['availability']
        sampling = results['sampling']
        slips = results['slips']
        multipathSnr = results['multipathSnr']
        missingObs = results['missingObs']

        if outputFormat == 'json':
            reportDict = c_Report.GenerateJson(
                obsFile,
                availability=availability,
                sampling=sampling,
                slips=slips,
                multipathSnr=multipathSnr,
                missingObs=missingObs,
            )
            reportStr = c_Report.ToJsonString(reportDict)
        else:
            reportStr = c_Report.GenerateText(
                obsFile,
                availability=availability,
                sampling=sampling,
                slips=slips,
                multipathSnr=multipathSnr,
                missingObs=missingObs,
            )

        if outputFile is not None:
            with open(outputFile, 'w', encoding='utf-8') as outputHandle:
                outputHandle.write(reportStr)
            print(f"Report written to: {outputFile}")
        else:
            print('')
            print(reportStr)

        c_Plots = C_QcPlots()
        satFigure = c_Plots.PlotSatellites(obsFile, availability)
        availFigure = c_Plots.PlotAvailability(availability)
        intervalFigure = c_Plots.PlotIntervals(obsFile, sampling)
        missingFigure = c_Plots.PlotMissing(missingObs)
        if outputFile is None:
            print("Showing plots. Close the figures to exit.")
            c_Plots.Show(satFigure)
        else:
            satPath = c_Plots.SaveBeside(satFigure, outputFile, 'satellites')
            availPath = c_Plots.SaveBeside(availFigure, outputFile, 'availability')
            intervalPath = c_Plots.SaveBeside(intervalFigure, outputFile, 'intervals')
            missingPath = c_Plots.SaveBeside(missingFigure, outputFile, 'missing')
            print(f"Plot written to: {satPath}")
            print(f"Plot written to: {availPath}")
            print(f"Plot written to: {intervalPath}")
            print(f"Plot written to: {missingPath}")

        return 0

    #==============================================================================
    # \Function: Main
    # \Brief: Parses command-line arguments and runs the QC command
    # \Params:
    #           None
    # \Returns:
    #           None            Exits the process with the Run status code
    #==============================================================================
    def Main(self):
        parser = argparse.ArgumentParser(
            prog='ananse-qc',
            description='Ananse GNSS QC - RINEX Observation File Quality Control',
            epilog=(
                'Examples:\n'
                '  ananse-qc station.24o\n'
                '  ananse-qc data.rnx --format json --output report.json\n'
                '  ananse-qc data.obs --verbose\n'
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        parser.add_argument(
            'file',
            help='Path to the RINEX observation file',
        )
        parser.add_argument(
            '--format', '-f',
            choices=['text', 'json'],
            default='text',
            help='Output format (default: text)',
        )
        parser.add_argument(
            '--output', '-o',
            default=None,
            help='Output file path (default: print to stdout)',
        )
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose/debug output',
        )
        parser.add_argument(
            '--version',
            action='version',
            version=f'ananse-qc {__version__}',
        )

        args = parser.parse_args()
        exitCode = self.Run(
            filePath=args.file,
            outputFormat=args.format,
            outputFile=args.output,
            bVerbose=args.verbose,
        )
        sys.exit(exitCode)

#==============================================================================
# \Function: Main
# \Brief: Module entry point used by the console script and python -m
# \Params:
#           None
# \Returns:
#           None
#==============================================================================
def Main():
    C_QcCommand().Main()


if __name__ == '__main__':
    Main()
