# Ananse GNSS QC

**A comprehensive quality control tool for GNSS RINEX observation files.**

Ananse GNSS QC reads RINEX observation files (versions 2.x, 3.x, and 4.x) and performs a suite of quality control analyses to assess data readiness for GNSS processing. It produces detailed text and JSON reports suitable for both human inspection and programmatic consumption (e.g., via a web application). An optional RINEX navigation file supplies broadcast positions for a sky plot and elevation-binned SNR.

---

## Features

- **Automatic RINEX Version Detection** — reads RINEX 2.x (2.00–2.11), 3.x (3.00–3.05), and 4.x observation files
- **Multi-Constellation Support** — GPS, GLONASS, Galileo, BeiDou, QZSS, SBAS, NavIC
- **Satellite & Observable Availability** — per-satellite epoch count, tracking arcs, data gaps, Loss-of-Lock events
- **Missing Observables** — header observation types that are absent or incomplete, with epoch counts and missing percent
- **Epoch Sampling Analysis** — nominal interval detection, interval statistics, data completeness percentage, gap detection
- **Cycle Slip Detection** — Time-Differenced Carrier Phase (TDCP) and Melbourne-Wübbena (MW) dual-frequency methods
- **Multipath Estimation** — MP1/MP2 linear combinations (geometry-free, ionosphere-free) with per-satellite RMS
- **SNR Quality Metrics** — per-satellite, per-observable signal strength statistics with good/fair/poor classification
- **Navigation Files** — RINEX 2 and RINEX 3/4 broadcast ephemerides. GPS, Galileo, BeiDou, QZSS, and NavIC positions are computed. GLONASS and SBAS records are stored and are not used for positions
- **Dual Output Formats** — human-readable text reports and machine-readable JSON for web APIs
- **QC Plots** — seven matplotlib figures from the observation file, plus a sky plot and an elevation-binned SNR plot when `--nav` is given

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/johnaggrey/Ananse_GNSS_QC.git
cd Ananse_GNSS_QC

# Install in development mode
pip install -e ".[dev]"
```

### Command Line Usage

```bash
# Basic QC report (text output to terminal)
ananse-qc station.24o

# JSON output to file
ananse-qc data.rnx --format json --output report.json

# Verbose mode (debug logging)
ananse-qc data.obs --verbose

# Text report plus seven PNG figures beside the report file
ananse-qc station.24o --output report.txt

# The seven QC figures, plus a sky plot and elevation-binned SNR
ananse-qc station.24o --nav station.nav --output report.txt

# Or run as a Python module
python -m AnanseQC station.24o
```

### Python API Usage

`RunQualityCheck` is the call a web application should use. It reads the file once and returns a JSON-ready dictionary, a text report, and a status code. Times in the report are GPST. Positions are ECEF metres. SNR is dB-Hz. The dictionary field `schema_version` is the response contract (`1.0`).

```python
from AnanseQC.Core.Enums import eFileReadingStatus
from AnanseQC.QualityCheck import RunQualityCheck

report, textReport, eStatus = RunQualityCheck("station.24o")
if eStatus != eFileReadingStatus.eSuccess:
    print(f"Error: {eStatus.name}")
    exit(1)

