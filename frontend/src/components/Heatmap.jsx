// frontend/src/components/Heatmap.jsx

import React, { useState, useEffect } from 'react';
import { ComposableMap, Geographies, Geography } from 'react-simple-maps';
import { getHeatmapData } from '../api';

const INDIA_TOPO_JSON = '/india-states.json';

const Heatmap = () => {
    const [data, setData] = useState({});
    const [maxValue, setMaxValue] = useState(1); // Default to 1 to avoid division by zero
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const heatmapData = await getHeatmapData();
                setData(heatmapData);

                // FIX: Check if there's data before calculating the max value
                const values = Object.values(heatmapData);
                if (values.length > 0) {
                    setMaxValue(Math.max(...values));
                }
            } catch (error) {
                console.error("Failed to load heatmap data", error);
            } finally {
                setIsLoading(false);
            }
        };
        fetchData();
    }, []);

    const getColor = (count) => {
        if (!count) return "#EEE"; // A slightly different default color
        const intensity = count / maxValue;
        // A simple blue color scale
        return `rgba(5, 150, 255, ${intensity * 0.8 + 0.2})`;
    };

    if (isLoading) {
        return <div className="chart-container"><h3>Geographic Risk Distribution</h3><p>Loading map data...</p></div>;
    }

    return (
        <div className="chart-container">
            <h3>Geographic Risk Distribution</h3>
            <ComposableMap
                projectionConfig={{ scale: 800, center: [83, 23] }}
                style={{ width: "100%", height: "auto" }}
            >
                <Geographies geography={INDIA_TOPO_JSON}>
                    {({ geographies }) =>
                        geographies.map(geo => {
                            const stateName = geo.properties.ST_NM;
                            const count = data[stateName] || 0;
                            return (
                                <Geography
                                    key={geo.rsmKey}
                                    geography={geo}
                                    fill={getColor(count)}
                                    stroke="#FFF"
                                    strokeWidth={0.5}
                                    style={{
                                        default: { outline: 'none' },
                                        hover: { outline: 'none', fill: '#F53' },
                                        pressed: { outline: 'none' },
                                    }}
                                />
                            );
                        })
                    }
                </Geographies>
            </ComposableMap>
        </div>
    );
};

export default Heatmap;