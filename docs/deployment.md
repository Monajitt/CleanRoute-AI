# CleanRoute AI — Local Setup & Deployment Guide

This guide provides instructions for deploying CleanRoute AI locally for development and in production on Render.

---

## 1. System Requirements & Prerequisites

- **Python**: 3.11.x or 3.12.x
- **Database**: PostgreSQL 15+ installed locally or accessible remotely
- **OpenRouteService API Key**: Free account from [openrouteservice.org](https://openrouteservice.org)
- **Git**: Version control client

---

## 2. Local Development Setup

### Step 1: Clone Repository & Create Virtual Environment
```bash
git clone <repository-url>
cd cleanroot

# Create Python virtual environment inside backend/
python -m venv backend/venv

# Activate virtual environment
# On Windows PowerShell:
.\backend\venv\Scripts\Activate.ps1
# On Linux / macOS:
source backend/venv/bin/activate
```

### Step 2: Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### Step 3: Configure Environment Variables
Copy `backend/.env.example` to `backend/.env` and configure your credentials:
```bash
cp backend/.env.example backend/.env
```
Ensure your `backend/.env` contains:
```env
DEBUG=True
SECRET_KEY=your-django-dev-secret-key
DATABASE_NAME=cleanroute_db
DATABASE_USER=postgres
DATABASE_PASSWORD=your_db_password
DATABASE_HOST=localhost
DATABASE_PORT=5432
OPENROUTESERVICE_API_KEY=your_ors_api_key
FRONTEND_URL=http://127.0.0.1:5500
```

### Step 4: Run Migrations & Initialize RAG Knowledge Base
```bash
cd backend
python manage.py migrate
python manage.py init_rag  # Builds local ChromaDB vector embeddings
```

### Step 5: Execute Test Suite
```bash
python manage.py test
```

### Step 6: Launch Backend & Frontend Servers
In Terminal 1 (Backend):
```bash
cd backend
python manage.py runserver 127.0.0.1:8000
```

In Terminal 2 (Frontend):
```bash
python -m http.server 5500 --directory frontend
```

Open your browser and navigate to:  
👉 **`http://localhost:5500`**

---

## 3. Production Deployment on Render

CleanRoute AI is pre-configured for automated 1-click deployment via **Render Blueprints**.

### Option A: Automated Blueprint Deployment (`render.yaml`)
1. Push your repository to GitHub or GitLab.
2. In the [Render Dashboard](https://dashboard.render.com/), click **New** → **Blueprint**.
3. Connect your repository. Render will automatically detect `render.yaml` and configure:
   - **PostgreSQL Database** (`cleanroute-db` on the Free tier)
   - **Web Service** (`cleanroute-backend` with Python runtime, Gunicorn WSGI, and WhiteNoise static asset handling)
4. Add your `OPENROUTESERVICE_API_KEY` under Environment Variables.
5. Click **Apply**. Render will run `./build.sh` (`pip install`, `collectstatic`, `migrate`, `ingest_knowledge`) and launch Gunicorn.

### Option B: Manual Web Service Setup on Render
1. Create a **PostgreSQL Database** on Render:
   - Name: `cleanroute-db`
   - Copy the **Internal Database URL**.
2. Create a **Web Service**:
   - Runtime: `Python 3`
   - Root Directory: `backend`
   - Build Command: `./build.sh`
   - Start Command: `gunicorn config.wsgi:application`
   - Add Environment Variables:
     - `DATABASE_URL`: *(Paste your Internal Database URL)*
     - `PYTHON_VERSION`: `3.11.9`
     - `DEBUG`: `False`
     - `SECRET_KEY`: *(Generate a secure random string)*
     - `ALLOWED_HOSTS`: `.onrender.com`
     - `OPENROUTESERVICE_API_KEY`: *(Your ORS key)*
     - `CORS_ALLOW_ALL_ORIGINS`: `True`
     - `CSRF_TRUSTED_ORIGINS`: `https://*.onrender.com`
3. Click **Deploy**.

---

## 4. Verifying Production Deployment
- **Health Check**: Visit `https://<your-render-url>.onrender.com/api/health/`
- Expected output:
  ```json
  {"status": "success", "database": "connected", "version": "1.0.0"}
  ```
- **Static Assets**: WhiteNoise automatically serves static files from `/static/` with cache-busting headers.
