#==============================================================================
# Imported classes and modules
#==============================================================================
# In-memory records for a parsed RINEX navigation file.
# Readers fill these records. Orbit and geometry code consumes them later.
#
# Structures:
#   S_KeplerEph         Broadcast Kepler ephemeris
#   S_StateEph          Broadcast position and velocity (GLONASS, SBAS)
#   S_RinexNavHeader    Navigation header
#   S_RinexNavFile      Complete parsed navigation file
#
# Units and frames:
#   toc_gpst and toe_gpst are absolute seconds, GPST.
#   Kepler angles are radians. sqrt_a is metres^0.5.
#   Harmonic radius terms are metres. Harmonic angle terms are radians.
#   Clock af0 is seconds, af1 is seconds/second, af2 is seconds/second^2.
#   State position is ECEF metres. Velocity is metres/second.
#   Acceleration is metres/second^2.
#   GLONASS state is stored in those SI units. The RINEX kilometres
#   conversion belongs in the reader.
#==============================================================================
from dataclasses import dataclass, field
from typing import List

from AnanseQC.Core.Enums import eGnss, eRinexObsVersion


#==============================================================================
# \Class: S_KeplerEph
# \Brief: One broadcast Kepler ephemeris for GPS, Galileo, BeiDou, QZSS, or NavIC
# \Note:
#   toc_gpst and toe_gpst are absolute GPST seconds.
#   week is the broadcast week number before that conversion.
#   health 0 means the satellite is usable.
#==============================================================================
@dataclass
class S_KeplerEph:
    """Broadcast Kepler ephemeris.

    Attributes:
        system (eGnss): Constellation.
        prn (int): Satellite PRN.
        toc_gpst (float): Clock epoch, absolute GPST seconds.
        toe_gpst (float): Ephemeris epoch, absolute GPST seconds.
        week (int): Broadcast week number.
        health (int): 0 means usable.
        af0 (float): Clock bias, seconds.
        af1 (float): Clock drift, seconds/second.
        af2 (float): Clock drift rate, seconds/second^2.
        iode (float): Issue of data, ephemeris.
        iodc (float): Issue of data, clock.
        crs (float): Radius correction sine, metres.
        crc (float): Radius correction cosine, metres.
        cuc (float): Argument-of-latitude correction cosine, radians.
        cus (float): Argument-of-latitude correction sine, radians.
        cic (float): Inclination correction cosine, radians.
        cis (float): Inclination correction sine, radians.
        delta_n (float): Mean-motion correction, radians/second.
        m0 (float): Mean anomaly, radians.
        e (float): Eccentricity, dimensionless.
        sqrt_a (float): Square root of semi-major axis, metres^0.5.
        omega0 (float): Longitude of ascending node, radians.
        i0 (float): Inclination, radians.
        omega (float): Argument of perigee, radians.
        omega_dot (float): Node rate, radians/second.
        idot (float): Inclination rate, radians/second.
        tgd (float): Group delay, seconds.
        codes (float): L2 or data-source code, as broadcast.
        fit_interval (float): Fit interval, hours. 0 when absent.
    """
    system: eGnss = eGnss.eUnknownSystem
    prn: int = 0
    toc_gpst: float = 0.0
    toe_gpst: float = 0.0
    week: int = 0
    health: int = 0
    af0: float = 0.0
    af1: float = 0.0
    af2: float = 0.0
    iode: float = 0.0
    iodc: float = 0.0
    crs: float = 0.0
    crc: float = 0.0
    cuc: float = 0.0
    cus: float = 0.0
    cic: float = 0.0
    cis: float = 0.0
    delta_n: float = 0.0
    m0: float = 0.0
    e: float = 0.0
    sqrt_a: float = 0.0
    omega0: float = 0.0
    i0: float = 0.0
    omega: float = 0.0
    omega_dot: float = 0.0
    idot: float = 0.0
    tgd: float = 0.0
    codes: float = 0.0
    fit_interval: float = 0.0


#==============================================================================
# \Class: S_StateEph
# \Brief: One broadcast state record for GLONASS or SBAS
# \Note:
#   Position is ECEF metres. GLONASS coordinates are PZ-90.
#   Positions are stored for a later orbit step. They are not used yet.
#==============================================================================
@dataclass
class S_StateEph:
    """Broadcast position, velocity, and acceleration.

    Attributes:
        system (eGnss): eGLN or eSBAS.
        prn (int): Slot or PRN.
        epoch_gpst (float): State epoch, absolute GPST seconds.
        x_m (float): ECEF X, metres.
        y_m (float): ECEF Y, metres.
        z_m (float): ECEF Z, metres.
        vx_mps (float): ECEF X velocity, metres/second.
        vy_mps (float): ECEF Y velocity, metres/second.
        vz_mps (float): ECEF Z velocity, metres/second.
        ax_mps2 (float): ECEF X acceleration, metres/second^2.
        ay_mps2 (float): ECEF Y acceleration, metres/second^2.
        az_mps2 (float): ECEF Z acceleration, metres/second^2.
        clock_bias (float): Clock bias, seconds.
        frequency_bias (float): Relative frequency bias, dimensionless.
        frequency_slot (int): GLONASS frequency slot. 0 when absent.
        health (int): 0 means usable.
    """
    system: eGnss = eGnss.eUnknownSystem
    prn: int = 0
    epoch_gpst: float = 0.0
    x_m: float = 0.0
    y_m: float = 0.0
    z_m: float = 0.0
    vx_mps: float = 0.0
    vy_mps: float = 0.0
    vz_mps: float = 0.0
    ax_mps2: float = 0.0
    ay_mps2: float = 0.0
    az_mps2: float = 0.0
    clock_bias: float = 0.0
    frequency_bias: float = 0.0
    frequency_slot: int = 0
    health: int = 0


#==============================================================================
# \Class: S_RinexNavHeader
# \Brief: Parsed RINEX navigation file header
#==============================================================================
@dataclass
class S_RinexNavHeader:
    """Parsed RINEX navigation file header.

    Attributes:
        version (float): RINEX format version (for example 2.11 or 3.04).
        version_enum (eRinexObsVersion): Coarse version category.
        file_type (str): 'N' for navigation.
        satellite_system (str): System character ('G', 'M', 'R', and so on).
        leap_seconds (int): Leap seconds from the header, or 0 when absent.
        comments (list): COMMENT lines from the header.
    """
    version: float = 0.0
    version_enum: eRinexObsVersion = eRinexObsVersion.eRinexObsVersion_Unknown
    file_type: str = ''
    satellite_system: str = ''
    leap_seconds: int = 0
    comments: List[str] = field(default_factory=list)


#==============================================================================
# \Class: S_RinexNavFile
# \Brief: Complete parsed RINEX navigation file
#==============================================================================
@dataclass
class S_RinexNavFile:
    """Complete parsed RINEX navigation file.

    Attributes:
        header (S_RinexNavHeader): Parsed header.
        kepler_eph (list): Kepler records for GPS, Galileo, BeiDou, QZSS, NavIC.
        state_eph (list): GLONASS and SBAS state records. Positions are not
                          computed from these yet.
        file_path (str): Path to the original navigation file.
    """
    header: S_RinexNavHeader = field(default_factory=S_RinexNavHeader)
    kepler_eph: List[S_KeplerEph] = field(default_factory=list)
    state_eph: List[S_StateEph] = field(default_factory=list)
    file_path: str = ''
