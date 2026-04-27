# Multi-Agent Traffic Simulator

A real-time, 3D traffic simulator where every car is an independent agent driving by the **Improved Intelligent Driver Model (IIDM)** and **asymmetric MOBIL** lane-change logic — the same physics models used in academic traffic engineering research. Six driver personalities share a configurable ring road, and the resulting interactions reproduce the phantom traffic jams, shockwaves, and capacity collapses you see on real highways.

The backend runs a fixed-step physics loop in Python and streams state over WebSockets at 30 ticks per second. The frontend renders the scene in React + Three.js and provides live controls over driver mix, road geometry, and time scale.

## Stack

**Backend** — Python 3.11+, FastAPI, WebSockets, asyncio. Strict OOP, no ML libraries; the simulation is pure first-principles physics.

**Frontend** — React 19, Vite, TypeScript, `@react-three/fiber`, `@react-three/drei`, Recharts, Tailwind CSS. The hot path uses refs (not React state) so 30 Hz position updates do not trigger re-renders.

## Physics

Each vehicle samples its IIDM parameters from a profile-specific Gaussian (so two "Commuters" never drive identically), then on every tick:

1. Computes free-road acceleration `a_free = a · (1 − (v/v₀)ⁿ)`.
2. If a lead vehicle exists, computes the desired dynamic gap `s* = s₀ + max(0, vT + (v·Δv)/(2√(a·b)))` and blends with `a_free` via the IIDM piecewise formulation (Treiber/Kesting) — strictly stable in the v→v₀ limit, unlike the original IDM.
3. Evaluates **asymmetric MOBIL** lane-change criteria: `Δa_self + p · (Δa_old_follower + Δa_new_follower) > Δa_threshold`, with profile-specific bias toward right or left lanes and a hard safety constraint on follower deceleration.
4. Integrates ballistically with a predictive stopping heuristic to avoid overshoot when `v_next < 0`.

Speed cap is 80 m/s (~180 mph). Lane changes have a 3-second cooldown.

## Driver Profiles

| Profile | Behavior |
|---|---|
| **Commuter** (gray) | Baseline: speed-limit cruise, standard following distance, predictable. |
| **Weaver** (red) | High-speed, tailgating, aggressive lane changes — the source of most phantom jams. |
| **Left Camper** (purple) | Sits in the passing lane at the limit, refuses to yield. |
| **Cautious** (yellow) | Below-limit speed, large gaps, reluctant to change lanes. |
| **Pass & Return** (blue) | Treats the left lane strictly as a passing zone, returns right when clear. |
| **Auto Pacer** (green) | Algorithmic agent with cooperative platooning — absorbs upstream shockwaves to keep flow continuous. |

Each profile has independently tuned `(v_mult, T, s₀, a, b, politeness, lane-bias)` and several emergent behaviors layered on top (slow-lead headway compression for Weavers, cooperative gap-tightening for paired Pacers, etc.).

## Features

- **Live telemetry** — average speed, flow rate (veh/h), density (veh/mi), per-profile counts, with a rolling 60-second chart.
- **Driver-mix presets** — one-click scenarios (Rush Hour, Autobahn, Robotaxi Future, Lane Blockade, Demolition, Default).
- **Cause Incident** — picks a random vehicle and forces a 3-second hard brake. Watch the shockwave propagate backwards through the pack in real time.
- **Environment controls** — adjustable lane count (1–6), lap length (400–3000 ft), and speed limit (15–150 mph).
- **Time controls** — pause, and 1×/2×/5×/10× fast-forward via physics substepping (numerically stable at all speeds).
- **3D scene** — orbit-controlled camera, GLB car models tinted per profile, dynamic taillights that fire on hard deceleration, hover tooltips with live gap telemetry per car.
- **Onboarding modal** — first-load welcome guide, re-openable by clicking the dashboard title.

## Running locally

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The simulation loop starts immediately on boot at 30 TPS. WebSocket endpoint is `ws://localhost:8000/ws`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend auto-reconnects if the backend restarts.

### Tests

```bash
cd backend
source venv/bin/activate
python -m unittest discover -v
```

Covers IIDM following behavior, MOBIL lane changes, pacer flow contributions, and incident-trigger physics.

## Architecture notes

- **Why refs instead of state for vehicle positions**: at 30 Hz × 30 vehicles, calling `setState` would saturate React's reconciler. The WebSocket handler writes directly into a `useRef` array; each `<Car>` reads from that ref inside `useFrame` and mutates `THREE.Group` transforms imperatively. The IDs of the vehicle set are polled at 2 Hz to mount/unmount cars — that's the only re-render path.
- **Why IIDM over IDM**: the original IDM has a discontinuity at `v = v₀` that produces unrealistic micro-oscillations under near-saturated conditions. The Treiber/Kesting piecewise reformulation eliminates this without changing free-flow or congested behavior.
- **Why asymmetric MOBIL**: U.S./European keep-right rules require an explicit lane-bias term, otherwise the symmetric MOBIL settles into either-lane equilibria that look unrealistic.

## Project layout

```
backend/
  main.py                      # FastAPI app, command handlers, sim loop
  simulation/
    ring_road.py               # Topology + per-tick orchestration + MOBIL evaluation
    vehicle.py                 # IIDM physics, profile parameters, incident state
    merge_road.py              # (parked) merge-zone topology
  test_*.py                    # Unit tests
frontend/
  src/
    hooks/useSimulation.ts     # WebSocket lifecycle + telemetry throttling
    components/
      Scene.tsx                # R3F canvas + lighting + sky
      Car.tsx                  # Per-vehicle 3D model + taillights + hover tooltip
      RingRoadMesh.tsx         # Procedural road geometry
    ui/
      Dashboard.tsx            # Glassmorphic control panel + telemetry
      OnboardingModal.tsx      # Welcome modal
      Slider.tsx, TelemetryChart.tsx
    types.ts                   # Shared frontend types
```

## License

MIT.
