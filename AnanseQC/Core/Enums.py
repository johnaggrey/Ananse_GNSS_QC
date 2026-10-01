#==============================================================================
# Imported classes and modules
#==============================================================================
from enum import Enum

import AnanseQC.Core.Constants as Constants

#==============================================================================
# \Class: eGnss
# \Brief: Enumerator for all available GNSS systems
#==============================================================================
class eGnss(Enum):
    eGPS = 0
    eGLN = 1
    eGAL = 2
    eBDS = 3
    eSBAS = 4
    eQZSS = 5
    eNavIC = 6
    eMaxNumSystems = 7
    eUnknownSystem = 8

#==============================================================================
# \Class: eGnssObsType
# \Brief: Enumerator for all available GNSS observation types
#==============================================================================
class eGnssObsType(Enum):
    ePseudorange = 0
    eCarrierPhase = 1
    eDoppler = 2
    eSnr = 3
    eMaxNumObsTypes = 4
    eUnknownObsType = 5

#==============================================================================
# \Class: eGnssFreq
# \Brief: Enumerator for all available GNSS frequencies
#==============================================================================
class eGnssFreq(Enum):
    eGPS_F1_L1 = 0              # GPS L1 frequency 1575.42 MHz
    eGPS_F2_L2 = 1              # GPS L2 frequency 1227.60 MHz
    eGPS_F3_L5 = 2              # GPS L5 frequency 1176.45 MHz
    eGLN_F1_G1 = 3              # GLONASS G1 frequency 1602.00 MHz
    eGLN_F1_G1a = 4             # GLONASS G1a frequency 1600.995 MHz
    eGLN_F2_G2 = 5              # GLONASS G2 frequency 1246.00 MHz
    eGLN_F2_G2b = 6             # GLONASS G2b frequency 1248.060 MHz
    eGLN_F3_G3 = 7              # GLONASS G3 frequency 1202.025 MHz
    eGAL_F1_E1 = 8              # Galileo E1 frequency 1575.42 MHz
    eGAL_F2_E5b = 9             # Galileo E5b frequency 1207.14 MHz
    eGAL_F2_E5ab = 10           # Galileo E5ab frequency 1191.795 MHz
    eGAL_F3_E5a = 11            # Galileo E5a frequency 1176.45 MHz
    eGAL_F4_E6 = 12             # Galileo E6 frequency 1278.75 MHz
    eBDS_F1_B1I = 13            # BeiDou B1I frequency 1561.098 MHz
    eBDS_F1_B1C = 14            # BeiDou B1C frequency 1575.42 MHz
    eBDS_F2_B2A = 15            # BeiDou B2a frequency 1176.45 MHz
    eBDS_F2_B2B = 16            # BeiDou B2b frequency 1207.140 MHz
    eBDS_F2_B2AB = 17           # BeiDou B2ab frequency 1191.795 MHz
    eBDS_F3_B3I = 18            # BeiDou B3I frequency 1268.520 MHz
    eSBAS_F1_L1 = 19            # SBAS L1 frequency 1575.42 MHz
    eSBAS_F2_L5 = 20            # SBAS L5 frequency 1176.45 MHz
    eQZSS_F1_L1 = 21            # QZSS L1 frequency 1575.42 MHz
    eQZSS_F2_L2 = 22            # QZSS L2 frequency 1227.60 MHz
    eQZSS_F3_L5 = 23            # QZSS L5 frequency 1176.45 MHz
    eQZSS_F4_L6 = 24            # QZSS L6 frequency 1278.75 MHz
    eNavIC_F1_L1 = 25           # NavIC L1 frequency 1575.42 MHz
    eNavIC_F2_L5 = 26           # NavIC L5 frequency 1176.45 MHz
    eNavIC_F3_S = 27            # NavIC S frequency 2492.028 MHz
    eMaxNumFreqs = 28
    eUnknownFreq = 29

#==============================================================================
# \Class: eTrackType
# \Brief: Enumerator for RINEX observation attribute / tracking codes
#==============================================================================
class eTrackType(Enum):
    eCA = 0                     # C/A, standard FDMA correlation
    eL1C_D = 1                  # L1C / L2C data channel
    eL1C_P = 2                  # L1C / L2C pilot channel
    eL1C_DP = 3                 # Combined data + pilot, or I+Q
    eP = 4                      # P code
    eW = 5                      # Z-tracking / codeless
    eY = 6                      # Y code
    eM = 7                      # M code
    eI = 8                      # In-phase / data component
    eQ = 9                      # Quadrature / pilot component
    eL1_CA_P2P1 = 10            # L1 C/A + (P2-P1) semi-codeless
    eN = 11                     # Codeless / squaring
    eA = 12                     # A channel
    eB = 13                     # B channel
    eZ = 14                     # A+B+C combined
    eUnknownTrackType = 15

#==============================================================================
# \Class: eFileReadingStatus
# \Brief: Status codes returned by file reading operations
#==============================================================================
class eFileReadingStatus(Enum):
    eSuccess = 0
    eFileNotFound = 1
    eFileOpenError = 2
    eFileReadError = 3
    eFileFormatError = 4
    eFileNotSupported = 5
    eInvalidHeader = 6
    eEmptyFile = 7
    eMaxError = 8
    eUnknownError = 9

#==============================================================================
# \Class: eRinexObsVersion
# \Brief: Detected RINEX observation file version
#==============================================================================
class eRinexObsVersion(Enum):
    eRinexObsVersion_Unknown = 0
    eRinexObsVersion_2 = 2
    eRinexObsVersion_3 = 3
    eRinexObsVersion_4 = 4
    eRinexObsVersion_Invalid = -1

