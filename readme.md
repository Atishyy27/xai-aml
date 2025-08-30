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