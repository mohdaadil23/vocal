from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.staticfiles import StaticFiles
from pathlib import Path
import subprocess
import shutil
import uuid
import os
import sys

app = FastAPI(title="Vocal Separation API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
TMP_DIR = BASE_DIR / "tmp"
OUT_DIR = BASE_DIR / "storage"

TMP_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/files", StaticFiles(directory=str(OUT_DIR)), name="files")


def run_demucs_two_stems(input_path: Path, job_dir: Path) -> Path:
    cmd = [
        sys.executable,
        "-m",
        "demucs",
        "--two-stems",
        "vocals",
        "-o",
        str(job_dir),
        str(input_path),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout)
    return job_dir


@app.post("/api/separate")
async def separate(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")
    ext = Path(file.filename).suffix.lower()
    if ext not in [".mp3", ".wav", ".flac", ".m4a", ".ogg"]:
        raise HTTPException(status_code=400, detail="Unsupported audio format.")

    job_id = str(uuid.uuid4())
    job_tmp = TMP_DIR / job_id
    job_out = OUT_DIR / job_id
    job_tmp.mkdir(parents=True, exist_ok=True)
    job_out.mkdir(parents=True, exist_ok=True)

    input_path = job_tmp / f"input{ext}"
    try:
        with open(input_path, "wb") as f:
            content = await file.read()
            f.write(content)

        run_demucs_two_stems(input_path, job_out)

        vocals_path = None
        inst_path = None
        for root, dirs, files in os.walk(job_out):
            p = Path(root)
            has_vocals = "vocals.wav" in files
            inst_candidate = None
            if "accompaniment.wav" in files:
                inst_candidate = p / "accompaniment.wav"
            elif "no_vocals.wav" in files:
                inst_candidate = p / "no_vocals.wav"
            if has_vocals and inst_candidate is not None:
                vocals_path = p / "vocals.wav"
                inst_path = inst_candidate
                break

        if not vocals_path or not inst_path:
            raise RuntimeError("Demucs did not produce expected output files.")

        final_vocals = job_out / "vocals.wav"
        final_inst = job_out / "instrumental.wav"
        shutil.move(str(vocals_path), final_vocals)
        shutil.move(str(inst_path), final_inst)

        return JSONResponse(
            {
                "job_id": job_id,
                "vocals_url": f"/files/{job_id}/vocals.wav",
                "instrumental_url": f"/files/{job_id}/instrumental.wav",
            }
        )
    except Exception as e:
        if job_out.exists():
            shutil.rmtree(job_out, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}") from e
    finally:
        if job_tmp.exists():
            shutil.rmtree(job_tmp, ignore_errors=True)
@app.get("/api/status/{job_id}")
def status(job_id: str):
    job_out = OUT_DIR / job_id
    if not job_out.exists():
        return {"job_id": job_id, "status": "not_found"}
    vocals = job_out / "vocals.wav"
    inst = job_out / "instrumental.wav"
    if vocals.exists() and inst.exists():
        return {"job_id": job_id, "status": "done"}
    return {"job_id": job_id, "status": "running"}



@app.get("/api/health")
def health():
    return {"status": "ok"}
