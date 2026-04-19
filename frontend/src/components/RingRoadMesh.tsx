import { useMemo } from 'react';
import * as THREE from 'three';
import type { RoadData } from '../types';

interface RingRoadMeshProps {
  road: RoadData;
}

/**
 * 3D ring road with lane markings, rendered as concentric torus geometries.
 */
export function RingRoadMesh({ road }: RingRoadMeshProps) {
  const { inner_radius, num_lanes, lane_width } = road;

  // Road surface material
  const roadMaterial = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: '#44445a',
        roughness: 0.9,
        metalness: 0.1,
        side: THREE.DoubleSide,
      }),
    []
  );

  // Lane marking material
  const markingMaterial = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: '#e2e8f0',
        emissive: '#e2e8f0',
        emissiveIntensity: 0.3,
        roughness: 0.5,
      }),
    []
  );

  // Edge line material
  const edgeMaterial = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: '#fbbf24',
        emissive: '#fbbf24',
        emissiveIntensity: 0.2,
        roughness: 0.5,
      }),
    []
  );

  // Road surface — flat torus (ring)
  const roadGeometries = useMemo(() => {
    const totalWidth = num_lanes * lane_width;
    const outerR = inner_radius + totalWidth;
    const ringShape = new THREE.Shape();
    // Outer circle
    ringShape.absarc(0, 0, outerR, 0, Math.PI * 2, false);
    // Inner circle (hole)
    const holePath = new THREE.Path();
    holePath.absarc(0, 0, inner_radius, 0, Math.PI * 2, true);
    ringShape.holes.push(holePath);

    return new THREE.ShapeGeometry(ringShape, 96);
  }, [inner_radius, num_lanes, lane_width]);

  // Dashed lane markings
  const dashSegments = 60;
  const dashLength = 0.4; // fraction of segment that is visible
  const dashes = useMemo(() => {
    const items: { x: number; z: number; angle: number }[] = [];
    for (let i = 0; i < dashSegments; i++) {
      const visibleFraction = dashLength;
      const theta = (i / dashSegments) * Math.PI * 2;
      const endTheta = ((i + visibleFraction) / dashSegments) * Math.PI * 2;
      const midTheta = (theta + endTheta) / 2;
      items.push({
        x: Math.cos(midTheta),
        z: Math.sin(midTheta),
        angle: midTheta,
      });
    }
    return items;
  }, []);

  return (
    <group>
      {/* Road surface */}
      <mesh
        geometry={roadGeometries}
        material={roadMaterial}
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, 0, 0]}
      />

      {/* Lane divider markings (between lanes) */}
      {Array.from({ length: num_lanes - 1 }, (_, laneIdx) => {
        const markRadius = inner_radius + (laneIdx + 1) * lane_width;
        return dashes.map((dash, i) => (
          <mesh
            key={`mark-${laneIdx}-${i}`}
            material={markingMaterial}
            position={[
              dash.x * markRadius,
              0.1,
              dash.z * markRadius,
            ]}
            rotation={[0, -dash.angle + Math.PI / 2, 0]}
          >
            <boxGeometry
              args={[
                (2 * Math.PI * markRadius * dashLength) / dashSegments,
                0.01,
                0.12,
              ]}
            />
          </mesh>
        ));
      })}

      {/* Inner edge line (solid yellow) */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.1, 0]}>
        <ringGeometry args={[inner_radius - 0.08, inner_radius + 0.08, 96]} />
        <meshStandardMaterial {...edgeMaterial} side={THREE.DoubleSide} />
      </mesh>

      {/* Outer edge line (solid yellow) */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.1, 0]}>
        <ringGeometry
          args={[
            inner_radius + num_lanes * lane_width - 0.08,
            inner_radius + num_lanes * lane_width + 0.08,
            96,
          ]}
        />
        <meshStandardMaterial {...edgeMaterial} side={THREE.DoubleSide} />
      </mesh>

      {/* Ground plane */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -2, 0]}>
        <circleGeometry args={[inner_radius + num_lanes * lane_width + 40, 64]} />
        <meshStandardMaterial color="#2d3748" roughness={1} />
      </mesh>

      {/* Inner grass/terrain */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1, 0]}>
        <circleGeometry args={[inner_radius - 0.3, 64]} />
        <meshStandardMaterial color="#385822" roughness={1} />
      </mesh>
    </group>
  );
}