print(textReport)
print(report["schema_version"])
print(report["availability"]["duration_seconds"])
```

`RunQualityCheck` returns the report only. It does not open or save figures, and it does not read a navigation file. A web application should keep using that call. The sky plot and the elevation SNR plot are command-line figures.

### Plots

The command-line tool draws seven figures from the same QC results as the report. Time axes are hours from the first epoch, labelled GPST. Satellite labels use the RINEX system character and PRN, such as `G01`.

| PNG file | Figure |
|----------|--------|
| `report_satellites.png` | Satellites versus time |
| `report_availability.png` | Percent of epochs each satellite is present |
| `report_intervals.png` | Epoch interval and gaps, in seconds |
| `report_missing.png` | Missing observables as a percent of that satellite's tracked epochs |
| `report_slips.png` | Cycle slips versus time (TDCP and Melbourne-Wübbena) |
| `report_multipath.png` | MP1 and MP2 RMS, in metres |
| `report_snr.png` | Mean SNR per satellite, in dB-Hz, with lines at 25 and 35 |
| `report_sky.png` | Polar sky plot. Written only with `--nav` |
| `report_snr_elevation.png` | Mean SNR in 10-degree elevation bins, in dB-Hz. Written only with `--nav` |

Without `--output`, the text report is printed and the figures open on screen. Close the figures to exit. With `--output`, the report is written to that path and each figure is saved beside it. The PNG name is the report file name without its extension, plus the plot name. `ananse-qc station.24o --output report.json` writes `report.json` and the seven observation PNG files, including `report_snr.png`. Adding `--nav station.nav` also writes `report_sky.png` and `report_snr_elevation.png`.

### Navigation file

`--nav` reads a RINEX 2 navigation file (GPS `N`, GLONASS `G`, or GEO/SBAS `H`) or a RINEX 3/4 mixed navigation file (type `N`). RINEX 4 `> EPH` records use the RINEX 3 layout. Other RINEX 4 blocks are skipped. The observation QC report is unchanged when `--nav` is omitted. If `--nav` is set and the navigation file cannot be read, the run stops before the report and the plots.

Broadcast positions are ECEF metres. The receiver is the observation-header approximate position, also ECEF metres on WGS84. Antenna height is not applied. Azimuth is degrees clockwise from north, in the range 0 to 360. Elevation is degrees from the horizon, positive upward. One light-time iteration is applied. On the sky plot, north is at the top, azimuth increases clockwise, and the radius is 90 degrees minus elevation, so zenith is at the centre.

Times stored on each ephemeris are absolute GPST seconds.

| System | Broadcast time | Position |
|--------|----------------|----------|
| GPS, QZSS, NavIC | GPST | Kepler orbit, ECEF metres |
| Galileo | GST, treated as GPST | Kepler orbit, ECEF metres |
| BeiDou | BDT. GPST = BDT + 14 s | Kepler orbit, ECEF metres. GEO PRNs 1–5 and 59–63 include the 5 degree ICD rotation |
| GLONASS | The file epoch is UTC. The stored epoch is that calendar time read as GPST, plus the header leap seconds | State record stored in metres, m/s, and m/s². The frame is PZ-90. No position is computed |
| SBAS | GPST | State record stored in metres, m/s, and m/s². No position is computed |

A Kepler satellite is plotted only when its health is 0 and the epoch is within 4 hours of the time of ephemeris (14400 s). GLONASS and SBAS records are read and are not drawn.

The elevation SNR figure places each `S*` observation into a 10-degree bin from 0 to 90 degrees. Each sample has weight 1, and the bin value is the count-weighted mean in dB-Hz. Empty bins stay empty. The same 25 and 35 dB-Hz lines are drawn. Both navigation figures are skipped when the approximate position is the ECEF origin `(0, 0, 0)`. The tool then prints `Approximate position is zero. Sky plot and elevation SNR plot skipped.`

---

## Architecture

```
AnanseQC/
├── Core/                      # Foundation layer
│   ├── Constants.py           # GNSS constants (CLIGHT, frequencies, time system)
│   ├── Enums.py               # eGnss, eGnssFreq, eFileReadingStatus, eRinexObsVersion
│   └── TimeUtils.py           # C_TimeUtils (calendar, Julian date, GPS week/SOW)
│
├── Readers/                   # RINEX file parsing
│   ├── ObsTypes.py            # S_RinexObsFile, S_EpochRecord, S_SatObs
│   ├── NavTypes.py            # S_KeplerEph, S_StateEph, S_RinexNavFile
│   ├── RinexDetector.py       # C_RinexVersionDetector
│   ├── RinexV2Reader.py       # C_RinexObsReaderV2
│   ├── RinexV3Reader.py       # C_RinexObsReaderV3 (also reads 4.x)
│   ├── RinexNavV2Reader.py    # C_RinexNavReaderV2
│   ├── RinexNavV3Reader.py    # C_RinexNavReaderV3 (also reads 4.x)
│   ├── Reader.py              # C_RinexObsReader
│   └── NavReader.py           # C_RinexNavReader
│
├── Navigation/                # Broadcast orbits and topocentric geometry
│   ├── BroadcastOrbit.py      # C_BroadcastOrbit (ECEF metres, GPST)
│   └── SatGeometry.py         # C_SatGeometry (azimuth and elevation, degrees)
│
├── QualityChecks/             # QC analysis engines
│   ├── Availability.py        # C_ObsAvailability
│   ├── MissingObservables.py  # C_MissingObservables
│   ├── EpochSampling.py       # C_EpochSampling
│   ├── CycleSlips.py          # C_CycleSlipDetector (TDCP + Melbourne-Wübbena)
│   ├── MultipathSnr.py        # C_MultipathSnr
│   └── ElevationSnr.py        # C_ElevationSnr (dB-Hz in 10-degree bins)
│
├── Reports/                   # Report generation
│   ├── QualityCheckReport.py  # C_QcReport (text and JSON)
│   └── Plots.py               # C_QcPlots (screen figures and PNG files)
│
├── QualityCheck.py            # RunQualityCheck
├── CommandLineInterface.py    # C_QcCommand
└── __main__.py                # python -m AnanseQC entry point

