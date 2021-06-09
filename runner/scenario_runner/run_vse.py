#!/usr/bin/env python3
#
# Copyright (c) 2020-2021 LG Electronics, Inc.
#
# This software contains code licensed as described in LICENSE.
#

import json
import logging
import os
import sys
import lgsvl

FORMAT = '%(asctime)-15s [%(levelname)s][%(module)s] %(message)s'

logging.basicConfig(level=logging.INFO, format=FORMAT)
log = logging.getLogger(__name__)


class VSERunner:
    def __init__(self, json_file):
        with open(json_file) as f:
            self.VSE_dict = json.load(f)

        self.sim = None
        self.ego_agents = []
        self.npc_agents = []
        self.pedestrian_agents = []

    def reset(self):
        log.debug("Reset VSE runner")
        self.ego_agents.clear()
        self.npc_agents.clear()
        self.pedestrian_agents.clear()

    def setup_sim(self, default_host="127.0.0.1", default_port=8181):
        if not self.sim:
            simulator_host = os.getenv('LGSVL__SIMULATOR_HOST', default_host)
            simulator_port = int(os.getenv('LGSVL__SIMULATOR_PORT', default_port))
            log.debug("simulator_host is {}, simulator_port is {}".format(simulator_host, simulator_port))
            self.sim = lgsvl.Simulator(simulator_host, simulator_port)

    def connect_bridge(self, ego_agent, ego_index=0, default_host="127.0.0.1", default_port=9090):
        autopilot_host_env = "LGSVL__AUTOPILOT_{}_HOST".format(ego_index)
        autopilot_port_env = "LGSVL__AUTOPILOT_{}_PORT".format(ego_index)
        if  autopilot_host_env not in os.environ:
            raise RuntimeWarning("Environment variable {} is absent or empty.".format(autopilot_host_env))

        bridge_host = os.environ.get(autopilot_host_env, default_host)
        bridge_port = int(os.environ.get(autopilot_port_env, default_port))
        ego_agent.connect_bridge(bridge_host, bridge_port)

        return bridge_host, bridge_port

    def load_scene(self):
        if "map" not in self.VSE_dict.keys():
            log.error("No map specified in the scenario.")
            sys.exit(1)

        scene = self.VSE_dict["map"]["name"]
        log.info("Loading {} map.".format(scene))
        if self.sim.current_scene == scene:
            self.sim.reset()
        else:
            self.sim.load(scene)

    def load_agents(self):
        if "agents" not in self.VSE_dict.keys():
            log.warning("No agents specified in the scenario")
            return

        agents_data = self.VSE_dict["agents"]
        for agent_data in agents_data:
            log.debug("Adding agent {}, type: {}".format(agent_data["variant"], agent_data["type"]))
            agent_type_id = agent_data["type"]
            if agent_type_id == lgsvl.AgentType.EGO.value:
                self.ego_agents.append(agent_data)

            elif agent_type_id == lgsvl.AgentType.NPC.value:
                self.npc_agents.append(agent_data)

            elif agent_type_id == lgsvl.AgentType.PEDESTRIAN.value:
                self.pedestrian_agents.append(agent_data)

            else:
                log.warning("Unsupported agent type {}. Skipping agent.".format(agent_data["type"]))

        log.info("Loaded {} ego agents".format(len(self.ego_agents)))
        log.info("Loaded {} NPC agents".format(len(self.npc_agents)))
        log.info("Loaded {} pedestrian agents".format(len(self.pedestrian_agents)))

    def add_controllables(self):
        if "controllables" not in self.VSE_dict.keys():
            log.debug("No controllables specified in the scenarios")
            return

        controllables_data = self.VSE_dict["controllables"]
        for controllable_data in controllables_data:	
            #Name checking for backwards compability
            spawned = "name" in controllable_data or ("spawned" in controllables_data and controllable_data["spawned"])
            if spawned:
                log.debug("Adding controllable {}".format(controllable_data["name"]))
                controllable_state = lgsvl.ObjectState()
                controllable_state.transform = self.read_transform(controllable_data["transform"])
                try:
                    controllable = self.sim.controllable_add(controllable_data["name"], controllable_state)
                    policy = controllable_data["policy"]
                    if len(policy) > 0:
                        controllable.control(policy)
                except Exception as e:
                    msg = "Failed to add controllable {}, please make sure you have the correct simulator".format(controllable_data["name"])
                    log.error(msg)
                    log.error("Original exception: " + str(e))
            else:
                uid = controllable_data["uid"]
                log.debug("Setting policy for controllable {}".format(uid))
                controllable = self.sim.get_controllable_by_uid(uid)
                policy = controllable_data["policy"]
                if len(policy) > 0:
                    controllable.control(policy)
                

    def add_ego(self):
        for i, agent in enumerate(self.ego_agents):
            if "id" in agent:
                agent_name = agent["id"]
            else:
                agent_name = agent["variant"]
            agent_state = lgsvl.AgentState()
            agent_state.transform = self.read_transform(agent["transform"])
            if "destinationPoint" in agent:
                agent_destination = lgsvl.Vector(
                    agent["destinationPoint"]["position"]["x"],
                    agent["destinationPoint"]["position"]["y"],
                    agent["destinationPoint"]["position"]["z"]
                )
                #
                # Set distination rotation once it is supported by DreamView
                #
                agent_destination_rotation = lgsvl.Vector(
                    agent["destinationPoint"]["rotation"]["x"],
                    agent["destinationPoint"]["rotation"]["y"],
                    agent["destinationPoint"]["rotation"]["z"],
                )

            try:
                if "sensorsConfigurationId" in agent:
                    ego = self.sim.add_agent(agent["sensorsConfigurationId"], lgsvl.AgentType.EGO, agent_state)
                else:
                    ego = self.sim.add_agent(agent_name, lgsvl.AgentType.EGO, agent_state)
            except Exception as e:
                msg = "Failed to add agent {}, please make sure you have the correct simulator".format(agent_name)
                log.error(msg)
                log.error("Original exception: " + str(e))
                sys.exit(1)

            try:
                bridge_host = self.connect_bridge(ego, i)[0]

                default_modules = [
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

                if agent.get("sensorsConfigurationId") in {
                        lgsvl.wise.DefaultAssets.ego_lincoln2017mkz_apollo5_modular,
                        lgsvl.wise.DefaultAssets.ego_lincoln2017mkz_apollo6_modular,
                    }:
                    default_modules = [
                        'Localization',
                        'Transform',
                        'Routing',
                        'Prediction',
                        'Planning',
                        'Control',
                        'Recorder'
                    ]

                try:
                    modules = os.environ.get("LGSVL__AUTOPILOT_{}_VEHICLE_MODULES".format(i)).split(",")
                    if len(modules) == 0:
                        modules = default_modules
                except Exception:
                    modules = default_modules
                dv = lgsvl.dreamview.Connection(self.sim, ego, bridge_host)
                dv.set_hd_map(os.environ.get("LGSVL__AUTOPILOT_HD_MAP", self.sim.current_scene))
                dv.set_vehicle(os.environ.get("LGSVL__AUTOPILOT_{}_VEHICLE_CONFIG".format(i), agent["variant"]))
                if "destinationPoint" in agent:
                    dv.setup_apollo(agent_destination.x, agent_destination.z, modules)
                else:
                    log.info("No destination set for EGO {}".format(agent_name))
                    for mod in modules:
                        dv.enable_module(mod)
            except RuntimeWarning as e:
                msg = "Skipping bridge connection for vehicle: {}".format(agent["id"])
                log.warning("Original exception: " + str(e))
                log.warning(msg)
            except Exception as e:
                msg = "Something went wrong with bridge / dreamview connection."
                log.error("Original exception: " + str(e))
                log.error(msg)

    def add_npc(self):
        for agent in self.npc_agents:
            if "id" in agent:
                agent_name = agent["id"]
            else:
                agent_name = agent["variant"]
            agent_state = lgsvl.AgentState()
            agent_state.transform = self.read_transform(agent["transform"])
            agent_color = lgsvl.Vector(agent["color"]["r"], agent["color"]["g"], agent["color"]["b"]) if "color" in agent else None

            try:
                npc = self.sim.add_agent(agent_name, lgsvl.AgentType.NPC, agent_state, agent_color)
            except Exception as e:
                msg = "Failed to add agent {}, please make sure you have the correct simulator".format(agent_name)
                log.error(msg)
                log.error("Original exception: " + str(e))
                sys.exit(1)

            if agent["behaviour"]["name"] == "NPCWaypointBehaviour":
                waypoints = self.read_waypoints(agent["waypoints"])
                if waypoints:
                    npc.follow(waypoints)
            elif agent["behaviour"]["name"] == "NPCLaneFollowBehaviour":
                npc.follow_closest_lane(
                    True,
                    agent["behaviour"]["parameters"]["maxSpeed"],
                    agent["behaviour"]["parameters"]["isLaneChange"]
                )

    def add_pedestrian(self):
        for agent in self.pedestrian_agents:
            if "id" in agent:
                agent_name = agent["id"]
            else:
                agent_name = agent["variant"]
            agent_state = lgsvl.AgentState()
            agent_state.transform = self.read_transform(agent["transform"])

            try:
                pedestrian = self.sim.add_agent(agent_name, lgsvl.AgentType.PEDESTRIAN, agent_state)
            except Exception as e:
                msg = "Failed to add agent {}, please make sure you have the correct simulator".format(agent_name)
                log.error(msg)
                log.error("Original exception: " + str(e))
                sys.exit(1)

            waypoints = self.read_waypoints(agent["waypoints"])
            if waypoints:
                pedestrian.follow(waypoints)

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
            angle = lgsvl.Vector.from_json(waypoint_data["angle"])
            if "wait_time" in waypoint_data:
                wait_time = waypoint_data["wait_time"]
            else:
                wait_time = waypoint_data["waitTime"]
            trigger = self.read_trigger(waypoint_data)
            waypoint = lgsvl.DriveWaypoint(position, speed, angle=angle, idle=wait_time, trigger=trigger)
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
            effector = lgsvl.TriggerEffector(effector_data["typeName"], effector_data["parameters"])
            effectors.append(effector)
        trigger = lgsvl.WaypointTrigger(effectors)

        return trigger

    def run(self, duration=0.0, force_duration=False, loop=False):
        log.debug("Duration is set to {}.".format(duration))
        self.setup_sim()

        while True:
            self.load_scene()
            self.load_agents()
            self.add_ego()  # Must go first since dreamview api may call sim.run()
            self.add_npc()
            self.add_pedestrian()
            self.add_controllables()

            def _on_agents_traversed_waypoints():
                log.info("All agents traversed their waypoints.")

                if not force_duration:
                    log.info("Stopping simulation")
                    self.sim.stop()

            self.sim.agents_traversed_waypoints(_on_agents_traversed_waypoints)

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
