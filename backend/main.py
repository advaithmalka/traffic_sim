"""
FastAPI server for the traffic simulation.

Runs an async game loop at 30 TPS that broadcasts vehicle state
over WebSockets to all connected clients.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import random
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from simulation.ring_road import (
    DEFAULT_CIRCUMFERENCE_M,
    DEFAULT_LANE_WIDTH_M,
    DEFAULT_NUM_LANES,
    RingRoad,
)

# ── Logging ─────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("traffic_sim")


# ── Connection Manager ──────────────────────────────────────────────────
class ConnectionManager:
    """Track active WebSocket connections and broadcast messages."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            "Client connected. Total: %d", len(self.active_connections)
        )

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(
            "Client disconnected. Total: %d", len(self.active_connections)
        )

    async def broadcast(self, data: dict[str, Any]) -> None:
        """Send data to all connected clients. Remove broken connections."""
        message = json.dumps(data)
        dead: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead.append(connection)
        for ws in dead:
            self.disconnect(ws)


# ── Global State ────────────────────────────────────────────────────────
manager = ConnectionManager()
DEFAULT_TRACK_TYPE = "ring"
DEFAULT_PROFILE_COUNTS = {
    "COMMUTER": 8,
    "FOLLOWER": 3,
    "CAUTIOUS": 3,
    "AGGRESSIVE": 2,
    "CAMPER": 1,
    "PACER": 1,
}

PRESETS: dict[str, dict[str, int]] = {
    "default": DEFAULT_PROFILE_COUNTS,
    "rush_hour": {
        "COMMUTER": 14,
        "AGGRESSIVE": 4,
        "CAUTIOUS": 4,
        "CAMPER": 2,
        "FOLLOWER": 2,
    },
    "autobahn": {
        "AGGRESSIVE": 5,
        "FOLLOWER": 5,
        "COMMUTER": 3,
    },
    "robotaxi": {
        "PACER": 16,
        "COMMUTER": 2,
    },
    "campers": {
        "CAMPER": 8,
        "COMMUTER": 4,
        "CAUTIOUS": 2,
    },
    "demolition": {
        "AGGRESSIVE": 10,
        "CAMPER": 4,
        "CAUTIOUS": 4,
    },
}

INITIAL_VEHICLE_COUNT = sum(DEFAULT_PROFILE_COUNTS.values())
TICK_RATE = 30  # ticks per second
DT = 1.0 / TICK_RATE


def create_track(track_type: str) -> RingRoad:
    """Create the active track topology."""
    # MergeRoad support is parked for now while ring-road behavior changes land.
    return RingRoad(
        circumference=DEFAULT_CIRCUMFERENCE_M,
        num_lanes=DEFAULT_NUM_LANES,
        lane_width=DEFAULT_LANE_WIDTH_M,
    )


road = create_track(DEFAULT_TRACK_TYPE)


class SimContext:
    speed_multiplier: int = 1

sim_context = SimContext()


def spawn_vehicles_evenly(profile_counts: dict[str, int]) -> None:
    """Spawn vehicles for a given mix with even lane-balanced spacing."""
    profiles = [
        profile
        for profile, count in profile_counts.items()
        for _ in range(count)
    ]
    if not profiles:
        return
    random.Random(7).shuffle(profiles)

    slots_per_lane = max(1, math.ceil(len(profiles) / road.num_lanes))
    longitudinal_spacing = road.circumference / slots_per_lane
    lane_phase_offset = longitudinal_spacing / road.num_lanes
    cruise_seed_speed = road.desired_speed * 0.88

    for idx, profile in enumerate(profiles):
        lane = idx % road.num_lanes
        slot = idx // road.num_lanes
        position = (slot * longitudinal_spacing + lane * lane_phase_offset) % road.circumference
        vehicle = road.add_vehicle(profile=profile, lane=lane, position=position)
        vehicle.velocity = min(vehicle.desired_speed, cruise_seed_speed)


def seed_initial_vehicles() -> None:
    """Spawn a realistic default traffic mix with even lane-balanced spacing."""
    spawn_vehicles_evenly(DEFAULT_PROFILE_COUNTS)


def build_road_payload() -> dict[str, Any]:
    """Serialize the currently active track layout."""
    return {
        "track_type": road.track_type,
        "circumference": road.circumference,
        "inner_radius": road.inner_radius,
        "straight_length": road.straight_length,
        "aux_lane_start": road.aux_lane_start,
        "merge_start": road.merge_start,
        "merge_end": road.merge_end,
        "num_lanes": road.num_lanes,
        "lane_width": road.lane_width,
        "speed_limit_mph": round(road.desired_speed * 2.23694, 1),
        "paused": road.paused,
    }

