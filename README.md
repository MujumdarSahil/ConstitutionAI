# ConstitutionAI 🇮🇳⚖️

> An AI-powered personal tutor for the Indian Constitution, built for UPSC Civil Services aspirants.

ConstitutionAI uses Retrieval-Augmented Generation (RAG) to teach every constitutional article in depth — with historical context, landmark judgements, amendments, and UPSC exam strategy. It tracks your progress, applies spaced repetition, and generates quizzes after each session.

---

## Features

- 📖 **Article-by-Article Teaching** — Structured lessons covering all 7 constitutional dimensions
- 🤖 **Dual AI Providers** — Groq (primary) with automatic Google Gemini fallback
- 📄 **RAG Pipeline** — ChromaDB + sentence-transformers for accurate article retrieval
- 📊 **Spaced Repetition** — Articles scored below 60% resurface for review in 3 days
- 🧠 **UPSC Quiz Engine** — 3 MCQ + 2 match-the-following + 1 short answer per session
- 💾 **Session Persistence** — All progress saved in MongoDB; survives app restarts
- 🔴 **Streaming Lessons** — SSE-powered live typing effect, no waiting for full response
- 📅 **Progress Tracking** — Streak counter, heatmap calendar, weak topics dashboard
- 🚀 **Single-Command Launch** — Start frontend + backend together with `python main.py`

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Required for match statements |
| Node.js | 18+ | LTS recommended |
| MongoDB | 6.0+ | Must be running locally on `mongodb://localhost:27017` |
| Groq API Key | — | Free at [console.groq.com](https://console.groq.com) |
| Gemini API Key | — | Free at [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| Constitution PDF | — | See below |

---

## Getting Your API Keys

### Groq (Primary AI — Free)
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up / log in
3. Navigate to **API Keys** → **Create API Key**
4. Copy the key starting with `gsk_...`

### Google Gemini (Fallback — Free)
1. Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click **Create API Key**
4. Copy the key starting with `AIza...`

---

## Getting the Constitution PDF

Download the official text from:
- **Legislative.gov.in** (official): https://legislative.gov.in/constitution-of-india/
- Or search: "Constitution of India PDF download official"

Place the PDF at: `backend/data/constitution.pdf`

---

## 🚀 Quick Start (Recommended)

Follow these steps **once** to set everything up. After that, a single command starts the whole project.

### Step 1 — Clone the repository

```bash
git clone <your-repo-url>
cd ConstitutionAI
```

### Step 2 — Start MongoDB

MongoDB must be running before you launch the app.

```bash
# Windows — if installed as a service
net start MongoDB

# Windows — manual start
mongod --dbpath C:\data\db

# macOS / Linux
mongod --dbpath /data/db
```

> **Connection string used by the app:** `mongodb://localhost:27017`
> Database name: `jarvis`

### Step 3 — Create a Python virtual environment

```bash
# From the project root
python -m venv venv

# Activate — Windows
venv\Scripts\activate

# Activate — macOS / Linux
source venv/bin/activate
```

### Step 4 — Install Python dependencies

```bash
pip install -r backend/requirements.txt
```

### Step 5 — Configure environment variables

```bash
# Windows
copy backend\.env.example backend\.env

# macOS / Linux
cp backend/.env.example backend/.env
```

Now open `backend/.env` and fill in your keys:

```env
GROQ_API_KEY=gsk_your_groq_key_here
GEMINI_API_KEY=AIza_your_gemini_key_here
MONGODB_URI=mongodb://localhost:27017
DB_NAME=jarvis
CHROMA_DB_PATH=./chroma_db
PDF_PATH=./data/constitution.pdf
```

### Step 6 — Place the Constitution PDF

```
ConstitutionAI/
└── backend/
    └── data/
        └── constitution.pdf   ← place your PDF here
```

### Step 7 — Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

---

## ▶️ Running the Project

Once setup is complete, **just run one command** from the project root:

```bash
python main.py
```

This will:
- ✅ Start the **FastAPI backend** on `http://localhost:8000`
- ✅ Start the **Vue/Vite frontend** on `http://localhost:5173`
- ✅ Auto-install `node_modules` if they are missing
- ✅ Create `backend/.env` from the example if it doesn't exist

Open your browser at → **http://localhost:5173**

Press **Ctrl+C** to stop both servers.

---

## First-Time Usage

1. Open the app at **http://localhost:5173**
2. The backend auto-triggers PDF ingestion on startup (takes 2–5 minutes the first time)
3. Watch the terminal for:
   ```
   ✅  MongoDB connected
   ✅  Constitution PDF found
   ✅  Auto-ingestion complete: N articles embedded
   🚀  ConstitutionAI ready at http://localhost:8000
   ```
4. If you see a "Setup required" banner, click **Run Setup**
5. Click **Start Today's Session** on the dashboard

---

## Project Structure

```
ConstitutionAI/
├── main.py                      # ← Run this to start everything
├── README.md
├── backend/
│   ├── main.py                  # FastAPI app entrypoint
│   ├── config.py                # Environment configuration
│   ├── requirements.txt
│   ├── .env.example             # Copy this to .env
│   ├── .env                     # Your secrets (not in git)
│   ├── agents/
│   │   ├── tutor_agent.py       # Constitutional law lesson generator
│   │   ├── session_planner.py   # Session planning + motivational messages
│   │   └── test_generator.py    # Quiz generation + grading
│   ├── core/
│   │   ├── llm_provider.py      # Groq + Gemini with failover
│   │   ├── pdf_ingestion.py     # PDF parse + article chunking
│   │   ├── rag_pipeline.py      # ChromaDB embed + retrieval
│   │   └── session_manager.py   # Progress tracking + spaced repetition
│   ├── db/
│   │   ├── mongodb.py           # Motor async client
│   │   └── models.py            # Pydantic models
│   ├── routers/
│   │   ├── session.py           # Session lifecycle endpoints
│   │   ├── teach.py             # SSE lesson streaming + setup
│   │   ├── test.py              # Quiz endpoints
│   │   └── progress.py          # Progress + article endpoints
│   └── data/
│       └── constitution.pdf     # ← Place your PDF here
└── frontend/
    ├── src/
    │   ├── views/
    │   │   ├── HomeView.vue     # Dashboard
    │   │   ├── LearnView.vue    # Streaming lesson UI
    │   │   ├── TestView.vue     # Quiz UI
    │   │   ├── ProgressView.vue # Analytics + heatmap
    │   │   └── RevisionView.vue # Article browser
    │   ├── stores/
    │   │   ├── session.js       # Pinia session state
    │   │   └── progress.js      # Pinia progress state
    │   └── components/
    │       ├── ArticleCard.vue
    │       ├── LessonPanel.vue
    │       ├── QuizQuestion.vue
    │       ├── ScoreBadge.vue
    │       ├── ProgressTimeline.vue
    │       └── ProviderStatus.vue
    └── package.json
```

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | System health check |
| `/api/setup` | POST | Trigger PDF ingestion (streaming) |
| `/api/session/plan` | GET | Get today's study plan |
| `/api/session/start` | POST | Create a new session |
| `/api/session/end` | POST | End and save a session |
| `/api/teach/{article_id}` | GET | Stream lesson via SSE |
| `/api/test/{session_id}` | GET | Generate quiz |
| `/api/test/submit` | POST | Submit and grade an answer |
| `/api/progress` | GET | Full progress summary |
| `/api/articles` | GET | All articles with progress |
| `/api/articles/{id}/jump` | GET | Revision mode for an article |

API docs (Swagger UI): http://localhost:8000/docs

---

## MongoDB

| Setting | Value |
|---------|-------|
| Connection string | `mongodb://localhost:27017` |
| Database name | `jarvis` |
| Collections | `sessions`, `article_progress`, `test_results` |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| MongoDB connection error | Run `mongod` or start MongoDB service — connection string: `mongodb://localhost:27017` |
| PDF not found | Place PDF at `backend/data/constitution.pdf` |
| API key errors | Check `backend/.env`, ensure keys are valid |
| ChromaDB empty after setup | Run `POST /api/setup` or restart the app |
| Groq rate limit | Gemini fallback activates automatically |
| Frontend can't reach backend | Ensure backend runs on port 8000 |
| `npm` not found | Install Node.js 18+ from https://nodejs.org |
| `python` not found | Ensure Python 3.11+ is installed and in PATH |

---

## Technology Stack

- **Backend**: Python 3.11, FastAPI, Motor (async MongoDB)
- **AI**: Groq (llama-3.3-70b-versatile) → Gemini (gemini-1.5-flash) failover
- **Vector Store**: ChromaDB with all-MiniLM-L6-v2 embeddings
- **Database**: MongoDB (local) — `mongodb://localhost:27017`
- **Frontend**: Vue 3, Vite, Pinia, Vue Router
- **PDF Parsing**: PyMuPDF (fitz)

---

## License

See [LICENSE](LICENSE) for details.
