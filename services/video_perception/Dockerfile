# Separate GPL perception service. No SoccerNet/TrackLab code is vendored in this repository.
FROM nvidia/cuda:11.7.1-cudnn8-runtime-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG SN_GAMESTATE_REF
RUN test -n "$SN_GAMESTATE_REF" || (echo "SN_GAMESTATE_REF must be a pinned commit or tag" && exit 1)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git python3 python3-pip ffmpeg ca-certificates && \
    rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --no-cache-dir uv

WORKDIR /opt
RUN git clone https://github.com/SoccerNet/sn-gamestate.git && \
    cd sn-gamestate && git checkout "$SN_GAMESTATE_REF"
WORKDIR /opt/sn-gamestate
# Mirrors the upstream uv installation guide for the pinned commit.
RUN uv python install 3.9 && \
    uv venv --python 3.9 && \
    uv pip install -e . && \
    uv run mim install mmcv==2.0.1

COPY run_gsr.py /opt/midfielders-eye-service/run_gsr.py
ENTRYPOINT ["uv", "run", "python", "/opt/midfielders-eye-service/run_gsr.py"]
