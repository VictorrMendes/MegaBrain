"use client";

import dynamic from "next/dynamic";
import { useCallback, useRef } from "react";
import type { GraphEdge, GraphNode, ObsidianGraph } from "@/lib/api";

// react-force-graph-2d uses canvas — must be loaded client-side only
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

interface Props {
  graph: ObsidianGraph;
  onNodeClick?: (node: GraphNode) => void;
}

interface FGNode {
  id: string;
  title: string;
  tags: string[];
  path: string;
  x?: number;
  y?: number;
}

interface FGLink {
  source: string;
  target: string;
  link_text: string | null;
}

function tagColor(tags: string[]): string {
  if (tags.includes("work") || tags.includes("trabalho")) return "#60a5fa";
  if (tags.includes("study") || tags.includes("estudos")) return "#34d399";
  if (tags.includes("daily") || tags.includes("diario")) return "#f472b6";
  return "#a78bfa";
}

export function ForceGraph({ graph, onNodeClick }: Props) {
  const fgRef = useRef<{ centerAt: (x: number, y: number, ms: number) => void } | null>(null);

  const nodes: FGNode[] = graph.nodes.map((n) => ({ ...n }));
  const links: FGLink[] = graph.edges
    .filter((e) => graph.nodes.some((n) => n.id === e.source) && graph.nodes.some((n) => n.id === e.target))
    .map((e) => ({ source: e.source, target: e.target, link_text: e.link_text }));

  const handleNodeClick = useCallback(
    (node: FGNode) => {
      if (fgRef.current && node.x != null && node.y != null) {
        fgRef.current.centerAt(node.x, node.y, 500);
      }
      onNodeClick?.({ id: node.id, title: node.title, tags: node.tags, path: node.path });
    },
    [onNodeClick]
  );

  const paintNode = useCallback((node: FGNode, ctx: CanvasRenderingContext2D) => {
    const x = node.x ?? 0;
    const y = node.y ?? 0;
    const r = 5;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, 2 * Math.PI);
    ctx.fillStyle = tagColor(node.tags);
    ctx.fill();
    ctx.font = "4px sans-serif";
    ctx.fillStyle = "#e5e7eb";
    ctx.textAlign = "center";
    ctx.fillText(node.title.slice(0, 20), x, y + r + 4);
  }, []);

  return (
    <ForceGraph2D
      ref={fgRef as never}
      graphData={{ nodes, links }}
      nodeId="id"
      linkSource="source"
      linkTarget="target"
      nodeCanvasObject={paintNode as never}
      nodeCanvasObjectMode={() => "replace"}
      linkColor={() => "#374151"}
      linkWidth={1}
      backgroundColor="#111827"
      onNodeClick={handleNodeClick as never}
      nodeLabel="title"
      width={undefined}
      height={undefined}
    />
  );
}
