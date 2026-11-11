import React, { useCallback, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Edge,
  MarkerType,
  NodeTypes,
  ReactFlowProvider,
  useReactFlow,
} from '@xyflow/react';
import dagre from 'dagre';
import { CustomNode, CustomNodeType } from './CustomNode';
import { GraphResponse } from '../types';

interface GraphCanvasProps {
  graphData: GraphResponse | null;
  onSelectNode: (nodeId: string) => void;
  direction?: 'LR' | 'TB';
  activeNodeId?: string | null;
}

const nodeWidth = 240;
const nodeHeight = 85;

const getLayoutedElements = (
  nodes: CustomNodeType[],
  edges: Edge[],
  direction = 'LR'
) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: 45,
    ranksep: 90,
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

const GraphCanvasInner: React.FC<GraphCanvasProps> = ({
  graphData,
  onSelectNode,
  direction = 'LR',
  activeNodeId,
}) => {
  const { setCenter, getNodes } = useReactFlow();

  const nodeTypes = useMemo<NodeTypes>(
    () => ({
      customNode: CustomNode as any,
    }),
    []
  );

  const [nodes, setNodes, onNodesChange] = useNodesState<CustomNodeType>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Build and layout nodes & edges
  useEffect(() => {
    if (!graphData || !graphData.nodes) {
      setNodes([]);
      setEdges([]);
      return;
    }

    const rawNodes: CustomNodeType[] = graphData.nodes.map((n) => {
      const isNodeActive =
        n.id === activeNodeId ||
        (n as any).file_id === activeNodeId ||
        (n as any).data?.file_id === activeNodeId;

      return {
        id: n.id,
        type: 'customNode',
        data: {
          ...n,
          isActive: isNodeActive,
        },
        position: { x: 0, y: 0 },
      };
    });

    const rawEdges: Edge[] = graphData.edges.map((e) => {
      const isConnectedToActive =
        e.source === activeNodeId || e.target === activeNodeId;

      return {
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        animated: !!e.is_cycle || isConnectedToActive,
        style: {
          stroke: e.is_cycle
            ? '#f85149'
            : isConnectedToActive
            ? '#34d399'
            : '#58a6ff',
          strokeWidth: isConnectedToActive ? 2.5 : e.is_cycle ? 2.5 : 1.5,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: e.is_cycle
            ? '#f85149'
            : isConnectedToActive
            ? '#34d399'
            : '#58a6ff',
        },
      };
    });

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      rawNodes,
      rawEdges,
      direction
    );

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [graphData, direction, activeNodeId, setNodes, setEdges]);

  // Center screen on activeNodeId whenever it changes
  useEffect(() => {
    if (!activeNodeId) return;

    // Small delay to ensure layout positions are set
    const timer = setTimeout(() => {
      const currentNodes = getNodes();
      const targetNode = currentNodes.find(
        (n) =>
          n.id === activeNodeId ||
          (n.data as any)?.file_id === activeNodeId
      );

      if (targetNode && targetNode.position) {
        const centerX = targetNode.position.x + nodeWidth / 2;
        const centerY = targetNode.position.y + nodeHeight / 2;
        setCenter(centerX, centerY, { zoom: 1.15, duration: 750 });
      }
    }, 120);

    return () => clearTimeout(timer);
  }, [activeNodeId, getNodes, setCenter]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: CustomNodeType) => {
      const targetId = (node.data.file_id as string) || node.id;
      onSelectNode(targetId);
    },
    [onSelectNode]
  );

  return (
    <div className="w-full h-full relative">
      <ReactFlow<CustomNodeType, Edge>
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        fitView
        minZoom={0.1}
        maxZoom={2.5}
      >
        <Background color="#21262d" gap={20} size={1} />
        <Controls />
        <MiniMap
          nodeColor={(n) => ((n.data as any)?.isActive ? '#34d399' : '#58a6ff')}
          maskColor="rgba(13, 17, 23, 0.7)"
          zoomable
          pannable
        />
      </ReactFlow>
    </div>
  );
};

export const GraphCanvas: React.FC<GraphCanvasProps> = (props) => {
  return (
    <ReactFlowProvider>
      <GraphCanvasInner {...props} />
    </ReactFlowProvider>
  );
};