#==============================================================================
# RINEX system character tables
#==============================================================================
# Maps a RINEX system character to eGnss.
RINEX_SYSTEM_CHAR = {
    'G': eGnss.eGPS,
    'R': eGnss.eGLN,
    'E': eGnss.eGAL,
    'C': eGnss.eBDS,
    'S': eGnss.eSBAS,
    'J': eGnss.eQZSS,
    'I': eGnss.eNavIC,
}

# Maps eGnss back to the RINEX system character.
SYSTEM_TO_CHAR = {eSystem: czChar for czChar, eSystem in RINEX_SYSTEM_CHAR.items()}

# Maps a RINEX observation prefix to eGnssObsType.
# C and P are both pseudorange. L is carrier phase, D is Doppler, S is SNR.
RINEX_OBS_PREFIX = {
    'C': eGnssObsType.ePseudorange,
    'P': eGnssObsType.ePseudorange,
    'L': eGnssObsType.eCarrierPhase,
    'D': eGnssObsType.eDoppler,
    'S': eGnssObsType.eSnr,
}

# Maps (eGnss, RINEX band number) to eGnssFreq.
RINEX_BAND_MAP = {
    (eGnss.eGPS, 1): eGnssFreq.eGPS_F1_L1,
    (eGnss.eGPS, 2): eGnssFreq.eGPS_F2_L2,
    (eGnss.eGPS, 5): eGnssFreq.eGPS_F3_L5,
    (eGnss.eGLN, 1): eGnssFreq.eGLN_F1_G1,
    (eGnss.eGLN, 2): eGnssFreq.eGLN_F2_G2,
    (eGnss.eGLN, 3): eGnssFreq.eGLN_F3_G3,
    (eGnss.eGLN, 4): eGnssFreq.eGLN_F1_G1a,
    (eGnss.eGLN, 6): eGnssFreq.eGLN_F2_G2b,
    (eGnss.eGAL, 1): eGnssFreq.eGAL_F1_E1,
    (eGnss.eGAL, 5): eGnssFreq.eGAL_F3_E5a,
    (eGnss.eGAL, 6): eGnssFreq.eGAL_F4_E6,
    (eGnss.eGAL, 7): eGnssFreq.eGAL_F2_E5b,
    (eGnss.eGAL, 8): eGnssFreq.eGAL_F2_E5ab,
    (eGnss.eBDS, 1): eGnssFreq.eBDS_F1_B1C,
    (eGnss.eBDS, 2): eGnssFreq.eBDS_F1_B1I,
    (eGnss.eBDS, 5): eGnssFreq.eBDS_F2_B2A,
    (eGnss.eBDS, 6): eGnssFreq.eBDS_F3_B3I,
    (eGnss.eBDS, 7): eGnssFreq.eBDS_F2_B2B,
    (eGnss.eBDS, 8): eGnssFreq.eBDS_F2_B2AB,
    (eGnss.eSBAS, 1): eGnssFreq.eSBAS_F1_L1,
    (eGnss.eSBAS, 5): eGnssFreq.eSBAS_F2_L5,
    (eGnss.eQZSS, 1): eGnssFreq.eQZSS_F1_L1,
    (eGnss.eQZSS, 2): eGnssFreq.eQZSS_F2_L2,
    (eGnss.eQZSS, 5): eGnssFreq.eQZSS_F3_L5,
    (eGnss.eQZSS, 6): eGnssFreq.eQZSS_F4_L6,
    (eGnss.eNavIC, 1): eGnssFreq.eNavIC_F1_L1,
    (eGnss.eNavIC, 5): eGnssFreq.eNavIC_F2_L5,
    (eGnss.eNavIC, 9): eGnssFreq.eNavIC_F3_S,
}

#==============================================================================
# \Function: GetMaxSatId
# \Brief: Returns the maximum satellite PRN or slot for a GNSS system
# \Params:
#           eSystem         [in]    eGnss constellation
# \Returns:
#           int             Maximum PRN/slot, or 0 when the system is unknown
#==============================================================================
def GetMaxSatId(eSystem):
    dMaxIds = {
        eGnss.eGPS: Constants.MAX_GPS_SAT_ID,
        eGnss.eGLN: Constants.MAX_GLN_SAT_ID,
        eGnss.eGAL: Constants.MAX_GAL_SAT_ID,
        eGnss.eBDS: Constants.MAX_BDS_SAT_ID,
        eGnss.eQZSS: Constants.MAX_QZSS_SAT_ID,
        eGnss.eSBAS: Constants.MAX_SBAS_SAT_ID,
        eGnss.eNavIC: Constants.MAX_NAVIC_SAT_ID,
    }
    return dMaxIds.get(eSystem, 0)

#==============================================================================
# \Function: GetMinSatId
# \Brief: Returns the minimum satellite PRN or slot for a GNSS system
# \Params:
#           eSystem         [in]    eGnss constellation
# \Returns:
#           int             Minimum PRN/slot, or 0 when the system is unknown
#==============================================================================
def GetMinSatId(eSystem):
    dMinIds = {
        eGnss.eGPS: Constants.MIN_GPS_SAT_ID,
        eGnss.eGLN: Constants.MIN_GLN_SAT_ID,
        eGnss.eGAL: Constants.MIN_GAL_SAT_ID,
        eGnss.eBDS: Constants.MIN_BDS_SAT_ID,
        eGnss.eQZSS: Constants.MIN_QZSS_SAT_ID,
        eGnss.eSBAS: Constants.MIN_SBAS_SAT_ID,
        eGnss.eNavIC: Constants.MIN_NAVIC_SAT_ID,
    }
    return dMinIds.get(eSystem, 0)
