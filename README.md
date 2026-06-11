# PK-FSL Web Application

This repository contains a FastAPI + static-frontend web application for prior-knowledge-guided small-sample prediction and process optimization.

The system integrates:

- teacher-model training based on prior knowledge data
- small-sample experiment modeling
- auxiliary feature selection
- GAN-based data augmentation and screening
- knowledge distillation / final-model training
- multi-objective optimization
- test-set validation and run logs

## Project Structure

```text
.
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  ├─ core/
│  │  ├─ services/
│  │  └─ utils/
│  ├─ requirements.txt
│  ├─ requirements-full.txt
│  └─ README.md
├─ frontend/
│  └─ static/
│     ├─ index.html
│     ├─ style.css
│     ├─ config.js
│     └─ app.js
├─ Dockerfile
├─ render.yaml
└─ README.md
```

## Features

### 1. Session and sample management

- create an independent run session
- load built-in sample data
- upload Excel / CSV files for different modules

### 2. Teacher model

- upload prior-knowledge data
- select sheet, target, and base features
- train and compare teacher models
- view partial dependence results

### 3. Experiment data modeling

- configure target, base features, and auxiliary features
- compare candidate models
- perform feature selection

### 4. Data enhancement and screening

- generate synthetic data with GAN
- filter generated samples by prediction error constraints

### 5. Final model and optimization

- train the final model with knowledge distillation
- run multi-objective optimization
- export Pareto results and all sampled candidates

### 6. Validation

- evaluate the final model on a test dataset
- compare metrics across models
- inspect prediction details and logs

## Local Run

### Minimal setup

This setup supports the main workflow without optional XGBoost and GAN dependencies.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

### Full setup

If you also want the optional XGBoost model and Step 6 GAN module:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-full.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Deployment

The backend serves the frontend directly through FastAPI static files.

### Render

- build command: `pip install -r backend/requirements.txt`
- start command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

If you need optional GAN / XGBoost features, use:

- build command: `pip install -r backend/requirements-full.txt`

### Frontend split deployment

If you deploy the frontend separately, edit `frontend/static/config.js` and set:

```js
window.__API_BASE__ = "https://<your-backend-domain>";
```

## What to Upload to GitHub

You should upload the source code and deployment/configuration files:

- `backend/app/`
- `backend/requirements.txt`
- `backend/requirements-full.txt`
- `backend/README.md`
- `frontend/static/`
- `Dockerfile`
- `render.yaml`
- `.gitignore`
- `README.md`

You may optionally upload example data and supporting documents if you want others to reproduce your demo:

- `All_Data.xlsx`
- `Web交互框架.xlsx`
- selected figures or screenshots for documentation

## What Not to Upload

These files are local runtime artifacts or temporary outputs and should normally be excluded:

- `backend/.venv/`
- `backend/runs/`
- `tmp_*` directories
- generated screenshots / preview images
- log files

## Tech Stack

- FastAPI
- Uvicorn
- Pandas / NumPy
- scikit-learn
- matplotlib / seaborn
- optional: XGBoost
- optional: PyTorch

## Notes

- the frontend is a static HTML/CSS/JavaScript interface
- the backend API is mounted under `/api`
- the frontend default interface is currently restored to Chinese
