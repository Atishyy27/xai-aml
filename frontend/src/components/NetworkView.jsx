// frontend/src/components/NetworkView.jsx

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import ForceGraph2D from 'react-force-graph-2d';
import { getNetworkGraph, getAccountExplanation, getIllicitTransactions } from '../api';
import TransactionList from './TransactionList';
import MetricsCard from './MetricsCard';
import ShapExplanation from './ShapExplanation.jsx';

const NetworkView = () => {
  const { networkId } = useParams();
  const navigate = useNavigate();
  const graphRef = useRef();
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [explanation, setExplanation] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [hops, setHops] = useState(1); // State to control 1-hop or 2-hops
  const [hoveredLink, setHoveredLink] = useState(null);
  const containerRef = useRef();
  const [dims, setDims] = useState({ width: 0, height: 0 });
  const hasZoomedRef = useRef(false); // To ensure zoomToFit only runs once per graph load

  // Effect for dynamic sizing of the graph container
  useEffect(() => {
    const measure = () => {
      if (containerRef.current) {
        setDims({
          width: containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight,
        });
      }
    };
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, []);

  // Effect for fetching data
  useEffect(() => {
    const fetchData = async () => {
      if (!networkId) return;
      setIsLoading(true);
      hasZoomedRef.current = false; // Reset zoom flag for new data
      try {
        // Fetch graph, explanation, and transactions concurrently
        const [graph, expl, trans] = await Promise.all([
          getNetworkGraph(networkId, hops), // Pass 'hops' parameter
          getAccountExplanation(networkId),
          getIllicitTransactions(networkId)
        ]);

        // Ensure data is in expected format for ForceGraph2D
        const nodes = graph?.graph?.nodes ?? [];
        const links = (graph?.graph?.edges ?? []).map(link => ({
          source: link.source,
          target: link.target,
          amount: link.amount
        }));

        setGraphData({ nodes, links });
        setExplanation(expl?.explanation ?? null);
        setTransactions(trans?.transactions ?? []);

      } catch (error) {
        console.error("Error fetching network details:", error);
        // Optionally set an error state here
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [networkId, hops]); // Re-run when networkId or hops change

  // Memoize node classifications for coloring
  const nodeClassifications = useMemo(() => {
    const incomingIds = new Set();
    const outgoingIds = new Set();
    graphData.links.forEach(link => {
      if (link.target === networkId) {
        incomingIds.add(link.source);
      }
      if (link.source === networkId) {
        outgoingIds.add(link.target);
      }
    });
    return { incomingIds, outgoingIds };
  }, [graphData.links, networkId]);

  // Node Canvas Object for custom rendering (coloring, labels, sizes)
  const nodeCanvasObject = (node, ctx, globalScale) => {
    const label = node.id;
    const fontSize = 12 / globalScale;
    ctx.font = `${fontSize}px Sans-Serif`;
    let nodeColor = 'rgba(128, 128, 128, 0.6)'; // Default Grey
    let radius = 5;

    const { incomingIds, outgoingIds } = nodeClassifications;

    // Color Logic
    if (node.id === networkId) {
      nodeColor = 'rgba(236, 72, 153, 0.9)'; // Pink - Center Node
      radius = 8; // Slightly larger for the center node
    } else if (incomingIds.has(node.id)) {
      nodeColor = 'rgba(16, 185, 129, 0.8)'; // Green - Incoming Money (Source)
    } else if (outgoingIds.has(node.id)) {
      nodeColor = 'rgba(239, 68, 68, 0.8)'; // Red - Outgoing Money (Destination)
    }

    // Draw circle
    ctx.fillStyle = nodeColor;
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
    ctx.fill();

    // Draw label
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = 'black';
    ctx.fillText(label, node.x, node.y + radius + 5);
  };

  return (
    <div className="network-view-container">
      <div className="left-panel">
        <Link to="/" className="back-link"> &larr; Back to Dashboard</Link>
        <div className="explanation-container">
          <h3>XAI Report for Account: {networkId}</h3>
          {isLoading ? <p>Loading report...</p> : (
            !explanation ? <p>Explanation data not available.</p> : (
              <>
                <p><strong>Summary:</strong> {explanation.summary}</p>

                {/* Render the new metrics cards */}
                <div className="metrics-grid">
                  {explanation.metrics && explanation.metrics.map(metric => (
                    <MetricsCard
                      key={metric.name}
                      title={metric.name}
                      value={metric.value}
                      benchmark={metric.benchmark}
                      definition={metric.definition}
                    />
                  ))}
                </div>

                {/* Render the new SHAP visualization */}
                <ShapExplanation features={explanation.feature_contributions} />

                {/* The transaction list can stay if you like */}
                <h4>Flagged Transactions</h4>
                <TransactionList
                  transactions={transactions}
                  onHoverTransaction={setHoveredLink}
                  currentAccountId={networkId}
                />
              </>
            )
          )}
        </div>
      </div>

      <div className="right-panel-container">
        <div className="hop-controls">
          <strong>Analysis Depth:</strong>
          <button
            onClick={() => setHops(1)}
            disabled={hops === 1 || isLoading}
          >
            1-Hop
          </button>
          <button
            onClick={() => setHops(2)}
            disabled={hops === 2 || isLoading}
          >
            2-Hops
          </button>
        </div>
        <div ref={containerRef} className="right-panel">
          {isLoading ? (
            <div className="loading-message">Loading graph...</div>
          ) : (
            <ForceGraph2D
              width={dims.width}
              height={dims.height}
              graphData={graphData}
              nodeId="id" // Specify node ID accessor
              linkSource="source" // Specify link source accessor
              linkTarget="target" // Specify link target accessor
              onNodeClick={(node) => {
                navigate(`/network/${node.id}`); // Navigate on node click
              }}
              linkWidth={link => (hoveredLink && link.source.id === hoveredLink.from && link.target.id === hoveredLink.to) ? 4 : 1}

              // ✅ Make the hovered link a bright color
              linkColor={link => (hoveredLink && link.source.id === hoveredLink.from && link.target.id === hoveredLink.to) ? 'rgba(255, 235, 59, 0.8)' : '#ccc'}

              nodeCanvasObject={(node, ctx, globalScale) => {
                // ... (existing node drawing logic for colors and labels)
                const label = node.id;
                const fontSize = 12 / globalScale;
                ctx.font = `${fontSize}px Sans-Serif`;
                let nodeColor = 'rgba(128, 128, 128, 0.6)';
                let radius = 5;

                const { incomingIds, outgoingIds } = nodeClassifications;
                if (node.id === networkId) {
                  nodeColor = 'rgba(236, 72, 153, 0.9)';
                  radius = 8;
                } else if (incomingIds.has(node.id)) {
                  nodeColor = 'rgba(16, 185, 129, 0.8)';
                } else if (outgoingIds.has(node.id)) {
                  nodeColor = 'rgba(239, 68, 68, 0.8)';
                }

                // ✅ HIGHLIGHT LOGIC: Draw a "halo" around hovered nodes
                if (hoveredLink && (node.id === hoveredLink.from || node.id === hoveredLink.to)) {
                  ctx.shadowBlur = 15;
                  ctx.shadowColor = 'rgba(255, 235, 59, 1)';
                } else {
                  ctx.shadowBlur = 0;
                }

                // Draw circle
                ctx.fillStyle = nodeColor;
                ctx.beginPath();
                ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
                ctx.fill();

                // Reset shadow for text
                ctx.shadowBlur = 0;

                // Draw label
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = 'black';
                ctx.fillText(label, node.x, node.y + radius + 5);
              }}
              // nodeCanvasObject={nodeCanvasObject} // Use the custom node renderer
              nodeVal={node => (node.id === networkId ? 3 : 1)}

              // ✅ ARROW PROPS ARE HERE
              linkDirectionalArrowLength={3.5}
              linkDirectionalArrowRelPos={1}
              linkCurvature={0.25} // Smooth curves for links

              // Link label (already good)
              linkLabel={link => link.amount ? `₹${Number(link.amount).toLocaleString('en-IN')}` : ''}

              // Zoom to fit after the engine settles
              onEngineStop={() => {
                if (graphRef.current && !hasZoomedRef.current && graphData.nodes.length > 0) {
                  graphRef.current.zoomToFit(400, 100);
                  hasZoomedRef.current = true;
                }
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default NetworkView;