#!/usr/bin/env python3
"""Normalizador de volumen para YouTube (EBU R128 / loudnorm de ffmpeg, 2 pasadas).
Uso: python3 app.py  ->  abre http://localhost:8000
Requiere: ffmpeg (brew install ffmpeg). Sin dependencias de pip."""
import json, os, re, subprocess, tempfile, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

# Usar el ffmpeg que está junto a este archivo (si existe)
os.environ["PATH"] = os.path.dirname(os.path.abspath(__file__)) + os.pathsep + os.environ["PATH"]

OUT_DIR = os.path.expanduser("~/Documents/AUDIOS FUERA DEL DISCO/AUDIOS PROCESADOS POR APP")
os.makedirs(OUT_DIR, exist_ok=True)

PAGE = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>VocalLevel &bull; YouTube Audio Normalizer</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090a0f;
      --card-bg: rgba(23, 25, 35, 0.72);
      --card-border: rgba(255, 255, 255, 0.08);
      --accent: #3b82f6;
      --accent-hover: #2563eb;
      --accent-glow: rgba(59, 130, 246, 0.25);
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --success: #10b981;
      --success-bg: rgba(16, 185, 129, 0.12);
      --danger: #ef4444;
      --danger-bg: rgba(239, 68, 68, 0.12);
      --radius-lg: 20px;
      --radius-md: 12px;
      --radius-sm: 8px;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
      background: var(--bg);
      background-image: 
        radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.15) 0px, transparent 50%),
        radial-gradient(at 100% 100%, rgba(139, 92, 246, 0.1) 0px, transparent 50%);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 40px 20px 80px;
      -webkit-font-smoothing: antialiased;
    }

    .container {
      width: 100%;
      max-width: 680px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    /* Header */
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 4px 8px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-icon {
      width: 40px;
      height: 40px;
      border-radius: 12px;
      background: linear-gradient(135deg, #3b82f6, #8b5cf6);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 8px 16px -4px var(--accent-glow);
    }
    .brand-icon svg { width: 22px; height: 22px; fill: white; }
    .brand-info h1 {
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }
    .brand-info p {
      font-size: 0.8rem;
      color: var(--text-muted);
    }

    .btn-folder {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      padding: 8px 14px;
      border-radius: var(--radius-sm);
      font-size: 0.8rem;
      font-weight: 500;
      cursor: pointer;
      backdrop-filter: blur(8px);
      transition: all 180ms cubic-bezier(0.16, 1, 0.3, 1);
    }
    .btn-folder:hover {
      background: rgba(255, 255, 255, 0.1);
      color: var(--text);
      transform: translateY(-1px);
    }
    .btn-folder:active {
      transform: scale(0.97);
    }

    /* Settings Card */
    .settings-panel {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      backdrop-filter: blur(20px);
      border-radius: var(--radius-md);
      padding: 16px 20px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    .param-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .param-label {
      font-size: 0.78rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
    }
    .param-input-wrap {
      position: relative;
      display: flex;
      align-items: center;
    }
    .param-input {
      width: 100%;
      background: rgba(0, 0, 0, 0.35);
      border: 1px solid var(--card-border);
      border-radius: var(--radius-sm);
      color: var(--text);
      font-family: inherit;
      font-size: 0.95rem;
      font-weight: 600;
      padding: 9px 12px;
      outline: none;
      transition: border-color 150ms ease, box-shadow 150ms ease;
    }
    .param-input:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px var(--accent-glow);
    }
    .unit-tag {
      position: absolute;
      right: 12px;
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--text-dim);
      pointer-events: none;
    }

    /* Drop Zone */
    .drop-zone {
      position: relative;
      background: var(--card-bg);
      border: 1.5px dashed rgba(255, 255, 255, 0.14);
      border-radius: var(--radius-lg);
      padding: 56px 28px;
      text-align: center;
      cursor: pointer;
      backdrop-filter: blur(20px);
      transition: all 220ms cubic-bezier(0.16, 1, 0.3, 1);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
      overflow: hidden;
    }
    .drop-zone:hover {
      border-color: rgba(255, 255, 255, 0.28);
      background: rgba(30, 34, 48, 0.7);
      transform: translateY(-2px);
    }
    .drop-zone.dragover {
      border-color: var(--accent);
      background: rgba(59, 130, 246, 0.08);
      box-shadow: 0 0 32px var(--accent-glow);
      transform: scale(1.01);
    }
    .drop-zone:active {
      transform: scale(0.99);
    }

    .drop-icon-wrap {
      width: 64px;
      height: 64px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 200ms cubic-bezier(0.16, 1, 0.3, 1);
    }
    .drop-zone:hover .drop-icon-wrap {
      transform: scale(1.08);
      background: rgba(59, 130, 246, 0.12);
      border-color: var(--accent);
    }
    .drop-icon-wrap svg {
      width: 28px;
      height: 28px;
      fill: none;
      stroke: var(--accent);
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    .drop-title {
      font-size: 1.05rem;
      font-weight: 600;
      letter-spacing: -0.01em;
    }
    .drop-desc {
      font-size: 0.85rem;
      color: var(--text-muted);
      max-width: 360px;
      line-height: 1.45;
    }
    .btn-select {
      margin-top: 4px;
      background: var(--text);
      color: #000;
      border: none;
      padding: 9px 20px;
      border-radius: var(--radius-sm);
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 150ms ease;
    }
    .btn-select:hover {
      background: #e2e8f0;
    }
    .btn-select:active {
      transform: scale(0.96);
    }

    /* Queue & History */
    .queue-section {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .section-title {
      font-size: 0.85rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-dim);
      padding-left: 4px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .file-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
      list-style: none;
    }

    .file-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--radius-md);
      padding: 16px;
      backdrop-filter: blur(16px);
      display: flex;
      flex-direction: column;
      gap: 12px;
      animation: cardIn 250ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    @keyframes cardIn {
      from { opacity: 0; transform: translateY(8px) scale(0.98); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    .file-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .file-name-wrap {
      display: flex;
      align-items: center;
      gap: 10px;
      overflow: hidden;
    }
    .file-badge {
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      background: rgba(255, 255, 255, 0.06);
      color: var(--text-muted);
    }
    .file-name {
      font-size: 0.92rem;
      font-weight: 600;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 380px;
    }

    .status-tag {
      font-size: 0.78rem;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 20px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
    }
    .status-processing {
      background: rgba(59, 130, 246, 0.12);
      color: #60a5fa;
      border: 1px solid rgba(59, 130, 246, 0.25);
    }
    .status-done {
      background: var(--success-bg);
      color: var(--success);
      border: 1px solid rgba(16, 185, 129, 0.25);
    }
    .status-error {
      background: var(--danger-bg);
      color: var(--danger);
      border: 1px solid rgba(239, 68, 68, 0.25);
    }

    /* Progress bar */
    .progress-track {
      width: 100%;
      height: 4px;
      background: rgba(255, 255, 255, 0.06);
      border-radius: 4px;
      overflow: hidden;
      position: relative;
    }
    .progress-bar-indeterminate {
      position: absolute;
      width: 40%;
      height: 100%;
      background: linear-gradient(90deg, transparent, var(--accent), transparent);
      animation: sweep 1.2s infinite ease-in-out;
    }
    @keyframes sweep {
      0% { left: -40%; }
      100% { left: 100%; }
    }

    .file-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px 16px;
      font-size: 0.8rem;
      color: var(--text-muted);
      border-top: 1px solid rgba(255, 255, 255, 0.04);
      padding-top: 10px;
    }
    .meta-item strong {
      color: var(--text);
      font-weight: 600;
    }

    .segments-chip-list {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 4px;
    }
    .seg-chip {
      background: rgba(59, 130, 246, 0.1);
      border: 1px solid rgba(59, 130, 246, 0.2);
      color: #93c5fd;
      padding: 2px 8px;
      border-radius: 6px;
      font-size: 0.72rem;
      font-weight: 500;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <div class="brand-icon">
          <svg viewBox="0 0 24 24"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3zm5 10a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21H9v2h6v-2h-2v-2.08A7 7 0 0 0 19 12h-2z"/></svg>
        </div>
        <div class="brand-info">
          <h1>VocalLevel</h1>
          <p>Normalizador dinámico de micrófono para YouTube</p>
        </div>
      </div>
      <button class="btn-folder" id="btnFolder" onclick="openFolder()">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
        Abrir carpeta
      </button>
    </header>

    <div class="settings-panel">
      <div class="param-group">
        <div class="param-label">
          <span>Pico objetivo de voz</span>
        </div>
        <div class="param-input-wrap">
          <input class="param-input" id="t" type="number" value="-2.0" step="0.5">
          <span class="unit-tag">dB</span>
        </div>
      </div>
      <div class="param-group">
        <div class="param-label">
          <span>Techo máximo (Limitador)</span>
        </div>
        <div class="param-input-wrap">
          <input class="param-input" id="tp" type="number" value="-1.0" step="0.5">
          <span class="unit-tag">dB</span>
        </div>
      </div>
    </div>

    <div class="drop-zone" id="drop">
      <div class="drop-icon-wrap">
        <svg viewBox="0 0 24 24">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
        </svg>
      </div>
      <div>
        <div class="drop-title">Arrastra tus videos o audios aquí</div>
        <div class="drop-desc">Sube archivos MP4, MOV, WAV, MKV o MP3. Se regularizarán los tramos bajos manteniendo intacto el resto.</div>
      </div>
      <input type="file" id="f" multiple hidden accept="video/*,audio/*">
      <button class="btn-select" onclick="f.click()">O explorar archivos</button>
    </div>

    <div class="queue-section">
      <div class="section-title">
        <span>Historial de procesamiento</span>
        <span id="queueCount" style="font-size:0.75rem; text-transform:none;"></span>
      </div>
      <ul class="file-list" id="log"></ul>
    </div>
  </div>

  <script>
    const log = document.getElementById('log');
    const drop = document.getElementById('drop');
    const f = document.getElementById('f');
    const t = document.getElementById('t');
    const tp = document.getElementById('tp');

    async function openFolder() {
      try {
        await fetch('/open_folder');
      } catch (e) {
        alert('No se pudo abrir la carpeta en Finder');
      }
    }

    const fmt = s => `${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`;

    async function send(file) {
      const ext = file.name.split('.').pop().toUpperCase();
      const card = document.createElement('li');
      card.className = 'file-card';
      card.innerHTML = `
        <div class="file-card-header">
          <div class="file-name-wrap">
            <span class="file-badge">${ext}</span>
            <span class="file-name" title="${file.name}">${file.name}</span>
          </div>
          <span class="status-tag status-processing">
            <span style="display:inline-block;animation:spin 1s linear infinite;">⏳</span> Analizando audio...
          </span>
        </div>
        <div class="progress-track"><div class="progress-bar-indeterminate"></div></div>
      `;
      log.prepend(card);

      const q = `?name=${encodeURIComponent(file.name)}&i=${t.value}&tp=${tp.value}`;
      try {
        const r = await fetch('/process' + q, { method: 'POST', body: file });
        const j = await r.json();

        const track = card.querySelector('.progress-track');
        if (track) track.remove();

        const tag = card.querySelector('.status-tag');
        if (j.ok) {
          tag.className = 'status-tag status-done';
          tag.innerHTML = `✅ Pico final: ${j.peak} dB`;

          const segs = j.segs || [];
          let segsHtml = '';
          if (segs.length > 0) {
            segsHtml = `
              <div style="width:100%;margin-top:4px;">
                <span style="font-size:0.75rem;color:var(--text-dim);font-weight:600;">TRAMOS SUBIDOS:</span>
                <div class="segments-chip-list">
                  ${segs.map(s => `<span class="seg-chip">${fmt(s.start)} - ${fmt(s.end)} (+${s.gain_db} dB)</span>`).join('')}
                </div>
              </div>
            `;
          } else {
            segsHtml = `<div style="font-size:0.75rem;color:var(--text-dim);margin-top:2px;">El volumen era uniforme; no requirió aumentos locales.</div>`;
          }

          const meta = document.createElement('div');
          meta.className = 'file-meta';
          meta.innerHTML = `
            <div class="meta-item">Guardado en: <strong>AUDIOS PROCESADOS POR APP</strong></div>
            ${segsHtml}
          `;
          card.appendChild(meta);
        } else {
          tag.className = 'status-tag status-error';
          tag.textContent = '❌ Error';
          const err = document.createElement('div');
          err.className = 'file-meta';
          err.style.color = 'var(--danger)';
          err.textContent = j.error || 'Fallo desconocido';
          card.appendChild(err);
        }
      } catch (e) {
        const tag = card.querySelector('.status-tag');
        tag.className = 'status-tag status-error';
        tag.textContent = '❌ ' + e.message;
      }
    }

    async function run(files) {
      for (const x of files) await send(x);
    }

    f.onchange = () => run(f.files);
    drop.ondragover = e => { e.preventDefault(); drop.classList.add('dragover'); };
    drop.ondragleave = () => drop.classList.remove('dragover');
    drop.ondrop = e => {
      e.preventDefault();
      drop.classList.remove('dragover');
      run(e.dataTransfer.files);
    };
  </script>
</body>
</html>"""

import array, math, statistics

WIN = 0.05          # ventana de análisis (s)
GATE_DB = -50       # debajo de esto se considera silencio (pico)
DEADBAND_DB = 1.0   # no tocar diferencias menores a esto
MAX_GAIN_DB = 12.0  # subida/bajada máxima permitida

def analyze_levels(src, cmd_path, peak_target=-2.0):
    """Mide los picos por ventana y escribe un archivo de comandos (asendcmd) con la
    ganancia que lleva los picos de cada tramo a peak_target. Devuelve los tramos subidos."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000",
                          "-f", "s16le", "-"], capture_output=True).stdout
    pcm = array.array("h"); pcm.frombytes(raw[: len(raw) // 2 * 2])
    n = int(16000 * WIN)
    levels = []
    for i in range(0, len(pcm) - n + 1, n):
        pk = max(max(pcm[i:i + n]), -min(pcm[i:i + n]))
        levels.append(20 * math.log10(max(pk, 1) / 32768))
    if sum(1 for l in levels if l > GATE_DB) < 20:
        return []
    R = 20                                            # ±1 s de contexto
    gains = []
    for i in range(len(levels)):
        near = sorted(l for l in levels[max(0, i - R): i + R + 1] if l > GATE_DB)
        if len(near) < 5:
            gains.append(0.0); continue
        local_peak = near[int(len(near) * 0.9)]       # pico típico del tramo
        g = max(-MAX_GAIN_DB, min(MAX_GAIN_DB, peak_target - local_peak))
        gains.append(0.0 if abs(g) < DEADBAND_DB else g)
    sm = []                                           # suavizar para evitar saltos
    for i in range(len(gains)):
        seg = gains[max(0, i - 4): i + 5]
        sm.append(sum(seg) / len(seg))
    with open(cmd_path, "w") as f:
        last = 0.0
        for i, g in enumerate(sm):
            if abs(g - last) > 0.3:
                f.write("%.2f volume volume %.4f;\n" % (i * WIN, 10 ** (g / 20))); last = g
    segs, start = [], None
    for i, g in enumerate(sm + [0.0]):
        if g >= DEADBAND_DB and start is None:
            start = i
        elif g < DEADBAND_DB and start is not None:
            if (i - start) * WIN >= 1.0:
                segs.append({"start": round(start * WIN, 1), "end": round(i * WIN, 1),
                             "gain_db": round(sum(sm[start:i]) / (i - start), 1)})
            start = None
    return segs

def normalize(src, dst, peak_target, ceiling, cmd_path=None):
    """Aplica la ganancia por tramos y un limitador que garantiza que ningún pico pase del techo."""
    pre = f"asendcmd=f={cmd_path},volume=1," if cmd_path and os.path.getsize(cmd_path) else ""
    lim = 10 ** (float(ceiling) / 20)
    flt = f"{pre}alimiter=limit={lim:.4f}:attack=3:release=60:level=disabled"
    has_video = "Video:" in subprocess.run(["ffmpeg", "-i", src], capture_output=True, text=True).stderr
    cmd = ["ffmpeg", "-y", "-hide_banner", "-i", src, "-af", flt, "-ar", "48000"]
    cmd += (["-c:v", "copy", "-c:a", "aac", "-b:a", "320k"] if has_video else ["-c:a", "pcm_s16le"])
    r = subprocess.run(cmd + [dst], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-300:])
    # Medir el pico resultante
    m = subprocess.run(["ffmpeg", "-hide_banner", "-i", dst, "-vn", "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    mv = re.search(r"max_volume: (-?[\d.]+) dB", m.stderr)
    return mv.group(1) if mv else "?"

class H(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/open_folder":
            subprocess.run(["open", OUT_DIR])
            self._json({"ok": True, "path": OUT_DIR})
            return
        b = PAGE.encode()
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_POST(self):
        q = parse_qs(urlparse(self.path).query)
        name = os.path.basename(q["name"][0]); base, ext = os.path.splitext(name)
        n = int(self.headers["Content-Length"])
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            left = n
            while left:
                chunk = self.rfile.read(min(1 << 20, left)); tmp.write(chunk); left -= len(chunk)
        out_ext = ext if ext.lower() in (".mp4", ".mov", ".mkv") else ".wav"
        out = os.path.join(OUT_DIR, f"{base}_norm{out_ext}")
        cmd_path = tmp.name + ".cmd"
        try:
            segs = analyze_levels(tmp.name, cmd_path, float(q["i"][0]))
            peak = normalize(tmp.name, out, q["i"][0], q["tp"][0], cmd_path)
            self._json({"ok": True, "peak": peak, "out": out, "segs": segs})
        except Exception as e:
            self._json({"ok": False, "error": str(e)})
        finally:
            os.unlink(tmp.name)
            if os.path.exists(cmd_path):
                os.unlink(cmd_path)

if __name__ == "__main__":
    print("Abriendo http://localhost:8000  (salida en", OUT_DIR + ")")
    webbrowser.open("http://localhost:8000")
    HTTPServer(("127.0.0.1", 8000), H).serve_forever()
