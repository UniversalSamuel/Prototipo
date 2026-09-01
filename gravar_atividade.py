"""
Botao de gravacao de atividade - P&D Univel

Uso: associar este script a um atalho na area de trabalho (via pythonw.exe,
para nao abrir janela de console). Primeiro clique inicia a gravacao,
segundo clique encerra e salva o audio na pasta 'pendentes'.

Dependencias (instalar uma vez):
    pip install sounddevice soundfile

Nao depende do Claude Code estar aberto. O processamento (transcricao,
classificacao, registro e envio) acontece depois, quando o Claude Code
processar a pasta 'pendentes' (ver CLAUDE.md, secao "Etapa 0").
"""

import os
import sys
import time
import wave
import tempfile
from datetime import datetime

try:
    import sounddevice as sd
except ImportError:
    print("Instale as dependencias: pip install sounddevice soundfile")
    sys.exit(1)

# ---- Configuracao ----
# Ajuste este caminho para a pasta do projeto onde o Claude Code roda.
PROJECT_DIR = r"C:\Users\samuel.oliveira\.claude\Controle de atividades"
PENDENTES_DIR = os.path.join(PROJECT_DIR, "pendentes")
SAMPLE_RATE = 44100
CHANNELS = 1

LOCK_FILE = os.path.join(tempfile.gettempdir(), "pd_record.lock")
STOP_FLAG = os.path.join(tempfile.gettempdir(), "pd_record.stop")


def beep(freq=880, dur_ms=150):
    try:
        import winsound
        winsound.Beep(freq, dur_ms)
    except Exception:
        pass  # silencioso em sistemas sem winsound (ex: fora do Windows)


def is_recording():
    return os.path.exists(LOCK_FILE)


def signal_stop():
    # Ja existe uma gravacao rodando: sinaliza para ela parar e sai.
    with open(STOP_FLAG, "w") as f:
        f.write("stop")
    beep(440, 200)  # tom mais grave = "parando"


def start_recording():
    os.makedirs(PENDENTES_DIR, exist_ok=True)
    # Remove flag de stop antigo, se sobrou de alguma execucao anterior
    if os.path.exists(STOP_FLAG):
        os.remove(STOP_FLAG)

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

    beep(880, 150)  # tom mais agudo = "gravando"

    frames = []

    def callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                             callback=callback):
            while not os.path.exists(STOP_FLAG):
                time.sleep(0.2)
    finally:
        # Salva o audio mesmo se algo interromper
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        out_path = os.path.join(PENDENTES_DIR, f"{timestamp}.wav")

        if frames:
            import numpy as np
            audio = np.concatenate(frames, axis=0)
            with wave.open(out_path, "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes((audio * 32767).astype(np.int16).tobytes())

        for f in (LOCK_FILE, STOP_FLAG):
            if os.path.exists(f):
                os.remove(f)

        beep(660, 150)  # tom de confirmacao = "salvo"


if __name__ == "__main__":
    if is_recording():
        signal_stop()
    else:
        start_recording()
