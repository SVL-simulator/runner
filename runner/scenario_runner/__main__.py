#!/usr/bin/env python3
"""Scenario supervisor controller"""

import argparse
import os
import sys

try:
    import scenic  # noqa: F401
    HAVE_SCENIC = True
except ModuleNotFoundError:
    HAVE_SCENIC = False

if HAVE_SCENIC:
    from .run_scenic import run_scenic, check_scenic

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
    global HAVE_SCENIC

    if HAVE_SCENIC:
        description = 'Run Scenic scenarios on LGSVL Simulator'
        scenario_file_description = 'Scenic scenario file'
    else:
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

    if HAVE_SCENIC:
        parser.add_argument("--num-iterations", '-i', type=int,
                            default=42,
                            help="Number of scenario iterations. (default: %(default)s)")

        parser.add_argument("--duration", '-d', type=float,
                            default=20.,
                            help="Scenario duration in seconds. (default: %(default)s)")

        parser.add_argument("--force-duration", '-f', action='store_true',
                            default=False,
                            help="Force simulation to end after given duration. \
                            If not set, simulation will end by given duration or \
                            at the time when all NPCs' waypoints have been reached.")

        parser.add_argument("--lgsvl-map", '-m', metavar="MAP_NAME", type=str,
                            default="GoMentum",
                            help="Map (default:  %(default)s)")

        parser.add_argument("--output-dir", '-O', metavar="OUTPUT_DIR", type=str,
                            default=None,
                            help="Default results output folder.")

        parser.add_argument("--sampler", '-s', action='store_true',
                            default=False,
                            help="Save sampler data after simulation is finished.")

        parser.add_argument("--check", '-t', action='store_true',
                            default=False,
                            help="Parse scenic files and exits")

    return parser.parse_args()


def main():
    args = parse_args()

    setup_log_levels(args.log_level.upper())

    if not os.path.exists(args.scenario_file):
        log.error("Can't find file %s", args.scenario_file)
        return 1

    global HAVE_SCENIC

    if HAVE_SCENIC and args.scenario_file[-3:] == ".sc":
        if args.check:
            try:
                check_scenic(args.scenario_file)
                log.info(" Scenic script %s OK ", args.scenario_file)
            except Exception as e:
                log.error("Error in scenic script %s: %s", args.scenario_file, e)
                raise
        else:
            log.info("Run Scenic scenario from %s", args.scenario_file)
            run_scenic(args.scenario_file, args.num_iterations, args.duration, args.lgsvl_map, args.output_dir, args.sampler)
    elif args.scenario_file[-3:] == ".py":
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
