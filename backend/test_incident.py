"""Verify that trigger_incident actually causes a vehicle to brake hard."""

import unittest

from simulation.ring_road import RingRoad
from simulation.vehicle import ProfileType


class IncidentBrakeTest(unittest.TestCase):
    def test_incident_decelerates_vehicle_with_no_lead(self) -> None:
        """A solo car on the ring should still hard-brake during an incident.

        This is the behavior that broke previously: setting desired_speed=0
        in IIDM produced a_free=0 with no lead, so the car coasted.
        """
        road = RingRoad(circumference=400.0, num_lanes=1)
        v = road.add_vehicle(profile=ProfileType.COMMUTER.value, lane=0, position=0.0)
        v.velocity = 25.0  # ~56 mph

        v.trigger_incident(duration=3.0)
        initial_speed = v.velocity

        # Step the simulation for 1 second (30 ticks at dt=1/30)
        dt = 1.0 / 30.0
        for _ in range(30):
            road.update(dt)

        self.assertLess(
            v.velocity,
            initial_speed - 5.0,
            f"Vehicle should have lost >5 m/s in 1s of incident; went {initial_speed:.2f} → {v.velocity:.2f}",
        )

    def test_incident_stops_vehicle_within_window(self) -> None:
        """A 25 m/s car should be near-stopped after the full 3s incident."""
        road = RingRoad(circumference=400.0, num_lanes=1)
        v = road.add_vehicle(profile=ProfileType.COMMUTER.value, lane=0, position=0.0)
        v.velocity = 25.0

        v.trigger_incident(duration=3.0)

        dt = 1.0 / 30.0
        for _ in range(int(3.0 / dt) + 5):
            road.update(dt)

        self.assertLess(v.velocity, 1.0, f"Vehicle should be ~stopped; speed={v.velocity:.2f}")

    def test_incident_recovery(self) -> None:
        """Once the incident timer expires, IIDM should resume accelerating."""
        road = RingRoad(circumference=400.0, num_lanes=1)
        v = road.add_vehicle(profile=ProfileType.COMMUTER.value, lane=0, position=0.0)
        v.velocity = 20.0
        original_desired = v.desired_speed

        v.trigger_incident(duration=1.0)

        dt = 1.0 / 30.0
        # Run through the incident
        for _ in range(int(1.0 / dt) + 5):
            road.update(dt)

        speed_after_incident = v.velocity

        # Now run for another second — should be accelerating back up
        for _ in range(30):
            road.update(dt)

        self.assertGreater(
            v.velocity,
            speed_after_incident,
            "Vehicle should be re-accelerating after incident expires",
        )
        self.assertEqual(v.desired_speed, original_desired)


if __name__ == "__main__":
    unittest.main()
