import { useState, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Sky } from '@react-three/drei';
import * as THREE from 'three';
import { Car } from './Car';
import { RingRoadMesh } from './RingRoadMesh';
import type { VehicleData, RoadData } from '../types';

interface SceneProps {
  vehiclesRef: React.MutableRefObject<VehicleData[]>;
  road: RoadData | null;
}

/**
 * Inner scene content — must be inside <Canvas>
 */
function SceneContent({ vehiclesRef, road }: SceneProps) {
  const [vehicleConfigs, setVehicleConfigs] = useState<{ id: number; color: string; profile: string }[]>([]);

  // Poll vehicle IDs periodically (low frequency) to create/remove Car components
  useEffect(() => {
    const interval = setInterval(() => {
      const current = vehiclesRef.current;
      setVehicleConfigs((prev) => {
        // Only update if the set of IDs actually changed
        const prevIds = new Set(prev.map((v) => v.id));
        const currentIds = new Set(current.map((v) => v.id));

        if (
          prevIds.size === currentIds.size &&
          [...prevIds].every((id) => currentIds.has(id))
        ) {
          return prev;
        }

        return current.map((v) => ({ id: v.id, color: v.color, profile: v.profile }));
      });
    }, 500);

    return () => clearInterval(interval);
  }, [vehiclesRef]);

  return (
    <>
      {/* Camera controls */}
      <OrbitControls
        enablePan
        enableZoom
        enableRotate
        maxPolarAngle={Math.PI / 2.2}
        minDistance={20}
        maxDistance={300}
        target={[0, 0, 0]}
      />

      {/* Lighting */}
      <ambientLight intensity={0.8} color="#aaccff" />
      <directionalLight
        position={[50, 80, 30]}
        intensity={1.5}
        color="#ffffff"
      />
      <hemisphereLight
        args={['#6688cc', '#335522', 0.6]}
      />

      {/* Sky / environment */}
      <Sky distance={450000} sunPosition={[50, 80, 30]} inclination={0} azimuth={0.25} />
      <fog attach="fog" args={['#87ceeb', 300, 1000]} />

      {/* Road */}
      {road && <RingRoadMesh road={road} />}

      {/* Vehicles */}
      {vehicleConfigs.map(({ id, color, profile }) => (
        <Car
          key={id}
          vehicleId={id}
          vehiclesRef={vehiclesRef}
          color={color}
          profile={profile}
        />
      ))}
    </>
  );
}

/**
 * Main 3D scene component with Canvas wrapper.
 */
export function Scene({ vehiclesRef, road }: SceneProps) {
  return (
    <Canvas
      camera={{
        position: [0, 120, 120],
        fov: 45,
        near: 0.1,
        far: 1000,
      }}
      gl={{
        antialias: true,
        toneMapping: THREE.ACESFilmicToneMapping,
        toneMappingExposure: 1.2,
      }}
      style={{ width: '100%', height: '100%' }}
    >
      <SceneContent vehiclesRef={vehiclesRef} road={road} />
    </Canvas>
  );
}
