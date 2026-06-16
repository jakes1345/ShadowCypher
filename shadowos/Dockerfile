# Build ShadowOS ISO inside an Arch container.
# Host (Mint/Ubuntu) does not ship archiso — Arch does.
FROM archlinux:latest

RUN pacman -Syyu --noconfirm && \
    pacman -S --noconfirm archiso git squashfs-tools libisoburn dosfstools e2fsprogs erofs-utils mtools grub edk2-shell curl ca-certificates reflector python3 && \
    pacman -Scc --noconfirm

WORKDIR /build
ENTRYPOINT ["/bin/bash"]
