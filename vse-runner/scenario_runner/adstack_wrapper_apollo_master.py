#
# Copyright (c) 2020-2021 LG Electronics, Inc.
#
# This software contains code licensed as described in LICENSE.
#

from scenario_runner.adstack_wrapper_apollo_6_0 import Wrapper as Apollo6Wrapper


class Wrapper(Apollo6Wrapper):
    """
    As the Apollo 6.0 and 'Apollo master' now behaves exactly the same
    in terms of DreamView API usage, there is a single wrapper
    for both of them. This class exists only for the AD stack 
    naming convenience.
    """
    pass
