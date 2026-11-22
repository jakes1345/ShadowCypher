# Graphics environment for machines that run NVIDIA's own driver.
#
# Not for /etc/environment: the image ships Mesa and no NVIDIA driver, and on
# a machine without that driver these name libraries that are not installed.
# libva then loads no driver at all, and video is decoded on the CPU.
#
# /sys/module/nvidia_drm is there once NVIDIA's driver is installed and loaded.
if [ -d /sys/module/nvidia_drm ]; then
    export GBM_BACKEND=nvidia-drm
    export __GLX_VENDOR_LIBRARY_NAME=nvidia
    # VA-API on NVIDIA comes from libva-nvidia-driver. Without it, leave libva
    # to choose for itself.
    if [ -e /usr/lib/dri/nvidia_drv_video.so ]; then
        export LIBVA_DRIVER_NAME=nvidia
    fi
fi
