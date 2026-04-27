import React, { useRef, useMemo, Suspense, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { useGLTF, Html } from '@react-three/drei';
import * as THREE from 'three';
import type { VehicleData } from '../types';



const MODEL_PATH = '/models/car_low_poly_style.glb';

// Preload the model
useGLTF.preload(MODEL_PATH);

interface CarProps {
  vehicleId: number;
  vehiclesRef: React.MutableRefObject<VehicleData[]>;
  color: string;
  profile: string;
}

/**
 * A single car in the 3D scene using a loaded GLB model.
 * Reads position from the shared ref every frame (imperative, no re-renders).
 *
 * Coordinate mapping:
 *   Backend sends (x, y) in the math plane. In Three.js:
 *     Three.js X = backend x
 *     Three.js Z = backend y  (ground plane is X/Z)
 *   The backend rotation is the tangent angle in the math x/y plane (counter-clockwise from +x).
 *   In Three.js, rotation.y rotates around the Y (up) axis.
 *   A rotation of 0 in the backend means the car moves along +x.
 *   We negate because Three.js Y-rotation is clockwise when viewed from above.
 */
function CarInner({ vehicleId, vehiclesRef, color, profile }: CarProps) {
  const [hovered, setHovered] = useState(false);
  const groupRef = useRef<THREE.Group>(null);
  const bodyMatsRef = useRef<THREE.MeshStandardMaterial[]>([]);
  const gapLabelRef = useRef<HTMLSpanElement>(null);
  const gapBarRef = useRef<HTMLDivElement>(null);
  const brakeLightLeftRef = useRef<THREE.PointLight>(null);
  const brakeLightRightRef = useRef<THREE.PointLight>(null);

  // Load the GLB model
  const { scene } = useGLTF(MODEL_PATH);

  // Clone the scene so each car gets its own instance
  const clonedScene = useMemo(() => {
    const clone = scene.clone(true);
    const c = new THREE.Color(color || '#ffffff');
    // Reset standard materials cache
    bodyMatsRef.current = [];

    clone.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const mesh = child as THREE.Mesh;
        if (mesh.material) {
          if (Array.isArray(mesh.material)) {
            mesh.material = mesh.material.map((m) => m.clone());
          } else {
            mesh.material = mesh.material.clone();
            const mat = mesh.material as THREE.MeshStandardMaterial;
            if (mat.color) {
              // Only tint materials that are significantly lit and not transparent
              // (This preserves pitch-black tires and glass windows while wrapping the body)
              if (mat.color.getHex() > 0x333333 && !mat.transparent) {
                mat.color.copy(c); // 100% exact profile skin color mapping
                bodyMatsRef.current.push(mat);
              }
            }
          }
        }
      }
    });
    return clone;
  }, [scene, color]);

  useFrame(() => {
    if (!groupRef.current) return;

    const vehicle = vehiclesRef.current.find((v) => v.id === vehicleId);
    if (!vehicle) {
      groupRef.current.visible = false;
      return;
    }

    groupRef.current.visible = true;

    groupRef.current.position.set(vehicle.x, 0, vehicle.y);
    groupRef.current.rotation.set(0, -vehicle.rotation + Math.PI / 2, 0);

    // Update Brake Light dynamically (both rear taillights)
    const accel = vehicle.acceleration || 0.0;
    const brakeIntensity = accel < -0.5 ? 8.0 : 0.0;
    if (brakeLightLeftRef.current) brakeLightLeftRef.current.intensity = brakeIntensity;
    if (brakeLightRightRef.current) brakeLightRightRef.current.intensity = brakeIntensity;

    // High-frequency UI Label DOM manual updates
    const safeGap = vehicle.gap || 0.0;
    if (gapLabelRef.current) {
      gapLabelRef.current.innerText = `${safeGap.toFixed(1)}m`;
    }
    if (gapBarRef.current) {
      const pct = Math.max(0, Math.min(100, (safeGap / 35.0) * 100));
      gapBarRef.current.style.width = `${pct}%`;
      gapBarRef.current.style.background = safeGap < 8.0 ? '#ef4444' : safeGap < 15.0 ? '#f59e0b' : '#10b981';
    }
  });

  return (
    <group
      ref={groupRef}
      onPointerOver={(e) => {
        e.stopPropagation();
        setHovered(true);
      }}
      onPointerOut={() => {
        setHovered(false);
      }}
    >
      <primitive object={clonedScene} scale={0.010} />
      {/* Rear taillights — local +Z is forward, so back-of-car sits at -Z */}
      <pointLight ref={brakeLightLeftRef} position={[-0.5, 1, -1.9]} color="#ff0101" decay={2} distance={6} intensity={0} />
      <pointLight ref={brakeLightRightRef} position={[0.5, 1, -1.9]} color="#ff0101" decay={2} distance={6} intensity={0} />
      {hovered && (
        <Html position={[0, 4.5, 0]} center zIndexRange={[100, 0]} style={{ pointerEvents: 'none' }}>
          <div style={{
            background: 'rgba(10, 15, 30, 0.85)', backdropFilter: 'blur(4px)',
            padding: '6px 10px', borderRadius: '6px', border: `1px solid ${color}`,
            color: 'white', display: 'flex', flexDirection: 'column', alignItems: 'center',
            gap: '6px', transform: 'scale(0.8)', minWidth: '90px'
          }}>
            <span style={{ fontSize: '11px', fontWeight: 800, letterSpacing: '0.05em', color }}>{profile}</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '100%' }}>
              <div style={{ flex: 1, height: '4px', background: 'rgba(255, 255, 255, 0.1)', borderRadius: '2px', overflow: 'hidden' }}>
                <div ref={gapBarRef} style={{ height: '100%', width: '0%', background: '#10b981' }} />
              </div>
              <span ref={gapLabelRef} style={{ fontSize: '10px', width: '28px', textAlign: 'right', fontFamily: 'monospace' }}>--m</span>
            </div>
          </div>
        </Html>
      )}
    </group>
  );
}

/**
 * Wrapper with Suspense fallback for model loading.
 */
export function Car(props: CarProps) {
  return (
    <Suspense fallback={null}>
      <CarInner {...props} />
    </Suspense>
  );
}
