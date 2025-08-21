# Vocal – Minimal Web App for Vocal Removal

This repository contains a minimal, deployable MVP for removing vocals from songs.

- Frontend: Vite + React single page with drag-and-drop/click-to-upload, progress indicator, playback, and download links.
- Backend: FastAPI endpoint that runs Demucs (two-stem) to split an audio file into vocals and instrumental, and serves the resulting files.

No login/auth required.

## Prerequisites

- Python 3.12+
- Node.js 18+ (with npm, yarn, or pnpm)
- ffmpeg installed (required by Demucs/torchaudio in many environments)

On Ubuntu/Debian:
```
sudo apt-get update && sudo apt-get install -y ffmpeg
```

First run will download Demucs model weights (hundreds of MB), so initial processing can take several minutes.

## Local Setup

Clone the repo and create a virtual environment:

```
cd vocal
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r backend/requirements.txt
```

Start the backend:

```
uvicorn app.main:app --reload --port 8000 --app-dir backend
```

Status/progress endpoint:
- Check a job status: `GET http://localhost:8000/api/status/{job_id}` returns one of `not_found | running | done`.

In another terminal, start the frontend:

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Usage

1. Drag-and-drop or click to upload an audio file (mp3, wav, flac, m4a, ogg).
2. Wait while the backend processes the track (spinner shown).
3. On completion, two audio players appear:
   - Instrumental
   - Vocals
4. Use the Download buttons to save each stem.

Outputs are served from the backend under `/files/{job_id}/...` and stored in `backend/storage/{job_id}`.
Temporary upload data is cleaned after each job from `backend/tmp`.

## Notes and Limitations

- This MVP runs inference on CPU; processing time depends on file length and machine performance.
- There is no authentication or persistence beyond storing output files for each job.
- Consider using small test files during development.

## Developing

- Backend code: `backend/app/main.py`
- Frontend entry: `frontend/src/App.tsx`, `frontend/src/main.tsx`
- Proxy in development: Vite proxies `/api` and `/files` to `http://localhost:8000`

## Deployment

- Backend deploys as a FastAPI app with Poetry from `backend/` (ASGI app is `app` in `app/main.py`).
- Frontend must be pointed at the deployed backend URL via Vite env:
  - Create `frontend/.env` with `VITE_API_BASE=https://your-backend-url` (no trailing slash).
  - Build with `npm run build` and deploy `frontend/dist`.

## Credits

- Separation model: [Demucs](https://github.com/facebookresearch/demucs)
