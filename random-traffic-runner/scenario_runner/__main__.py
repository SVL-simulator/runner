#!/usr/bin/env python3
"""Scenario supervisor controller"""

import argparse
import os
import sys

from .run_random_traffic import run_random_traffic

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
    description = 'Run RandomTraffic scenario on SVL Simulator'

    parser = argparse.ArgumentParser(os.path.basename(sys.argv[0]),
                                     description=description)

    parser.add_argument('--log-level', '-L', metavar='LEVEL', type=str,
                        default='INFO', help="Logging level")

    parser.add_argument("--duration", '-d', type=float,
                        default=0.,
                        help="Scenario duration in seconds. (default: %(default)s)")

    return parser.parse_args()


def main():
    args = parse_args()

    setup_log_levels(args.log_level.upper())

    run_random_traffic(args.duration)


if __name__ == "__main__":
    sys.exit(main())
