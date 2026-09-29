"use client";

import { Background, Controls, ReactFlow, ReactFlowProvider, useReactFlow, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect } from "react";
import type { CourtNodeData } from "@/lib/graphState";
import { nodeTypes } from "./CourtNodes";

interface Props {
  nodes: Node<CourtNodeData>[];
  edges: Edge[];
  onSelect: (data: CourtNodeData | null) => void;
}

function Inner({ nodes, edges, onSelect }: Props) {
  const { fitView } = useReactFlow();
  const firstId = nodes[0]?.id;
  useEffect(() => {
    const t = setTimeout(() => fitView({ padding: 0.15, duration: 300 }), 50);
    return () => clearTimeout(t);
  }, [nodes.length, firstId, fitView]);
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      nodesConnectable={false}
      minZoom={0.1}
      onNodeClick={(_, n) => onSelect(n.data as CourtNodeData)}
      onPaneClick={() => onSelect(null)}
      proOptions={{ hideAttribution: false }}
    >
      <Background gap={24} color="#e2e8f0" />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}

export default function TrialGraph(props: Props) {
  return (
    <div className="h-[55vh] min-h-[360px] w-full overflow-hidden rounded-xl border border-slate-200 bg-slate-50 sm:h-[62vh]">
      <ReactFlowProvider>
        <Inner {...props} />
      </ReactFlowProvider>
    </div>
  );
}
