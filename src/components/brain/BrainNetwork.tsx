// ═══════════════════════════════════════════════════════════════════
// BrainNetwork — شبكة الأدمغة ثلاثية الأبعاد
// Three.js 3D visualization of 5 brain nodes connected by synapses
// Uses @react-three/fiber + @react-three/drei
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useRef, useMemo, useEffect, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, Text, Line } from '@react-three/drei';
import * as THREE from 'three';
import gsap from 'gsap';

// ─── Theme ─────────────────────────────────────────────────────

const BRAIN_COLORS: Record<string, string> = {
  neural: '#00e5ff',
  causal: '#ff9100',
  symbolic: '#448aff',
  bayesian: '#69f0ae',
  world_model: '#ffd740',
};

const BRAIN_NAMES: Record<string, string> = {
  neural: 'العصبي',
  causal: 'السببي',
  symbolic: 'الرمزي',
  bayesian: 'البيزي',
  world_model: 'العالمي',
};

// ─── Brain Node Positions (pentagon layout) ────────────────────

const BRAIN_IDS = ['neural', 'causal', 'symbolic', 'bayesian', 'world_model'];

function getBrainPosition(index: number): [number, number, number] {
  const angle = (index / 5) * Math.PI * 2 - Math.PI / 2;
  const radius = 2.2;
  return [Math.cos(angle) * radius, Math.sin(angle) * radius, 0];
}

// ─── Brain Sphere Component ────────────────────────────────────

interface BrainSphereProps {
  brainId: string;
  position: [number, number, number];
  isActive: boolean;
  confidence: number;
  onClick: (id: string) => void;
}

function BrainSphere({ brainId, position, isActive, confidence, onClick }: BrainSphereProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const glowRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);
  const color = BRAIN_COLORS[brainId] || '#ffffff';

  useFrame((state) => {
    if (!meshRef.current) return;
    const t = state.clock.getElapsedTime();

    // Breathing animation for active brains
    if (isActive) {
      const breathe = 1 + 0.08 * Math.sin(t * 2 + BRAIN_IDS.indexOf(brainId));
      meshRef.current.scale.setScalar(breathe);
    } else {
      meshRef.current.scale.setScalar(0.85);
    }

    // Slow rotation
    meshRef.current.rotation.y = t * 0.3;
    meshRef.current.rotation.x = Math.sin(t * 0.2) * 0.1;

    // Glow pulsing
    if (glowRef.current) {
      const glowScale = isActive
        ? 1.8 + 0.3 * Math.sin(t * 3)
        : 1.3 + 0.1 * Math.sin(t * 1.5);
      glowRef.current.scale.setScalar(glowScale);
    }
  });

  const geometry = useMemo(() => {
    switch (brainId) {
      case 'neural': return <icosahedronGeometry args={[0.4, 2]} />;
      case 'causal': return <octahedronGeometry args={[0.4, 1]} />;
      case 'symbolic': return <dodecahedronGeometry args={[0.4, 0]} />;
      case 'bayesian': return <sphereGeometry args={[0.4, 16, 16]} />;
      case 'world_model': return <torusKnotGeometry args={[0.3, 0.12, 64, 8]} />;
      default: return <sphereGeometry args={[0.4, 16, 16]} />;
    }
  }, [brainId]);

  return (
    <group position={position}>
      {/* Glow sphere */}
      <mesh ref={glowRef}>
        <sphereGeometry args={[0.5, 16, 16]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={isActive ? 0.12 : 0.04}
        />
      </mesh>

      {/* Main brain mesh */}
      <mesh
        ref={meshRef}
        onClick={() => onClick(brainId)}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        {geometry}
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={isActive ? 0.5 : hovered ? 0.3 : 0.1}
          transparent
          opacity={isActive ? 0.9 : 0.6}
          wireframe={brainId === 'symbolic'}
          roughness={0.3}
          metalness={0.7}
        />
      </mesh>

      {/* Label */}
      <Text
        position={[0, -0.7, 0]}
        fontSize={0.18}
        color={isActive ? '#ffffff' : '#8899aa'}
        anchorX="center"
        anchorY="middle"
        font={undefined}
      >
        {BRAIN_NAMES[brainId]}
      </Text>

      {/* Confidence indicator */}
      {isActive && confidence > 0 && (
        <Text
          position={[0, 0.65, 0]}
          fontSize={0.14}
          color={color}
          anchorX="center"
          anchorY="middle"
          font={undefined}
        >
          {Math.round(confidence * 100)}%
        </Text>
      )}
    </group>
  );
}

// ─── Instanced Particles for Synapse ──────────────────────────
// Uses a single InstancedMesh for ALL synapse particles across
// ALL connections — massive performance improvement vs per-connection instancing

const TOTAL_PARTICLES_PER_CONN = 6;

