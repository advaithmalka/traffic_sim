"""
RingRoad topology — a circular road with multiple lanes.

Vehicles travel along a 1-D arc-length coordinate that wraps around
the circumference. Cartesian (x, y) positions are computed for rendering
via x = R·cos(θ), y = R·sin(θ).
"""

from __future__ import annotations

import math
import random
from dataclasses import asdict
from typing import Any, Optional

from .vehicle import Vehicle, VehicleState

DEFAULT_CIRCUMFERENCE_M = 287.26
DEFAULT_NUM_LANES = 2
DEFAULT_LANE_WIDTH_M = 4.5
DEFAULT_SPEED_LIMIT_MPS = 30.0


class RingRoad:
    """
    A circular road of a given circumference with *num_lanes* concentric lanes.
    Lane 0 is the inner lane; higher indices are further out.
    """

    def __init__(
        self,
        circumference: float = DEFAULT_CIRCUMFERENCE_M,
        num_lanes: int = DEFAULT_NUM_LANES,
        lane_width: float = DEFAULT_LANE_WIDTH_M,
    ) -> None:
        self.circumference: float = circumference
        self.num_lanes: int = num_lanes
        self.lane_width: float = lane_width

        # Derived geometry
        self.inner_radius: float = circumference / (2.0 * math.pi)
        self.center_x: float = 0.0
        self.center_y: float = 0.0

        # Vehicle storage: flat list, lane stored per vehicle
        self.vehicles: list[Vehicle] = []

        # Simulation configuration (mutable at runtime)
        self.global_aggression: float = 0.5
        self.desired_speed: float = DEFAULT_SPEED_LIMIT_MPS  # m/s (~108 km/h)
        self.paused: bool = False

    # ────────────────────────────────────────────────────────────────────
    #  Vehicle management
    # ────────────────────────────────────────────────────────────────────

    def add_vehicle(self, profile: str = "COMMUTER", lane: int | None = None, position: float | None = None) -> Vehicle:
        """Spawn a new vehicle at a random or specified position."""
        if lane is None:
            lane = random.randint(0, self.num_lanes - 1)
        if position is None:
            position = random.uniform(0, self.circumference)

        v = Vehicle(
            position=position,
            velocity=random.uniform(self.desired_speed * 0.8, self.desired_speed * 1.2),
            lane=lane,
            profile=profile,
            global_speed_limit=self.desired_speed,
        )
        self.vehicles.append(v)
        return v

    def clear_vehicles(self) -> None:
        """Remove all vehicles from the simulation."""
        self.vehicles.clear()

    def remove_vehicle_by_profile(self, profile: str) -> bool:
        """Removes the first found vehicle matching the profile."""
        for i, v in enumerate(self.vehicles):
            if v.profile == profile:
                self.vehicles.pop(i)
                break


    #  Neighbour queries
    # ────────────────────────────────────────────────────────────────────

    def _vehicles_in_lane(self, lane: int) -> list[Vehicle]:
        """Return vehicles in a lane sorted by position."""
        return sorted(
            [v for v in self.vehicles if v.lane == lane],
            key=lambda v: v.position,
        )

    def _circular_gap(self, pos_behind: float, pos_ahead: float) -> float:
        """Arc-length gap from *pos_behind* to *pos_ahead*, wrapping."""
        gap = pos_ahead - pos_behind
        if gap < 0:
            gap += self.circumference
        return gap

    def get_lead_vehicle(self, vehicle: Vehicle) -> tuple[Optional[Vehicle], float]:
        """
        Find the vehicle directly ahead in the same lane.
        Returns (lead_vehicle, gap) or (None, inf).
        """
        lane_vehicles = self._vehicles_in_lane(vehicle.lane)
        n = len(lane_vehicles)
        if n <= 1:
            return None, float("inf")

        idx = next(
            (i for i, v in enumerate(lane_vehicles) if v.id == vehicle.id), None
        )
        if idx is None:
            return None, float("inf")

        lead_idx = (idx + 1) % n
        lead = lane_vehicles[lead_idx]
        gap = self._circular_gap(vehicle.position, lead.position)
        return lead, gap

    def get_follower_vehicle(self, vehicle: Vehicle, lane: int) -> tuple[Optional[Vehicle], float]:
        """Find the vehicle directly behind a given position in a lane."""
        lane_vehicles = self._vehicles_in_lane(lane)
        if not lane_vehicles:
            return None, float("inf")

        # Find nearest vehicle behind
        best: Optional[Vehicle] = None
        best_gap = float("inf")
        for v in lane_vehicles:
            if v.id == vehicle.id:
                continue
            gap = self._circular_gap(v.position, vehicle.position)
            if gap < best_gap:
                best_gap = gap
                best = v
        return best, best_gap

    # ────────────────────────────────────────────────────────────────────
    #  Simulation step
    # ────────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        """
        Advance the simulation by one time step:
        1. Compute IDM accelerations for all vehicles.
        2. Evaluate MOBIL lane changes.
        3. Integrate positions & velocities.
        4. Wrap positions.
        """
        if self.paused:
            return

        avg_speed = 30.0
        if len(self.vehicles) > 0:
            avg_speed = sum(v.velocity for v in self.vehicles) / len(self.vehicles)

        # ── Phase 1: Pre-process dynamic states ───────────────────────────────────
        for vehicle in self.vehicles:
            if vehicle.profile == "FOLLOWER":
                # Temporarily speed up ~12.5 mph (5.58 m/s) when passing (not in the outermost right lane)
                if vehicle.lane < self.num_lanes - 1:
                    vehicle.desired_speed = vehicle.base_desired_speed + 5.58
                else:
                    vehicle.desired_speed = vehicle.base_desired_speed

        # ── Phase 2: MOBIL lane changes ─────────────────────────────────
        for vehicle in self.vehicles:
            if vehicle.lane_change_cooldown > 0:
                continue
            if self.num_lanes < 2:
                continue

            # Try each adjacent lane
            for target_lane in range(self.num_lanes):
                if target_lane == vehicle.lane:
                    continue
                # Prevent checking non-adjacent lanes
                if abs(target_lane - vehicle.lane) != 1:
                    continue

                self._try_lane_change(vehicle, target_lane)

        # ── Phase 3: Kinematics ──────────────────────────────────
        for vehicle in self.vehicles:
            lead, gap = self.get_lead_vehicle(vehicle)
            vehicle.update(dt, lead, gap)
            # Wrap position around the ring
            vehicle.position %= self.circumference

    def _try_lane_change(self, vehicle: Vehicle, target_lane: int) -> None:
        """Evaluate and execute a MOBIL lane change if criteria are met."""
        # Current situation
        current_accel = vehicle.acceleration

        # Prospective situation in target lane
        # Temporarily move vehicle to compute hypothetical accelerations
        original_lane = vehicle.lane
        vehicle.lane = target_lane

        # In target lane: find lead and compute new ego accel
        new_lead, new_gap = self.get_lead_vehicle(vehicle)
        new_accel = vehicle.calculate_iidm_acceleration(new_lead, new_gap)

        # New follower in target lane
        vehicle.lane = original_lane  # restore for follower search
        new_follower, _ = self.get_follower_vehicle(vehicle, target_lane)

        # Old follower in current lane
        old_follower, _ = self.get_follower_vehicle(vehicle, original_lane)

        # Compute follower accelerations before/after
        if old_follower:
            old_follower_accel_before = old_follower.acceleration
            # After: old follower's new lead is vehicle's current lead
            lead_of_ego, gap_of_lead = self.get_lead_vehicle(vehicle)
            if lead_of_ego:
                new_gap_for_old_follower = self._circular_gap(
                    old_follower.position, lead_of_ego.position
                )
                old_follower_accel_after = old_follower.calculate_iidm_acceleration(
                    lead_of_ego, new_gap_for_old_follower
                )
            else:
                old_follower_accel_after = old_follower.calculate_iidm_acceleration(None, None)
        else:
            old_follower_accel_before = 0.0
            old_follower_accel_after = 0.0

        if new_follower:
            new_follower_accel_before = new_follower.acceleration
            # After: new follower's lead becomes *this* vehicle
            new_gap_for_new_follower = self._circular_gap(
                new_follower.position, vehicle.position
            )
            new_follower_accel_after = new_follower.calculate_iidm_acceleration(
                vehicle, new_gap_for_new_follower
            )
        else:
            new_follower_accel_before = 0.0
            new_follower_accel_after = 0.0

        should_change = vehicle.calculate_mobil_lane_change(
            current_accel=current_accel,
            new_accel=new_accel,
            old_follower_accel_before=old_follower_accel_before,
            old_follower_accel_after=old_follower_accel_after,
            new_follower_accel_before=new_follower_accel_before,
            new_follower_accel_after=new_follower_accel_after,
            target_lane=target_lane,
        )

        if should_change:
            vehicle.lane = target_lane
            vehicle.acceleration = new_accel
            vehicle.lane_change_cooldown = 3.0  # 3 second cooldown

    # ────────────────────────────────────────────────────────────────────
    #  State serialisation
    # ────────────────────────────────────────────────────────────────────

    def _arc_to_cartesian(self, vehicle: Vehicle) -> tuple[float, float, float]:
        """Convert physical state to (x, y, rotation) using smooth lane transitioning.

        The vehicle is placed at the CENTER of its current structural floating inner-lane.
        Rotation applies a yaw angle physically turning the car along vector derivatives.
        """
        radius = self.inner_radius + vehicle.actual_lane * self.lane_width + self.lane_width / 2.0
        theta = (vehicle.position / self.circumference) * 2.0 * math.pi
        x = radius * math.cos(theta)
        y = radius * math.sin(theta)
        
        # Radial & Tangential velocity conversions
        v_r = vehicle.radial_velocity * self.lane_width
        v_t = max(vehicle.velocity, 0.1)

        # Tangent facing calculation with turning logic
        base_rotation = theta + math.pi / 2.0
        yaw_offset = math.atan2(v_r, v_t)

        return x, y, base_rotation - yaw_offset

    def get_state(self) -> list[dict[str, Any]]:
        """Return the full simulation state as a list of dicts."""
        states: list[dict[str, Any]] = []
        for vehicle in self.vehicles:
            x, y, rotation = self._arc_to_cartesian(vehicle)
            state = vehicle.to_state(x, y, rotation)
            states.append(asdict(state))
        return states

    def get_telemetry(self) -> dict[str, Any]:
        """Compute aggregate telemetry data."""
        if not self.vehicles:
            return {"avg_speed": 0, "flow": 0, "count": 0, "density": 0}

        speeds = [v.velocity for v in self.vehicles]
        avg_speed = sum(speeds) / len(speeds)

        # Flow = density × average speed  (vehicles per hour per lane)
        density = len(self.vehicles) / (self.circumference / 1609.34)  # veh/mile
        flow = density * (avg_speed * 2.23694)  # veh/hr (speed in mph)
        
        profile_counts = {}
        for v in self.vehicles:
            profile_counts[v.profile] = profile_counts.get(v.profile, 0) + 1

        return {
            "avg_speed": round(avg_speed * 2.23694, 1),  # mph
            "flow": round(flow, 0),
            "count": len(self.vehicles),
            "density": round(density, 1),
            "profile_counts": profile_counts,
        }

    def set_speed_limit(self, speed_kmh: float) -> None:
        """Update the desired speed for all vehicles."""
        speed_ms = speed_kmh / 3.6
        self.desired_speed = speed_ms
        for v in self.vehicles:
            v.base_desired_speed = speed_ms * v.v_mult
            v.desired_speed = v.base_desired_speed

    def set_num_lanes(self, lanes: int) -> None:
        """Update maximum lanes and enforce limits."""
        self.num_lanes = max(1, lanes)
        for v in self.vehicles:
            if v.lane >= self.num_lanes:
                v.lane = self.num_lanes - 1

    def set_circumference(self, circ: float) -> None:
        """Update road diameter and clamp vehicles extending past the new track size."""
        self.circumference = max(50.0, circ)
        self.inner_radius = self.circumference / (2.0 * math.pi)
        for v in self.vehicles:
            v.position %= self.circumference

    def toggle_pause(self) -> None:
        """Toggle the running state of the simulation."""
        self.paused = not self.paused

    def reset(self) -> None:
        """Restore the simulation to default topological state."""
        self.vehicles.clear()
        self.num_lanes = DEFAULT_NUM_LANES
        self.lane_width = DEFAULT_LANE_WIDTH_M
        self.set_circumference(DEFAULT_CIRCUMFERENCE_M)  # 150ft radius
        self.desired_speed = DEFAULT_SPEED_LIMIT_MPS
        self.paused = False
