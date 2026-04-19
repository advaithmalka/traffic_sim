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
        "v_mult": (1.0, 0.05), "T": (0.8, 0.15), "s0": (2.0, 0.2), "a": (1.4, 0.4), "b": (2.0, 0.5), 
        "p": 0.2, "dath": 0.2, "bias_dir": "Right", "color": "#808080"
    },
    ProfileType.AGGRESSIVE: {
        "v_mult": (1.15, 0.05), "T": (0.05, 0.05), "s0": (1.5, 0.2), "a": (4, 0.5), "b": (4.0, 0.8), 
        "p": 0.0, "dath": 0.05, "bias_dir": "None", "color": "#FF0000"
    },
    ProfileType.CAMPER: {
        "v_mult": (0.95, 0.05), "T": (1.0, 0.2), "s0": (2.0, 0.2), "a": (1.0, 0.3), "b": (1.5, 0.4), 
        "p": 0.0, "dath": 0.5, "bias_dir": "Left", "color": "#800080"
    },
    ProfileType.CAUTIOUS: {
        "v_mult": (0.85, 0.05), "T": (1.5, 0.2), "s0": (3.0, 0.3), "a": (0.8, 0.2), "b": (1.0, 0.3), 
        "p": 0.5, "dath": 0.8, "bias_dir": "Right", "color": "#FFFF00"
    },
    ProfileType.FOLLOWER: {
        "v_mult": (1.05, 0.05), "T": (0.8, 0.15), "s0": (2.0, 0.2), "a": (1.5, 0.4), "b": (2.0, 0.5), 
        "p": 0.3, "dath": 0.1, "bias_dir": "Right", "color": "#0000FF"
    },
    ProfileType.PACER: {
        "v_mult": (1.0, 0.02), "T": (1.8, 0.1), "s0": (2.5, 0.1), "a": (0.8, 0.1), "b": (0.8, 0.1), 
        "p": 1.0, "dath": 0.5, "bias_dir": "None", "color": "#00FF00"
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

        self.time_headway: float = max(0.5, random.gauss(*cfg["T"]))
        self.min_gap: float = max(0.5, random.gauss(*cfg["s0"]))
        self.max_acceleration: float = max(0.3, random.gauss(*cfg["a"]))
        self.comfortable_decel: float = max(0.5, random.gauss(*cfg["b"]))
        self.accel_exponent: float = 4.0

        # MOBIL & Asymmetric Parameters
        self.politeness: float = cfg["p"]
        self.lane_change_threshold: float = cfg["dath"]
        self.safe_decel: float = 6.0 if profile == "AGGRESSIVE" else 4.0
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
        self.length: float = 4.5
        self.current_gap: float = 0.0

        # Human Factors: Action Points & Wiener Process (Stochasticity)
        self.reaction_time: float = max(0.6, random.gauss(1.2, 0.2))
        self.time_since_action: float = self.reaction_time
        
        self.wiener_s: float = 0.0
        self.wiener_v: float = 0.0
        self.tau_wiener: float = 15.0  # Correlation time (s)
        self.v_s: float = 0.1          # Spatial estimation variance
        self.sigma_r: float = 0.1      # Velocity estimation variance

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

        # Desired dynamic gap
        s_star = self.min_gap + max(0.0, v * self.time_headway + (v * dv) / (2.0 * math.sqrt(a * b)))
        
        # Interaction ratio
        z = s_star / s_true

        # IIDM Piecewise Formulation
        if z >= 1.0:
            # Strongly constrained regime
            return a * (1.0 - z**2)
        else:
            # Weakly constrained / free-flow blending
            if a_free > 0.01:
                return a_free * (1.0 - z**(2 * a / a_free))
            else:
                return a * (1.0 - z**2)  # Fallback near v0

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
        self.current_gap = gap if gap is not None else 0.0

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
            self.velocity = v_next

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
            gap=round(self.current_gap, 1)
        )