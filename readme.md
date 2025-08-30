# Project SENTINEL

An Explainable AI (XAI) Framework for Detecting and Dismantling Financial Laundering Networks. This project is a submission for the National CyberShield Hackathon 2025.

### Current Progress
* **Data Pipeline**: Synthetic data generation and loading into the graph database is complete.
* **AI Core**: Model development is pending.
* **Backend API**: Server development is pending.
* **Frontend UI**: User interface development is pending.

---
### System Architecture (Blueprint)
```mermaid
graph TD
    A[SynthDataGen] --> B{Data Files};
    B --> C[DB Loader];
    C --> D[(Neo4j Graph DB)];
    D --> E[AI Core];
    E --> F[XAI Engine];
    F --> G{Backend API};
    G --> H[Frontend UI];

---
### Documentation

Detailed technical documentation and Project Requirements Documents (PRDs) are located in the `/docs` folder.

- **Primary Document**: For a detailed technical report on the dataset generation methodology, see [**PRD_Synthetic_Dataset.md**](https://www.google.com/search?q=docs/PRD_Synthetic_Dataset.md).

---

### Component Status

- **/SynthDataGen & /docs** - [Complete]
    - **Function**: Generates a realistic, large-scale financial dataset with embedded laundering typologies. All documentation is housed in the `/docs` folder.
- **/models** - [Pending]
    - **Function**: Will contain the hybrid AI core (Autoencoder + GCN) for detecting suspicious networks.
- **/backend** - [Pending]
    - **Function**: Will be a FastAPI server to expose the AI's findings via a REST API.
- **/frontend** - [Pending]
    - **Function**: Will be a React.js application to visualize networks for investigators.

---

### Project Setup and Installation

### Prerequisites

Make sure you have the following software installed on your system:

- **Git**: For version control.
- **Docker Desktop**: To run the Neo4j database container.
- **Python 3.10+**: For the backend, models, and data generation.
- **Node.js and npm**: For the frontend application.