#==============================================================================
# GNSS physical and system constants
#==============================================================================
# Fundamental GNSS constants used by the readers and QC engines.
#
# Units:
#   Distance    meters
#   Time        seconds (GPST unless noted)
#   Frequency   Hz
#   Angles      radians
#==============================================================================

#==============================================================================
# Satellite system ID ranges
#==============================================================================
# GPS satellite PRN range
MAX_GPS_SAT_ID = 32
MIN_GPS_SAT_ID = 1
MAX_GPS_SATS = (MAX_GPS_SAT_ID - MIN_GPS_SAT_ID + 1)

# GLONASS satellite slot range
MAX_GLN_SAT_ID = 24
MIN_GLN_SAT_ID = 1
MAX_GLN_SATS = (MAX_GLN_SAT_ID - MIN_GLN_SAT_ID + 1)
MAX_GLN_FREQ_SLOT = 6
MIN_GLN_FREQ_SLOT = -7
MAX_GLN_FREQ_SLOTS = (MAX_GLN_FREQ_SLOT - MIN_GLN_FREQ_SLOT + 1)

# Galileo satellite PRN range
MAX_GAL_SAT_ID = 36
MIN_GAL_SAT_ID = 1
MAX_GAL_SATS = (MAX_GAL_SAT_ID - MIN_GAL_SAT_ID + 1)

# BeiDou satellite PRN range
MAX_BDS_SAT_ID = 63
MIN_BDS_SAT_ID = 1
MAX_BDS_SATS = (MAX_BDS_SAT_ID - MIN_BDS_SAT_ID + 1)

# QZSS satellite PRN range
MAX_QZSS_SAT_ID = 211
MIN_QZSS_SAT_ID = 183
MAX_QZSS_SATS = (MAX_QZSS_SAT_ID - MIN_QZSS_SAT_ID + 1)

# SBAS satellite PRN range
MAX_SBAS_SAT_ID = 158
MIN_SBAS_SAT_ID = 120
MAX_SBAS_SATS = (MAX_SBAS_SAT_ID - MIN_SBAS_SAT_ID + 1)

# NavIC/IRNSS satellite PRN range
MAX_NAVIC_SAT_ID = 14
MIN_NAVIC_SAT_ID = 1
MAX_NAVIC_SATS = (MAX_NAVIC_SAT_ID - MIN_NAVIC_SAT_ID + 1)

#==============================================================================
# Sentinel / invalid values
#==============================================================================
INVALID = -99999.99999

#==============================================================================
# Physical constants
#==============================================================================
CLIGHT = 299792458.0                            # Speed of light (m/s)
PI = 3.14159265358979323846                     # Pi

#==============================================================================
# Signal frequencies (Hz)
#==============================================================================
GPS_L1 = 1575.42e6                              # GPS L1 frequency
GPS_L2 = 1227.60e6                              # GPS L2 frequency
GPS_L5 = 1176.45e6                              # GPS L5 frequency

GLN_BASEFREQ_G1 = 1602.0e6                      # GLONASS G1 base frequency
GLN_BASEFREQ_G2 = 1246.0e6                      # GLONASS G2 base frequency
GLN_G1A = 1600.995e6                            # GLONASS G1a frequency
GLN_G2B = 1248.060e6                            # GLONASS G2b frequency
GLN_G3 = 1202.025e6                             # GLONASS G3 frequency
GLN_DELTA_L1 = 0.5625e6                         # G1 frequency slot step (Hz)
GLN_DELTA_L2 = 0.4375e6                         # G2 frequency slot step (Hz)

# GLONASS per-slot frequency tables. Slot range is -7..+6.
GLN_L1 = [GLN_BASEFREQ_G1 + slot * GLN_DELTA_L1 for slot in range(-7, 7 + 1)]
GLN_L2 = [GLN_BASEFREQ_G2 + slot * GLN_DELTA_L2 for slot in range(-7, 7 + 1)]

GAL_E1 = 1575.42e6                              # Galileo E1 frequency
GAL_E5A = 1176.45e6                             # Galileo E5a frequency
GAL_E5B = 1207.140e6                            # Galileo E5b frequency
GAL_E5 = 1191.795e6                             # Galileo E5ab (AltBOC) frequency
GAL_E6 = 1278.75e6                              # Galileo E6 frequency

BDS2_B1 = 1561.098e6                            # BeiDou-2 B1I frequency
BDS3_B1C = 1575.42e6                            # BeiDou-3 B1C frequency
BDS3_B1A = 1575.42e6                            # BeiDou-3 B1A frequency
BDS3_B2A = 1176.45e6                            # BeiDou-3 B2a frequency
BDS3_B2B = 1207.140e6                           # BeiDou-3 B2b frequency
BDS2_B2 = 1207.140e6                            # BeiDou-2 B2I frequency
BDS3_B2AB = 1191.795e6                          # BeiDou-3 B2ab frequency
BDS3_B3 = 1268.520e6                            # BeiDou B3 frequency

SBAS_L1 = 1575.42e6                             # SBAS L1 frequency
SBAS_L5 = 1176.45e6                             # SBAS L5 frequency

QZSS_L1 = 1575.42e6                             # QZSS L1 frequency
QZSS_L2 = 1227.60e6                             # QZSS L2 frequency
QZSS_L5 = 1176.45e6                             # QZSS L5 frequency
QZSS_L6 = 1278.75e6                             # QZSS L6 frequency

NAVIC_L1 = 1575.42e6                            # NavIC L1 frequency
NAVIC_L5 = 1176.45e6                            # NavIC L5 frequency
NAVIC_S = 2492.028e6                            # NavIC S frequency

#==============================================================================
# Maximum number of frequencies per system
#==============================================================================
MAXGPSFREQ = 3
MAXGLONASSFREQ = 3
MAXGALILEOFREQ = 5
MAXBEIDOUFREQ = 5
MAXSBASFREQ = 2
MAXQZSSFREQ = 4
MAXNAVICFREQ = 3

#==============================================================================
# Time system constants
# Time system: GPST. GPS epoch is 1980-01-06 00:00:00.
#==============================================================================
JULIAN_DATE_AT_GPS_EPOCH = 2444244.5
SECONDS_IN_WEEK = 604800.0
SECONDS_IN_DAY = 86400.0
SECONDS_IN_HALF_DAY = 43200.0
SECONDS_IN_HOUR = 3600.0
SECONDS_IN_MINUTE = 60.0
GPS_EPOCH = 315964800.0                         # GPS epoch as a Unix timestamp
GPS_START_YEAR = 1980
GPS_START_MONTH = 1
GPS_START_DAY = 6

#==============================================================================
# Angle conversion constants
#==============================================================================
DEG2RAD = PI / 180.0
RAD2DEG = 180.0 / PI

#==============================================================================
# Ionosphere constants
#==============================================================================
TECCST = 40.3e16                                # TEC constant (m^2/s^2)

#==============================================================================
# Numerical tolerances
#==============================================================================
EPSILON = 1e-12                                 # Floating-point comparison tolerance
