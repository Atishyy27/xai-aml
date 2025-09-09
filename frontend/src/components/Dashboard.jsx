// frontend/src/components/Dashboard.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getSuspiciousNetworks } from '../api';
import PatternChart from './PatternChart.jsx';
import Heatmap from './Heatmap.jsx';

const Dashboard = () => {
  const [networks, setNetworks] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchNetworks = async () => {
      try {
        setIsLoading(true);
        const data = await getSuspiciousNetworks();
        setNetworks(data);
        setError(null);
      } catch (err) {
        setError('Failed to fetch suspicious networks. Is the backend running?');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchNetworks();
  }, []);

  const handleNetworkSelect = (network) => {
    navigate(`/network/${network.account_id}`);
  };

  if (isLoading) {
    return <div className="loading-message">Loading suspicious networks...</div>;
  }
  
  if (error) {
    return <div className="error-message">{error}</div>;
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-main">
        <h2>Top Flagged Networks / Accounts</h2>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Account ID</th>
                <th>Risk Score</th>
                <th>Pattern Type</th>
              </tr>
            </thead>
            <tbody>
              {networks.map((network) => (
                <tr
                  key={network.account_id}
                  onClick={() => handleNetworkSelect(network)}
                  className="network-row"
                >
                  <td>{network.account_id}</td>
                  <td>{(network.risk_score * 100).toFixed(1)}%</td>
                  <td>{network.pattern_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
        <aside className="dashboard-sidebar">
          <PatternChart />
          <Heatmap /> 
      </aside>
    </div>
  );
};

export default Dashboard;