function AllSynapseParticles({ connections, activeBrains, brainPositions }: {
  connections: Array<{ from: number; to: number }>;
  activeBrains: string[];
  brainPositions: Array<[number, number, number]>;
}) {
  const totalParticles = connections.length * TOTAL_PARTICLES_PER_CONN;
  const instRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  useFrame((state) => {
    if (!instRef.current) return;
    const t = state.clock.getElapsedTime();
    let idx = 0;

    for (let ci = 0; ci < connections.length; ci++) {
      const conn = connections[ci];
      const fromPos = conn.from >= 0 ? brainPositions[conn.from] : [0, 0, 0] as [number, number, number];
      const toPos = conn.to >= 0 ? brainPositions[conn.to] : [0, 0, 0] as [number, number, number];
      const isActiveConn = conn.from >= 0 && conn.to >= 0
        ? activeBrains.includes(BRAIN_IDS[conn.from]) || activeBrains.includes(BRAIN_IDS[conn.to])
        : conn.from >= 0
          ? activeBrains.includes(BRAIN_IDS[conn.from])
          : true;

      for (let i = 0; i < TOTAL_PARTICLES_PER_CONN; i++) {
        if (isActiveConn) {
          const progress = ((t * 0.5 + i / TOTAL_PARTICLES_PER_CONN) % 1);
          const x = fromPos[0] + (toPos[0] - fromPos[0]) * progress;
          const y = fromPos[1] + (toPos[1] - fromPos[1]) * progress + Math.sin(progress * Math.PI) * 0.3;
          const z = fromPos[2] + (toPos[2] - fromPos[2]) * progress;
          dummy.position.set(x, y, z);
          dummy.scale.setScalar(0.04 + 0.02 * Math.sin(t * 3 + i));
        } else {
          dummy.position.set(0, 0, -100); // Hide inactive particles far away
          dummy.scale.setScalar(0.001);
        }
        dummy.updateMatrix();
        instRef.current.setMatrixAt(idx, dummy.matrix);
        idx++;
      }
    }
    instRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={instRef} args={[undefined, undefined, totalParticles]}>
      <sphereGeometry args={[0.04, 6, 6]} />
      <meshBasicMaterial color="#00e5ff" transparent opacity={0.7} />
    </instancedMesh>
  );
}

// ─── Center Core ───────────────────────────────────────────────

function CenterCore({ vitality }: { vitality: number }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (meshRef.current) {
      const breathe = 1 + 0.05 * Math.sin(t * 1.5);
      meshRef.current.scale.setScalar(breathe);
      meshRef.current.rotation.y = t * 0.2;
    }
    if (ringRef.current) {
      ringRef.current.rotation.z = t * 0.4;
    }
  });

  return (
    <group position={[0, 0, 0]}>
      <mesh ref={meshRef}>
        <sphereGeometry args={[0.5, 32, 32]} />
        <meshStandardMaterial
          color="#0d7bb5"
          emissive="#0d7bb5"
          emissiveIntensity={0.3}
          transparent
          opacity={0.4}
        />
      </mesh>

      {/* Rotating ring */}
      <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.7, 0.02, 8, 64]} />
        <meshBasicMaterial color="#0a9b8a" transparent opacity={0.4} />
      </mesh>

      {/* Vitality text */}
      <Text
        position={[0, 0, 0.55]}
        fontSize={0.16}
        color="#0a9b8a"
        anchorX="center"
        anchorY="middle"
        font={undefined}
      >
        {Math.round(vitality)}%
      </Text>
    </group>
  );
}

// ─── Scene ─────────────────────────────────────────────────────

interface BrainSceneProps {
  activeBrains: string[];
  brainConfidences: Record<string, number>;
  onBrainClick: (id: string) => void;
  vitality: number;
}

