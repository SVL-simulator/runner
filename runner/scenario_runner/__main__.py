#!/usr/bin/env python3
"""Scenario supervisor controller"""

import argparse
import os
import sys

from .run_python import run_python
from .run_vse import VSERunner

import logging

FORMAT = "[%(levelname)6s] [%(name)s] %(message)s"

logging.basicConfig(level=logging.DEBUG, format=FORMAT)
log = logging.getLogger("scenario_runner")


def setup_log_levels(log_level):
    log.setLevel(log_level)

    # Reset levels for some chatty modules
    logging.getLogger('matplotlib').setLevel(logging.INFO)
    logging.getLogger('websockets').setLevel(logging.INFO)
    logging.getLogger('selector_events').setLevel(logging.INFO)
    logging.getLogger('asyncio').setLevel(logging.INFO)


def parse_args():
    description = 'Run Python and VSE-generated scenarios on LGSVL Simulator'
    scenario_file_description = 'Python (*.py) or VSE JSON (*.json) scenario file'

    parser = argparse.ArgumentParser(os.path.basename(sys.argv[0]),
                                     description=description)

    parser.add_argument('scenario_file', metavar='SCENARIO_FILE', type=str,
                        help=scenario_file_description)

    parser.add_argument('extra_args', metavar='ARGS', type=str, nargs='*',
                        help='(optional) Extra arguments for scenario.')

    parser.add_argument('--log-level', '-L', metavar='LEVEL', type=str,
                        default='INFO', help="Logging level")

    parser.add_argument("--duration", '-d', type=float,
                        default=20.,
                        help="Scenario duration in seconds. (default: %(default)s)")

    parser.add_argument("--force-duration", '-f', action='store_true',
                        default=False,
                        help="Force simulation to end after given duration. \
                        If not set, simulation will end by given duration or \
                        at the time when all NPCs' waypoints have been reached.")

    return parser.parse_args()


def main():
    args = parse_args()

    setup_log_levels(args.log_level.upper())

    if not os.path.exists(args.scenario_file):
        log.error("Can't find file %s", args.scenario_file)
        return 1

    if args.scenario_file[-3:] == ".py":
        log.info("Run python script %s", args.scenario_file)
        return run_python(args.scenario_file, args.extra_args)
    elif args.scenario_file[-5:] == ".json":
        log.info("Run VSE scenario %s", args.scenario_file)
        vse_runner = VSERunner(args.scenario_file)
        vse_runner.run(args.duration, args.force_duration)
    else:
        log.error("Failed to process file of unknown type %s", args.scenario_file)


if __name__ == "__main__":
    sys.exit(main())
