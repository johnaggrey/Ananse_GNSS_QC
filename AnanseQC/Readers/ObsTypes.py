#==============================================================================
# Imported classes and modules
#==============================================================================
# In-memory records for a parsed RINEX observation file.
# Shared by the version-specific readers and the QC engines.
#
# Structures:
#   S_RinexObsHeader    Header metadata
#   S_SatObs            One satellite in one epoch
#   S_EpochRecord       One observation epoch
#   S_RinexObsFile      Complete parsed file
#==============================================================================
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from AnanseQC.Core.Enums import eGnss, eRinexObsVersion


#==============================================================================
# \Class: S_RinexObsHeader
# \Brief: Parsed RINEX observation file header
# \Note:
#   Positions are ECEF metres. Antenna delta is H/E/N metres.
#   obsTypes maps eGnss to the ordered list of observation descriptors.
#==============================================================================
@dataclass
class S_RinexObsHeader:
    """Parsed RINEX observation file header.

    Attributes:
        version (float): RINEX format version (e.g. 2.11, 3.05, 4.00).
        version_enum (eRinexObsVersion): Coarse version category (V2, V3, V4).
        file_type (str): 'O' for observation.
        satellite_system (str): Satellite system indicator ('G','R','E','C','M',etc.).
        marker_name (str): Station marker name.
        marker_number (str): Station marker number.
        observer (str): Observer name.
        agency (str): Agency name.
        receiver_number (str): Receiver serial number.
        receiver_type (str): Receiver type descriptor.
        receiver_version (str): Receiver firmware version.
        antenna_number (str): Antenna serial number.
        antenna_type (str): Antenna type descriptor.
        approx_position (tuple): Approximate position (X, Y, Z) in metres, ECEF.
        antenna_delta (tuple): Antenna delta (H, E, N) in metres.
        obs_types (dict): Maps eGnss -> list of observation descriptor
                          strings (e.g. ['C1C','L1C','S1C','C2W',...]).
        interval (float): Expected observation interval in seconds (may be 0
                          if not specified in header).
        time_of_first_obs (tuple): (year, month, day, hour, minute, second).
        time_of_last_obs (tuple): (year, month, day, hour, minute, second) or None.
        time_system (str): Time system indicator ('GPS','GLO','GAL','BDT','QZS', etc.).
        leap_seconds (int): Number of leap seconds (if present).
        num_satellites (int): Number of satellites listed in header (if present).
        comments (list): List of COMMENT lines from header.
        glonass_slots (dict): Maps PRN -> frequency slot number (if present).
    """
    version: float = 0.0
    version_enum: eRinexObsVersion = eRinexObsVersion.eRinexObsVersion_Unknown
    file_type: str = ''
    satellite_system: str = ''
    marker_name: str = ''
    marker_number: str = ''
    observer: str = ''
    agency: str = ''
    receiver_number: str = ''
    receiver_type: str = ''
    receiver_version: str = ''
    antenna_number: str = ''
    antenna_type: str = ''
    approx_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    antenna_delta: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    obs_types: Dict[eGnss, List[str]] = field(default_factory=dict)
    interval: float = 0.0
    time_of_first_obs: Optional[Tuple] = None
    time_of_last_obs: Optional[Tuple] = None
    time_system: str = 'GPS'
    leap_seconds: int = 0
    num_satellites: int = 0
    comments: List[str] = field(default_factory=list)
    glonass_slots: Dict[int, int] = field(default_factory=dict)


#==============================================================================
# \Class: S_SatObs
# \Brief: Observations for one satellite in one epoch
# \Note:
#   obs maps an observation descriptor (for example C1C) to its value.
#   Missing observations are omitted. lli and signalStrength use the same keys.
#==============================================================================
@dataclass
class S_SatObs:
    """Observations for a single satellite in a single epoch.

    Attributes:
        system (eGnss): GNSS constellation.
        prn (int): Satellite PRN or slot number.
        obs (dict): Maps observation descriptor (str, e.g. 'C1C') to value (float).
                    Missing observations are not included.
        lli (dict): Maps descriptor -> Loss-of-Lock Indicator (int), if present.
        signal_strength (dict): Maps descriptor -> signal strength indicator (int).
    """
    system: eGnss = eGnss.eUnknownSystem
    prn: int = 0
    obs: Dict[str, float] = field(default_factory=dict)
    lli: Dict[str, int] = field(default_factory=dict)
    signal_strength: Dict[str, int] = field(default_factory=dict)


#==============================================================================
# \Class: S_EpochRecord
# \Brief: One complete observation epoch
# \Note:
#   epochFlag 0 is a normal epoch. Values above 1 are special events.
#   absGpsTime is seconds since the GPS epoch (GPST).
#==============================================================================
@dataclass
class S_EpochRecord:
    """One complete observation epoch.

    Attributes:
        year (int): 4-digit year.
        month (int): Month [1..12].
        day (int): Day [1..31].
        hour (int): Hour [0..23].
        minute (int): Minute [0..59].
        second (float): Second [0..60).
        epoch_flag (int): Epoch flag (0=OK, 1=power failure, >1=event).
        num_satellites (int): Number of satellites in this epoch.
        receiver_clock_offset (float): Receiver clock offset in seconds (if present).
        satellites (list): List of S_SatObs for each satellite.
        abs_gps_time (float): Absolute GPS time computed from epoch timestamp.
    """
    year: int = 0
    month: int = 0
    day: int = 0
    hour: int = 0
    minute: int = 0
    second: float = 0.0
    epoch_flag: int = 0
    num_satellites: int = 0
    receiver_clock_offset: float = 0.0
    satellites: List[S_SatObs] = field(default_factory=list)
    abs_gps_time: float = 0.0


#==============================================================================
# \Class: S_RinexObsFile
# \Brief: Complete parsed RINEX observation file
#==============================================================================
@dataclass
class S_RinexObsFile:
    """Complete parsed RINEX observation file.

    Attributes:
        header (S_RinexObsHeader): Parsed header data.
        epochs (list): List of S_EpochRecord, one per observation epoch.
        file_path (str): Path to the original RINEX file.
    """
    header: S_RinexObsHeader = field(default_factory=S_RinexObsHeader)
    epochs: List[S_EpochRecord] = field(default_factory=list)
    file_path: str = ''
