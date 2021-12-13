#
# Copyright (c) 2020-2021 LG Electronics, Inc.
#
# This software contains code licensed as described in LICENSE.
#

from scenario_runner.adstack_wrapper_interface import BaseADStackWrapper
from scenario_runner.runner_utils import print_vector
import logging

FORMAT = '%(asctime)-15s [%(levelname)s][%(module)s] %(message)s'

logging.basicConfig(level=logging.INFO, format=FORMAT)
log = logging.getLogger(__name__)


class Wrapper(BaseADStackWrapper):
    def __init__(self, parent, bridge_host, bridge_port):
        assert parent, "Can not create an AD stack wrapper without a valid parent EgoWrapper!"
        self.parent = parent
        self.bridge_host = bridge_host
        self.bridge_port = bridge_port
        self.destinations_queue = self.parent.destinations_queue

    def setup(self):
        if not self.parent.sim_vehicle.bridge_connected:
            raise RuntimeError(f"The ego {self.parent.index} is not connected to"
                               " a bridge, can not set up the AD stack.")
        self.parent.sim_vehicle.set_initial_pose()

    def goto_next_destination(self):
        if not self.destinations_queue.empty():
            destination = self.destinations_queue.get()
            log.info(f"Setting new destination {print_vector(destination.position)}"
                     f" for the ego {self.parent.index}")
            self.parent.sim_vehicle.set_destination(destination)
