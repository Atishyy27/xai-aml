// frontend/src/components/ShapChart.jsx

import React from 'react';
import { Bar } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend,
} from 'chart.js';

ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend
);

const ShapChart = ({ explanation }) => {
    if (!explanation || !explanation.feature_contributions || explanation.feature_contributions.length === 0) {
        return <p>No specific risk contributors identified.</p>;
    }

    const chartData = {
        labels: explanation.feature_contributions.map(item => item.feature),
        datasets: [
            {
                label: 'Risk Contribution (SHAP Value)',
                data: explanation.feature_contributions.map(item => item.impact),
                backgroundColor: 'rgba(255, 99, 132, 0.5)',
                borderColor: 'rgba(255, 99, 132, 1)',
                borderWidth: 1,
            },
        ],
    };

    const options = {
        indexAxis: 'y', // This makes the bar chart horizontal
        elements: {
            bar: {
                borderWidth: 2,
            },
        },
        responsive: true,
        plugins: {
            legend: {
                display: false, // We don't need a legend for a single dataset
            },
            title: {
                display: true,
                text: 'Primary Risk Contributors',
            },
        },
    };

    return <Bar options={options} data={chartData} />;
};

export default ShapChart;