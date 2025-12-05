#!/bin/bash
# IRIS Local Launcher - for desktop integration
# Launches the IRIS voice client GUI with ffmpeg audio support

cd /home/x-forge/repos/iris/packages/voice-backend
source .venv/bin/activate
exec python iris_local.py --gui --ffmpeg
