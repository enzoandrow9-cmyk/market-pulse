from __future__ import annotations

from quantlab.simulation.event_simulator import EventDrivenSimulator
from quantlab.simulation.vectorized_simulator import VectorizedSimulator


class SimulationEngine:
    def __init__(self, event_simulator: EventDrivenSimulator, vectorized_simulator: VectorizedSimulator) -> None:
        self.event_simulator = event_simulator
        self.vectorized_simulator = vectorized_simulator

    def run(self, config, loaded_data, strategies: list) -> dict:
        if config.simulation_mode == "vectorized":
            return self.vectorized_simulator.run(config, loaded_data, strategies)
        return self.event_simulator.run(config, loaded_data, strategies)
