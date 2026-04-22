from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional
from enum import Enum

@dataclass
class VehicleState:
    """Serializable snapshot of a vehicle's state for WebSocket broadcast."""
    id: int
    x: float
    y: float
    rotation: float
    speed: float
    lane: int
    profile: str
    color: str
    acceleration: float
    gap: float
    raw_gap: float

class ProfileType(str, Enum):
    COMMUTER = "COMMUTER"
    AGGRESSIVE = "AGGRESSIVE"
    CAMPER = "CAMPER"
    CAUTIOUS = "CAUTIOUS"
    FOLLOWER = "FOLLOWER"
    PACER = "PACER"

# Profiles now define Gaussian distributions (mu, sigma) to enforce inter-driver heterogeneity.
PROFILES = {
    ProfileType.COMMUTER: {
        "v_mult": (1.0, 0.05), "T": (1.05, 0.12), "s0": (1.5, 0.25), "a": (1.4, 0.4), "b": (2.0, 0.5), 
        "p": 0.2, "dath": 0.2, "bias_dir": "Right", "color": "#808080"
    },
    ProfileType.AGGRESSIVE: {
        "v_mult": (1.15, 0.05), "T": (0.8, 0.08), "s0": (0.8, 0.15), "a": (4, 0.5), "b": (4.0, 0.8), 
        "p": 0.0, "dath": 0.05, "bias_dir": "None", "color": "#FF0000",
        "slow_lead_headway_factor": 0.58,
        "slow_lead_min_gap_factor": 0.72,
        "slow_lead_activation_delta": 2.5,
        "slow_lead_full_delta": 5.0,
    },
    ProfileType.CAMPER: {
        "v_mult": (0.95, 0.05), "T": (1.4, 0.18), "s0": (2.0, 0.25), "a": (1.0, 0.3), "b": (1.5, 0.4), 
        "p": 0.0, "dath": 0.5, "bias_dir": "Left", "color": "#800080"
    },
    ProfileType.CAUTIOUS: {
        "v_mult": (0.85, 0.05), "T": (1.7, 0.2), "s0": (2.8, 0.3), "a": (0.8, 0.2), "b": (1.0, 0.3), 
        "p": 0.5, "dath": 0.8, "bias_dir": "Right", "color": "#FFFF00"
    },
    ProfileType.FOLLOWER: {
        "v_mult": (1.05, 0.05), "T": (1.0, 0.1), "s0": (1.4, 0.2), "a": (1.5, 0.4), "b": (2.0, 0.5), 
        "p": 0.3, "dath": 0.1, "bias_dir": "Right", "color": "#0000FF"
    },
    ProfileType.PACER: {
        "v_mult": (1.03, 0.015), "T": (0.9, 0.06), "s0": (1.1, 0.12), "a": (1.4, 0.12), "b": (2.0, 0.2),
        "p": 0.7, "dath": 0.25, "bias_dir": "None", "color": "#00FF00",
        "cooperative_headway_factor": 0.97,
        "cooperative_min_gap_factor": 0.96,
        "cooperative_sync_window": 2.0,
    }
}

