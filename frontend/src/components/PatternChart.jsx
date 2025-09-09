// frontend/src/components/PatternChart.jsx

import React, { useState, useEffect } from 'react';
import { Pie } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import { getPatternStatistics } from '../api';

ChartJS.register(ArcElement, Tooltip, Legend);

const PatternChart = () => {
    // ✅ Add isLoading and error states
    const [chartData, setChartData] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const stats = await getPatternStatistics();
                if (stats && stats.length > 0) {
                    setChartData({
                        labels: stats.map(s => s.pattern),
                        datasets: [{
                            label: '# of Networks',
                            data: stats.map(s => s.count),
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.7)',
                                'rgba(54, 162, 235, 0.7)',
                                'rgba(255, 206, 86, 0.7)',
                                'rgba(75, 192, 192, 0.7)',
                            ],
                            borderColor: [
                                'rgba(255, 99, 132, 1)',
                                'rgba(54, 162, 235, 1)',
                                'rgba(255, 206, 86, 1)',
                                'rgba(75, 192, 192, 1)',
                            ],
                            borderWidth: 1,
                        }],
                    });
                }
            } catch (err) {
                console.error("Failed to load pattern data:", err);
                setError("Could not load data.");
            } finally {
                setIsLoading(false);
            }
        };
        fetchData();
    }, []);

    if (isLoading) return <div className="chart-container"><h3>Illicit Pattern Distribution</h3><p>Loading pattern data...</p></div>;
    if (error) return <div className="chart-container"><h3>Illicit Pattern Distribution</h3><p>{error}</p></div>;
    if (!chartData) return <div className="chart-container"><h3>Illicit Pattern Distribution</h3><p>No pattern data available.</p></div>;
    
    return (
        <div className="chart-container">
            <h3>Illicit Pattern Distribution</h3>
            <Pie data={chartData} />
        </div>
    );
};

export default PatternChart;