function BrainScene({ activeBrains, brainConfidences, onBrainClick, vitality }: BrainSceneProps) {
  const groupRef = useRef<THREE.Group>(null);

  // GSAP transitions when active brains change
  useEffect(() => {
    if (!groupRef.current) return;
    gsap.to(groupRef.current.rotation, {
      y: groupRef.current.rotation.y + 0.1,
      duration: 0.5,
      ease: 'power2.out',
    });
  }, [activeBrains]);

  // Brain positions as array for instanced particles
  const brainPositions = useMemo(() =>
    BRAIN_IDS.map((_, i) => getBrainPosition(i)),
  []);

  // Connections: each brain connects to center + neighbors
  const connections = useMemo(() => {
    const conns: Array<{ from: number; to: number }> = [];
    // All brains to center
    for (let i = 0; i < 5; i++) {
      conns.push({ from: i, to: -1 }); // -1 = center
    }
    // Adjacent brains
    for (let i = 0; i < 5; i++) {
      conns.push({ from: i, to: (i + 1) % 5 });
    }
    // Cross connections
    conns.push({ from: 0, to: 2 });
    conns.push({ from: 1, to: 3 });
    conns.push({ from: 2, to: 4 });
    return conns;
  }, []);

  // Pre-compute connection lines (static geometry)
  const connectionLines = useMemo(() => {
    return connections.map((conn) => {
      const fromPos = conn.from >= 0 ? brainPositions[conn.from] : [0, 0, 0] as [number, number, number];
      const toPos = conn.to >= 0 ? brainPositions[conn.to] : [0, 0, 0] as [number, number, number];
      const midPoint: [number, number, number] = [
        (fromPos[0] + toPos[0]) / 2,
        (fromPos[1] + toPos[1]) / 2 + 0.3,
        (fromPos[2] + toPos[2]) / 2,
      ];
      const curve = new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(...fromPos),
        new THREE.Vector3(...midPoint),
        new THREE.Vector3(...toPos),
      );
      const points = curve.getPoints(20).map(p => [p.x, p.y, p.z] as [number, number, number]);
      const isActiveConn = conn.from >= 0 && conn.to >= 0
        ? activeBrains.includes(BRAIN_IDS[conn.from]) || activeBrains.includes(BRAIN_IDS[conn.to])
        : conn.from >= 0
          ? activeBrains.includes(BRAIN_IDS[conn.from])
          : true;
      return { points, active: isActiveConn, fromId: conn.from, toId: conn.to };
    });
  }, [connections, brainPositions, activeBrains]);

  return (
    <>
      <ambientLight intensity={0.3} />
      <pointLight position={[5, 5, 5]} intensity={0.8} color="#0d7bb5" />
      <pointLight position={[-5, -5, 3]} intensity={0.4} color="#0a9b8a" />

      <group ref={groupRef}>
        {/* Center core */}
        <CenterCore vitality={vitality} />

        {/* Brain nodes */}
        {BRAIN_IDS.map((id, i) => {
          const pos = getBrainPosition(i);
          const isActive = activeBrains.includes(id);
          return (
            <BrainSphere
              key={id}
              brainId={id}
              position={pos}
              isActive={isActive}
              confidence={brainConfidences[id] || 0}
              onClick={onBrainClick}
            />
          );
        })}

        {/* Connection lines (lightweight) */}
        {connectionLines.map((line, i) => (
          <Line
            key={`line-${i}`}
            points={line.points}
            color={line.active ? (BRAIN_COLORS[BRAIN_IDS[line.fromId]] || '#0d7bb5') : '#1a2a3a'}
            lineWidth={line.active ? 1.5 : 0.3}
            transparent
            opacity={line.active ? 0.5 : 0.1}
          />
        ))}

        {/* Instanced particles for ALL connections — high performance */}
        <AllSynapseParticles
          connections={connections}
          activeBrains={activeBrains}
          brainPositions={brainPositions}
        />
      </group>
    </>
  );
}

// ─── Camera Controller ─────────────────────────────────────────

function CameraController() {
  const cameraRef = useRef<THREE.PerspectiveCamera>(null);

  useFrame((state) => {
    const cam = state.camera as THREE.PerspectiveCamera;
    const t = state.clock.getElapsedTime();
    cam.position.x = Math.sin(t * 0.1) * 0.5;
    cam.position.y = Math.cos(t * 0.08) * 0.3;
    cam.position.z = 7;
    cam.lookAt(0, 0, 0);
  });

  return null;
}

// ─── Error Boundary Fallback ───────────────────────────────────

function BrainNetworkFallback() {
  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#080810',
      color: '#5a6a80',
      fontSize: 12,
      flexDirection: 'column',
      gap: 8,
    }}>
      <div style={{ fontSize: 32 }}>🧠</div>
      <div>جاري تحميل شبكة الأدمغة...</div>
    </div>
  );
}

// ─── Main Export ───────────────────────────────────────────────

export interface BrainNetworkProps {
  activeBrains: string[];
  brainConfidences: Record<string, number>;
  onBrainClick: (id: string) => void;
  vitality: number;
}

const BrainNetwork = React.memo(function BrainNetwork({
  activeBrains,
  brainConfidences,
  onBrainClick,
  vitality,
}: BrainNetworkProps) {
  return (
    <React.Suspense fallback={<BrainNetworkFallback />}>
      <Canvas
        style={{ width: '100%', height: '100%' }}
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
        dpr={[1, 1.5]}
      >
        <CameraController />
        <BrainScene
          activeBrains={activeBrains}
          brainConfidences={brainConfidences}
          onBrainClick={onBrainClick}
          vitality={vitality}
        />
      </Canvas>
    </React.Suspense>
  );
});

export default BrainNetwork;
