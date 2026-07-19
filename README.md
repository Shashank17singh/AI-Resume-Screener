<div align="center">

# 🧑‍💼 AI Resume Screener
**An LLM-powered pipeline that parses resumes and job descriptions into structured data — then ranks candidates by fit**

[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Groq](https://img.shields.io/badge/Groq-openai--gpt--oss--120b-F55036?style=for-the-badge&logoColor=white)](https://groq.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-Schema%20Validation-E92063?style=for-the-badge&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![pypdf](https://img.shields.io/badge/pypdf-PDF%20Parsing-2C8EBB?style=for-the-badge&logoColor=white)](https://pypdf.readthedocs.io/)
[![python--docx](https://img.shields.io/badge/python--docx-DOCX%20Parsing-2B579A?style=for-the-badge&logoColor=white)](https://python-docx.readthedocs.io/)

</div>

---

## 📖 Overview

A resume-screening tool built with Streamlit, Groq, and Pydantic. Paste a job description and upload a batch of resumes (PDF or DOCX) — the app extracts structured data from both, scores every candidate against the role's requirements, and returns a ranked shortlist with matching and missing skills called out per candidate.

---



### 🏗️ Extraction & Scoring Pipeline

`mermaid
graph TD
    subgraph "Input Layer"
    A[Job Description]
    B[Candidate Resumes PDF/DOCX]
    end
    
    subgraph "Processing Engine"
    B -->|pypdf / python-docx| C(Raw Text Extraction)
    C --> D{Prompt Injection}
    A --> D
    D -->|Strict JSON Schema| E(Groq LLM)
    E -->|Pydantic Validation| F[Structured Candidate Profile]
    end
    
    subgraph "Ranking Logic"
    F --> G(Scoring Algorithm)
    A --> G
    G --> H[Ranked Shortlist with Match Details]
    H --> I[Streamlit Dashboard]
    end
    
    classDef io fill:#f9f0ff,stroke:#8a2be2,stroke-width:2px,color:#000;
    classDef core fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#000;
    classDef logic fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#000;
    
    class A,B,I io;
    class C,F,H core;
    class D,E,G logic;
`

## ✨ Features

| | |
|---|---|
| 📋 **Structured JD Parsing** | Extracts role, required/preferred skills, minimum experience, education, and responsibilities from raw job description text |
| 📄 **Multi-Resume Upload** | Screen a whole batch of PDF/DOCX resumes in one run |
| 🧩 **Schema-Driven Extraction** | Resumes are parsed into a fixed Pydantic schema regardless of formatting or section headings |
| ⚡ **Groq-Powered LLM** | Fast structured-JSON inference via `openai/gpt-oss-120b` |
| 🔁 **Retry with Backoff** | LLM calls retry with exponential backoff instead of failing the whole batch on one hiccup |
| 💾 **Resume Caching** | Parsed resumes are cached by file hash, so re-screening against a new JD skips redundant LLM calls |
| 🛡️ **Per-File Error Isolation** | A corrupt or scanned resume is reported and skipped, not a batch-ending crash |
| 📊 **Ranked Shortlist UI** | Clean Streamlit view of candidates sorted by match score, with skill gaps highlighted |

---

## 🧠 Architecture

```
Job Description (text)              Resumes (PDF / DOCX)
        │                                    │
        ▼                                    ▼
  LLM → JobDescription schema      pypdf / python-docx → raw text
        │                                    │
        │                                    ▼
        │                          LLM → Resume schema
        │                          (cached by file hash)
        │                                    │
        └───────────────┬────────────────────┘
                         ▼
              LLM → MatchResult schema
        (score, matching/missing skills, verdict)
                         │
                         ▼
              Ranked Shortlist (Streamlit) 📊
```

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Frontend | Streamlit |
| LLM | Groq — `openai/gpt-oss-120b` |
| Schema Validation | Pydantic |
| PDF Parsing | pypdf |
| DOCX Parsing | python-docx |
| Resilience | Custom retry/backoff wrapper + disk cache |

---

## ⚙️ Setup and Installation

### Prerequisites
- Python 3.11+
- A [Groq API key](https://console.groq.com/keys)

### 1. Clone the repository
```bash
git clone https://github.com/Shashank17singh/ai-resume-screener.git
cd ai-resume-screener
```

### 2. Install dependencies
```bash
pip install -e .
```

### 3. Set your Groq API key
```bash
cp .env.example .env
# then edit .env and add: GROQ_API_KEY=your_api_key_here
```

### 4. Run the app
```bash
streamlit run app.py
```
Open the local URL Streamlit prints in your terminal, paste a job description, upload resumes, and screen candidates.

---

## 📂 Project Structure

```
ai-resume-screener/
├── app.py            # Streamlit UI
├── pipeline.py        # Batch screening: caching + per-file error isolation
├── parsing.py          # JD / resume → structured Pydantic data
├── scorer.py            # Candidate vs. JD scoring
├── llm_client.py          # Groq wrapper with retry/backoff
├── file_readers.py         # PDF / DOCX text extraction
├── models.py                # Pydantic schemas
└── .env.example
```

---

## ⚠️ Known Limitations

- Scores are LLM-judged rather than a fixed formula, so they can vary slightly between runs on the same inputs.
- Scanned/image-only PDFs with no extractable text are skipped (reported as a failure, not silently dropped).
