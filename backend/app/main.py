from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.staticfiles import StaticFiles
from pathlib import Path
import shutil
import uuid
import os
import sys

import torch
import numpy as np
import wave
from demucs.pretrained import get_model
from demucs.apply import apply_model

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


def _read_wav_float32_stereo(path: Path):
    with wave.open(str(path), "rb") as w:
        n_channels = w.getnchannels()
        sampwidth = w.getsampwidth()
        framerate = w.getframerate()
        n_frames = w.getnframes()
        if framerate != 44100:
            raise RuntimeError(f"Unsupported sample rate {framerate}, please upload 44.1kHz WAV.")
        raw = w.readframes(n_frames)
    if sampwidth == 2:
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 4:
        data = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise RuntimeError(f"Unsupported sample width: {sampwidth*8} bits.")
    data = data.reshape(-1, n_channels)
    if n_channels == 1:
        data = np.repeat(data, 2, axis=1)
    elif n_channels > 2:
        data = data[:, :2]
    return data  # shape (num_samples, 2)

def _write_wav_float32_stereo(path: Path, audio: np.ndarray):
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(pcm.tobytes())

def run_demucs_two_stems(input_path: Path, job_dir: Path) -> Path:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.set_num_threads(max(1, torch.get_num_threads()))
    wav = _read_wav_float32_stereo(input_path)  # (N,2) float32 [-1,1]
    x = torch.tensor(wav.T, dtype=torch.float32).unsqueeze(0).to(device)
    model = get_model("htdemucs").to(device)
    model.eval()
    with torch.no_grad():
        sources = apply_model(model, x, shifts=1, overlap=0.25, split=True, progress=False)[0]
    names = model.sources
    src_map = {name: sources[i].cpu().numpy().T for i, name in enumerate(names)}
    if "vocals" not in src_map:
        raise RuntimeError("Model output missing vocals stem.")
    vocals = src_map["vocals"]
    instrumental = np.zeros_like(vocals)
    for name, audio in src_map.items():
        if name != "vocals":
            instrumental += audio
    out_vocals = job_dir / "vocals.wav"
    out_inst = job_dir / "instrumental.wav"
    _write_wav_float32_stereo(out_vocals, vocals)
    _write_wav_float32_stereo(out_inst, instrumental)
    return job_dir


@app.post("/api/separate")
async def separate(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")
    ext = Path(file.filename).suffix.lower()
    if ext not in [".wav"]:
        raise HTTPException(status_code=400, detail="Only WAV is supported on the deployed server for now. Please upload a 44.1kHz WAV.")

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

        final_vocals = job_out / "vocals.wav"
        final_inst = job_out / "instrumental.wav"
        if not final_vocals.exists() or not final_inst.exists():
            raise RuntimeError("Separation did not produce expected output files.")

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
