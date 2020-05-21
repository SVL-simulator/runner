import subprocess

import logging
log = logging.getLogger(__name__)


def run_python(filename, extra_args):
    log.debug("Run python %s %s", filename, extra_args)

    cmd = ['python', filename]
    cmd += extra_args

    log.debug("Run CMD %s", cmd)

    return subprocess.call(cmd)
