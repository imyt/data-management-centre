import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Sparkles,
  Database,
  Server,
  BarChart3,
  BookOpen,
  ShieldCheck,
  Activity,
  Layers,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  RefreshCw,
  GitFork,
  ExternalLink,
  ChevronRight,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { lineageGraphStyles } from "./LineageGraph.styles";

export interface ILineageNode {
  id: string;
  name: string;
  asset_type_id?: string | null;
  asset_type_code?: string | null;
  domain_id?: string | null;
  status?: string | null;
  version_number?: number | null;
  is_current: boolean;
  depth: number;
  direction: "upstream" | "downstream" | "current";
  metadata?: Record<string, unknown>;
}

export interface ILineageEdge {
  id: string;
  source_asset_head_id: string;
  target_asset_head_id: string;
  relation_type_id?: string | null;
  relation_type_code?: string | null;
  role_name?: string | null;
  direction?: "upstream" | "downstream";
}

export interface ILineageGraphData {
  root_asset_head_id: string;
  nodes: ILineageNode[];
  edges: ILineageEdge[];
}

export interface ILineageGraphProps {
  assetHeadId?: string;
  assetHead?: {
    id: string;
    published_version?: { name: string; status?: string; version_number?: number } | null;
    active_draft_version?: { name: string; status?: string; version_number?: number } | null;
  } | null;
  initialData?: ILineageGraphData;
  onSelectAsset?: (assetId: string) => void;
  className?: string;
}

interface EdgeCoordinate {
  edge: ILineageEdge;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  midX: number;
  midY: number;
  pathD: string;
}

