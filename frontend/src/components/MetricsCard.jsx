import React from 'react';

const MetricsCard = ({ title, value, definition, benchmark }) => {
  // Helper to safely format numbers, returning 'N/A' if the value is invalid
  const formatNumber = (num) => {
    // Check if it's a valid, finite number
    if (typeof num === 'number' && isFinite(num)) {
      return num.toLocaleString('en-IN');
    }
    // Return the value as is if it's a string (like a percentage)
    if (typeof num === 'string') {
        return num;
    }
    return 'N/A';
  };

  const formattedValue = formatNumber(value);
  const formattedBenchmark = formatNumber(benchmark);

  return (
    <div className="metric-card">
      <div className="metric-header">
        <h5 className="metric-title">{title}</h5>
        <div className="tooltip-container">
          <span className="tooltip-icon">ⓘ</span>
          <p className="tooltip-text">{definition || 'No definition available.'}</p>
        </div>
      </div>
      <p className="metric-value">{formattedValue}</p>
      {/* Only render the benchmark if it's available */}
      {formattedBenchmark !== 'N/A' && (
        <p className="metric-benchmark">Benchmark: {formattedBenchmark}</p>
      )}
    </div>
  );
};

export default MetricsCard;