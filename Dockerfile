FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV QT_X11_NO_MITSHM=1

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0 \
    nmap \
    tcpdump \
    wireshark-tshark \
    john \
    hydra \
    aircrack-ng \
    binwalk \
    exiftool \
    git \
    wget \
    unzip \
    curl \
    ffuf \
    pkg-config \
    libcairo2-dev \
    libgirepository1.0-dev && \
    rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/SpiderLabs/Responder.git /opt/Responder && \
    wget -q https://github.com/projectdiscovery/nuclei/releases/download/v3.2.0/nuclei_3.2.0_linux_amd64.zip && \
    unzip nuclei_3.2.0_linux_amd64.zip -d /usr/local/bin/ && \
    rm nuclei_3.2.0_linux_amd64.zip && \
    wget -q https://github.com/BishopFox/sliver/releases/download/v1.5.42/sliver-server_linux -O /usr/local/bin/sliver-server && \
    chmod +x /usr/local/bin/sliver-server

RUN useradd -ms /bin/bash shadowuser

WORKDIR /opt/ShadowCypher
COPY .dockerignore .
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY shadowcypher/ ./shadowcypher/
COPY config.json pyproject.toml ./
RUN mkdir -p /home/shadowuser/.cache projects payloads reports logs && \
    chown -R shadowuser:shadowuser /home/shadowuser /opt/ShadowCypher

USER shadowuser
ENV FONTCONFIG_PATH=/etc/fonts
ENV XDG_CACHE_HOME=/home/shadowuser/.cache

CMD ["python3", "-m", "shadowcypher.app"]