export const LineageGraph: React.FC<ILineageGraphProps> = ({
  assetHeadId: propAssetHeadId,
  assetHead,
  initialData,
  onSelectAsset,
  className,
}) => {
  const targetId = propAssetHeadId || assetHead?.id || "";

  const [graphData, setGraphData] = useState<ILineageGraphData | null>(initialData || null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters & layout controls
  const [maxDepth, setMaxDepth] = useState<number>(2);
  const [directionFilter, setDirectionFilter] = useState<"both" | "upstream" | "downstream">("both");
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | null>(null);

  // Layout & coordinate refs
  const viewportRef = useRef<HTMLDivElement>(null);
  const cardRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const [edgeCoords, setEdgeCoords] = useState<EdgeCoordinate[]>([]);

  // Fetch or synthesize lineage
  const loadGraph = useCallback(async () => {
    if (!targetId) return;
    if (initialData) {
      setGraphData(initialData);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem("dgc_auth_token") || "";
      const res = await fetch(
        `http://localhost:8000/api/v1/assets/${targetId}/lineage?max_depth=${maxDepth}&direction=${directionFilter}`,
        {
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        }
      );

      if (res.ok) {
        const data: ILineageGraphData = await res.json();
        setGraphData(data);
      } else {
        // Graceful fallback: synthesize center node from assetHead and attempt relations query
        const activeVer = assetHead?.published_version || assetHead?.active_draft_version;
        const centerNode: ILineageNode = {
          id: targetId,
          name: activeVer?.name || `Asset ${targetId.slice(0, 8)}`,
          status: activeVer?.status || "PUBLISHED",
          version_number: activeVer?.version_number || 1,
          is_current: true,
          depth: 0,
          direction: "current",
        };

        // Try fetching active outgoing relations
        let edges: ILineageEdge[] = [];
        let fetchedNodes: ILineageNode[] = [centerNode];

        try {
          const relRes = await fetch(`http://localhost:8000/api/v1/assets/${targetId}/relations`, {
            headers: {
              "Content-Type": "application/json",
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
          });
          if (relRes.ok) {
            const rawRels = await relRes.json();
            if (Array.isArray(rawRels)) {
              edges = rawRels.map((r: any) => ({
                id: r.id,
                source_asset_head_id: r.source_asset_head_id,
                target_asset_head_id: r.target_asset_head_id,
                relation_type_id: r.relation_type_id,
                relation_type_code: r.relation_type_code || "FLOWS_TO",
                direction: "downstream",
              }));

              // Add placeholder target nodes
              rawRels.forEach((r: any) => {
                if (r.target_asset_head_id !== targetId) {
                  fetchedNodes.push({
                    id: r.target_asset_head_id,
                    name: `Target Asset (${r.target_asset_head_id.slice(0, 8)})`,
                    status: "PUBLISHED",
                    version_number: 1,
                    is_current: false,
                    depth: 1,
                    direction: "downstream",
                  });
                }
              });
            }
          }
        } catch {
          // Ignore relations fallback error
        }

        setGraphData({
          root_asset_head_id: targetId,
          nodes: fetchedNodes,
          edges,
        });
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load lineage graph.");
    } finally {
      setLoading(false);
    }
  }, [targetId, maxDepth, directionFilter, initialData, assetHead]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  // Measure card elements and calculate SVG paths
  const updateCoordinates = useCallback(() => {
    if (!viewportRef.current || !graphData || graphData.edges.length === 0) {
      setEdgeCoords([]);
      return;
    }

    const viewport = viewportRef.current;
    const vRect = viewport.getBoundingClientRect();
    const scrollLeft = viewport.scrollLeft;
    const scrollTop = viewport.scrollTop;

    const newCoords: EdgeCoordinate[] = [];

    for (const edge of graphData.edges) {
      const sourceCard = cardRefs.current.get(edge.source_asset_head_id);
      const targetCard = cardRefs.current.get(edge.target_asset_head_id);

      if (!sourceCard || !targetCard) continue;

      const sRect = sourceCard.getBoundingClientRect();
      const tRect = targetCard.getBoundingClientRect();

      // Right-center of source
      const x1 = sRect.right - vRect.left + scrollLeft;
      const y1 = sRect.top + sRect.height / 2 - vRect.top + scrollTop;

      // Left-center of target
      const x2 = tRect.left - vRect.left + scrollLeft;
      const y2 = tRect.top + tRect.height / 2 - vRect.top + scrollTop;

      // Midpoints
      const midX = (x1 + x2) / 2;
      const midY = (y1 + y2) / 2;

      // Smooth horizontal cubic bezier curve
      const dx = Math.max(Math.abs(x2 - x1) * 0.45, 40);
      const pathD = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;

      newCoords.push({
        edge,
        x1,
        y1,
        x2,
        y2,
        midX,
        midY,
        pathD,
      });
    }

    setEdgeCoords(newCoords);
  }, [graphData]);

  useEffect(() => {
    // Schedule measurement after DOM elements paint
    const timer = setTimeout(updateCoordinates, 50);
    window.addEventListener("resize", updateCoordinates);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("resize", updateCoordinates);
    };
  }, [updateCoordinates, graphData, zoomLevel]);

  // Categorize nodes into columns
  const upstreamNodes = (graphData?.nodes || [])
    .filter((n) => !n.is_current && (n.direction === "upstream" || n.depth < 0))
    .sort((a, b) => b.depth - a.depth);

  const centerNode = (graphData?.nodes || []).find((n) => n.is_current) || {
    id: targetId,
    name: "Inspected Asset",
    status: "PUBLISHED",
    version_number: 1,
    is_current: true,
    depth: 0,
    direction: "current" as const,
  };

  const downstreamNodes = (graphData?.nodes || [])
    .filter((n) => !n.is_current && (n.direction === "downstream" || n.depth > 0))
    .sort((a, b) => a.depth - b.depth);

  const getAssetTypeIcon = (code?: string | null) => {
    switch (code?.toUpperCase()) {
      case "DATABASE":
      case "SOURCE_SYSTEM":
      case "STORAGE":
        return <Database className="w-3.5 h-3.5 text-blue-500" />;
      case "TABLE":
      case "DATASET":
      case "MODEL":
        return <Layers className="w-3.5 h-3.5 text-indigo-500" />;
      case "REPORT":
      case "DASHBOARD":
        return <BarChart3 className="w-3.5 h-3.5 text-cyan-500" />;
      case "APPLICATION":
      case "SERVICE":
        return <Server className="w-3.5 h-3.5 text-purple-500" />;
      case "POLICY":
        return <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />;
      case "METRIC":
        return <Activity className="w-3.5 h-3.5 text-amber-500" />;
      default:
        return <BookOpen className="w-3.5 h-3.5 text-primary" />;
    }
  };

  const getStatusBadge = (status?: string | null) => {
    if (!status) return null;
    const s = status.toUpperCase();
    if (s === "PUBLISHED") {
      return <span className={lineageGraphStyles.statusBadgePublished}>PUBLISHED</span>;
    }
    if (s === "DRAFT") {
      return <span className={lineageGraphStyles.statusBadgeDraft}>DRAFT</span>;
    }
    return <span className={lineageGraphStyles.statusBadgeDefault}>{s}</span>;
  };

  const isEdgeHighlighted = (e: ILineageEdge) => {
    if (hoveredEdgeId === e.id) return true;
    if (hoveredNodeId && (e.source_asset_head_id === hoveredNodeId || e.target_asset_head_id === hoveredNodeId)) {
      return true;
    }
    return false;
  };

  return (
    <div className={cn(lineageGraphStyles.container, className)}>
      {/* Interactive Toolbar */}
      <div className={lineageGraphStyles.toolbar}>
        <div className={lineageGraphStyles.toolbarGroup}>
          <span className={lineageGraphStyles.titleText}>
            <GitFork className="w-3.5 h-3.5 text-primary rotate-90" />
            Semantic Lineage & Relation Graph
          </span>
          <span className={lineageGraphStyles.statsBadge}>
            {upstreamNodes.length} Upstream • 1 Focus • {downstreamNodes.length} Downstream
          </span>
        </div>

        <div className={lineageGraphStyles.toolbarGroup}>
          {/* Depth / Hop Selector */}
          <label className="text-[10px] uppercase font-semibold text-muted-foreground mr-1">
            Max Hops:
          </label>
          <select
            value={maxDepth}
            onChange={(e) => setMaxDepth(Number(e.target.value))}
            className={lineageGraphStyles.selectInput}
          >
            <option value={1}>1 Hop</option>
            <option value={2}>2 Hops</option>
            <option value={3}>3 Hops</option>
          </select>

          {/* Direction Filter */}
          <select
            value={directionFilter}
            onChange={(e) => setDirectionFilter(e.target.value as any)}
            className={lineageGraphStyles.selectInput}
          >
            <option value="both">All Relations</option>
            <option value="upstream">Upstream Only</option>
            <option value="downstream">Downstream Only</option>
          </select>

          {/* Zoom & Reset Controls */}
          <div className="h-4 w-px bg-border/60 mx-1" />

          <button
            title="Zoom In"
            onClick={() => setZoomLevel((z) => Math.min(z + 0.15, 1.6))}
            className={lineageGraphStyles.controlButton}
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            title="Zoom Out"
            onClick={() => setZoomLevel((z) => Math.max(z - 0.15, 0.65))}
            className={lineageGraphStyles.controlButton}
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <button
            title="Reset Zoom"
            onClick={() => setZoomLevel(1)}
            className={lineageGraphStyles.controlButton}
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
          <button
            title="Refresh Lineage"
            onClick={loadGraph}
            className={lineageGraphStyles.controlButton}
          >
            <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Main Graph Viewport */}
      <div
        ref={viewportRef}
        onScroll={updateCoordinates}
        className={lineageGraphStyles.viewport}
      >
        {loading && !graphData && (
          <div className={lineageGraphStyles.loadingOverlay}>
            <div className="flex items-center gap-2 text-xs font-semibold text-primary">
              <RefreshCw className="w-4 h-4 animate-spin" />
              Traversing semantic relation graph...
            </div>
          </div>
        )}

        {error && !graphData && (
          <div className="flex items-center justify-center p-8 text-center text-xs text-destructive gap-2">
            <AlertCircle className="w-4 h-4" />
            <span>{error}</span>
          </div>
        )}

        {/* SVG Directed Edge Connectors Canvas */}
        <svg
          className={lineageGraphStyles.svgCanvas}
          style={{ transform: `scale(${zoomLevel})`, transformOrigin: "top left" }}
        >
          <defs>
            <linearGradient id="edge-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="var(--color-primary, #6366f1)" stopOpacity="0.4" />
              <stop offset="100%" stopColor="var(--color-primary, #6366f1)" stopOpacity="0.9" />
            </linearGradient>
            <marker
              id="arrow-default"
              viewBox="0 0 10 7"
              refX="9"
              refY="3.5"
              markerWidth="6"
              markerHeight="4.5"
              orient="auto-start-reverse"
            >
              <polygon points="0 0, 10 3.5, 0 7" className="fill-border" />
            </marker>
            <marker
              id="arrow-active"
              viewBox="0 0 10 7"
              refX="9"
              refY="3.5"
              markerWidth="7"
              markerHeight="5"
              orient="auto-start-reverse"
            >
              <polygon points="0 0, 10 3.5, 0 7" className="fill-primary" />
            </marker>
          </defs>

          {edgeCoords.map(({ edge, pathD }) => {
            const active = isEdgeHighlighted(edge);
            return (
              <g key={edge.id} className="transition-all duration-200">
                {/* Thick invisible hit-area for hover */}
                <path
                  d={pathD}
                  fill="none"
                  stroke="transparent"
                  strokeWidth="18"
                  className="cursor-pointer pointer-events-auto"
                  onMouseEnter={() => setHoveredEdgeId(edge.id)}
                  onMouseLeave={() => setHoveredEdgeId(null)}
                />
                {/* Background glow when active */}
                {active && (
                  <path
                    d={pathD}
                    fill="none"
                    stroke="var(--color-primary, #6366f1)"
                    strokeWidth="6"
                    strokeOpacity="0.25"
                    strokeLinecap="round"
                  />
                )}
                {/* Visual Connector Line */}
                <path
                  d={pathD}
                  fill="none"
                  stroke={active ? "var(--color-primary, #6366f1)" : "currentColor"}
                  strokeWidth={active ? 2.5 : 1.5}
                  strokeDasharray={active ? undefined : "4 2"}
                  className={cn(
                    "transition-all duration-200",
                    active ? "text-primary" : "text-border/80"
                  )}
                  markerEnd={active ? "url(#arrow-active)" : "url(#arrow-default)"}
                />
              </g>
            );
          })}
        </svg>

        {/* HTML Multi-Column Card Hierarchy */}
        <div
          className={lineageGraphStyles.columnsLayout}
          style={{ transform: `scale(${zoomLevel})`, transformOrigin: "top left" }}
        >
          {/* Column 1: Upstream Source Systems */}
          <div className={lineageGraphStyles.column}>
            <div className={lineageGraphStyles.columnHeader}>
              <Database className="w-3 h-3 text-blue-500" />
              Upstream Sources ({upstreamNodes.length})
            </div>

            {upstreamNodes.length === 0 ? (
              <div className="text-center p-4 border border-dashed border-border/60 rounded-xl text-muted-foreground/70 text-[11px] w-full">
                No upstream sources linked
              </div>
            ) : (
              upstreamNodes.map((node) => (
                <div
                  key={node.id}
                  ref={(el) => {
                    if (el) cardRefs.current.set(node.id, el);
                    else cardRefs.current.delete(node.id);
                  }}
                  onMouseEnter={() => setHoveredNodeId(node.id)}
                  onMouseLeave={() => setHoveredNodeId(null)}
                  onClick={() => onSelectAsset?.(node.id)}
                  className={cn(
                    lineageGraphStyles.nodeCard,
                    hoveredNodeId === node.id && "border-primary/80 ring-1 ring-primary/30"
                  )}
                >
                  <div className={lineageGraphStyles.nodeHeader}>
                    <div className="flex items-center gap-1.5 truncate">
                      {getAssetTypeIcon(node.asset_type_code)}
                      <span className={lineageGraphStyles.nodeTitle} title={node.name}>
                        {node.name}
                      </span>
                    </div>
                    {getStatusBadge(node.status)}
                  </div>

                  <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-1 border-t border-border/40">
                    <span className="font-mono">v{node.version_number ?? 1}</span>
                    <span className="flex items-center gap-0.5 text-blue-500 font-medium">
                      Source System <ChevronRight className="w-2.5 h-2.5" />
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Column 2: Center Inspected Asset (Active Focus Badge) */}
          <div className={lineageGraphStyles.column}>
            <div className={lineageGraphStyles.columnHeader}>
              <Sparkles className="w-3 h-3 text-primary" />
              Focus Asset
            </div>

            <div
              ref={(el) => {
                if (el) cardRefs.current.set(centerNode.id, el);
                else cardRefs.current.delete(centerNode.id);
              }}
              onMouseEnter={() => setHoveredNodeId(centerNode.id)}
              onMouseLeave={() => setHoveredNodeId(null)}
              className={lineageGraphStyles.nodeCardCenter}
            >
              <div className={lineageGraphStyles.nodeHeader}>
                <div className="flex items-center gap-2 truncate">
                  {getAssetTypeIcon(centerNode.asset_type_code)}
                  <span
                    className={cn(lineageGraphStyles.nodeTitle, "text-sm text-foreground")}
                    title={centerNode.name}
                  >
                    {centerNode.name}
                  </span>
                </div>
                <span className={lineageGraphStyles.activeBadge}>
                  <Sparkles className="w-2.5 h-2.5" />
                  CURRENT FOCUS
                </span>
              </div>

              <p className="text-[11px] text-muted-foreground line-clamp-2">
                Central semantic model being inspected in the data catalog.
              </p>

              <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-1.5 border-t border-primary/20">
                <span className="font-mono font-medium">v{centerNode.version_number ?? 1}</span>
                {getStatusBadge(centerNode.status)}
              </div>
            </div>
          </div>

          {/* Column 3: Downstream Consumers & Reports */}
          <div className={lineageGraphStyles.column}>
            <div className={lineageGraphStyles.columnHeader}>
              <BarChart3 className="w-3 h-3 text-cyan-500" />
              Downstream Consumers ({downstreamNodes.length})
            </div>

            {downstreamNodes.length === 0 ? (
              <div className="text-center p-4 border border-dashed border-border/60 rounded-xl text-muted-foreground/70 text-[11px] w-full">
                No downstream consumers linked
              </div>
            ) : (
              downstreamNodes.map((node) => (
                <div
                  key={node.id}
                  ref={(el) => {
                    if (el) cardRefs.current.set(node.id, el);
                    else cardRefs.current.delete(node.id);
                  }}
                  onMouseEnter={() => setHoveredNodeId(node.id)}
                  onMouseLeave={() => setHoveredNodeId(null)}
                  onClick={() => onSelectAsset?.(node.id)}
                  className={cn(
                    lineageGraphStyles.nodeCard,
                    hoveredNodeId === node.id && "border-primary/80 ring-1 ring-primary/30"
                  )}
                >
                  <div className={lineageGraphStyles.nodeHeader}>
                    <div className="flex items-center gap-1.5 truncate">
                      {getAssetTypeIcon(node.asset_type_code)}
                      <span className={lineageGraphStyles.nodeTitle} title={node.name}>
                        {node.name}
                      </span>
                    </div>
                    {getStatusBadge(node.status)}
                  </div>

                  <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-1 border-t border-border/40">
                    <span className="font-mono">v{node.version_number ?? 1}</span>
                    <span className="flex items-center gap-0.5 text-cyan-500 font-medium">
                      Consumer / Report <ExternalLink className="w-2.5 h-2.5" />
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Floating Relation Code Badges / Edge Labels */}
        {edgeCoords.map(({ edge, midX, midY }) => {
          const active = isEdgeHighlighted(edge);
          const label = edge.relation_type_code || edge.role_name || "FLOWS_TO";
          return (
            <div
              key={`badge-${edge.id}`}
              style={{
                position: "absolute",
                left: `${midX}px`,
                top: `${midY}px`,
                transform: `translate(-50%, -50%) scale(${zoomLevel})`,
                transformOrigin: "center center",
              }}
              onMouseEnter={() => setHoveredEdgeId(edge.id)}
              onMouseLeave={() => setHoveredEdgeId(null)}
              className={cn(
                lineageGraphStyles.edgePill,
                active && "border-primary bg-primary/10 text-primary font-bold shadow-md ring-1 ring-primary/20"
              )}
              title={`${edge.role_name || "Relation"}: ${label}`}
            >
              {label}
            </div>
          );
        })}
      </div>
    </div>
  );
};