class Vehicle:
    """
    A single vehicle on the road, governed by the Improved IDM (IIDM),
    asymmetric MOBIL lane-change logic, and ballistic kinematics.
    """
    _next_id: int = 0

    def __init__(
        self,
        position: float = 0.0,
        velocity: float = 10.0,
        lane: int = 0,
        profile: str = ProfileType.COMMUTER,
        global_speed_limit: float = 30.0,
    ) -> None:
        Vehicle._next_id += 1
        self.id: int = Vehicle._next_id
        
        cfg = PROFILES.get(profile, PROFILES[ProfileType.COMMUTER])
        self.profile: str = profile
        self.color: str = cfg["color"]

        # Heterogeneous parameter sampling via Gaussian distributions
        self.v_mult: float = max(0.5, random.gauss(*cfg["v_mult"]))
        self.base_desired_speed: float = global_speed_limit * self.v_mult
        self.desired_speed: float = self.base_desired_speed

        self.time_headway: float = max(0.7, random.gauss(*cfg["T"]))
        self.min_gap: float = max(0.75, random.gauss(*cfg["s0"]))
        self.max_acceleration: float = max(0.3, random.gauss(*cfg["a"]))
        self.comfortable_decel: float = max(0.5, random.gauss(*cfg["b"]))
        self.accel_exponent: float = 4.0
        self.slow_lead_headway_factor: float = max(
            0.4, min(1.0, cfg.get("slow_lead_headway_factor", 1.0))
        )
        self.slow_lead_min_gap_factor: float = max(
            0.4, min(1.0, cfg.get("slow_lead_min_gap_factor", 1.0))
        )
        self.slow_lead_activation_delta: float = max(
            0.0, cfg.get("slow_lead_activation_delta", float("inf"))
        )
        self.slow_lead_full_delta: float = max(
            0.1, cfg.get("slow_lead_full_delta", 1.0)
        )
        self.cooperative_headway_factor: float = max(
            0.5, min(1.0, cfg.get("cooperative_headway_factor", 1.0))
        )
        self.cooperative_min_gap_factor: float = max(
            0.5, min(1.0, cfg.get("cooperative_min_gap_factor", 1.0))
        )
        self.cooperative_sync_window: float = max(
            0.1, cfg.get("cooperative_sync_window", 1.0)
        )

        # MOBIL & Asymmetric Parameters
        self.politeness: float = cfg["p"]
        self.lane_change_threshold: float = cfg["dath"]
        self.safe_decel: float = 9.0 if profile == "AGGRESSIVE" else 4.0
        self.bias_dir: str = cfg["bias_dir"]
        self.asymmetric_bias: float = 0.3  # m/s² continuous pressure
        self.lane_change_cooldown: float = 0.0

        # Kinematic state
        self.position: float = position
        self.velocity: float = max(0.0, min(velocity, self.desired_speed))
        self.acceleration: float = 0.0
        self.lane: int = lane
        self.actual_lane: float = float(lane)
        self.radial_velocity: float = 0.0
        self.length: float = 4
        self.current_gap: float = float("inf")
        self.current_raw_gap: float = float("inf")

        # Human Factors: Action Points & Wiener Process (Stochasticity)
        self.reaction_time: float = max(0.6, random.gauss(1.2, 0.2))
        self.time_since_action: float = self.reaction_time
        
        self.wiener_s: float = 0.0
        self.wiener_v: float = 0.0
        self.tau_wiener: float = 10.0  # Correlation time (s)
        self.v_s: float = 0.25         # Spatial estimation variance (increased error)
        self.sigma_r: float = 0.25     # Velocity estimation variance (increased error)

    # ────────────────────────────────────────────────────────────────────
    #  IIDM — Improved Intelligent Driver Model + Human Perception
    # ────────────────────────────────────────────────────────────────────

    def update_perception_noise(self, dt_action: float) -> None:
        """Update the discrete Wiener process for perception errors."""
        decay = math.exp(-dt_action / self.tau_wiener)
        noise_amp = math.sqrt(2 * dt_action / self.tau_wiener)
        self.wiener_s = decay * self.wiener_s + noise_amp * random.gauss(0, 1)
        self.wiener_v = decay * self.wiener_v + noise_amp * random.gauss(0, 1)

    def calculate_iidm_acceleration(
        self,
        lead_vehicle: Optional[Vehicle],
        true_gap: Optional[float] = None,
    ) -> float:
        """Compute acceleration using the Improved IDM to fix steady-state anomalies."""
        v = max(self.velocity, 0.0)
        v0 = self.desired_speed
        a = self.max_acceleration
        b = self.comfortable_decel

        # Free-road acceleration
        a_free = a * (1.0 - (v / v0) ** self.accel_exponent) if v0 > 0 else 0.0

        if lead_vehicle is None or true_gap is None:
            return a_free

        # Use true values without catastrophic stochastic scaling
        s_true = max(true_gap - self.length, 0.1)
        dv = v - lead_vehicle.velocity

        min_gap, time_headway = self.get_effective_following_params(lead_vehicle)

        # Desired dynamic gap
        s_star = min_gap + max(
            0.0,
            v * time_headway + (v * dv) / (2.0 * math.sqrt(a * b)),
        )
        
        # Interaction ratio
        z = s_star / s_true

        # IIDM Piecewise Formulation (Treiber/Kesting stable transition)
        accel = 0.0
        if a_free > 1e-6:
            if z >= 1.0:
                # Strongly constrained regime
                accel = a * (1.0 - z**2)
            else:
                # Weakly constrained / free-flow blending
                # Safety check for a_free near zero handled by block condition
                accel = a_free * (1.0 - z**(2 * a / a_free))
        elif a_free >= -1e-6:
            # v ~= v0 regime
            if z >= 1.0:
                accel = a * (1.0 - z**2)
            else:
                accel = 0.0
        else:
            # v > v0 case: Neutralize over-speeding even with clear road
            if z >= 1.0:
                accel = a_free + a * (1.0 - z**2)
            else:
                accel = a_free

        # Safety: Ensure numeric stability
        if not math.isfinite(accel):
            return 0.0
        return accel

    def get_effective_following_params(
        self,
        lead_vehicle: Optional[Vehicle],
    ) -> tuple[float, float]:
        """Adjust following params for profile-specific behavior."""
        if lead_vehicle is None:
            return self.min_gap, self.time_headway

        min_gap = self.min_gap
        time_headway = self.time_headway

        # Automated pacers can safely run slightly tighter when platooning
        # behind another speed-matched pacer, which raises roadway capacity.
        if self.profile == ProfileType.PACER and lead_vehicle.profile == ProfileType.PACER:
            speed_alignment = max(
                0.0,
                1.0 - (abs(self.velocity - lead_vehicle.velocity) / self.cooperative_sync_window),
            )
            if speed_alignment > 0.0:
                min_gap *= 1.0 - (
                    (1.0 - self.cooperative_min_gap_factor) * speed_alignment
                )
                time_headway *= 1.0 - (
                    (1.0 - self.cooperative_headway_factor) * speed_alignment
                )

        speed_deficit = max(0.0, self.desired_speed - lead_vehicle.velocity)
        if speed_deficit <= self.slow_lead_activation_delta:
            return max(0.5, min_gap), max(0.45, time_headway)

        pressure = min(
            1.0,
            (speed_deficit - self.slow_lead_activation_delta)
            / self.slow_lead_full_delta,
        )
        min_gap *= (
            1.0 - ((1.0 - self.slow_lead_min_gap_factor) * pressure)
        )
        time_headway *= (
            1.0 - ((1.0 - self.slow_lead_headway_factor) * pressure)
        )
        return max(0.5, min_gap), max(0.45, time_headway)

    # ────────────────────────────────────────────────────────────────────
    #  Asymmetric MOBIL
    # ────────────────────────────────────────────────────────────────────

    def calculate_mobil_lane_change(
        self,
        current_accel: float,
        new_accel: float,
        old_follower_accel_before: float,
        old_follower_accel_after: float,
        new_follower_accel_before: float,
        new_follower_accel_after: float,
        target_lane: int,
    ) -> bool:
        """Evaluate lane changes using formal asymmetric acceleration biases."""
        if self.lane_change_cooldown > 0:
            return False

        # Physical safety criterion (hard constraint)
        if new_follower_accel_after < -self.safe_decel:
            return False

        ego_gain = new_accel - current_accel
        old_follower_change = old_follower_accel_after - old_follower_accel_before
        new_follower_change = new_follower_accel_after - new_follower_accel_before

        # Determine threshold based on topological bias rules
        threshold = self.lane_change_threshold
        
        if self.bias_dir == "Right":
            if target_lane > self.lane:
                # Moving right (returning to cruise)
                threshold -= self.asymmetric_bias
            else:
                # Moving left (passing)
                threshold += self.asymmetric_bias
                # Neglect old follower advantage to prioritize passing lane flow
                old_follower_change = min(0.0, old_follower_change)
                
        elif self.bias_dir == "Left":
            if target_lane < self.lane:
                threshold -= self.asymmetric_bias
            else:
                threshold += self.asymmetric_bias

        altruistic_cost = self.politeness * (old_follower_change + new_follower_change)

        return (ego_gain + altruistic_cost) > threshold

    # ────────────────────────────────────────────────────────────────────
    #  Kinematics: Ballistic Integration & Action Points
    # ────────────────────────────────────────────────────────────────────

    def update(
        self, 
        dt: float, 
        lead_vehicle: Optional[Vehicle], 
        gap: Optional[float]
    ) -> None:
        """Second-order Ballistic Update with Action Point evaluation."""
        raw_gap = gap if gap is not None else float("inf")
        self.current_raw_gap = raw_gap
        self.current_gap = max(raw_gap - self.length, 0.0) if math.isfinite(raw_gap) else float("inf")

        # Acceleration computed dynamically every frame (no cognitive freezing)
        self.acceleration = self.calculate_iidm_acceleration(lead_vehicle, gap)

        # Ballistic Kinematic Integration (Predictive Stopping Heuristic)
        v_next = self.velocity + self.acceleration * dt

        if v_next < 0:
            # Prevent position overshoot and negative velocities
            if self.acceleration < -0.001:
                dt_stop = -self.velocity / self.acceleration
                self.position += (self.velocity * dt_stop) + (0.5 * self.acceleration * (dt_stop ** 2))
            
            self.velocity = 0.0
            self.acceleration = 0.0
        else:
            self.position += (self.velocity * dt) + (0.5 * self.acceleration * (dt ** 2))
            self.velocity = min(v_next, 80.0)  # Safety Cap: ~180 mph

        # Smooth lateral lane shift
        diff = self.lane - self.actual_lane
        if abs(diff) > 0.01:
            shift = math.copysign(min(abs(diff), 1.0 * dt), diff)
            self.radial_velocity = shift / dt
            self.actual_lane += shift
        else:
            self.radial_velocity = 0.0
            self.actual_lane = float(self.lane)

        if self.lane_change_cooldown > 0:
            self.lane_change_cooldown = max(0.0, self.lane_change_cooldown - dt)

    def to_state(self, x: float, y: float, rotation: float) -> VehicleState:
        return VehicleState(
            id=self.id,
            x=round(x, 3),
            y=round(y, 3),
            rotation=round(rotation, 4),
            speed=round(self.velocity, 2),
            lane=self.lane,
            profile=self.profile,
            color=self.color,
            acceleration=round(self.acceleration, 2),
            gap=round(self.current_gap, 1) if math.isfinite(self.current_gap) else 999.0,
            raw_gap=round(self.current_raw_gap, 1) if math.isfinite(self.current_raw_gap) else 999.0,
        )
