# TrustDoc

TrustDoc is a document forensics AI web application for analyzing documents for authenticity, metadata anomalies, and AI-generated content.

## Stack

| Layer    | Technology                          |
| -------- | ----------------------------------- |
| Backend  | FastAPI, Uvicorn, Celery, Redis     |
| Frontend | React, Vite, Tailwind CSS           |
| Database | Supabase                            |
| LLM      | Google Gemini API                   |

## Project Structure

```
TrustDoc/
├── backend/          # FastAPI application
├── frontend/         # React + Tailwind application
└── README.md
```

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- Redis (for Celery background tasks)
- [ExifTool](https://exiftool.org/) installed on your system (required by pyexiftool)

## Backend Setup

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Supabase and Gemini credentials

uvicorn app.main:app --reload --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
# Edit .env with your Supabase and API URLs

npm run dev
```

App: [http://localhost:5173](http://localhost:5173)

## Environment Variables

### Backend (`backend/.env`)

| Variable               | Description                    |
| ---------------------- | ------------------------------ |
| `SUPABASE_URL`         | Supabase project URL           |
| `SUPABASE_ANON_KEY`    | Supabase anonymous key         |
| `SUPABASE_SERVICE_KEY` | Supabase service role key      |
| `GEMINI_API_KEY`       | Google Gemini API key          |

### Frontend (`frontend/.env`)

| Variable                 | Description              |
| ------------------------ | ------------------------ |
| `VITE_SUPABASE_URL`      | Supabase project URL     |
| `VITE_SUPABASE_ANON_KEY` | Supabase anonymous key   |
| `VITE_API_URL`           | Backend API base URL     |

## License

See [LICENSE](LICENSE).
