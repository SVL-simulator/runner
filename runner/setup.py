#!/usr/bin/env python3

from setuptools import setup

setup(
    name="scenario_runner",
    description="Scenario Runner for LGSVL Simulator",
    author="LGSVL",
    author_email="contact@lgsvlsimulator.com",
    python_requires=">=3.6.0",
    packages=["scenario_runner"],
    entry_points={
        'console_scripts': [
            'run_scenario = scenario_runner:main',
            'run = scenario_runner:main',
        ],
    },
    install_requires=["lgsvl", ],
    extras_require = {
        "scenic":  ["scenic", "verifai"],
    },

    license="Other",
    classifiers=[
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ],
)
