import sys
import traceback

sys.path.append('.')
from simulation.ring_road import RingRoad

try:
    rr = RingRoad(num_lanes=3, circumference=500, )
    for _ in range(10):
        rr.add_vehicle("COMMUTER")
    for _ in range(5):
        rr.add_vehicle("FOLLOWER")
    
    print("Simulating 100 ticks...")
    for _ in range(100):
        rr.update(0.1)
    print("Success")
except Exception as e:
    traceback.print_exc()

