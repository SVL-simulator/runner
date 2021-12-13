#
# Copyright (c) 2020-2021 LG Electronics, Inc.
#
# This software contains code licensed as described in LICENSE.
#

class BaseADStackWrapper():
    """
        This is the base class for AD Stack wrappers,
        declaring the unified interface of an interaction
        between a Runner script and an AD stack.
    """

    def __init__(self, parent, bridge_host, bridge_port):
        raise NotImplementedError

    """
    As there is a pause necessary for establishing a web connection
    with an autopilot bridge and a pause for initializing of the localization
    after setting the initial ego pose estimate, the methods here are
    intended to be called in the defined order with running simultaion
    for some time between them.
    """

    def request_bridge_connection(self):
        """
        The first method to call, it requests establishing a web socket
        connection with the bridge.
        """
        self.parent.sim_vehicle.connect_bridge(self.bridge_host, self.bridge_port)

    def setup(self):
        """
        The second call, this method
        a) checks if the bridge is connected
        b) if so, it sets up everything necessary in the AD stack, like an
            HD map name, vehicle configuration, AD stack modules enabled
        """
        raise NotImplementedError

    def goto_next_destination(self):
        """
        The third call, this method sets the destination point.
        If there are more than 1 destination (e.g. several waypoints)
        this method is called whenever the previous destination is reached
        and sets the next one, if it is in a waypoint queue.
        """
        raise NotImplementedError