Tests/
├── data/                      # Sample RINEX snippets for testing
├── Test_TimeUtils.py
├── Test_RinexReaders.py
├── Test_QC_Engines.py
├── Test_MissingObservables.py
├── Test_GapSampling.py
├── Test_QualityCheck.py
├── Test_SatellitePlot.py
├── Test_AvailabilityPlot.py
├── Test_IntervalPlot.py
├── Test_MissingPlot.py
├── Test_SlipPlot.py
├── Test_MultipathPlot.py
├── Test_SnrPlot.py
├── Test_NavDetector.py
├── Test_NavV3Reader.py
├── Test_NavV2Reader.py
├── Test_BroadcastOrbitGps.py
├── Test_BroadcastOrbitOther.py
├── Test_SatGeometry.py
├── Test_SkyPlot.py
└── Test_ElevationSnr.py
```

---

## QC Metrics Explained

### Satellite Availability
Tracks which satellites are present in each epoch, computes tracking arc lengths and data gaps per satellite, and counts Loss-of-Lock Indicator (LLI) transitions. Observation duration is the GPST span from the first epoch to the last epoch, in seconds.

### Missing Observables
Each constellation's observation types are taken from the RINEX header. For every satellite, a declared type is missing at a tracked epoch when that descriptor has no value. The report gives the present count, the missing count, and the missing percent of that satellite's tracked epochs. A header type that is never observed on any satellite of its constellation is listed separately.

### Epoch Sampling
Detects the nominal sampling interval (statistical mode of inter-epoch intervals), identifies data gaps (intervals exceeding 1.5× nominal), and computes overall data completeness as a percentage.

### Cycle Slip Detection

**TDCP (Time-Differenced Carrier Phase):** Computes the second difference of carrier phase measurements. Jumps exceeding 0.5 cycles indicate a probable cycle slip. Works with single-frequency data.

**Melbourne-Wübbena:** Combines dual-frequency code and phase measurements to form the widelane ambiguity, which should remain constant over time. Jumps exceeding 1.0 widelane cycle indicate a slip. More robust than TDCP but requires dual-frequency observations.

### Multipath (MP1/MP2)
The standard multipath linear combinations:

$$MP_1 = P_1 - \lambda_1 \phi_1 - \frac{2 f_2^2}{f_1^2 - f_2^2}(\lambda_1 \phi_1 - \lambda_2 \phi_2)$$

$$MP_2 = P_2 - \lambda_2 \phi_2 - \frac{2 f_1^2}{f_1^2 - f_2^2}(\lambda_1 \phi_1 - \lambda_2 \phi_2)$$

These combinations eliminate geometry and ionosphere, isolating pseudorange multipath + noise. The arc mean is removed to account for phase ambiguity bias, and the RMS of the residuals is reported.

### SNR Quality
Classifies signal strength observations into three tiers:
- **Good**: ≥ 35 dBHz
- **Fair**: 25–35 dBHz
- **Poor**: < 25 dBHz

When `--nav` is supplied, mean SNR is also accumulated in 10-degree elevation bins. See Navigation file above.

---

## Supported RINEX Versions

| Version | Header | Body | Notes |
|---------|--------|------|-------|
| 2.00–2.11 | ✅ | ✅ | 2-digit year, single obs type list |
| 3.00–3.05 | ✅ | ✅ | Per-system obs types, 3-char descriptors |
| 4.00+ | ✅ | ✅ | Parsed via V3 reader (compatible format) |

---

## Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run the test suite
pytest Tests/ -v
```

---

## Roadmap

- [x] Navigation file reading (RINEX 2 and 3/4), sky plot, and elevation-binned SNR
- [ ] Elevation-dependent multipath
- [ ] Ionospheric delay estimation (geometry-free combination)
- [ ] RINEX file repair/cleaning suggestions
- [ ] HTML report generation with charts
- [ ] Web application frontend for file upload and QC
- [ ] Support for RINEX meteorological files
- [ ] Hatanaka compressed RINEX (CRX) decompression

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Author

**John Aggrey** — GNSS Software Engineer
