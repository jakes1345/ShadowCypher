FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV QT_X11_NO_MITSHM=1

# Install all penetration testing dependencies and UI libraries
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
    sudo \
    policykit-1 \
    pkg-config \
    libcairo2-dev \
    libgirepository1.0-dev && \
    rm -rf /var/lib/apt/lists/*

# Add a non-root user for X11 UI safety
RUN useradd -ms /bin/bash shadowuser && echo "shadowuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

WORKDIR /opt/ShadowCypher
COPY . .

RUN pip3 install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /home/shadowuser/.cache && chown -R shadowuser:shadowuser /home/shadowuser && chown -R shadowuser:shadowuser /opt/ShadowCypher

USER shadowuser
ENV FONTCONFIG_PATH=/etc/fonts
ENV XDG_CACHE_HOME=/home/shadowuser/.cache

# Start the HUD
CMD ["python3", "-m", "shadowcypher.app"]
