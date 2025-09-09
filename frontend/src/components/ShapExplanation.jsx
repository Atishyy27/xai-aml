import React from 'react';

// Helper function to format feature names nicely
const formatFeatureName = (name) => {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, char => char.toUpperCase()); // Capitalize each word
};

const ShapExplanation = ({ features }) => {
  if (!features || features.length === 0) {
    return <p className="no-contributors">No specific risk contributors were identified by the model.</p>;
  }

  // Find the maximum impact to scale the bars correctly
  const maxImpact = Math.max(...features.map(f => Math.abs(f.impact)));

  return (
    <div className="shap-container">
      <h4>Primary Risk Contributors</h4>
      <div className="shap-list">
        {features.map((item, index) => {
          const percentageImpact = (item.impact * 100);
          const barWidth = maxImpact > 0 ? (Math.abs(percentageImpact) / (maxImpact * 100)) * 100 : 0;
          
          return (
            <div key={index} className="shap-item">
              <div className="shap-label">
                <span>{formatFeatureName(item.feature)}</span>
                <span className="shap-value">+{percentageImpact.toFixed(1)}% risk</span>
              </div>
              <div className="shap-bar-container">
                <div 
                  className="shap-bar" 
                  style={{ width: `${barWidth}%` }}
                ></div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ShapExplanation;