Markdown
# 🛡️ Agentic AI Code Review & Security Intelligence System

An enterprise-grade, autonomous code review and security auditing platform powered by **LangGraph**, **Retrieval-Augmented Generation (RAG)**, and **Machine Learning**. 

This platform acts as an intelligent virtual reviewer that orchestrates multiple AI agents to perform automated static analysis, security vulnerability detection, risk score calculation, and pull request (PR) merge outcome prediction.

---

## ✨ Key Features

- **🤖 Multi-Agent Orchestration**: Built with LangGraph using a Supervisor-Agent topology for dynamic routing, state management, and continuous reflection.
- **📚 Domain-Aware RAG Engine**: Indexes repository history and query bases using local embedding models for contextual code retrieval and dynamic prompt augmentation.
- **🔮 Predictive ML Engine**: Uses trained Machine Learning models (`RandomForest`, `LogisticRegression`) to evaluate code metrics and predict PR merge status.
- **🛡️ Enterprise Guardrails**: Strict input/output validation, prompt injection protection, and schema enforcement to guarantee safe LLM operations.
- **🚨 Advanced Security Engine**: Static code scanning, custom threat classification, and risk evaluation engines for proactive vulnerability detection.
- **📊 Evaluation Suite**: Built-in benchmark tools for routing evaluation, model comparison, and framework quality metrics.
- **🖥️ Interactive UI & API**: Streamlit-driven user dashboard combined with CLI utility workflows.

---

## 🏗️ System Architecture

                   +-------------------+
                   |   Streamlit UI /  |
                   |    CLI Engine     |
                   +---------+---------+
                             |
                             v
                   +-------------------+
                   |  Supervisor Agent |
                   +---------+---------+
                             |
    +------------------------+------------------------+
    |                        |                        |
    v                        v                        v
+---------------+        +---------------+        +---------------+
| Code Review   |        | Security &    |        | PR Merge      |
| Agent (RAG)   |        | Risk Agent    |        | Predictor(ML) |
+-------+-------+        +-------+-------+        +-------+-------+
|                        |                        |
+------------------------+------------------------+
|
v
+-------------------+
| Reflection &      |
| Output Guardrails |
+-------------------+


---

## 📂 Project Structure

```text
person2_integrated/
├── README.md                     # Project documentation
├── requirements.txt              # System dependencies
├── evaluation/                   # Evaluation & bench-marking suites
│   ├── EVALUATION.md
│   ├── merge_prediction_comparison.py
│   └── supervisor_routing_eval.py
├── models/                       # Trained ML artifacts & feature schemas
│   ├── feature_columns.json
│   ├── logistic_regression.pkl
│   └── random_forest.pkl
├── src/                          # Core source code
│   ├── agents/                   # Agent definitions (Supervisor, etc.)
│   ├── guardrails/               # Security, input/output validation
│   ├── ml/                       # ML pipeline (Data collection, Training, Inference)
│   ├── rag/                      # Vector embedding, indexing & retrieval
│   ├── reflection/               # Agent output refinement & reflection
│   ├── review/                   # Code review logic & LLM client wrapper
│   ├── security/                 # Threat classification & risk engine
│   ├── tools/                    # Static analysis & GitHub tools
│   ├── conditions.py             # Graph state transition logic
│   ├── feature_bridge.py         # Feature engineering bridge for ML/RAG
│   ├── main_security_scan.py     # Main security scanning script
│   ├── nodes.py                  # LangGraph operational nodes
│   ├── state.py                  # Graph state definitions
│   └── workflow.py               # LangGraph compiled pipeline execution
└── ui/                           # User Interface components
    └── app.py                    # Streamlit web interface
🚀 Quick Start Guide
1. Prerequisites
Ensure you have Python 3.9+ installed on your environment.

2. Installation
Clone the repository and install the required dependencies:

Bash
# Clone the repository
git clone [https://github.com/your-org/code-review-security-ai.git](https://github.com/your-org/code-review-security-ai.git)
cd person2_integrated

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
3. Environment Configuration
Create a .env file in the root directory and add your API credentials:

Ini, TOML
OPENAI_API_KEY=your_openai_api_key
GITHUB_TOKEN=your_github_personal_access_token
LOG_LEVEL=INFO
💻 Usage
Launching the Streamlit Web Application
To run the interactive UI dashboard:

Bash
streamlit run ui/app.py
Running Automated Security Scanning
Run a full static security analysis over your target codebase:

Bash
python src/main_security_scan.py --path /path/to/target/repository
Training the PR Merge Prediction Model
To retrain or evaluate the machine learning models:

Bash
python src/ml/train.py
python evaluation/merge_prediction_comparison.py
🧪 Running Benchmarks & Evaluations
Run the supervisor routing benchmark and evaluation suite to verify system accuracy:

Bash
# Evaluate Agent Supervisor Routing Decisions
python evaluation/supervisor_routing_eval.py

# Check Evaluation Specs
cat evaluation/EVALUATION.md
🛠️ Built With
Orchestration: LangGraph / LangChain

ML Framework: Scikit-Learn, Pandas, NumPy

Vector Indexing & RAG: Local Embeddings & Vector Search

Web UI: Streamlit

Code Parsing & Security: Custom AST / Static Analysis Analyzers

📜 License
Distributed under the MIT License. See LICENSE for more information.