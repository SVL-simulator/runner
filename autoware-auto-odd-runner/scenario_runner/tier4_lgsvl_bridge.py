#
# Copyright (c) 2019-2021 LG Electronics, Inc.
#
# This software contains code licensed as described in LICENSE.
#

# autopep8: off
import logging
import os
import zmq
import sys
import lgsvl
import socket as web_socket
import math
import numpy as np
import threading

sys.path.append("proto")
# A workaround for using inside the docker container
sys.path.append("/app/proto")

import simulation_api_schema_pb2
# autopep8: on


FORMAT = '%(asctime)-15s [%(levelname)s][%(module)s] %(message)s'
logging.basicConfig(level=logging.INFO, format=FORMAT)
log = logging.getLogger(__name__)

TIER4_API_PORTS = [5555, 5556, 5557, 5558, 5559,
                   5560, 5561, 5562, 5563, 5564]

DEBUG_NONEGO_VEHICLES = True

NPC_CONFIGURATIONS = \
    ["Sedan", "SUV", "Jeep", "Hatchback"]

PEDESTRIAN_CONFIGURATIONS = \
    ["Bob", "EntrepreneurFemale", "Howard", "Johny",
     "Pamela", "Presley", "Robin", "Stephen", "Zoe"]

DEFAULT_UNITY_OBJECT_ROTATION = lgsvl.Vector(0, -90, 0)


def euler_degree_from_quaternion(x, y, z, w):
    """
    Convert a quaternion into euler angles (roll, pitch, yaw)
    roll is rotation around x in radians (counterclockwise)
    pitch is rotation around y in radians (counterclockwise)
    yaw is rotation around z in radians (counterclockwise)
    """
    def rad_to_degree(radians):
        return radians * 180 / math.pi

    t0 = +2.0 * (w * x + y * z)
    t1 = +1.0 - 2.0 * (x * x + y * y)
    roll_x = rad_to_degree(math.atan2(t0, t1))

    t2 = +2.0 * (w * y - z * x)
    t2 = +1.0 if t2 > +1.0 else t2
    t2 = -1.0 if t2 < -1.0 else t2
    pitch_y = rad_to_degree(math.asin(t2))

    t3 = +2.0 * (w * z + x * y)
    t4 = +1.0 - 2.0 * (y * y + z * z)
    yaw_z = rad_to_degree(math.atan2(t3, t4))

    return roll_x, pitch_y, yaw_z  # in degree


def is_socket_alive(host, port):
    short_timeout_seconds = 2
    sock = web_socket.socket(web_socket.AF_INET, web_socket.SOCK_STREAM)
    sock.settimeout(short_timeout_seconds)
    result = sock.connect_ex((host, port))
    sock.close()
    return result == 0


def empty_envar_error_msg(envar_name):
    return f"The '{envar_name}' environment variable is " \
        "either not set or empty, can not proceed."


def print_vector(vector=lgsvl.Vector(0, 0, 0)):
    return f"[{vector.x:.2f} {vector.y:.2f} {vector.z:.2f}]"


