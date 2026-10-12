#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Descargar ffmpeg local si no está instalado
if [ ! -f "$DIR/ffmpeg" ] && ! command -v ffmpeg &> /dev/null; then
    echo "Configurando FFmpeg por primera vez..."
    curl -L -f -o "$DIR/ffmpeg.zip" https://www.osxexperts.net/ffmpeg7arm.zip
    unzip -o "$DIR/ffmpeg.zip" ffmpeg -d "$DIR"
    chmod +x "$DIR/ffmpeg"
    rm -f "$DIR/ffmpeg.zip"
fi

python3 "$DIR/app.py"
