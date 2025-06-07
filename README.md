# Cybersecurity Agentic RAG System

This project implements a Retrieval Augmented Generation (RAG) system tailored for cybersecurity knowledge. It features agents that can query a specialized vector database populated with diverse cybersecurity documents and threat intelligence.

## Features

- **Vector Database:** Utilizes ChromaDB to store and query cybersecurity knowledge.
- **Document Processing:** Ingests and processes various document types including PDFs, JSON, CSV, and TXT files.
- **Multiple Data Sources:** Populates the database with:
  - Incident Response Playbooks (PDFs)
  - Prevention Framework Documents (PDFs)
  - MITRE ATT&CK Enterprise Framework (JSON)
  - Threat Intelligence Feeds:
    - Feodo Tracker IP Blocklist (JSON)
    - CISA Known Exploited Vulnerabilities (JSON)
    - Emerging Threats IP Blocklist (TXT)
    - URLHaus Malicious URL Links (CSV)
- **Agent-Specific Search:** Allows for knowledge retrieval filtered by agent type (e.g., incident_response, threat_intelligence, prevention) as well as shared knowledge.
- **Modular Design:** Code is structured into directories for data processing, database management, and application logic.

## Project Structure

```
cybersecurity-agentic-rag/
├── agents/               # (Likely for agent-specific logic - to be developed)
├── data/
│   └── raw/              # Raw data files organized by type
│       ├── incident_response/
│       ├── framework_basics/
│       ├── mitre_attack/
│       └── threat_intelligence/
├── database/
│   ├── chromadb/         # Persistent storage for ChromaDB
│   ├── document_processor.py # Script for processing raw data
│   └── vector_db.py      # Class for interacting with the vector database
├── utils/                # (Likely for utility functions - to be developed)
├── app.py                # Main application to populate and test the database
├── cli.py                # (Likely for command-line interface - to be developed)
├── requirements.txt      # Python package dependencies
└── README.md             # This file
```

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd cybersecurity-agentic-rag
    ```
2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Populate `data/raw/` directory:**
    - Ensure the following directories exist under `data/raw/`:
      - `incident_response/` (add your PDF playbooks here)
      - `framework_basics/` (add your PDF prevention framework documents here)
      - `mitre_attack/` (should contain `enterprise-attack.json`)
      - `threat_intelligence/` (should contain `ipblocklist.json`, `known_exploited_vulnerabilities.json`, `emerging-Block-IPs.txt`, `urlhaus_links.csv`)
    - Download or place the necessary data files into these directories according to the types listed under "Data Sources".

## Usage

To populate the database and run test searches:

```bash
python app.py
```

This will:

1.  Process all documents from the `data/raw/` directory.
2.  Populate the ChromaDB vector store.
3.  Print database population statistics.
4.  Run a series of test searches for different agent types and print the results.

## Further Development Ideas

- Implement specific agent logic in the `agents/` directory.
- Develop a more interactive user interface (e.g., using Streamlit, or a CLI through `cli.py`).
- Add more data sources and document processors.
- Implement advanced RAG chain logic with LLMs.
