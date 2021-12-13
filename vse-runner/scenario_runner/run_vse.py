#!/usr/bin/env python3
#
# Copyright (c) 2020-2021 LG Electronics, Inc.
#
# This software contains code licensed as described in LICENSE.
#

import importlib
from scenario_runner.runner_utils import print_vector, empty_envar_error_msg, is_socket_alive
from time import sleep
from queue import Queue
import lgsvl
import json
import logging
import os
import re
import sys


FORMAT = '%(asctime)-15s [%(levelname)s][%(module)s] %(message)s'
DEFAULT_WAYPOINT_SPEED_MS = 6

logging.basicConfig(level=logging.INFO, format=FORMAT)
log = logging.getLogger(__name__)


class EgoWrapper:
    """
    This is a convenient container for storing both Agent and Instance
    of an Ego vehicle in runtime.
    """

    def __init__(self, index: int, metadata: dict, sim_vehicle: lgsvl.agent.EgoVehicle,
                 waypoints_list=[]):
        """
        metadata - a dict describing an agent meta data and the HD map name
        sim_vehicle - a reference to the Simulator instance of a vehicle
            its connect_bridge(), get_bridge_type(), bridge_connected are used
        waypoints_list - a list of Transforms that are set as destinations
        """
        assert isinstance(index, int), "index must be int"
        assert index >= 0, "index must be >= 0"
        assert isinstance(metadata, dict), "metadata must be dict"
        assert "agent" in metadata, "metadata must contain an 'agent' record"
        assert "hd_map_name" in metadata, "metadata must contain an 'hd_map_name' record"
        assert isinstance(sim_vehicle, lgsvl.agent.EgoVehicle), "sim_vehicle must be lgsvl.agent.EgoVehicle"
        self.metadata = metadata
        self.sim_vehicle = sim_vehicle
        self.index = index
        self.name = self.sim_vehicle.name

        """
        The 'has_bridge' flag is intended to be always True except
        for Egos with KeyboardControl sensor configuration, mostly
        in some debug scenarios.
        """
        self.has_bridge = False

        adstack_name_envar = (f"LGSVL__AUTOPILOT_{self.index}_NAME")
        adstack_name = os.getenv(adstack_name_envar)
        if not adstack_name:
            log.info(f"Ego vehicle {index} has no AD stack specified, no bridge will be used for it.")
            self.has_bridge = False
            self.waypoints = waypoints_list
            return

        bridge_host_env = f"LGSVL__AUTOPILOT_{index}_HOST"
        bridge_host = os.environ.get(bridge_host_env)
        if not bridge_host:
            raise RuntimeError(empty_envar_error_msg(bridge_host_env))

        bridge_port_env = f"LGSVL__AUTOPILOT_{index}_PORT"
        bridge_port_str = os.environ.get(bridge_port_env)
        if not bridge_port_str:
            raise RuntimeError(empty_envar_error_msg(bridge_port_env))
        try:
            bridge_port = int(bridge_port_str)
        except:
            raise RuntimeError(f"The {bridge_port_env} has invalid value "
                               f"'{bridge_port_str}'', an integer expected.")

        if not is_socket_alive(bridge_host, bridge_port):
            raise RuntimeError("Impossible to connect to an AD stack bridge at "
                               f"{bridge_host}:{bridge_port}.")

        self.has_bridge = True

        self.destinations_queue = Queue()
        for w in waypoints_list:
            self.destinations_queue.put(w)

        # 'Apollo master' --> apollo_master
        # 'Apollo 5.0' --> apollo_5_0
        # 'apollo 5 0' --> apollo_5_0
        # 'Nav2' --> nav2
        adstack_filename = adstack_name.lower().replace(" ", "_").replace(".", "_")

        adstack_module_name = f"scenario_runner.adstack_wrapper_{adstack_filename}"
        try:
            adstack_module = importlib.import_module(adstack_module_name)
        except Exception as e:
            raise RuntimeError(f"Failed to load a module '{adstack_module_name}' "
                               f"for AD stack '{adstack_name}', please verify "
                               "the corresponding module file exists.\n"
                               f"Original exception: {str(e)}")
        self.ad_stack = adstack_module.Wrapper(self, bridge_host, bridge_port)

    def request_bridge_connection(self):
        if self.has_bridge:
            self.ad_stack.request_bridge_connection()

    def set_initial_params(self):
        if self.has_bridge:
            self.ad_stack.setup()

    def goto_next_destination(self):
        if self.has_bridge:
            self.ad_stack.goto_next_destination()


