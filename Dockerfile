# ─────────────────────────────────────────────────────────────
# ShadowCypher Autonomous Offensive Suite — Ultimate Build
# ─────────────────────────────────────────────────────────────
FROM ubuntu:22.04

# Core Dependencies
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0 \
    gir1.2-vte-2.91 \
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
    golang-go \
    pkg-config \
    libcairo2-dev \
    libgirepository1.0-dev \
    php-cli \
    sqlmap \
    nikto \
    exploitdb && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# ─────────────────────────────────────────────────────────────
# ShadowCypher Core Weapons Systems (Local Staging)
# ─────────────────────────────────────────────────────────────
RUN mkdir -p /app/tools && \
    git clone --depth 1 https://github.com/lgandx/Responder.git /app/tools/Responder && \
    git clone --depth 1 https://github.com/offensive-security/exploitdb.git /app/tools/exploitdb && \
    git clone --depth 1 https://github.com/JoasASantos/ShadowPhish.git /app/shadowcypher/modules/phish_data

# ─────────────────────────────────────────────────────────────
# High-Performance Go Utilities
# ─────────────────────────────────────────────────────────────
RUN go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest && \
    go install -v github.com/ffuf/ffuf/v2@latest && \
    go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest && \
    cp /root/go/bin/* /usr/local/bin/

# Python Environment
RUN pip3 install --no-cache-dir -r requirements.txt

# Finalize Environment
ENV QT_X11_NO_MITSHM=1
ENV OLLAMA_BASE="http://127.0.0.1:11434"
ENV DISPLAY=:0
ENV PATH="/app/tools/exploitdb:$PATH"

EXPOSE 8080 55553 4444 1080

CMD ["./run.sh"]
