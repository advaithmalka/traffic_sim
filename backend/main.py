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
ring_road = RingRoad(
    circumference=DEFAULT_CIRCUMFERENCE_M,
    num_lanes=DEFAULT_NUM_LANES,
    lane_width=DEFAULT_LANE_WIDTH_M,
)

DEFAULT_PROFILES = ("COMMUTER", "AGGRESSIVE", "CAMPER", "CAUTIOUS", "FOLLOWER", "PACER")
DEFAULT_PROFILE_COPIES = 3
INITIAL_VEHICLE_COUNT = len(DEFAULT_PROFILES) * DEFAULT_PROFILE_COPIES
TICK_RATE = 30  # ticks per second
DT = 1.0 / TICK_RATE

class SimContext:
    speed_multiplier: int = 1

sim_context = SimContext()


def seed_initial_vehicles() -> None:
    """Spawn the default cohort with even lane-balanced spacing."""
    profiles = [profile for _ in range(DEFAULT_PROFILE_COPIES) for profile in DEFAULT_PROFILES]
    random.Random(7).shuffle(profiles)

    slots_per_lane = max(1, math.ceil(len(profiles) / ring_road.num_lanes))
    longitudinal_spacing = ring_road.circumference / slots_per_lane
    lane_phase_offset = longitudinal_spacing / ring_road.num_lanes
    cruise_seed_speed = ring_road.desired_speed * 0.88

    for idx, profile in enumerate(profiles):
        lane = idx % ring_road.num_lanes
        slot = idx // ring_road.num_lanes
        position = (slot * longitudinal_spacing + lane * lane_phase_offset) % ring_road.circumference
        vehicle = ring_road.add_vehicle(profile=profile, lane=lane, position=position)
        vehicle.velocity = min(vehicle.desired_speed, cruise_seed_speed)

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
                ring_road.update(DT)

            # 2. Broadcast state to all clients
            if manager.active_connections:
                vehicle_states = ring_road.get_state()
                telemetry = ring_road.get_telemetry()
                payload = {
                    "type": "state",
                    "tick": tick,
                    "vehicles": vehicle_states,
                    "telemetry": telemetry,
                    "road": {
                        "circumference": ring_road.circumference,
                        "inner_radius": ring_road.inner_radius,
                        "num_lanes": ring_road.num_lanes,
                        "lane_width": ring_road.lane_width,
                        "speed_limit_mph": round(ring_road.desired_speed * 2.23694, 1),
                        "paused": ring_road.paused,
                    },
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
    return {"status": "ok", "vehicles": str(len(ring_road.vehicles))}


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
    cmd_type = command.get("type", "")

    if cmd_type == "add_profile":
        profile = command.get("profile", "COMMUTER")
        ring_road.add_vehicle(profile=profile)
        logger.info("Spawned 1 %s", profile)

    elif cmd_type == "remove_profile":
        profile = command.get("profile", "COMMUTER")
        ring_road.remove_vehicle_by_profile(profile)
        logger.info("Removed 1 %s", profile)
        
    elif cmd_type == "remove_all_profiles":
        ring_road.clear_vehicles()
        logger.info("Removed all vehicles")

    elif cmd_type == "speed_limit":
        # Adjust speed limit from mph -> m/s
        value = max(10, min(150, float(command.get("value", 65))))
        speed_kmh = value * 1.60934
        ring_road.set_speed_limit(speed_kmh)
        logger.info("Speed limit set to %.0f mph", value)

    elif cmd_type == "num_lanes":
        value = max(1, min(6, int(command.get("value", 2))))
        ring_road.set_num_lanes(value)
        logger.info("Lanes set to %d", value)

    elif cmd_type == "circumference":
        # Value arrives as circumference in feet, convert to meters for physics 
        value_ft = float(command.get("value", 500.0))
        value_m = max(50.0, min(5000.0, value_ft * 0.3048))
        ring_road.set_circumference(value_m)
        logger.info("Circumference set to %.1f m (%.1f ft)", value_m, value_ft)

    elif cmd_type == "toggle_pause":
        ring_road.toggle_pause()
        logger.info("Paused state toggled to %s", ring_road.paused)

    elif cmd_type == "set_sim_speed":
        value = max(1, min(20, int(command.get("value", 1))))
        sim_context.speed_multiplier = value
        logger.info("Simulation speed multiplied to %dx", value)

    elif cmd_type == "reset_simulation":
        ring_road.reset()
        sim_context.speed_multiplier = 1
        seed_initial_vehicles()
        logger.info("Simulation reset to defaults")

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
