# Ananse GNSS QC

**A comprehensive quality control tool for GNSS RINEX observation files.**

Ananse GNSS QC reads RINEX observation files (versions 2.x, 3.x, and 4.x) and performs a suite of quality control analyses to assess data readiness for GNSS processing. It produces detailed text and JSON reports suitable for both human inspection and programmatic consumption (e.g., via a web application).

---

## Features

- **Automatic RINEX Version Detection** — reads RINEX 2.x (2.00–2.11), 3.x (3.00–3.05), and 4.x observation files
- **Multi-Constellation Support** — GPS, GLONASS, Galileo, BeiDou, QZSS, SBAS, NavIC
- **Satellite & Observable Availability** — per-satellite epoch count, tracking arcs, data gaps, Loss-of-Lock events
- **Epoch Sampling Analysis** — nominal interval detection, interval statistics, data completeness percentage, gap detection
- **Cycle Slip Detection** — Time-Differenced Carrier Phase (TDCP) and Melbourne-Wübbena (MW) dual-frequency methods
- **Multipath Estimation** — MP1/MP2 linear combinations (geometry-free, ionosphere-free) with per-satellite RMS
- **SNR Quality Metrics** — per-satellite, per-observable signal strength statistics with good/fair/poor classification
- **Dual Output Formats** — human-readable text reports and machine-readable JSON for web APIs

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/YourUsername/Ananse-GNSS-QC.git
cd Ananse-GNSS-QC

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

# Or run as a Python module
python -m ananse_qc station.24o
```

### Python API Usage

```python
from ananse_qc.core.enums import eFileReadingStatus
from ananse_qc.qc.availability import C_ObsAvailability
from ananse_qc.qc.cycle_slips import C_CycleSlipDetector
from ananse_qc.qc.epoch_sampling import C_EpochSampling
from ananse_qc.qc.multipath_snr import C_MultipathSnr
from ananse_qc.readers.reader import C_RinexObsReader
from ananse_qc.reports.qc_report import C_QcReport

# Read a RINEX file. The reader detects version 2.x, 3.x, or 4.x.
obsFile, eStatus = C_RinexObsReader().Read("station.24o")
if eStatus != eFileReadingStatus.eSuccess:
    print(f"Error: {eStatus.name}")
    exit(1)

print(f"Station: {obsFile.header.marker_name}")
print(f"Epochs:  {len(obsFile.epochs)}")

# Run QC analyses
availability = C_ObsAvailability().Analyse(obsFile)
sampling = C_EpochSampling().Analyse(obsFile)
slips = C_CycleSlipDetector().Analyse(obsFile)
mpSnr = C_MultipathSnr().Analyse(obsFile)

# Generate a text report, or a JSON report for a web API
c_Report = C_QcReport()
print(c_Report.GenerateText(obsFile, availability, sampling, slips, mpSnr))
jsonReport = c_Report.GenerateJson(obsFile, availability, sampling, slips, mpSnr)
```

---

## Architecture

```
ananse_qc/
├── core/                  # Foundation layer
│   ├── constants.py       # GNSS constants (CLIGHT, frequencies, time system)
│   ├── enums.py           # eGnss, eGnssFreq, eFileReadingStatus, eRinexObsVersion
│   └── time_utils.py      # C_TimeUtils (calendar, Julian date, GPS week/SOW)
│
├── readers/               # RINEX file parsing
│   ├── obs_types.py       # S_RinexObsFile, S_EpochRecord, S_SatObs
│   ├── rinex_detector.py  # C_RinexVersionDetector
│   ├── rinex_v2_reader.py # C_RinexObsReaderV2
│   ├── rinex_v3_reader.py # C_RinexObsReaderV3 (also reads 4.x)
│   └── reader.py          # C_RinexObsReader
│
├── qc/                    # QC analysis engines
│   ├── availability.py    # C_ObsAvailability
│   ├── epoch_sampling.py  # C_EpochSampling
│   ├── cycle_slips.py     # C_CycleSlipDetector (TDCP + Melbourne-Wübbena)
│   └── multipath_snr.py   # C_MultipathSnr
│
├── reports/               # Report generation
│   └── qc_report.py       # C_QcReport (text and JSON)
│
├── cli.py                 # C_QcCommand
└── __main__.py            # python -m ananse_qc entry point

tests/
├── data/                  # Sample RINEX snippets for testing
├── test_time_utils.py     # Time conversion tests
├── test_rinex_readers.py  # Reader tests (V2, V3, unified)
└── test_qc_engines.py     # QC engine tests
```

---

## QC Metrics Explained

### Satellite Availability
Tracks which satellites are present in each epoch, computes tracking arc lengths and data gaps per satellite, and counts Loss-of-Lock Indicator (LLI) transitions.

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
pytest tests/ -v
```

---

## Roadmap

- [ ] Navigation file reading (for elevation-dependent analysis)
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
