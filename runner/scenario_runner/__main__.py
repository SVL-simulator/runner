#!/usr/bin/env python3
"""Scenic supervisor controller"""

import argparse
import os
import sys

from .run_scenic import run_scenic
from .run_python import run_python

import logging

FORMAT = "[%(levelname)6s] [%(name)s] %(message)s"

logging.basicConfig(level=logging.DEBUG, format=FORMAT)
log = logging.getLogger("scenario_runner")


def setup_log_levels():
    logging.getLogger('matplotlib').setLevel(logging.INFO)
    logging.getLogger('websockets').setLevel(logging.INFO)
    logging.getLogger('selector_events').setLevel(logging.INFO)
    logging.getLogger('asyncio').setLevel(logging.INFO)


def parse_args():
    description = '''Run Scenic scenarios on LGSVL Simulator
    '''
    parser = argparse.ArgumentParser(os.path.basename(sys.argv[0]),
                                     description=description)

    parser.add_argument('scenario_file', metavar='SCENARIO_FILE', type=str,
                        help='Scenic scenario file.')

    parser.add_argument('extra_args', metavar='ARGS', type=str, nargs='*',
                        help='(optional) Extra arguments for scenario.')

    parser.add_argument("--num-iterations", '-i', type=int,
                        default=42,
                        help="Number of scenario iterations. (default: %(default)s)")

    parser.add_argument("--duration", '-d', type=float,
                        default=20.,
                        help="Scenario duration in seconds. (default: %(default)s)")

    parser.add_argument("--lgsvl-map", '-m', metavar="MAP_NAME", type=str,
                        default="GoMentum",
                        help="Map (default:  %(default)s)")

    parser.add_argument("--output-dir", '-O', metavar="OUTPUT_DIR", type=str,
                        default=None,
                        help="Default results output folder.")

    parser.add_argument("--sampler", '-s', action='store_true',
                        default=False,
                        help="Save sampler data after simulation is finished.")

    return parser.parse_args()


def main():
    args = parse_args()

    setup_log_levels()

    if args.scenario_file[-3:] == ".sc":
        log.info("Run Scenic scenario from %s", args.scenario_file)
        run_scenic(args.scenario_file, args.num_iterations, args.duration, args.lgsvl_map, args.output_dir, args.sampler)
    elif args.scenario_file[-3:] == ".py":
        log.info("Run python script %s", args.scenario_file)
        run_python(args.scenario_file, args.extra_args)
    else:
        log.error("Failed to process file of unknown type %s", args.scenario_file)


if __name__ == "__main__":
    main()
