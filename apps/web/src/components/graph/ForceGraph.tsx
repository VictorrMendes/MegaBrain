"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { GraphNode, ObsidianGraph } from "@/lib/api";

interface SimNode extends GraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

function tagColor(tags: string[]): string {
  if (tags.includes("work") || tags.includes("trabalho")) return "#60a5fa";
  if (tags.includes("study") || tags.includes("estudos")) return "#34d399";
  if (tags.includes("daily") || tags.includes("diario")) return "#f472b6";
  return "#a78bfa";
}

function simStep(
  nodes: SimNode[],
  edges: { source: string; target: string }[],
  w: number,
  h: number,
): SimNode[] {
  const k = Math.sqrt((w * h) / Math.max(nodes.length, 1));
  const repulsion = k * k * 2;
  const springLen = k * 1.5;
  const nx = nodes.map((n) => ({ ...n }));
  const fx = new Float64Array(nx.length);
  const fy = new Float64Array(nx.length);

  for (let i = 0; i < nx.length; i++) {
    for (let j = i + 1; j < nx.length; j++) {
      const dx = nx[i].x - nx[j].x || 0.01;
      const dy = nx[i].y - nx[j].y || 0.01;
      const d = Math.sqrt(dx * dx + dy * dy);
      const f = repulsion / (d * d);
      const ux = (dx / d) * f;
      const uy = (dy / d) * f;
      fx[i] += ux; fy[i] += uy;
      fx[j] -= ux; fy[j] -= uy;
    }
  }

  const idx = new Map(nx.map((n, i) => [n.id, i]));
  for (const e of edges) {
    const si = idx.get(e.source);
    const ti = idx.get(e.target);
    if (si === undefined || ti === undefined) continue;
    const dx = nx[ti].x - nx[si].x;
    const dy = nx[ti].y - nx[si].y;
    const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
    const f = ((d - springLen) / d) * 0.1;
    fx[si] += dx * f; fy[si] += dy * f;
    fx[ti] -= dx * f; fy[ti] -= dy * f;
  }

  for (let i = 0; i < nx.length; i++) {
    nx[i].vx = (nx[i].vx + fx[i]) * 0.9;
    nx[i].vy = (nx[i].vy + fy[i]) * 0.9;
    nx[i].x = Math.max(20, Math.min(w - 20, nx[i].x + nx[i].vx));
    nx[i].y = Math.max(20, Math.min(h - 20, nx[i].y + nx[i].vy));
  }
  return nx;
}

interface Props {
  graph: ObsidianGraph;
  onNodeClick?: (node: GraphNode) => void;
}

export function ForceGraph({ graph, onNodeClick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ w: 800, h: 600 });
  const rafRef = useRef<number | null>(null);

  const [simNodes, setSimNodes] = useState<SimNode[]>([]);

  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDims({ w: width || 800, h: height || 600 });
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    setSimNodes(
      graph.nodes.map((n) => ({
        ...n,
        x: dims.w / 2 + (Math.random() - 0.5) * 200,
        y: dims.h / 2 + (Math.random() - 0.5) * 200,
        vx: 0,
        vy: 0,
      })),
    );
  }, [graph.nodes, dims.w, dims.h]);

  const edges = useMemo(() => {
    const ids = new Set(graph.nodes.map((n) => n.id));
    return graph.edges.filter((e) => ids.has(e.source) && ids.has(e.target));
  }, [graph.nodes, graph.edges]);

  useEffect(() => {
    let step = 0;
    const tick = () => {
      if (step < 250) {
        setSimNodes((prev) => simStep(prev, edges, dims.w, dims.h));
        step++;
        rafRef.current = requestAnimationFrame(tick);
      }
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [edges, dims]);

  const nodeMap = useMemo(
    () => new Map(simNodes.map((n) => [n.id, n])),
    [simNodes],
  );

  return (
    <div ref={containerRef} className="w-full h-full bg-gray-900">
      <svg width={dims.w} height={dims.h}>
        <g>
          {edges.map((e, i) => {
            const s = nodeMap.get(e.source);
            const t = nodeMap.get(e.target);
            if (!s || !t) return null;
            return (
              <line
                key={i}
                x1={s.x} y1={s.y}
                x2={t.x} y2={t.y}
                stroke="#374151"
                strokeWidth={1}
                opacity={0.5}
              />
            );
          })}
        </g>
        <g>
          {simNodes.map((n) => (
            <g
              key={n.id}
              transform={`translate(${n.x},${n.y})`}
              style={{ cursor: "pointer" }}
              onClick={() =>
                onNodeClick?.({ id: n.id, title: n.title, tags: n.tags, path: n.path })
              }
            >
              <circle r={5} fill={tagColor(n.tags)} />
              <text
                x={0} y={11}
                textAnchor="middle"
                fontSize={9}
                fill="#9ca3af"
                style={{ pointerEvents: "none", userSelect: "none" }}
              >
                {n.title.length > 22 ? n.title.slice(0, 22) + "…" : n.title}
              </text>
            </g>
          ))}
        </g>
      </svg>
    </div>
  );
}
