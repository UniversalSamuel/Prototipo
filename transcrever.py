"""
Transcricao local de audio (offline) - P&D Univel

Uso: python transcrever.py caminho\para\arquivo.wav

Modelo Whisper roda 100% local, primeira execucao baixa o modelo (~500MB) e
guarda em cache (~/.cache/huggingface). Execucoes seguintes sao mais rapidas.
"""

import sys
from faster_whisper import WhisperModel

def main():
    if len(sys.argv) < 2:
        print("Uso: python transcrever.py caminho\\para\\arquivo.wav", file=sys.stderr)
        sys.exit(1)

    audio_path = sys.argv[1]
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio_path, language="pt", beam_size=5)

    texto = " ".join(segment.text.strip() for segment in segments)
    print(texto)

if __name__ == "__main__":
    main()
