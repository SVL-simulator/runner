#
# Copyright (c) 2020-2021 LG Electronics, Inc.
#
# This software contains code licensed as described in LICENSE.
#

from scenario_runner.adstack_wrapper_interface import BaseADStackWrapper
from scenario_runner.runner_utils import print_vector
import logging
import os
import lgsvl

FORMAT = '%(asctime)-15s [%(levelname)s][%(module)s] %(message)s'

logging.basicConfig(level=logging.INFO, format=FORMAT)
log = logging.getLogger(__name__)


class Wrapper(BaseADStackWrapper):
    def __init__(self, parent, bridge_host, bridge_port):
        assert parent, "Can not create an AD stack wrapper without a valid parent EgoWrapper!"
        self.parent = parent
        self.bridge_host = bridge_host
        self.bridge_port = bridge_port
        if not "hd_map_name" in self.parent.metadata:
            raise RuntimeError(f"The ego {self.parent.index} Apollo autopilot requires a valid HD map name")
        self.hd_map_name = self.parent.metadata["hd_map_name"]
        self.destinations_queue = self.parent.destinations_queue

        # The Apollo stack does not support multiple waypoints for now
        # so only the last one (final destination) is used
        while self.destinations_queue.qsize() > 1:
            self.destinations_queue.get()

        self.dv = None
        self.default_modules = [
            'Localization',
            'Perception',
            'Transform',
            'Routing',
            'Prediction',
            'Planning',
            'Traffic Light',
            'Control',
            'Recorder'
        ]
        self.modules = self.default_modules

    def setup(self):
        """
        Performs all the necessary initial calls to set up the Apollo AD stack.
        Does NOT set the destination as it would cause an immediate start of
        the driving, which confclicts with the scene startup in simulation.
        """
        if not self.parent.sim_vehicle.bridge_connected:
            raise RuntimeError(f"The ego {self.parent.index} is not connected to"
                               " a bridge, can not set up the AD stack.")

        agent = self.parent.metadata["agent"]
        i = self.parent.index

        if agent.get("sensorsConfigurationId") in {
            lgsvl.wise.DefaultAssets.ego_lincoln2017mkz_apollo5_modular,
            lgsvl.wise.DefaultAssets.ego_lincoln2017mkz_apollo6_modular,
        }:
            default_modules = [
                'Localization',
                'Transform',
                'Planning',
                'Prediction',
                'Routing',
                'Control'
            ]

        try:
            modules = os.environ.get(f"LGSVL__AUTOPILOT_{i}_VEHICLE_MODULES").split(",")
            if len(modules) == 0:
                modules = default_modules
        except Exception:
            modules = default_modules
        self.modules = modules
        log.info(f"Apollo AD stack loading with modules: {modules}")
        self.dv = lgsvl.dreamview.Connection(self.parent.metadata["simulator"],
                                             self.parent.sim_vehicle,
                                             self.bridge_host)

        self.dv.set_hd_map(self.hd_map_name)
        self.dv.set_vehicle(os.environ.get(f"LGSVL__AUTOPILOT_{i}_VEHICLE_CONFIG", agent["variant"]))

        if self.destinations_queue.empty():
            log.info(f"No destination set for EGO {self.parent.index}")

        self.dv.startup_apollo(self.modules)

    def goto_next_destination(self):
        """
        Note: for now there is no signal from Apollo stack about the ego
        car has reached its destination, so this method will effectively be
        called only once for setting the final destination.
        """
        if not self.dv:
            raise RuntimeError(f"No DreamView connection available for ego {self.parent.index}")
        if self.destinations_queue.empty():
            return
        destination = self.destinations_queue.get().position
        log.info(f"Setting new destination {print_vector(destination)}"
                 f" for the ego {self.parent.index}")
        self.dv.set_destination(destination.x, destination.z)
