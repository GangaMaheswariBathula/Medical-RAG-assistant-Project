# Medical RAG Assistant

A document-grounded medical information assistant. Upload PDF, TXT, or DOCX documents, index their text in Pinecone, and ask questions through a Streamlit chat interface. The FastAPI service retrieves relevant document chunks and sends those chunks with the question to a Groq-hosted language model. Answers include source filenames and page numbers when the document loader provides page metadata.

> **Important:** This project is for learning and document search. It is not a medical device and does not replace a qualified healthcare professional. Answers depend on the documents you upload and may be incomplete or wrong. Do not use it for diagnosis, treatment decisions, emergencies, or as a substitute for professional advice.

## Contents

- [How it works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Get API keys](#get-api-keys)
- [Install and configure on Windows](#install-and-configure-on-windows)
- [Run the application](#run-the-application)
- [Use the application](#use-the-application)
- [Run tests](#run-tests)
- [Evaluate answers](#evaluate-answers)
- [API endpoints](#api-endpoints)
- [Configuration](#configuration)
- [Deploy to Render](#deploy-to-render)
- [Troubleshooting](#troubleshooting)
- [Project layout](#project-layout)
- [Privacy and security](#privacy-and-security)

## How it works

1. The UI sends an uploaded document to the FastAPI service.
2. The API extracts text from the document, cleans it, splits it into overlapping chunks, and generates embeddings locally with Sentence Transformers.
3. The API stores the vectors and chunk metadata in a Pinecone serverless index. On first use, the app creates the index if it does not already exist.
4. When you ask a question, the API embeds it, retrieves the most similar chunks, and filters out chunks below the configured similarity score.
5. The API sends the question and retrieved text to Groq and returns the answer with its source chunks.

The default embedding model is `BAAI/bge-small-en-v1.5` (384 dimensions). The default Groq model is `openai/gpt-oss-120b`. Model availability and account access can change; check Groq's [supported models](https://console.groq.com/docs/models) if you receive a model error.

## Prerequisites

- Python 3.12 recommended
- Internet access for package installation, initial embedding model download, Groq, and Pinecone
- A Groq API key
- A Pinecone API key and an account that can create serverless indexes
- Windows PowerShell for the main instructions below (macOS/Linux commands are included where relevant)

## Get API keys

1. Create or sign in to a Groq account at [console.groq.com](https://console.groq.com/) and create an API key.
2. Create or sign in to Pinecone at [pinecone.io](https://www.pinecone.io/) and create an API key.
3. Keep both keys private. Put them only in the local `.env` file or in your hosting provider's secret settings. Never commit `.env` to Git.

## Install and configure on Windows

Run these commands from the project root (`RAG-PRO`). In VS Code, choose **File → Open Folder** and open this project, then choose **Terminal → New Terminal**.

Check Python:

```powershell
python --version
```

Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell says script execution is disabled, allow activation only for the current terminal process, then activate:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

The terminal prompt should show `(venv)` when the environment is active. Install the API, development, and UI packages:

```powershell
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -r requirements-frontend.txt
```

The first API startup downloads the embedding model (about 130 MB), so it can take longer than later starts.

Create your local environment file:

```powershell
Copy-Item .env.example .env
```

Open `.env` in a text editor and replace the placeholder values:

```dotenv
GROQ_API_KEY=paste_your_groq_key_here
PINECONE_API_KEY=paste_your_pinecone_key_here
```

Save the file. Do not include quotes unless they are part of the key. The `.env` file is ignored by Git.

### macOS/Linux alternative

From the project root:

```bash
python3.12 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -r requirements-frontend.txt
cp .env.example .env
```

Then edit `.env` and add the two API keys. Run the same `uvicorn` and `streamlit` commands shown below.

## Run the application

The API and UI run in separate terminals. Keep both terminals open while using the app.

### Terminal 1: FastAPI backend

Open a terminal in the project root, activate the virtual environment if it is not already active, then run:

```powershell
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

The `--reload` option restarts the API when Python source files change. For a normal local run without automatic reload, omit `--reload`.

Check the service:

- Health response: [http://localhost:8000/health](http://localhost:8000/health)
- Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

The health endpoint reports whether the two key values are configured. It does not verify that the keys are valid or that the external services are reachable.

### Terminal 2: Streamlit frontend

Open a second terminal in the project root and run:

```powershell
.\venv\Scripts\Activate.ps1
streamlit run frontend/streamlit_app.py
```

Streamlit prints a local URL, usually [http://localhost:8501](http://localhost:8501). Open that address in your browser. The sidebar's API URL should be `http://localhost:8000` for a local backend.

To stop either service, focus its terminal and press **Ctrl+C**. After changing `.env`, restart the API so it reloads the settings.

## Use the application

1. Open the Streamlit page at `http://localhost:8501`.
2. In the sidebar, leave **API URL** as `http://localhost:8000` for local use.
3. Upload one or more PDF, TXT, or DOCX files. Each file must be no larger than 10 MB.
4. Click **Index documents** and wait for the per-file success message.
5. Ask a question in the chat box. Answers are based on retrieved text from indexed documents and show source excerpts, filenames, and page numbers where available.
6. Use **Limit to one filename** to restrict retrieval to an uploaded filename, or **Show index stats** to see the Pinecone index vector count.

A scanned PDF that contains only page images has no extractable text. Run OCR on it first and upload the searchable PDF, or upload a text-based source document. The app does not perform OCR.

Reindexing and storage: vectors are stored in your Pinecone index and persist between app runs. The index name defaults to `medical-rag`; use a different index name if you want to keep this app's vectors separate from other data in the same Pinecone project.

## Run tests

With the virtual environment active and development requirements installed:

```powershell
pytest
```

The unit and API tests use fakes for external services, so they do not require working Groq or Pinecone API keys. The guide's expected result is 21 passing tests.

## Evaluate answers

Evaluation sends questions to the running API and compares retrieved text and answers with expected keywords. The supplied `evaluation/eval_questions.json` is an example; edit it so questions, expected keywords, and `in_scope` values match the documents you indexed.

With the API running, open another terminal in the project root, activate the virtual environment, and run:

```powershell
python -m evaluation.evaluate --api http://localhost:8000
```

To also ask Groq to judge whether answer claims are supported by retrieved sources, use:

```powershell
python -m evaluation.evaluate --api http://localhost:8000 --judge
```

The evaluation prints a report and saves it as `evaluation/report.md` (which is excluded from Git). The judge option makes additional Groq requests. Evaluation is only a lightweight project metric; it does not establish clinical accuracy or safety.

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Reports service status and whether API keys are configured. |
| `POST` | `/upload` | Uploads and indexes one PDF, TXT, or DOCX file as multipart form data (`file`). |
| `POST` | `/ask` | Accepts JSON with `question`, and optional `top_k` and `filename`; returns an answer, sources, and latency. |
| `GET` | `/sources` | Retrieves source chunks without calling the language model. Requires a `question` query parameter; accepts optional `top_k` and `filename`. |
| `GET` | `/stats` | Returns Pinecone index name and vector count. |

Interactive request examples are available at `http://localhost:8000/docs` while the API is running. The default question limit is 1,000 characters; `top_k` can be from 1 to 10.

Example `/ask` request:

```json
{
  "question": "What symptoms does the document list?",
  "top_k": 4
}
```

## Configuration

Settings are read from environment variables and `.env`. Environment variable names use uppercase, such as `LLM_MODEL`; the corresponding Python setting names are shown below.

| Environment variable | Default | Purpose |
|---|---|---|
| `GROQ_API_KEY` | empty | Groq API key; required for generated answers. |
| `PINECONE_API_KEY` | empty | Pinecone API key; required for indexing and retrieval. |
| `PINECONE_INDEX_NAME` | `medical-rag` | Serverless index name. |
| `PINECONE_CLOUD` | `aws` | Pinecone serverless cloud provider. |
| `PINECONE_REGION` | `us-east-1` | Pinecone serverless region used when creating the index. |
| `LLM_MODEL` | `openai/gpt-oss-120b` | Groq chat model ID. |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Local Sentence Transformers embedding model (must produce 384 dimensions for the default index). |
| `CHUNK_SIZE` | `800` | Text chunk size in characters. |
| `CHUNK_OVERLAP` | `150` | Character overlap between adjacent chunks. |
| `TOP_K` | `4` | Number of candidate chunks retrieved per question. |
| `MIN_SCORE` | `0.35` | Similarity threshold; retrieved chunks below it are discarded. |

Optional settings can be added as active lines in `.env`, for example:

```dotenv
PINECONE_INDEX_NAME=medical-rag
LLM_MODEL=openai/gpt-oss-120b
TOP_K=4
MIN_SCORE=0.35
```

If you change the embedding model, confirm its output dimension matches `EMBEDDING_DIMENSION` and the dimension of the Pinecone index. Existing Pinecone indexes cannot be used with vectors of a different dimension.

## Deploy to Render

The included `render.yaml` defines two Render web services: `medical-rag-api` and `medical-rag-ui`.

1. Push this project to a GitHub repository. Make sure `.env` is not committed; `.gitignore` excludes it.
2. In Render, choose **New → Blueprint** and connect the repository containing `render.yaml`.
3. Create the services from the blueprint.
4. In the API service settings, add `GROQ_API_KEY` and `PINECONE_API_KEY` as secret environment variables.
5. Deploy the API and check `https://<api-service-name>.onrender.com/health`.
6. Set the UI service's `API_URL` to the API service URL, such as `https://medical-rag-api.onrender.com`, then deploy the UI.
7. Open the UI service URL and upload a document to confirm it can reach the API.

The API uses the Render Starter plan in the blueprint because loading the embedding model needs more memory than the 512 MB free plan usually provides. The UI uses the free plan. Hosting plans and provider settings can change; confirm current costs and limits in Render before deploying. Never put API keys in source files or the Git repository.

## Troubleshooting

| Symptom | What to check |
|---|---|
| `503` and `GROQ_API_KEY is not set` | Confirm `.env` exists in the project root, contains `GROQ_API_KEY=...`, and restart the API. |
| Groq returns `404 model_not_found` | The model may have been retired or may not be enabled for your account. Set `LLM_MODEL` in `.env` to a model available to your Groq account (the current project default is `openai/gpt-oss-120b`) and restart the API. Check Groq's [model list](https://console.groq.com/docs/models). |
| `503` and Pinecone unavailable | Check `PINECONE_API_KEY`, the Pinecone project, and whether your account can create serverless indexes in the configured cloud and region. |
| The UI says it cannot reach the API | Make sure the API terminal is still running and that the sidebar API URL is correct. Local default: `http://localhost:8000`. |
| Answers always say there is not enough information | Check that indexing succeeded and that the document contains the answer. Try lowering `MIN_SCORE` (for example, `MIN_SCORE=0.2`) and restart the API. |
| `No readable text found` | The file may be blank or a scanned PDF. OCR scanned pages first. |
| Upload is rejected | Only `.pdf`, `.txt`, and `.docx` files up to 10 MB are accepted by default. |
| Port 8000 or 8501 is already in use | Stop the other process using the port, or run the service on another port and update the API URL accordingly. |
| Python package installation fails | Confirm Python 3.12 is selected, the virtual environment is active, and the terminal has internet access. |

## Project layout

```text
RAG-PRO/
├── app/
│   ├── api/             # FastAPI routes
│   ├── chains/          # Retrieval and answer generation pipeline
│   ├── embeddings/      # Local embedding model
│   ├── loaders/         # PDF, TXT, DOCX loading and chunking
│   ├── prompts/         # Grounded-answer prompt
│   ├── services/        # Groq LLM integration
│   ├── utils/            # Text cleaning and validation
│   ├── vectorstore/     # Pinecone integration
│   ├── config.py        # Environment-based settings
│   ├── dependencies.py  # Shared API dependencies
│   ├── exceptions.py    # Application errors
│   └── main.py          # FastAPI application
├── data/                # Local placeholder; uploaded files are processed temporarily
├── docs/                # Documentation space
├── evaluation/          # Evaluation questions and evaluation runner
├── frontend/            # Streamlit UI
├── tests/               # Unit and API tests
├── .env.example         # Environment variable template
├── .gitignore
├── pytest.ini
├── render.yaml          # Render blueprint
├── requirements.txt     # API dependencies
├── requirements-dev.txt # API plus test dependencies
└── requirements-frontend.txt
```

## Privacy and security

- Keep `.env` private and rotate a key immediately if it is exposed.
- Uploaded file bytes are processed through a temporary file and deleted after ingestion. Extracted chunks and embeddings are stored in Pinecone; prompts containing retrieved chunks and your question are sent to Groq for answer generation.
- Use only documents you are permitted to process, and review Groq and Pinecone data handling terms for your account before uploading sensitive or identifiable health information.
- The local app is intended for development. Before exposing it publicly, add authentication, restrict CORS origins, configure secure secret management, and review upload and data retention requirements.
#   M e d i c a l - R A G - a s s i s t a n t - P r o j e c t  
 