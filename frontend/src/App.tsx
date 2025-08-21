import React, { useCallback, useRef, useState } from "react";

type Result = {
  job_id: string;
  vocals_url: string;
  instrumental_url: string;
};

const apiBase = (import.meta as any).env?.VITE_API_BASE || "";

export default function App() {
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const onDrop = useCallback(async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      await uploadFile(file);
    }
  }, []);

  const onSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      await uploadFile(file);
    }
  };

  const toAbs = (url: string) => (url.startsWith("/") ? `${apiBase}${url}` : url);

  const uploadFile = async (file: File) => {
    setError(null);
    setResult(null);
    setFileName(file.name);
    setLoading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${apiBase}/api/separate`, {
        method: "POST",
        body: form
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error((data as any).detail || `Upload failed (${res.status})`);
      }
      const data = (await res.json()) as Result;
      setResult({
        job_id: data.job_id,
        vocals_url: toAbs(data.vocals_url),
        instrumental_url: toAbs(data.instrumental_url)
      });
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.title}>Vocal Splitter</h1>
        <p style={styles.subtitle}>Upload an audio file (mp3, wav). We&apos;ll split vocals and instrumental.</p>

        <div
          style={{
            ...styles.drop,
            ...(dragOver ? styles.dropActive : {})
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".mp3,.wav,.flac,.m4a,.ogg,audio/*"
            style={{ display: "none" }}
            onChange={onSelect}
          />
          <div style={styles.dropInner}>
            <svg
              width="32"
              height="32"
              viewBox="0 0 24 24"
              fill="#111827"
              aria-hidden="true"
              style={styles.dropIcon}
            >
              <path d="M9 3v10.55A4 4 0 1 0 11 17V7h6V3H9z"/>
            </svg>
            <div style={styles.dropText}>
              <strong>Drag &amp; drop</strong> your audio here, or click to browse
            </div>
            {fileName && <div style={styles.fileName}>{fileName}</div>}
          </div>
        </div>

        {loading && (
          <div style={styles.progress}>
            <div style={styles.spinner} />
            <div>Processing your track…</div>
          </div>
        )}

        {error && (
          <div style={styles.error}>
            {error}
          </div>
        )}

        {result && (
          <div style={styles.results}>
            <h2 style={styles.sectionTitle}>Results</h2>

            <div style={styles.playerCard}>
              <h3 style={styles.playerTitle}>Instrumental</h3>
              <audio controls src={result.instrumental_url} style={styles.audio} />
              <a href={result.instrumental_url} download style={styles.button}>Download</a>
            </div>

            <div style={styles.playerCard}>
              <h3 style={styles.playerTitle}>Vocals</h3>
              <audio controls src={result.vocals_url} style={styles.audio} />
              <a href={result.vocals_url} download style={styles.button}>Download</a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: "100vh",
    display: "grid",
    placeItems: "center",
    background: "#f7f8fb",
    padding: 24
  },
  card: {
    width: "100%",
    maxWidth: 720,
    background: "#fff",
    borderRadius: 16,
    boxShadow: "0 10px 30px rgba(0,0,0,0.06)",
    padding: 24
  },
  title: {
    margin: "0 0 4px",
    fontSize: 28
  },
  subtitle: {
    margin: "0 0 20px",
    color: "#6b7280"
  },
  drop: {
    border: "2px dashed #cbd5e1",
    borderRadius: 12,
    padding: 24,
    textAlign: "center",
    background: "#fafafa",
    cursor: "pointer",
    transition: "all .2s ease"
  },
  dropActive: {
    borderColor: "#93c5fd",
    background: "#f0f9ff"
  },
  dropInner: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 8
  },
  dropIcon: {
    fontSize: 32
  },
  dropText: {
    color: "#374151"
  },
  fileName: {
    marginTop: 8,
    color: "#6b7280",
    fontSize: 14
  },
  progress: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    marginTop: 16
  },
  spinner: {
    width: 16,
    height: 16,
    borderRadius: "50%",
    border: "2px solid #93c5fd",
    borderTopColor: "transparent",
    animation: "spin 1s linear infinite"
  },
  error: {
    marginTop: 12,
    color: "#b91c1c",
    background: "#fee2e2",
    border: "1px solid #fecaca",
    padding: 12,
    borderRadius: 8
  },
  results: {
    marginTop: 24,
    display: "grid",
    gap: 16
  },
  sectionTitle: {
    margin: 0,
    fontSize: 20
  },
  playerCard: {
    padding: 16,
    border: "1px solid #e5e7eb",
    borderRadius: 12,
    background: "#f9fafb",
    display: "grid",
    gap: 8
  },
  playerTitle: {
    margin: 0,
    fontSize: 16
  },
  audio: {
    width: "100%"
  },
  button: {
    display: "inline-block",
    textDecoration: "none",
    background: "#111827",
    color: "#fff",
    padding: "10px 14px",
    borderRadius: 10,
    fontSize: 14,
    textAlign: "center"
  }
};
