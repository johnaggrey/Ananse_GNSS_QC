# Ananse GNSS QC

**A comprehensive quality control tool for GNSS RINEX observation files.**

Ananse GNSS QC reads RINEX observation files (versions 2.x, 3.x, and 4.x) and performs a suite of quality control analyses to assess data readiness for GNSS processing. It produces detailed text and JSON reports suitable for both human inspection and programmatic consumption (e.g., via a web application).

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
- **Dual Output Formats** — human-readable text reports and machine-readable JSON for web APIs
- **QC Plots** — seven matplotlib figures, shown on screen or saved as PNG files beside the report

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

`RunQualityCheck` returns the report only. It does not open or save figures. A web application should keep using that call.

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

Without `--output`, the text report is printed and the figures open on screen. Close the figures to exit. With `--output`, the report is written to that path and each figure is saved beside it. The PNG name is the report file name without its extension, plus the plot name. `ananse-qc station.24o --output report.json` writes `report.json` and the same seven PNG files, including `report_snr.png`.

A sky plot needs satellite azimuth and elevation from a navigation file. This tool reads observation files only, so sky plots and elevation-dependent SNR wait on navigation-file reading.

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
│   ├── RinexDetector.py       # C_RinexVersionDetector
│   ├── RinexV2Reader.py       # C_RinexObsReaderV2
│   ├── RinexV3Reader.py       # C_RinexObsReaderV3 (also reads 4.x)
│   └── Reader.py              # C_RinexObsReader
│
├── QualityChecks/             # QC analysis engines
│   ├── Availability.py        # C_ObsAvailability
│   ├── MissingObservables.py  # C_MissingObservables
│   ├── EpochSampling.py       # C_EpochSampling
│   ├── CycleSlips.py          # C_CycleSlipDetector (TDCP + Melbourne-Wübbena)
│   └── MultipathSnr.py        # C_MultipathSnr
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
└── Test_SnrPlot.py
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

- [ ] Navigation file reading (needed for sky plots and elevation-dependent SNR)
- [ ] Elevation-dependent multipath and SNR analysis
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
