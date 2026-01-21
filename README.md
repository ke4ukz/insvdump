# INSV Metadata Dumper (Python)

A Python tool for extracting and dumping metadata from Insta360 INSV video files to JSON format.

This is a Python port of the `dump-meta` command from [insvtools](https://github.com/alex-plekhanov/insvtools), a Java-based toolkit for working with Insta360 video files. The Python version provides the same metadata extraction functionality with fewer dependencies.

## Features

- Extracts metadata from Insta360 INSV video files
- Outputs human-readable JSON format
- Parses common frame types: INFO, GYRO, GPS, EXPOSURE, TIMELAPSE
- Optional parsing for additional frame types (MAGNETIC, EULER, etc.)
- Single dependency: `protobuf` Python package

## Installation

### Requirements

- Python 3.7+
- `protobuf` package

### Setup

```bash
# Install the protobuf dependency
pip install protobuf

# Clone or copy the insv_dump directory to your project
```

## Usage

```bash
# Basic usage - outputs to video.insv.meta.json
python insv_dump.py video.insv

# Specify output file
python insv_dump.py video.insv -o output.json

# Dump only a specific frame type (by numeric code)
python insv_dump.py video.insv --frame-type 3

# Include additional frame types for parsing
python insv_dump.py video.insv --include MAGNETIC,EULER
python insv_dump.py video.insv --include MAGNETIC --include EULER

# Scan a file to see what frame types it contains (no dump)
python insv_dump.py video.insv --scan

# Scan multiple files
python insv_dump.py --scan *.insv

# List all known frame types
python insv_dump.py --list-types
```

### Command-line Options

| Option | Description |
|--------|-------------|
| `input` | Input INSV file(s) (multiple files supported with `--scan`) |
| `-o, --output` | Output JSON file (default: `<input>.meta.json`) |
| `--frame-type CODE` | Dump only the specified frame type by numeric code |
| `--include TYPES` | Include additional frame types for parsing (comma-separated) |
| `--scan` | Scan file(s) and show frame types with counts (no dump) |
| `--list-types` | List all known frame types and exit |

## Frame Types

### Default Parsed Frames
| Code | Name | Description |
|------|------|-------------|
| 0 | INDEX | Frame index/offset table (internal) |
| 1 | INFO | Protobuf-encoded camera/file metadata |
| 3 | GYRO | Gyroscope sensor data |
| 4 | EXPOSURE | Camera exposure/shutter speed data |
| 6 | TIMELAPSE | Timelapse timestamp mapping |
| 7 | GPS | GPS location data |

### Optional Frames (use `--include`)
| Code | Name | Description |
|------|------|-------------|
| 12 | EXPOSURE_SECONDARY | Secondary exposure data |
| 13 | MAGNETIC | Magnetometer data |
| 14 | EULER | Orientation quaternions |
| 15 | GYRO_SECONDARY | Secondary gyroscope data |
| 16 | SPEED | Speed data |
| 19 | HEARTRATE | Heart rate monitor data |
| 23 | POS | Drone position/telemetry (see below) |

## Output Format

The JSON output structure matches the original Java tool:

```json
{
  "header": {
    "version": 3,
    "metaDataSize": 11001446,
    "metaDataPos": 272035488
  },
  "frames": [
    {
      "header": {
        "frameType": "INFO",
        "frameVersion": 1,
        "frameSize": 2954,
        "framePos": 283033646
      },
      "parsed": true,
      "extraMetadata": {
        "SerialNumber": "...",
        "CameraType": "Insta360 X4",
        "FwVersion": "v1.7.19_build1",
        "CreationTime": "20250615170133",
        ...
      }
    },
    {
      "header": {
        "frameType": "EXPOSURE",
        ...
      },
      "parsed": true,
      "records": [
        {"timestamp": 159610801, "shutterSpeed": 0.000815},
        ...
      ]
    }
  ]
}
```

## Drone Telemetry (POS Frame)

Videos recorded on drones (e.g., Antigravity A1) include a POS frame with flight telemetry data. Use `--include POS` to parse this data.

```bash
python insv_dump.py drone_video.insv --include POS
```

### POS Record Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | int | Timestamp in milliseconds |
| `xPos` | float | Local X position (units unclear) |
| `yPos` | float | Local Y position (units unclear) |
| `zPos` | float | Local Z position (units unclear) |
| `velocityH` | float | Horizontal velocity component (m/s) |
| `velocityV` | float | Vertical velocity / climb rate (m/s) |
| `speed` | float | Total speed magnitude (m/s) |
| `agl` | float | Above Ground Level in meters (omitted if N/A) |

**Note:** The `xPos`/`yPos`/`zPos` fields are local position coordinates whose exact meaning is not fully understood. They do NOT represent distance from home. To calculate total distance traveled, integrate the `speed` field over time.

### Example Output

```json
{
  "header": {"frameType": "POS", ...},
  "parsed": true,
  "records": [
    {
      "timestamp": 918895,
      "xPos": -0.0287,
      "yPos": -0.0193,
      "zPos": 1.8612,
      "velocityH": 0.0095,
      "velocityV": -0.0249,
      "speed": 0.0267,
      "agl": 4.65
    },
    ...
  ]
}
```

### Drone-Specific Frame Types

Drone recordings also include additional frame types that are not yet fully decoded:

| Code | Status | Notes |
|------|--------|-------|
| 32 | Unknown | Large frame, likely contains extended telemetry |
| 33 | Unknown | 33-byte records at 50Hz, possibly accelerometer data |
| 37 | Unknown | 36-byte records at 50Hz, velocity/orientation data |
| 38 | Unknown | Small frame, possibly configuration or summary |

The POS frame provides the most useful telemetry (position, velocity, AGL) for most applications.

### Reverse Engineering Status

**Confirmed fields:**
- `agl` (Float[9]): Above Ground Level in meters, -1.0 = N/A. Verified against video overlay.
- `velocityV` (Float[7]): Vertical velocity component in m/s. Correlates with overlay "D" (depth/vertical delta).
- `velocityH` (Float[6]): Horizontal velocity component in m/s.

**Partially understood:**
- `xPos`, `yPos`, `zPos` (Float[0-2]): Local position coordinates. NOT distance from home. Units and reference frame unclear. Values fluctuate rather than accumulate.
- Float[3-5]: Large values that change over time, possibly world coordinates or sensor data.
- Float[8]: Unknown, small values.

**Future work:** Controlled test flights (see [FLIGHT_TEST_PLAN.md](FLIGHT_TEST_PLAN.md)) would help decode the remaining fields.

## Notes

- **GYRO frame parsing**: The GYRO frame can only be parsed if the INFO frame contains a non-empty `Gyro` field (used to determine record size). This is the same behavior as the original Java tool.
- **INSV file format**: Metadata is stored at the end of the file and read backwards. The tool handles both indexed and non-indexed metadata formats.
- **Protobuf**: The `extra_metadata_pb2.py` file is pre-compiled and included, so you don't need the `protoc` compiler installed.

## Project Structure

```
insv_dump/
├── insv_dump.py                    # Standalone entry point
├── extra_metadata.proto            # Proto source (for reference)
├── README.md
└── insv_dump/                      # Package
    ├── __init__.py
    ├── header.py                   # INSV file header parsing
    ├── metadata.py                 # Main orchestration
    ├── dump.py                     # JSON serialization
    ├── frames/                     # Frame type implementations
    │   ├── frame_types.py
    │   ├── frame_header.py
    │   ├── frame.py
    │   ├── index_frame.py
    │   ├── info_frame.py
    │   ├── timestamped.py
    │   ├── gyro_frame.py
    │   ├── gps_frame.py
    │   ├── exposure_frame.py
    │   ├── timelapse_frame.py
    │   └── pos_frame.py            # Drone position/telemetry
    ├── records/                    # Record type implementations
    │   ├── base.py
    │   ├── gyro.py
    │   ├── gps.py
    │   ├── exposure.py
    │   ├── timelapse.py
    │   └── pos.py                  # Drone position records
    └── proto/
        └── extra_metadata_pb2.py   # Compiled protobuf
```

## License

This project is a derivative work based on [insvtools](https://github.com/alex-plekhanov/insvtools) by Alex Plekhanov, which is licensed under the Apache License 2.0.

This Python port is also licensed under the Apache License 2.0.

## Third-Party Licenses

### insvtools
- **Source**: https://github.com/alex-plekhanov/insvtools
- **License**: Apache License 2.0
- **Copyright**: Alex Plekhanov

### Protocol Buffers
- **Source**: https://github.com/protocolbuffers/protobuf
- **License**: BSD 3-Clause License
- **Copyright**: Google LLC

The `extra_metadata.proto` file format is derived from reverse-engineering the Insta360 INSV file format by the insvtools project.

## See Also

- [insvtools](https://github.com/alex-plekhanov/insvtools) - The original Java toolkit with additional features (video cutting, metadata manipulation, etc.)
- [Protocol Buffers](https://github.com/protocolbuffers/protobuf) - Google's data serialization library
