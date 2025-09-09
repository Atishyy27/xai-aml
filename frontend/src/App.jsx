// frontend/src/App.jsx
import React from 'react';
import { BrowserRouter as Router, Route, Routes, useParams } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import NetworkView from './components/NetworkView';
import './index.css';

function App() {
  return (
    <Router>
      <div className="app-container">
        <header className="app-header">
          <div className="logo">{<img src="/logo.png" alt="Logo" />}</div>
          <div className="app-title">XAI Anti-Money Laundering Detection</div>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/network/:networkId" element={<NetworkView />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

const NetworkViewWrapper = () => {
  const { networkId } = useParams();
  return <NetworkView networkId={networkId} />;
};

export default App;
