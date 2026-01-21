#!/usr/bin/env python3
"""
INSV Metadata Dumper

Standalone script to dump Insta360 INSV video file metadata to JSON format.
Replicates the functionality of the Java insvtools dump-meta command.

Usage:
    python insv_dump.py video.insv
    python insv_dump.py video.insv -o output.json
    python insv_dump.py video.insv --frame-type 3
    python insv_dump.py video.insv --include MAGNETIC,EULER
"""

import argparse
import os
import sys
from typing import Optional, Set

# Add the package directory to the path for standalone execution
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from insv_dump.metadata import InsvMetadata
from insv_dump.dump import dump_metadata, dump_frame
from insv_dump.frames.frame_types import FrameType, OPTIONAL_PARSED_TYPES


def parse_include_types(include_args: list) -> Set[FrameType]:
    """Parse --include arguments into a set of FrameTypes."""
    types = set()

    for arg in include_args:
        # Handle comma-separated values
        for name in arg.split(','):
            name = name.strip()
            if not name:
                continue

            frame_type = FrameType.from_name(name)
            if frame_type is None:
                print(f"Warning: Unknown frame type '{name}', ignoring", file=sys.stderr)
            else:
                types.add(frame_type)

    return types


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Dump INSV metadata to JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s video.insv                      Dump to video.insv.meta.json
  %(prog)s video.insv -o output.json       Dump to output.json
  %(prog)s video.insv --frame-type 3       Dump only GYRO frame
  %(prog)s video.insv --include MAGNETIC   Parse and include MAGNETIC frame
  %(prog)s video.insv --include MAGNETIC,EULER

Available frame types for --include:
  MAGNETIC, EULER, GYRO_SECONDARY, SPEED, HEARTRATE, EXPOSURE_SECONDARY
"""
    )
    parser.add_argument('input', nargs='?', help='Input INSV file')
    parser.add_argument('-o', '--output', help='Output JSON file (default: <input>.meta.json)')
    parser.add_argument('--frame-type', type=int, metavar='CODE',
                        help='Dump only the specified frame type (by numeric code)')
    parser.add_argument('--include', action='append', default=[], metavar='TYPES',
                        help='Include additional frame types for parsing (comma-separated)')
    parser.add_argument('--list-types', action='store_true',
                        help='List all known frame types and exit')

    args = parser.parse_args()

    # Handle --list-types
    if args.list_types:
        print("Known frame types:")
        for ft in FrameType:
            if ft == FrameType.RAW:
                continue
            optional = " (optional, use --include)" if ft in OPTIONAL_PARSED_TYPES else ""
            print(f"  {ft.value:3d}: {ft.name}{optional}")
        return 0

    # Check input file is provided
    if args.input is None:
        parser.error("the following arguments are required: input")

    # Check input file exists
    if not os.path.isfile(args.input):
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        return 1

    # Parse include types
    include_types = parse_include_types(args.include)

    # Read metadata
    try:
        with open(args.input, 'rb') as f:
            metadata = InsvMetadata.read(f)
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return 1

    if metadata is None:
        print(f"Error: No valid INSV metadata found in {args.input}", file=sys.stderr)
        return 1

    # Parse metadata
    try:
        metadata.parse(include_types if include_types else None)
    except Exception as e:
        print(f"Error parsing metadata: {e}", file=sys.stderr)
        return 1

    # Determine what to dump
    if args.frame_type is not None:
        frame = metadata.find_frame_by_code(args.frame_type)
        if frame is None:
            print(f"Error: Frame type {args.frame_type} not found", file=sys.stderr)
            return 1
        output_json = dump_frame(frame)
        default_suffix = f".frame{args.frame_type}.meta.json"
    else:
        output_json = dump_metadata(metadata)
        default_suffix = ".meta.json"

    # Determine output file
    if args.output:
        output_file = args.output
    else:
        output_file = os.path.basename(args.input) + default_suffix

    # Check if output file exists
    if os.path.exists(output_file):
        print(f"Error: File {output_file} already exists", file=sys.stderr)
        return 1

    # Write output
    try:
        with open(output_file, 'w') as f:
            f.write(output_json)
            f.write('\n')
        print(f"Metadata dumped to {output_file}")
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
