import random
import unittest

from simulation.ring_road import RingRoad
from simulation.vehicle import ProfileType, Vehicle


class PacerFlowTest(unittest.TestCase):
    def run_ring_scenario(self, profiles: list[ProfileType], seed: int = 7) -> dict:
        random.seed(seed)
        Vehicle._next_id = 0

        road = RingRoad(num_lanes=2, circumference=287.26)
        vehicle_count = len(profiles)

        for idx, profile in enumerate(profiles):
            lane = idx % road.num_lanes
            position = (idx / vehicle_count) * road.circumference
            vehicle = road.add_vehicle(profile=profile, lane=lane, position=position)
            vehicle.velocity = min(vehicle.desired_speed, road.desired_speed * 0.9)

        for _ in range(900):
            road.update(1.0 / 30.0)

        return road.get_telemetry()

    def test_pacers_improve_average_speed_and_flow_vs_commuters(self) -> None:
        commuters = self.run_ring_scenario([ProfileType.COMMUTER] * 20)
        pacers = self.run_ring_scenario([ProfileType.PACER] * 20)

        self.assertGreater(pacers["avg_speed"], commuters["avg_speed"])
        self.assertGreater(pacers["flow"], commuters["flow"])

    def test_replacing_commuters_with_pacers_improves_average_speed_and_flow(self) -> None:
        commuters = self.run_ring_scenario([ProfileType.COMMUTER] * 20)
        mixed = self.run_ring_scenario(
            [ProfileType.PACER] * 10 + [ProfileType.COMMUTER] * 10
        )

        self.assertGreater(mixed["avg_speed"], commuters["avg_speed"])
        self.assertGreater(mixed["flow"], commuters["flow"])

    def test_pacers_tighten_gap_when_following_another_pacer(self) -> None:
        pacer = Vehicle(profile=ProfileType.PACER, global_speed_limit=30.0)
        pacer.velocity = 28.0
        pacer.desired_speed = pacer.base_desired_speed

        lead_pacer = Vehicle(profile=ProfileType.PACER, global_speed_limit=30.0)
        lead_pacer.velocity = 27.5

        min_gap, time_headway = pacer.get_effective_following_params(lead_pacer)

        self.assertLess(min_gap, pacer.min_gap)
        self.assertLess(time_headway, pacer.time_headway)


if __name__ == "__main__":
    unittest.main()
