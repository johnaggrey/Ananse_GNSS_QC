#==============================================================================
# \Function: RunQualityCheck
# \Brief: Reads one RINEX observation file and returns the QC reports
# \Note:
#   This is the entry point for a web application. It reads the file once,
#   runs every QC engine, and returns both report forms.
#   JSON schema_version is defined by C_QcReport.
#   Times in the report are GPST. Distances are metres. SNR is dB-Hz.
# \Params:
#           filePath        [in]    Path to a RINEX 2.x, 3.x, or 4.x observation file
# \Returns:
#           dict            JSON-ready report. Empty when reading fails.
#           str             Text report. Empty when reading fails.
#           eFileReadingStatus
#==============================================================================

from AnanseQC.Core.Enums import eFileReadingStatus
from AnanseQC.QualityChecks.Availability import C_ObsAvailability
from AnanseQC.QualityChecks.CycleSlips import C_CycleSlipDetector
from AnanseQC.QualityChecks.EpochSampling import C_EpochSampling
from AnanseQC.QualityChecks.MissingObservables import C_MissingObservables
from AnanseQC.QualityChecks.MultipathSnr import C_MultipathSnr
from AnanseQC.Readers.Reader import C_RinexObsReader
from AnanseQC.Reports.QualityCheckReport import C_QcReport


#==============================================================================
# \Function: AnalyseFile
# \Brief: Reads one RINEX file and runs every QC engine
# \Note:
#   Times on the epochs are GPST seconds. The caller owns the returned file.
# \Params:
#           filePath        [in]    Path to a RINEX 2.x, 3.x, or 4.x observation file
# \Returns:
#           S_RinexObsFile or None
#           dict            Keys availability, sampling, slips, multipathSnr,
#                           missingObs. Empty when reading fails.
#           eFileReadingStatus
#==============================================================================
def AnalyseFile(filePath):
    obsFile, eStatus = C_RinexObsReader().Read(filePath)
    if eStatus != eFileReadingStatus.eSuccess:
        return None, {}, eStatus

    # The reader has already formed the measurements. Each call below is one
    # QC responsibility: availability, sampling, cycle slips, multipath, and
    # missing observables.
    results = {
        'availability': C_ObsAvailability().Analyse(obsFile),
        'sampling': C_EpochSampling().Analyse(obsFile),
        'slips': C_CycleSlipDetector().Analyse(obsFile),
        'multipathSnr': C_MultipathSnr().Analyse(obsFile),
        'missingObs': C_MissingObservables().Analyse(obsFile),
    }
    return obsFile, results, eStatus


def RunQualityCheck(filePath):
    obsFile, results, eStatus = AnalyseFile(filePath)
    if eStatus != eFileReadingStatus.eSuccess:
        return {}, '', eStatus

    availability = results['availability']
    sampling = results['sampling']
    slips = results['slips']
    multipathSnr = results['multipathSnr']
    missingObs = results['missingObs']

    cReport = C_QcReport()
    reportDict = cReport.GenerateJson(
        obsFile,
        availability=availability,
        sampling=sampling,
        slips=slips,
        multipathSnr=multipathSnr,
        missingObs=missingObs,
    )
    textReport = cReport.GenerateText(
        obsFile,
        availability=availability,
        sampling=sampling,
        slips=slips,
        multipathSnr=multipathSnr,
        missingObs=missingObs,
    )
    return reportDict, textReport, eStatus
