import unittest

from simulation.vehicle import ProfileType, Vehicle


class AggressiveFollowingBehaviorTest(unittest.TestCase):
    def make_vehicle(self, profile: ProfileType) -> Vehicle:
        vehicle = Vehicle(profile=profile, global_speed_limit=30.0)
        vehicle.base_desired_speed = 33.0
        vehicle.desired_speed = 33.0
        vehicle.velocity = 28.0
        vehicle.max_acceleration = 4.0
        vehicle.comfortable_decel = 4.0

        if profile == ProfileType.AGGRESSIVE:
            vehicle.time_headway = 0.8
            vehicle.min_gap = 0.8
            vehicle.slow_lead_headway_factor = 0.58
            vehicle.slow_lead_min_gap_factor = 0.72
            vehicle.slow_lead_activation_delta = 2.5
            vehicle.slow_lead_full_delta = 5.0
        else:
            vehicle.time_headway = 1.1
            vehicle.min_gap = 1.5
            vehicle.slow_lead_headway_factor = 1.0
            vehicle.slow_lead_min_gap_factor = 1.0
            vehicle.slow_lead_activation_delta = float("inf")
            vehicle.slow_lead_full_delta = 1.0

        return vehicle

    def make_lead(self, speed: float) -> Vehicle:
        lead = Vehicle(profile=ProfileType.COMMUTER, global_speed_limit=30.0)
        lead.velocity = speed
        return lead

    def test_aggressive_driver_tightens_following_params_for_slow_lead(self) -> None:
        aggressive = self.make_vehicle(ProfileType.AGGRESSIVE)
        slow_lead = self.make_lead(23.0)

        min_gap, time_headway = aggressive.get_effective_following_params(slow_lead)

        self.assertLess(min_gap, aggressive.min_gap)
        self.assertLess(time_headway, aggressive.time_headway)

    def test_aggressive_driver_keeps_base_gap_for_similar_speed_lead(self) -> None:
        aggressive = self.make_vehicle(ProfileType.AGGRESSIVE)
        near_speed_lead = self.make_lead(31.0)

        min_gap, time_headway = aggressive.get_effective_following_params(near_speed_lead)

        self.assertAlmostEqual(min_gap, aggressive.min_gap)
        self.assertAlmostEqual(time_headway, aggressive.time_headway)

    def test_non_aggressive_profile_keeps_base_gap_for_slow_lead(self) -> None:
        commuter = self.make_vehicle(ProfileType.COMMUTER)
        slow_lead = self.make_lead(23.0)

        min_gap, time_headway = commuter.get_effective_following_params(slow_lead)

        self.assertAlmostEqual(min_gap, commuter.min_gap)
        self.assertAlmostEqual(time_headway, commuter.time_headway)

    def test_aggressive_driver_brakes_less_for_same_gap_when_slow_lead_is_ahead(self) -> None:
        aggressive = self.make_vehicle(ProfileType.AGGRESSIVE)
        slow_lead = self.make_lead(23.0)
        gap = 22.0

        baseline = aggressive.calculate_iidm_acceleration(slow_lead, gap)

        aggressive.slow_lead_headway_factor = 1.0
        aggressive.slow_lead_min_gap_factor = 1.0
        without_tightening = aggressive.calculate_iidm_acceleration(slow_lead, gap)

        self.assertGreater(baseline, without_tightening)


if __name__ == "__main__":
    unittest.main()
