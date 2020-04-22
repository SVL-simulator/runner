import os

import scenic

from scenic.simulators.lgsvl.simulator import LGSVLSimulator

import verifai
import verifai.error_table
from verifai.samplers import scenic_sampler

import logging
log = logging.getLogger(__name__)


def run_scenic(scenario_filename, num_iterations, duration, lgsvl_map, output_folder, save_sampler_data):
    scenario_basename = os.path.basename(scenario_filename)[:-3]

    log.info("Loading scenario from  %s", scenario_filename)
    # Load Scenic scenario
    scenario = scenic.scenarioFromFile(scenario_filename)

    ignoredProps = (scenic_sampler.defaultIgnoredProperties | {'lgsvlObject', 'dreamview', 'elevation'})

    space = scenic_sampler.spaceForScenario(scenario, ignoredProps)
    table = verifai.error_table.error_table(space)

    tempName = f'.temp-{scenario_basename}.csv'
    tableName = f'all-runs-{scenario_basename}.csv'

    if output_folder:
        tempName = os.path.join(output_folder, tempName)
        tableName = os.path.join(output_folder, tableName)

    # Create the Simulator
    log.info("Connecting to simulator")
    simulator = LGSVLSimulator(lgsvl_map)

    log.debug("Run %d scenario iterations, %s seconds per iteration", num_iterations, duration)

    # Sample configurations from the scenario and run simulations
    for itr in range(1, num_iterations + 1):
        log.debug("Iteration #%d", itr)
        scene, _ = scenario.generate()

        # Compute number of time steps to run simulations
        timestep = scene.params['time_step']
        maxSteps = duration / timestep

        log.info("Create simulation")
        simulation = simulator.createSimulation(scene)
        log.info("Run simulation")
        simulation.run(maxSteps)
        log.info('Simulation is done')

        if save_sampler_data:
            log.info("Saving sampler data %s", tableName)

            # Update error table
            point = scenic_sampler.pointForScene(space, scene)
            # rho = -1 if simulation.collisionOccurred else 1
            rho = simulation.collisionOccurred
            table.update_error_table(point, rho)
            table.table.to_csv(tempName)
            os.rename(tempName, tableName)    # atomic


def check_scenic(filename):
    scenic.scenarioFromFile(filename)
