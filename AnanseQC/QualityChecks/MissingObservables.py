# =============================================================================
# QC Engine: Missing Observable Analysis
# =============================================================================
# Compares observation descriptors declared in the RINEX header with the
# descriptors actually present on each satellite.
#
# A declared type is missing at an epoch when the satellite is tracked but
# that descriptor has no value. Missing percent is relative to the epochs in
# which the satellite appears, not the full file length.
#
# Units:
#   epochs_present, epochs_missing: epoch counts
#   missing_percent: percent (0-100)
# Time system: GPST, already stored on each epoch. Special-event epochs
# (epoch flag greater than 1) are excluded, matching the other QC engines.

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from AnanseQC.Core.Enums import eGnss
from AnanseQC.Readers.ObsTypes import S_RinexObsFile


#==============================================================================
# \Class: S_ObsTypeGap
# \Brief: Missing-epoch counts for one declared observation type
#==============================================================================
@dataclass
class S_ObsTypeGap:
    """Missing-epoch counts for one header observation type on one satellite.

    Attributes:
        obs_type (str): RINEX observation descriptor, for example C1C.
        epochs_present (int): Epochs where this satellite has a value.
        epochs_missing (int): Tracked epochs where this descriptor is absent.
        missing_percent (float): 100 * epochs_missing / satellite epoch count.
    """
    obs_type: str = ''
    epochs_present: int = 0
    epochs_missing: int = 0
    missing_percent: float = 0.0


#==============================================================================
# \Class: S_SatMissingObs
# \Brief: Declared observation types missing for one satellite
#==============================================================================
@dataclass
class S_SatMissingObs:
    """Declared observation types that are incomplete for one satellite.

    Attributes:
        system (eGnss): GNSS constellation.
        prn (int): Satellite PRN or slot.
        epoch_count (int): Epochs in which this satellite was tracked.
        missing_types (list): S_ObsTypeGap rows with epochs_missing > 0.
    """
    system: eGnss = eGnss.eUnknownSystem
    prn: int = 0
    epoch_count: int = 0
    missing_types: List[S_ObsTypeGap] = field(default_factory=list)


#==============================================================================
# \Class: S_MissingObsResult
# \Brief: Header-versus-body observation completeness result
#==============================================================================
@dataclass
class S_MissingObsResult:
    """Observation types declared in the header but incomplete in the body.

    Attributes:
        satellites (dict): Maps (eGnss, prn) to S_SatMissingObs. Satellites
            with a complete set of declared types are omitted.
        absent_header_types (dict): Maps eGnss to descriptors that were
            declared and never observed on any satellite of that system.
        total_missing_records (int): Count of satellite/type pairs with at
            least one missing epoch.
    """
    satellites: Dict[Tuple[eGnss, int], S_SatMissingObs] = field(default_factory=dict)
    absent_header_types: Dict[eGnss, List[str]] = field(default_factory=dict)
    total_missing_records: int = 0


#==============================================================================
# \Class: C_MissingObservables
# \Brief: Finds header observation types missing from the observation body
#==============================================================================
class C_MissingObservables:
    #==============================================================================
    # \Function: Analyse
    # \Brief: Compares header observation types with values present per satellite
    # \Note:
    #   Missing percent uses the satellite's own tracked epochs as the
    #   denominator. Counts are epoch counts. Time is GPST.
    # \Params:
    #           obsFile         [in]    Parsed RINEX observation file
    # \Returns:
    #           S_MissingObsResult
    #==============================================================================
    def Analyse(self, obsFile: S_RinexObsFile):
        result = S_MissingObsResult()
        declaredBySystem = obsFile.header.obs_types

        # satKey = (eGnss, prn) -> tracked epoch count
        epochCount = {}
        # satKey -> descriptor -> epochs that contain a value
        presentCount = {}

        for epoch in obsFile.epochs:
            # Special-event records are not observation epochs.
            if epoch.epoch_flag > 1:
                continue

            for satObs in epoch.satellites:
                declared = declaredBySystem.get(satObs.system)
                if declared is None:
                    continue

                satKey = (satObs.system, satObs.prn)
                if satKey not in epochCount:
                    epochCount[satKey] = 0
                    presentCount[satKey] = {}
                    for obsType in declared:
                        presentCount[satKey][obsType] = 0

                epochCount[satKey] += 1

                for obsType in declared:
                    if obsType in satObs.obs:
                        presentCount[satKey][obsType] += 1
            # END for-loop over satellites
        # END for-loop over epochs

        # Sum of present epochs per declared type, including systems with no
        # tracked satellites so those header types stay absent.
        systemPresent = {}
        for sysEnum, typeList in declaredBySystem.items():
            systemPresent[sysEnum] = {}
            for obsType in typeList:
                systemPresent[sysEnum][obsType] = 0

        for satKey, nEpoch in epochCount.items():
            sysEnum, prn = satKey
            satResult = S_SatMissingObs()
            satResult.system = sysEnum
            satResult.prn = prn
            satResult.epoch_count = nEpoch

            for obsType, nPresent in presentCount[satKey].items():
                nMissing = nEpoch - nPresent
                systemPresent[sysEnum][obsType] += nPresent

                if nMissing > 0:
                    typeGap = S_ObsTypeGap()
                    typeGap.obs_type = obsType
                    typeGap.epochs_present = nPresent
                    typeGap.epochs_missing = nMissing
                    if nEpoch > 0:
                        typeGap.missing_percent = 100.0 * float(nMissing) / float(nEpoch)
                    satResult.missing_types.append(typeGap)

            if len(satResult.missing_types) > 0:
                result.satellites[satKey] = satResult
        # END for-loop over satellites

        for sysEnum, typeCounts in systemPresent.items():
            absentTypes = []
            for obsType, nPresent in typeCounts.items():
                if nPresent == 0:
                    absentTypes.append(obsType)
            if len(absentTypes) > 0:
                result.absent_header_types[sysEnum] = absentTypes

        nRecords = 0
        for satResult in result.satellites.values():
            nRecords += len(satResult.missing_types)
        result.total_missing_records = nRecords

        return result
