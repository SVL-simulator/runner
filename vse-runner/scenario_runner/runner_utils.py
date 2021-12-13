#
# Copyright (c) 2020-2021 LG Electronics, Inc.
#
# This software contains code licensed as described in LICENSE.
#

import socket
from lgsvl import Vector


def is_socket_alive(host, port):
    short_timeout_seconds = 2
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(short_timeout_seconds)
    result = sock.connect_ex((host, port))
    sock.close()
    return result == 0


def empty_envar_error_msg(envar_name):
    return f"The '{envar_name}' environment variable is " \
        "either not set or empty, can not proceed."


def print_vector(vector=Vector(0, 0, 0)):
    return f"[{vector.x:.2f} {vector.y:.2f} {vector.z:.2f}]"
