// frontend/src/components/NetworkView.jsx
import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import ForceGraph2D from 'react-force-graph-2d';
import { getNetworkGraph, getAccountExplanation } from '../api';

const NetworkView = ({ networkId }) => {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [explanation, setExplanation] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const graphRef = useRef();

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const [graph, expl] = await Promise.all([
          getNetworkGraph(networkId),
          getAccountExplanation(networkId)
        ]);

        const links = graph.graph.edges.map(link => ({ ...link }));
        setGraphData({ nodes: graph.graph.nodes, links });
        setExplanation(expl.explanation);
      } catch (error) {
        console.error("Error fetching network details:", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [networkId]);

  useEffect(() => {
    if (graphRef.current) {
        graphRef.current.zoomToFit(400, 100);
    }
  }, [graphData]);

  return (
    <div className="network-view-container">
      <div className="left-panel">
        <Link to="/" className="back-link"> &larr; Back to Dashboard</Link>
        <div className="explanation-container">
            <h3>XAI Report for Account: {networkId}</h3>
            {isLoading ? (
                <p>Loading explanation...</p>
            ) : explanation ? (
                <div>
                <p><strong>Summary:</strong> {explanation.summary}</p>
                <strong>Primary Risk Contributors:</strong>
                <ul>
                    {explanation.feature_contributions.map((item, index) => (
                    <li key={index}>
                        {item.feature}: <strong>{`+${(item.impact * 100).toFixed(0)}% risk`}</strong>
                    </li>
                    ))}
                </ul>
                </div>
            ) : (
                <p>No explanation available for this node.</p>
            )}
        </div>
      </div>
      <div className="right-panel">
        {isLoading ? (
            <div className="loading-message">Loading graph...</div>
        ) : (
            <ForceGraph2D
                ref={graphRef}
                graphData={graphData}
                nodeLabel="id"
                nodeAutoColorBy="id"
                linkLabel={link => `₹${link.amount.toLocaleString('en-IN')}`}
                linkDirectionalArrowLength={3.5}
                linkDirectionalArrowRelPos={1}
                linkCurvature={0.25}
            />
        )}
      </div>
    </div>
  );
};

export default NetworkView;