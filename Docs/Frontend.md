# Frontend UI for Project SENTINEL

## 1.0 Objective

This document outlines the requirements for the frontend of Project SENTINEL. The objective is to build an intuitive, powerful, and investigator-centric web application that transforms the raw, complex outputs of the backend API into clear, actionable intelligence through effective data visualization and a streamlined user experience.

## 2.0 Justification: Why an Interactive Visualization Dashboard?

The primary value proposition of Project SENTINEL to an Investigating Officer (IO) is clarity. An IO needs to see the "big picture" of a criminal conspiracy, not just a list of suspicious transactions.

- **Why a Web Application?** A web-based dashboard provides a secure, universally accessible platform for IOs without requiring any local software installation.
- **Why React?** React is a modern, industry-standard library for building complex, component-based, and stateful user interfaces. Its ecosystem is ideal for rapid prototyping in a hackathon.
- **Why Interactive Graph Visualization?** This is the single most critical feature of the UI. The paper
    
    **"Anti-Money Laundering: Using data visualization to identify suspicious activity" (Singh & Best, 2019)** is dedicated entirely to demonstrating that visualizing transaction data as a node-link graph is vastly superior to traditional tabular analysis for identifying patterns. It allows an IO to leverage their own powerful human pattern-recognition abilities on data that has been intelligently filtered and structured by the AI.
    

## 3.0 Methodology & Component Breakdown

### 3.1 UI/UX Philosophy

The design philosophy is **"Intelligence, not Data."** Every UI element should be designed to answer a specific question for the IO, not simply to display raw numbers. The workflow should be intuitive: from a high-level overview (dashboard) to a deep dive (graph view) to a clear justification (XAI report).

### 3.2 Core Components

- **Dashboard View (`App.jsx`):**
    - **Function:** The main application layout. It will manage the overall state, such as which network is currently selected for detailed viewing.
    - **Features:** Will contain the `SuspiciousNetworks` list and the `NetworkGraph` and `Explanation` detail components.
- **SuspiciousNetworks Component:**
    - **Function:** Displays a prioritized, sortable table of the top suspicious networks fetched from the `GET /suspicious-networks` endpoint.
    - **Features:** Each row will be clickable, allowing the IO to select a network for investigation. Key data points (risk score, pattern type, number of accounts) will be visible at a glance.
- **NetworkGraph Component:**
    - **Function:** The centerpiece of the application. It renders an interactive, force-directed graph of the selected network using data from the `GET /network/{account_id}` endpoint.
    - **Features:** IOs can pan, zoom, and drag nodes to explore relationships. Nodes can be clicked to reveal more details. Transaction flows will be represented by directed edges with labels indicating the amount.
    - **Technology:** This will be implemented using the **`react-force-graph-2d`** library, a high-performance wrapper for D3.js that is ideal for rapid development in a hackathon.
- **Explanation Component:**
    - **Function:** Displays the human-readable report fetched from the `GET /account/{account_id}/explanation` endpoint.
    - **Features:** It will clearly list the summary of the finding and the top contributing factors to the risk score, providing the crucial context behind the AI's decision.

## 4.0 Technical Specifications

- **Framework:** React.js (using Vite for the build tool).
- **Language:** JavaScript (JSX), CSS3.
- **Libraries:** `react-force-graph-2d` for visualization, `axios` or `fetch` for API calls.
- **Dependency:** A running and accessible Backend API that adheres to the `openapi.json` contract.
- **Deployment:** Static site built into a Docker container.