# ── Simulation Loop ────────────────────────────────────────────────────
async def simulation_loop() -> None:
    """Fixed-step game loop running at TICK_RATE TPS."""
    logger.info("Simulation loop started at %d TPS", TICK_RATE)

    # Seed initial vehicles
    seed_initial_vehicles()

    tick = 0
    while True:
        try:
            # 1. Advance physics via substepping to maintain numeric stability 
            # at high fast-forward multipliers
            for _ in range(sim_context.speed_multiplier):
                road.update(DT)

            # 2. Broadcast state to all clients
            if manager.active_connections:
                vehicle_states = road.get_state()
                telemetry = road.get_telemetry()
                payload = {
                    "type": "state",
                    "tick": tick,
                    "vehicles": vehicle_states,
                    "telemetry": telemetry,
                    "road": build_road_payload(),
                }
                await manager.broadcast(payload)

            tick += 1
        except Exception:
            logger.exception("CRITICAL: Error in simulation loop. Physics or Broadcast failed.")
            # Optional: Add a small delay to prevent rapid-fire log bombing if it stays broken
            await asyncio.sleep(1.0)
            
        await asyncio.sleep(DT)


# ── Application Lifespan ───────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the simulation loop on app startup, cancel on shutdown."""
    task = asyncio.create_task(simulation_loop())
    logger.info("Traffic simulation server started")
    yield
    task.cancel()
    logger.info("Traffic simulation server stopped")


# ── FastAPI App ─────────────────────────────────────────────────────────
app = FastAPI(
    title="Traffic Simulation Server",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Simple health endpoint."""
    return {"status": "ok", "vehicles": str(len(road.vehicles))}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for bidirectional communication.
    - Server → Client: vehicle state broadcasts (automatic via game loop)
    - Client → Server: configuration commands (density, aggression, etc.)
    """
    await manager.connect(websocket)
    try:
        while True:
            # Listen for config commands from the client
            raw = await websocket.receive_text()
            try:
                command = json.loads(raw)
                await handle_command(command)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from client: %s", raw[:100])
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        manager.disconnect(websocket)


async def handle_command(command: dict[str, Any]) -> None:
    """Process a configuration command from the frontend."""
    global road
    cmd_type = command.get("type", "")

    if cmd_type == "add_profile":
        profile = command.get("profile", "COMMUTER")
        road.add_vehicle(profile=profile)
        logger.info("Spawned 1 %s", profile)

    elif cmd_type == "remove_profile":
        profile = command.get("profile", "COMMUTER")
        road.remove_vehicle_by_profile(profile)
        logger.info("Removed 1 %s", profile)
        
    elif cmd_type == "remove_all_profiles":
        road.clear_vehicles()
        logger.info("Removed all vehicles")

    elif cmd_type == "speed_limit":
        # Adjust speed limit from mph -> m/s
        value = max(10, min(150, float(command.get("value", 65))))
        speed_kmh = value * 1.60934
        road.set_speed_limit(speed_kmh)
        logger.info("Speed limit set to %.0f mph", value)

    elif cmd_type == "num_lanes":
        value = max(1, min(6, int(command.get("value", 2))))
        road.set_num_lanes(value)
        logger.info("Lanes set to %d", value)

    elif cmd_type == "circumference":
        # Value arrives as circumference in feet, convert to meters for physics 
        value_ft = float(command.get("value", 500.0))
        value_m = max(50.0, min(5000.0, value_ft * 0.3048))
        road.set_circumference(value_m)
        logger.info("Circumference set to %.1f m (%.1f ft)", value_m, value_ft)

    elif cmd_type == "toggle_pause":
        road.toggle_pause()
        logger.info("Paused state toggled to %s", road.paused)

    elif cmd_type == "set_sim_speed":
        value = max(1, min(20, int(command.get("value", 1))))
        sim_context.speed_multiplier = value
        logger.info("Simulation speed multiplied to %dx", value)

    elif cmd_type == "set_track_type":
        logger.info("Track switching is temporarily disabled; keeping %s", road.track_type)

    elif cmd_type == "reset_simulation":
        road.reset()
        sim_context.speed_multiplier = 1
        seed_initial_vehicles()
        logger.info("Simulation reset to %s defaults", road.track_type)

    elif cmd_type == "apply_preset":
        preset = str(command.get("preset", "default"))
        counts = PRESETS.get(preset)
        if counts is None:
            logger.warning("Unknown preset: %s", preset)
            return
        road.clear_vehicles()
        spawn_vehicles_evenly(counts)
        logger.info("Applied preset: %s (%d vehicles)", preset, sum(counts.values()))

    elif cmd_type == "cause_incident":
        if not road.vehicles:
            logger.info("No vehicles to trigger incident on")
            return
        target = random.choice(road.vehicles)
        target.trigger_incident(duration=3.0)
        logger.info("Incident on vehicle %d (%s, lane %d)", target.id, target.profile, target.lane)

    else:
        logger.warning("Unknown command type: %s", cmd_type)


# ── Entry Point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