class VSERunner:
    def __init__(self, json_file):
        # Persistent internal state
        with open(json_file) as f:
            self.VSE_dict = json.load(f)
        self.sim = None
        self.force_duration = False
        self.hd_map_name = None
        self.bridge_connection_pause_sec = 3
        self.ego_init_pause_sec = 5

        # Resettable internal state
        self.ego_agents = []
        self.egos = []
        self.npc_agents = []
        self.pedestrian_agents = []
        self.total_egos_running = 0
        self.are_npcs_running = False

    def reset(self):
        log.debug("Reset VSE runner")
        self.ego_agents.clear()
        self.egos.clear()
        self.npc_agents.clear()
        self.pedestrian_agents.clear()
        self.total_egos_running = 0
        self.are_npcs_running = False

    def _find_ego_by_name(self, ego_name):
        for i, candidate in enumerate(self.egos):
            if candidate.name == ego_name:
                ego_wrapper = candidate
                ego_index = i
        if not ego_wrapper:
            log.error(f"The ego {ego_name} destination arrival was not"
                      " handled, as the VSE Runner does not know about it.")
        return ego_wrapper, ego_index

    def _on_ego_waypoint_reached(self, sender, waypoint_id):
        ego_wrapper, ego_index = self._find_ego_by_name(sender.name)
        # TODO: the below would work for the Linear waypoints,
        # but when a Bezier waypoint trajectory is used, the number
        # of waypoints is unknown at the start of the scenario (and
        # way greater than the number of the "key" waypoints) so
        # the simulation is stopped too early (after reaching the Nth
        # waypoint, where N is the number of the initial "key" wpts)
        if waypoint_id == len(ego_wrapper.waypoints) - 1:
            self.total_egos_running -= 1
        log.info(f"Ego {ego_index} reached waypoint {waypoint_id}"
                 f" total wpts for it {len(ego_wrapper.waypoints)}"
                 f" total egos running {self.total_egos_running}")
        self._stop_if_completed()

    def _on_ego_destination_reached(self, sender):
        ego_wrapper, ego_index = self._find_ego_by_name(sender.name)

        if not ego_wrapper.destinations_queue.empty():
            ego_wrapper.ad_stack.goto_next_destination()
            return

        log.info(f"Ego {ego_index} ({sender.name}) "
                 "has reached its final destination")
        self.total_egos_running -= 1
        if self.total_egos_running <= 0:
            log.info("All EGOs reached their destinations")
        else:
            log.info(f"Total {self.total_egos_running} ego(s) still have not reached "
                     "their destinations")
        self._stop_if_completed()

    def _stop_if_completed(self):
        if not self.force_duration \
           and self.total_egos_running <= 0 \
           and not self.are_npcs_running:
            self._safely_stop_simulation()

    def _on_agents_traversed_waypoints(self):
        log.info("All agents traversed their waypoints.")
        self.are_npcs_running = False
        self._stop_if_completed()

    def _agent_name(self, agent):
        if "id" in agent:
            return agent["id"]
        else:
            return agent["variant"]

    def _terminate_on_wrong_agent(self, agent_description, original_exception):
        log.error(f"Failed to add {agent_description}, "
                  "please make sure you have the correct simulator. ")
        self._terminate(str(original_exception))

    def _terminate(self, message=None):
        if message:
            log.error(message)
        self._safely_stop_simulation()
        sys.exit(1)

    def _safely_stop_simulation(self):
        if self.sim:
            log.info("Stopping simulation")
            self.sim.stop()

    def _safe_get_envar(self, envar_name):
        try:
            result = os.environ.get(envar_name)
            if result is None:
                raise RuntimeError(empty_envar_error_msg(envar_name))
        except Exception as e:
            self._terminate(str(e))
        return result

    def setup_sim(self, default_host="127.0.0.1", default_port=8181):
        if self.sim:
            return
        sim_host = os.getenv('LGSVL__SIMULATOR_HOST', default_host)
        sim_port = int(os.getenv('LGSVL__SIMULATOR_PORT', default_port))
        log.info(f"Connecting to the LG SVL at {sim_host}:{sim_port} ...")
        if not is_socket_alive(sim_host, sim_port):
            self._terminate(f"No LGSVL instance listening to {sim_host}:{sim_port} has"
                            " been found, unable to run the scenario.")
        self.sim = lgsvl.Simulator(sim_host, sim_port)

    def load_scene(self):
        if "map" not in self.VSE_dict.keys():
            log.error("No map specified in the scenario.")
            sys.exit(1)

        scene = self.VSE_dict["map"]["id"]
        log.info("Loading {} map.".format(scene))
        if self.sim.current_scene == scene:
            self.sim.reset()
        else:
            self.sim.load(scene)

        if "navData" in self.VSE_dict.keys():
            nav_origins = self.VSE_dict["navData"]["navOrigins"]
            for nav_origin in nav_origins:
                transform = lgsvl.Transform.from_json(nav_origin["transform"])
                origin_x = nav_origin["parameters"]["originX"]
                origin_y = nav_origin["parameters"]["originY"]
                rotation_param = nav_origin["parameters"]["rotation"]
                parameters = lgsvl.Vector(origin_x, origin_y, rotation_param)
                self.sim.set_nav_origin(transform, parameters)

        # TODO: what if there are a few different autopilots, using different HD maps
        # for the exactly the same location? Is thic case planned to be handled?
        hd_map_name_envar = "LGSVL__AUTOPILOT_HD_MAP"
        hd_map_name = os.environ.get(hd_map_name_envar)
        if not hd_map_name:
            hd_map_name = self.VSE_dict["map"]["name"]
            words = self.split_pascal_case(hd_map_name)
            hd_map_name = ' '.join(words)
            log.info(f"{hd_map_name_envar} environment variable is empty or not set. "
                     f"Using the map name '{hd_map_name}' from the scenario file as an"
                     " HD map name instead.")
        self.hd_map_name = hd_map_name

    def load_agents(self):
        if "agents" not in self.VSE_dict.keys():
            log.warning("No agents specified in the scenario")
            return

        agents_data = self.VSE_dict["agents"]
        for agent_data in agents_data:
            log.debug(f'Adding agent {agent_data["variant"]}, type: {agent_data["type"]}')
            agent_type_id = agent_data["type"]
            if agent_type_id == lgsvl.AgentType.EGO.value:
                self.ego_agents.append(agent_data)

            elif agent_type_id == lgsvl.AgentType.NPC.value:
                self.npc_agents.append(agent_data)

            elif agent_type_id == lgsvl.AgentType.PEDESTRIAN.value:
                self.pedestrian_agents.append(agent_data)

            else:
                log.warning(f"Unsupported agent type {agent_data['type']}. Skipping agent.")

        log.info(f"Loaded {len(self.ego_agents)} ego agents")
        log.info(f"Loaded {len(self.npc_agents)} NPC agents")
        log.info(f"Loaded {len(self.pedestrian_agents)} pedestrian agents")

    def add_controllables(self):
        if "controllables" not in self.VSE_dict.keys():
            log.debug("No controllables specified in the scenarios")
            return

        controllables_data = self.VSE_dict["controllables"]
        for record in controllables_data:
            # Name checking for backwards compability
            spawned = "name" in record or ("spawned" in record and record["spawned"])
            if spawned:
                controllable_name = record["name"]
                log.debug(f"Adding controllable {controllable_name}")
                controllable_state = lgsvl.ObjectState()
                controllable_state.transform = self.read_transform(record["transform"])
                try:
                    controllable = self.sim.controllable_add(controllable_name,
                                                             controllable_state,
                                                             uid=record["uid"])
                    policy = record["policy"]
                    if len(policy) > 0:
                        controllable.control(policy)
                except Exception as e:
                    self._terminate_on_wrong_agent(
                        f"controllable \"{controllable_name}\"", e)
            else:
                uid = record["uid"]
                log.debug("Setting policy for controllable {}".format(uid))
                controllable = self.sim.get_controllable_by_uid(uid)
                policy = record["policy"]
                if len(policy) > 0:
                    controllable.control(policy)

    def spawn_egos(self):
        for i, agent in enumerate(self.ego_agents):
            agent_name = self._agent_name(agent)
            agent_state = lgsvl.AgentState()
            agent_state.transform = self.read_transform(agent["transform"])
            agent_configuration = agent_name

            if "sensorsConfigurationId" in agent:
                agent_configuration = agent["sensorsConfigurationId"]

            try:
                sim_vehicle = self.sim.add_agent(
                    agent_configuration,
                    lgsvl.AgentType.EGO,
                    agent_state,
                    uid=agent["uid"])
            except Exception as e:
                self._terminate_on_wrong_agent(f"ego {i} ({agent_configuration})", e)

            log.info(f"Ego {i} (name {agent_name}, configuration {agent_configuration}, "
                     f"uid {sim_vehicle.uid}) has been spawned at point "
                     f"{print_vector(agent_state.transform.position)}")

            agent_metadata = {}
            agent_metadata["hd_map_name"] = self.hd_map_name
            agent_metadata["agent"] = agent
            agent_metadata["simulator"] = self.sim

            waypoints = []
            if "waypoints" in agent:
                waypoints = self.read_waypoints(agent["waypoints"])

            if "destinationPoint" in agent:
                destination_point_json = agent["destinationPoint"]
                if "playbackWaypointsPath" in destination_point_json:
                    if len(waypoints) > 0:
                        log.warning(f"Agent {agent_name} has both the 'waypoints' and a"
                                    " destination's 'playbackWaypointsPath', the playback path waypoints will"
                                    " override the given 'waypoins'!")
                    waypoints = self.read_waypoints(
                        destination_point_json["playbackWaypointsPath"])
                destination_raw = self.read_transform(destination_point_json)
                destination = lgsvl.DriveWaypoint(
                    position=destination_raw.position,
                    speed=waypoints[-1].speed if len(waypoints) > 0 else DEFAULT_WAYPOINT_SPEED_MS,
                    angle=destination_raw.rotation
                )
                waypoints.append(destination)
                log.info(f"Ego {i} final destination position: "
                         f"{print_vector(destination.position)}")

            try:
                wrapper = EgoWrapper(i, agent_metadata, sim_vehicle, waypoints)
                wrapper.request_bridge_connection()
            except Exception as e:
                self._terminate(str(e))

            self.egos.append(wrapper)

    def initialize_egos(self):
        try:
            for ego in self.egos:
                ego.set_initial_params()
        except Exception as e:
            self._terminate(str(e))

    def start_egos_navigation(self):
        try:
            for ego in self.egos:
                if ego.has_bridge:
                    ego.sim_vehicle.on_destination_reached(
                        self._on_ego_destination_reached)
                    ego.goto_next_destination()
                    self.total_egos_running += 1
                elif len(ego.waypoints) > 0:
                    ego.sim_vehicle.follow(ego.waypoints,
                                           ego.metadata["agent"]["waypointsLoop"],
                                           ego.metadata["agent"]["waypointsPathType"])
                    ego.sim_vehicle.on_waypoint_reached(
                        self._on_ego_waypoint_reached)
                    self.total_egos_running += 1
        except Exception as e:
            self._terminate(str(e))

    def add_npc(self):
        for agent in self.npc_agents:
            agent_name = self._agent_name(agent)
            log.info(f"Adding npc {agent_name}.")
            agent_state = lgsvl.AgentState()
            agent_state.transform = self.read_transform(agent["transform"])
            agent_color = (
                lgsvl.Vector(agent["color"]["r"],
                             agent["color"]["g"],
                             agent["color"]["b"])
                if "color" in agent
                else None
            )

            try:
                npc = self.sim.add_agent(agent_name,
                                         lgsvl.AgentType.NPC,
                                         agent_state, agent_color,
                                         uid=agent["uid"])
            except Exception as e:
                self._terminate_on_wrong_agent(f"npc \"{agent_name}\"", e)

            self.are_npcs_running = True

            if agent["behaviour"]["name"] == "NPCWaypointBehaviour":
                waypoints = self.read_waypoints(agent["waypoints"])
                if not waypoints:
                    continue
                loop = False
                if "waypointsLoop" in agent:
                    loop = agent["waypointsLoop"]
                if "waypointsPathType" in agent:
                    npc.follow(waypoints,
                               loop,
                               agent["waypointsPathType"])
                else:
                    npc.follow(waypoints, loop)
            elif agent["behaviour"]["name"] == "NPCLaneFollowBehaviour":
                npc.follow_closest_lane(
                    True,
                    agent["behaviour"]["parameters"]["maxSpeed"],
                    agent["behaviour"]["parameters"]["isLaneChange"]
                )

    def add_pedestrian(self):
        for agent in self.pedestrian_agents:
            agent_name = self._agent_name(agent)
            log.info(f"Adding pedestrian {agent_name}.")
            agent_state = lgsvl.AgentState()
            agent_state.transform = self.read_transform(agent["transform"])

            try:
                pedestrian = self.sim.add_agent(agent_name,
                                                lgsvl.AgentType.PEDESTRIAN,
                                                agent_state,
                                                uid=agent["uid"])

            except Exception as e:
                self._terminate_on_wrong_agent(f"pedestrian \"{agent_name}\"", e)

            self.are_npcs_running = True

            waypoints = self.read_waypoints(agent["waypoints"])

            if not waypoints:
                continue

            loop = False
            if "waypointsLoop" in agent:
                loop = agent["waypointsLoop"]
            if "waypointsPathType" in agent:
                pedestrian.follow(waypoints,
                                  loop,
                                  agent["waypointsPathType"])
            else:
                pedestrian.follow(waypoints, loop)

    def read_transform(self, transform_data):
        transform = lgsvl.Transform()
        transform.position = lgsvl.Vector.from_json(transform_data["position"])
        transform.rotation = lgsvl.Vector.from_json(transform_data["rotation"])
        return transform

    def read_waypoints(self, waypoints_data):
        waypoints = []
        for waypoint_data in waypoints_data:
            position = lgsvl.Vector.from_json(waypoint_data["position"])
            speed = waypoint_data["speed"]
            if "acceleration" in waypoint_data:
                acceleration = waypoint_data["acceleration"]
            else:
                acceleration = 0
            angle = lgsvl.Vector.from_json(waypoint_data["angle"])
            if "wait_time" in waypoint_data:
                wait_time = waypoint_data["wait_time"]
            elif "waitTime" in waypoint_data:
                wait_time = waypoint_data["waitTime"]
            else:
                wait_time = 0
            trigger = self.read_trigger(waypoint_data)
            waypoint = lgsvl.DriveWaypoint(
                position,
                speed,
                acceleration=acceleration,
                angle=angle,
                idle=wait_time,
                trigger=trigger,
            )
            waypoints.append(waypoint)

        return waypoints

    def read_trigger(self, waypoint_data):
        if "trigger" not in waypoint_data:
            return None
        effectors_data = waypoint_data["trigger"]["effectors"]
        if len(effectors_data) == 0:
            return None

        effectors = []
        for effector_data in effectors_data:
            effector = lgsvl.TriggerEffector(effector_data["typeName"],
                                             effector_data["parameters"])
            effectors.append(effector)
        trigger = lgsvl.WaypointTrigger(effectors)

        return trigger

    def split_pascal_case(self, s):
        matches = re.finditer('.+?(?:(?<=[a-z])(?=[A-Z\d])|(?<=[A-Z\d])(?=[A-Z][a-z])|$)', s)
        return [m.group(0) for m in matches]

    def run(self, duration=0.0, force_duration=False, loop=False):
        log.debug("Duration is set to {}.".format(duration))
        self.setup_sim()
        self.force_duration = force_duration

        while True:
            self.load_scene()
            self.load_agents()
            self.spawn_egos()
            log.info(f"Runnning simulation for {self.bridge_connection_pause_sec} "
                     "seconds to let all bridges to connect ...")
            self.sim.run(self.bridge_connection_pause_sec)
            self.initialize_egos()
            log.info(f"Runnning simulation for {self.ego_init_pause_sec} "
                     "seconds to let all AD stacks to init ...")
            self.sim.run(self.ego_init_pause_sec)
            self.start_egos_navigation()
            self.add_npc()
            self.add_pedestrian()
            self.add_controllables()

            self.sim.agents_traversed_waypoints(self._on_agents_traversed_waypoints)

            log.info("Starting scenario...")
            self.sim.run(duration)
            log.info("Scenario simulation ended.")

            if loop:
                self.reset()
            else:
                break


if __name__ == "__main__":
    if len(sys.argv) < 2:
        log.error("Input file is not specified, please provide the scenario JSON file.")
        sys.exit(1)

    json_file = sys.argv[1]
    vse_runner = VSERunner(json_file)
    vse_runner.run()