class Tier4LgSvlBridge():
    def __init__(self):
        self.is_api_initialized = False
        self.sim = None
        self.current_sim_time = 0
        self.initial_ros_time = 0
        self.current_ros_time = self.initial_ros_time
        self.ego = None  # Working with only 1 ego so far. To be refactored.
        # 'Agents' stores both NPCs and peds as there is no difference between them
        # in terms of the TierIV simulation scenario run
        self.agents = {}
        self.map_origin_northing = 0
        self.map_origin_easting = 0

    def soft_reset(self):
        # Does not reset the Simulator instance. Is intended to be called on
        # initialization request from the TierIV scenario runner
        self.is_api_initialized = False
        self.current_sim_time = 0
        self.initial_ros_time = 0
        self.current_ros_time = self.initial_ros_time
        self.ego = None
        self.agents.clear()

    def initialize_api_sockets(self):
        self.api_sockets = {}
        context = zmq.Context()
        self.poller = zmq.Poller()
        for port in TIER4_API_PORTS:
            api_socket = context.socket(zmq.REP)
            bind_address = f"tcp://*:{port}"
            api_socket.bind(bind_address)
            self.poller.register(api_socket)
            log.info(f"Registered listener for the port {port}")
            self.api_sockets[port] = api_socket

    def fill_handlers_lookup_table(self):
        self.handlers = {}
        self.handlers[5555] = self.handle_init_request
        self.handlers[5556] = self.handle_update_frame
        self.handlers[5557] = self.handle_update_sensor_frame
        self.handlers[5558] = self.handle_spawn_vehicle
        self.handlers[5559] = self.handle_spawn_pedestrian_entity
        self.handlers[5560] = self.handle_spawn_misc_object_entity
        self.handlers[5561] = self.handle_despawn_entity
        self.handlers[5562] = self.handle_update_entity_status
        self.handlers[5563] = self.handle_attach_lidar_sensor
        self.handlers[5564] = self.handle_attach_detection_sensor

    def safe_get_envar(self, envar_name):
        try:
            result = os.environ.get(envar_name)
            if result is None:
                raise RuntimeError(empty_envar_error_msg(envar_name))
        except Exception as e:
            self.terminate(str(e))
        return result

    def terminate(self, message=None):
        if message:
            log.error(message)
        self.safely_stop_simulation()
        sys.exit(1)

    def generate_initial_agent_state(self, bbox_center):
        agent_state = lgsvl.AgentState()
        transform = lgsvl.Transform()
        transform.position = lgsvl.Vector(bbox_center.x, bbox_center.z, bbox_center.y)
        transform.rotation = DEFAULT_UNITY_OBJECT_ROTATION
        agent_state.transform = transform
        return agent_state

    def to_unity_position(self, world_position):
        unity_position = lgsvl.Vector(x=-(world_position.y - self.map_origin_northing),
                                      y=world_position.z,
                                      z=world_position.x - self.map_origin_easting)
        return unity_position

    def to_unity_linear_velocity(self, vehicle_linear_velocity, unity_rotation):
        # Here we rely on a vehicle always having only its X axis velocity (forward-backward)
        unity_x_velocity = vehicle_linear_velocity.x \
            * math.sin(math.radians(unity_rotation.y))
        unity_z_velocity = vehicle_linear_velocity.x \
            * math.cos(math.radians(unity_rotation.y))
        return lgsvl.Vector(unity_x_velocity, 0, unity_z_velocity)

    def to_unity_angular_velocity(self, vehicle_angular_velocity):
        # only an angular velocity around unity Y axis is converted
        return lgsvl.Vector(0, vehicle_angular_velocity.z, 0)

    def to_unity_rotation(self, world_orientation_quaternion):
        map_rotation_x, map_rotation_y, map_rotation_z = \
            euler_degree_from_quaternion(
                world_orientation_quaternion.x,
                world_orientation_quaternion.y,
                world_orientation_quaternion.z,
                world_orientation_quaternion.w)
        unity_rotation = lgsvl.Vector(x=map_rotation_y,
                                      y=-map_rotation_z,
                                      z=-map_rotation_x)
        return unity_rotation

    def agent_state_from_world_coords(self,
                                      world_position,
                                      world_orientation_quaternion,
                                      vehicle_linear_velocity,
                                      vehicle_angular_velocity):
        unity_rotation = self.to_unity_rotation(world_orientation_quaternion)
        transform = lgsvl.Transform()
        transform.position = self.to_unity_position(world_position)
        transform.rotation = unity_rotation

        linear = self.to_unity_linear_velocity(vehicle_linear_velocity,
                                               unity_rotation)

        angular = self.to_unity_angular_velocity(vehicle_angular_velocity)
        agent_state = lgsvl.AgentState(transform, linear, angular)
        return agent_state

    def compute_scene_origin_coordinates(self):
        # Here we rely on two facts:
        # 1. LG SVL does NOT work with huge maps which are >1 km in size
        # 2. TierIV scenario runner operates in in-square coordinates
        # Therefore, a TierIV "world" coordinate's meaningful part
        # is always <100 km, and as the Unity MapOrigin has its Northing and
        # Easting in the global UTM, we can discard everything except the
        # least 5 integer digits which would be exactly equal to the TierIV
        # "world" coordinates.
        mgrs_square_size_meters = 100 * 1000
        map_origin = lgsvl.Transform(position=lgsvl.Vector(0, 0, 0))
        gps = self.sim.map_to_gps(map_origin)
        self.map_origin_northing = gps.northing % mgrs_square_size_meters
        self.map_origin_easting = gps.easting % mgrs_square_size_meters

    def safely_stop_simulation(self):
        if self.sim:
            log.info("Stopping simulation")
            self.sim.stop()

    def setup_sim(self):
        if self.sim:
            self.sim.reset()
            return
        simulator_host = self.safe_get_envar("LGSVL__SIMULATOR_HOST")
        simulator_port = int(self.safe_get_envar("LGSVL__SIMULATOR_PORT"))
        log.info(f"Connecting to the LG SVL at {simulator_host}:{simulator_port} ...")
        if not is_socket_alive(simulator_host, simulator_port):
            log.info(f"No LGSVL instance listening to {simulator_host}:{simulator_port} has"
                     " been found, unable to start the TierIV bridge server. Make sure"
                     " you have an LGSVL Simulator instance running in 'API-Only' mode.")
            sys.exit(1)
        self.sim = lgsvl.Simulator(simulator_host, simulator_port)

    def load_scene(self):
        scene_name = self.safe_get_envar("LGSVL__MAP")
        log.info(f"Loading scene {scene_name}")
        if self.sim.current_scene == scene_name:
            log.info(f"The '{scene_name}' was already loaded, resetting it.")
            self.sim.reset()
        else:
            self.sim.load(scene_name)
        self.compute_scene_origin_coordinates()

    def handle_init_request(self, msg):
        # port 5555
        req = simulation_api_schema_pb2.InitializeRequest()
        req.ParseFromString(msg)
        response = simulation_api_schema_pb2.InitializeResponse()
        response.result.success = False
        self.soft_reset()
        try:
            self.setup_sim()
            self.load_scene()
            self.realtime_factor = req.realtime_factor
            self.step_time = req.step_time
            self.is_api_initialized = True
            response.result.success = True
            response.result.description = \
                f"succeed to initialize simulation, realtime factor {self.realtime_factor}"\
                f", step time {self.step_time} seconds."
        except Exception as e:
            response.result.description = str(e)

        resp_msg = response.SerializeToString()
        log.info(f"{response.result.description}")
        return resp_msg

    def handle_update_frame(self, msg):
        # port 5556
        request = simulation_api_schema_pb2.UpdateFrameRequest()
        request.ParseFromString(msg)
        response = simulation_api_schema_pb2.UpdateFrameResponse()
        response.result.success = False
        if not self.is_api_initialized:
            response.result.description = "simulator have not initialized yet."
        else:
            self.current_sim_time = request.current_time
            self.current_ros_time = request.current_ros_time.sec
            if self.initial_ros_time == 0:
                self.initial_ros_time = self.current_ros_time
            try:
                self.sim.run(self.step_time)
                response.result.success = True
                response.result.description = "succeed to update frame"
            except Exception as e:
                response.result.description = str(e)
        # log.info(f"UpdateFrameRequest.current_time : {request.current_time}"
        #         f", current_ros_time : {request.current_ros_time.sec}"
        #         f", elapsed ROS: {self.current_ros_time - self.initial_ros_time}")
        resp_msg = response.SerializeToString()
        return resp_msg

    def handle_update_sensor_frame(self, msg):
        # port 5557
        request = simulation_api_schema_pb2.UpdateSensorFrameRequest()
        request.ParseFromString(msg)
        # TODO: handle:
        # current_time, current_ros_time

        # TODO: As I get it, lidars/radars/other sensors must update and post to their
        # corresp. ROS topics at this step

        response = simulation_api_schema_pb2.UpdateSensorFrameResponse()
        response.result.success = False
        response.result.description = "update_sensor_frame not implemented"
        resp_msg = response.SerializeToString()
        # log.error(response.result.description)  # DEBUG
        return resp_msg

    def handle_spawn_vehicle(self, msg):
        # port 5558
        request = simulation_api_schema_pb2.SpawnVehicleEntityRequest()
        request.ParseFromString(msg)
        response = simulation_api_schema_pb2.SpawnVehicleEntityResponse()
        response.result.success = False
        response.result.description = ""

        if not self.sim:
            response.result.description = "LG SVL simulator is not running"
            resp_msg = response.SerializeToString()
            return resp_msg

        vehicle_name = request.parameters.name
        vehicle_type = request.parameters.vehicle_category
        bbox_center = request.parameters.bounding_box.center
        log.info(f"\nSpawnVehicleEntityRequest.is_ego : {request.is_ego}"
                 f"\nSpawnVehicleEntityRequest.parameters.name : {vehicle_name}"
                 f"\nSpawnVehicleEntityRequest.parameters.vehicle_category : {vehicle_type}"
                 f"\nSpawnVehicleEntityRequest.parameters.bounding_box.center : {print_vector(bbox_center)}")

        agent_state = self.generate_initial_agent_state(bbox_center)

        try:
            ego_configuration = self.safe_get_envar("LGSVL__VEHICLE_0")
            if request.is_ego or (DEBUG_NONEGO_VEHICLES and vehicle_name == "ego"):
                self.ego = self.sim.add_agent(
                    ego_configuration,
                    lgsvl.AgentType.EGO,
                    agent_state)
            else:
                # As the TierIV editor does not allow setting any assetID as the NPC name,
                # the bridge just requests some default NPC creation. Any next NPC is
                # different to provide a better demo experience. TBD.
                npc_configuration = NPC_CONFIGURATIONS[
                    len(self.agents) % len(NPC_CONFIGURATIONS)
                ]
                self.agents[vehicle_name] = self.sim.add_agent(
                    npc_configuration,
                    lgsvl.AgentType.NPC,
                    agent_state)
            response.result.success = True
        except Exception as e:
            response.result.description = str(e)

        resp_msg = response.SerializeToString()
        return resp_msg

    def handle_spawn_pedestrian_entity(self, msg):
        # port 5559
        request = simulation_api_schema_pb2.SpawnPedestrianEntityRequest()
        request.ParseFromString(msg)
        response = simulation_api_schema_pb2.SpawnPedestrianEntityResponse()
        response.result.success = False
        response.result.description = ""

        if not self.sim:
            response.result.description = "LG SVL simulator is not running"
            resp_msg = response.SerializeToString()
            return resp_msg

        ped_name = request.parameters.name
        ped_type = request.parameters.pedestrian_category
        bbox_center = request.parameters.bounding_box.center
        log.info(f"\nSpawnPedestrianEntityRequest.parameters.name : {ped_name}"
                 f"\nSpawnPedestrianEntityRequest.parameters.pedestrian_category : {ped_type}"
                 f"\nSpawnPedestrianEntityRequest.parameters.bounding_box.center : {print_vector(bbox_center)}")

        agent_state = self.generate_initial_agent_state(bbox_center)

        try:
            # As the TierIV editor does not allow setting any assetID as the pedestrian name,
            # the bridge just requests some default pedestrian creation. Any next ped is
            # different to provide a better demo experience. TBD.
            ped_configuration = PEDESTRIAN_CONFIGURATIONS[
                len(self.agents) % len(PEDESTRIAN_CONFIGURATIONS)
            ]
            self.agents[ped_name] = self.sim.add_agent(
                ped_configuration,
                lgsvl.AgentType.PEDESTRIAN,
                agent_state)
            response.result.success = True
        except Exception as e:
            response.result.description = str(e)

        resp_msg = response.SerializeToString()
        return resp_msg

    def handle_spawn_misc_object_entity(self, msg):
        # port 5560
        request = simulation_api_schema_pb2.SpawnMiscObjectEntityRequest()
        request.ParseFromString(msg)
        # TODO: handle:
        # parameters: name, misc_object_category, bounding_box
        response = simulation_api_schema_pb2.SpawnMiscObjectEntityResponse()
        response.result.success = False
        response.result.description = "spawn_misc_object_entity not implemented"
        resp_msg = response.SerializeToString()
        log.error(response.result.description)  # DEBUG
        return resp_msg

    def handle_despawn_entity(self, msg):
        # port 5561
        request = simulation_api_schema_pb2.DespawnEntityRequest()
        request.ParseFromString(msg)
        agent_name = request.name
        response = simulation_api_schema_pb2.DespawnEntityResponse()
        response.result.success = False
        try:
            if agent_name == "ego":
                # This is a hack to handle only a car named "ego" BUT not of an
                # 'ego' type, as the scenario runner does not works with genuine Ego
                # vehicles without the AutowareAuto AD stack running.
                self.sim.remove_agent(self.ego)
                self.ego = None
            else:
                self.sim.remove_agent(self.agents[agent_name])
                self.agents.pop(agent_name)
            response.result.success = True
            response.result.description = f"successfully despawned agent {agent_name}"
        except Exception as e:
            response.result.description = str(e)
        resp_msg = response.SerializeToString()
        log.error(response.result.description)  # DEBUG
        return resp_msg

    def handle_update_entity_status(self, msg):
        # port 5562
        request = simulation_api_schema_pb2.UpdateEntityStatusRequest()
        request.ParseFromString(msg)
        response = simulation_api_schema_pb2.UpdateEntityStatusResponse()
        response.result.success = False

        if not self.ego or not self.sim:
            # TODO: handle the case with multiple egos and NPCs
            resp_msg = response.SerializeToString()
            return resp_msg
        try:
            for agent_status in request.status:
                agent_name = agent_status.name
                new_agent_state = self.agent_state_from_world_coords(
                    agent_status.pose.position,
                    agent_status.pose.orientation,
                    agent_status.action_status.twist.linear,
                    agent_status.action_status.twist.angular
                )

                # log.info(f"New {agent_name} position: {print_vector(new_agent_state.position)}, "
                #         f"rotation: {print_vector(new_agent_state.rotation)}")
                if agent_name == "ego":
                    # This is a hack to handle only a car named "ego" BUT not of an
                    # 'ego' type, as the scenario runner does not works with genuine Ego
                    # vehicles without the AutowareAuto AD stack running.
                    self.ego.state = new_agent_state
                else:
                    self.agents[agent_name].state = new_agent_state
            response.result.success = True
        except Exception as e:
            response.result.description = str(e)

        resp_msg = response.SerializeToString()
        return resp_msg

    def handle_attach_lidar_sensor(self, msg):
        # port 5563
        request = simulation_api_schema_pb2.AttachLidarSensorRequest()
        request.ParseFromString(msg)
        # TODO: handle:
        # configuration: entity, horizontal_resolution, [vertical_angles], scan_duration, topic_name
        response = simulation_api_schema_pb2.AttachLidarSensorResponse()
        response.result.success = False
        response.result.description = "attach_lidar_sensor not implemented"
        resp_msg = response.SerializeToString()
        log.error(response.result.description)  # DEBUG
        return resp_msg

    def handle_attach_detection_sensor(self, msg):
        # port 5564
        request = simulation_api_schema_pb2.AttachDetectionSensorRequest()
        request.ParseFromString(msg)
        # TODO: handle:
        # configuration: entity, update_duration, topic_name
        response = simulation_api_schema_pb2.AttachDetectionSensorResponse()
        response.result.success = False
        response.result.description = "attach_detection_sensor not implemented"
        resp_msg = response.SerializeToString()
        log.error(response.result.description)  # DEBUG
        return resp_msg

    def start(self):
        self.initialize_api_sockets()
        self.fill_handlers_lookup_table()
        self.setup_sim()
        self.load_scene()

    def poll(self):
        while True:
            try:
                new_data_sockets = dict(self.poller.poll())
            except KeyboardInterrupt:
                break

            for port in TIER4_API_PORTS:
                api_socket = self.api_sockets[port]
                if api_socket in new_data_sockets:
                    msg = api_socket.recv()
                    result = self.handlers[port](msg)
                    api_socket.send(result)


class Tier4LgSvlBridgeServerThread(threading.Thread):
    def __init__(self, startup_completed):
        threading.Thread.__init__(self, args=(startup_completed,))
        self.startup_completed = startup_completed
        self.startup_completed.clear()

    def run(self):
        server = Tier4LgSvlBridge()
        log.info("Server startup ...")
        server.start()
        log.info("Server startup completed")
        self.startup_completed.set()
        log.info("Start polling ...")
        server.poll()


if __name__ == "__main__":
    bridge_started_up = threading.Event()
    thread = Tier4LgSvlBridgeServerThread(bridge_started_up)
    thread.run()
