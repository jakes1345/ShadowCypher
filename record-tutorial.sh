#!/bin/bash

################################################################################
# ShadowCypher Tutorial Recording Script
#
# Helper script for recording screen and audio for ShadowCypher video tutorials.
# Supports multiple recording tools (FFmpeg, OBS) and recording presets.
#
# Usage:
#   ./record-tutorial.sh --title "Tutorial Title" --duration 10m
#   ./record-tutorial.sh --title "Tutorial Title" --preset 1080p-30fps
#   ./record-tutorial.sh --help
#
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TITLE=""
TOOL="ffmpeg"
PRESET="1080p-30fps"
DURATION=""
OUTPUT_DIR="${OUTPUT_DIR:-.}"
DISABLE_AUDIO=false
CURSOR_FOLLOW=false
VERBOSE=false

# Recording presets (resolution, fps, bitrate)
declare -A PRESETS=(
  ["1080p-30fps"]="1920:1080,30,3500k"
  ["1080p-60fps"]="1920:1080,60,5000k"
  ["720p-30fps"]="1280:720,30,2000k"
  ["720p-60fps"]="1280:720,60,3500k"
  ["1440p-30fps"]="2560:1440,30,6000k"
  ["mobile-preview"]="854:480,24,1200k"
  ["mobile-hd"]="1280:720,24,1800k"
)

################################################################################
# Helper Functions
################################################################################

log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[✓]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

show_usage() {
  cat << EOF
ShadowCypher Tutorial Recording Script

USAGE:
  $0 [OPTIONS]

OPTIONS:
  -t, --title TITLE              Tutorial title (required)
  -d, --duration DURATION        Recording duration (e.g., 10m, 600s)
  -p, --preset PRESET            Recording preset (default: 1080p-30fps)
  -o, --output OUTPUT_DIR        Output directory (default: current dir)
  -T, --tool TOOL                Recording tool: ffmpeg|obs (default: ffmpeg)
  --disable-audio                Record without audio
  --cursor-follow                Follow mouse cursor in recording
  -v, --verbose                  Enable verbose output
  -h, --help                     Show this help message
  --list-presets                 List available recording presets

PRESETS:
  1080p-30fps    - 1920x1080 @ 30fps, 3500kbps (standard)
  1080p-60fps    - 1920x1080 @ 60fps, 5000kbps (smooth motion)
  720p-30fps     - 1280x720 @ 30fps, 2000kbps (web streaming)
  720p-60fps     - 1280x720 @ 60fps, 3500kbps (smooth streaming)
  1440p-30fps    - 2560x1440 @ 30fps, 6000kbps (high quality)
  mobile-preview - 854x480 @ 24fps, 1200kbps (mobile)
  mobile-hd      - 1280x720 @ 24fps, 1800kbps (mobile HD)

EXAMPLES:
  # Basic recording with default preset
  $0 --title "Installation & Setup"

  # Custom preset and duration
  $0 --title "Guardian Vault Setup" --preset 1080p-60fps --duration 15m

  # Using OBS with specific output directory
  $0 --title "Advanced Features" --tool obs --output ./videos

NOTES:
  - FFmpeg requires: ffmpeg, X11 or Wayland display
  - OBS requires: obs-studio installed and configured
  - Audio normalization requires: ffmpeg-normalize (pip install ffmpeg-normalize)
  - Output files are saved as: videos/raw/[title-slug].mp4

EOF
}

show_presets() {
  echo "Available Recording Presets:"
  echo ""
  printf "%-20s %-15s %-10s %-10s\n" "PRESET" "RESOLUTION" "FPS" "BITRATE"
  printf "%-20s %-15s %-10s %-10s\n" "------" "----------" "---" "-------"
  for preset in "${!PRESETS[@]}"; do
    IFS=',' read -r res fps bitrate <<< "${PRESETS[$preset]}"
    printf "%-20s %-15s %-10s %-10s\n" "$preset" "$res" "$fps" "$bitrate"
  done
}

check_dependencies() {
  local missing=()

  # Check for common tools
  for cmd in which; do
    if ! command -v "$cmd" &> /dev/null; then
      missing+=("$cmd")
    fi
  done

  # Check for recording tool
  case "$TOOL" in
    ffmpeg)
      for cmd in ffmpeg xdotool; do
        if ! command -v "$cmd" &> /dev/null; then
          missing+=("$cmd")
        fi
      done
      ;;
    obs)
      if ! command -v obs &> /dev/null; then
        missing+=("obs-studio")
      fi
      ;;
  esac

  if [ ${#missing[@]} -gt 0 ]; then
    log_error "Missing required tools: ${missing[*]}"
    echo ""
    echo "Install missing dependencies:"
    echo ""
    echo "On Ubuntu/Debian:"
    echo "  sudo apt-get install ${missing[*]}"
    echo ""
    echo "For audio normalization (optional):"
    echo "  pip install ffmpeg-normalize"
    return 1
  fi

  log_success "All required dependencies found"
}

validate_preset() {
  if [[ ! -v PRESETS[$PRESET] ]]; then
    log_error "Unknown preset: $PRESET"
    echo ""
    echo "Available presets:"
    show_presets
    return 1
  fi
  log_success "Using preset: $PRESET"
}

sanitize_filename() {
  # Convert title to valid filename
  local filename="$1"
  filename="${filename,,}"  # lowercase
  filename="${filename// /-}"  # spaces to hyphens
  filename="${filename//[^a-z0-9-]/}"  # remove non-alphanumeric except hyphens
  filename="${filename//-+/-}"  # collapse multiple hyphens
  filename="${filename#-}"  # remove leading hyphen
  filename="${filename%-}"  # remove trailing hyphen
  echo "$filename"
}

get_display() {
  # Detect display (X11 or Wayland)
  if [ -n "${DISPLAY:-}" ]; then
    echo "$DISPLAY"
  elif [ -n "${WAYLAND_DISPLAY:-}" ]; then
    log_warn "Wayland detected - FFmpeg may have limited support"
    echo "$WAYLAND_DISPLAY"
  else
    log_error "No display found (X11 or Wayland)"
    return 1
  fi
}

get_screen_resolution() {
  # Get screen resolution using xdotool or other methods
  if command -v xdotool &> /dev/null; then
    xdotool getactivewindow getwindowgeometry | grep -oP 'Position.*' | head -1
  elif command -v xrandr &> /dev/null; then
    xrandr --current | grep -oP '\d+x\d+' | head -1
  else
    log_warn "Could not detect screen resolution, using 1920x1080"
    echo "1920x1080"
  fi
}

record_with_ffmpeg() {
  local output_file="$1"
  local resolution="$2"
  local fps="$3"

  log_info "Starting FFmpeg recording..."
  log_info "Recording $resolution @ ${fps}fps to $output_file"
  echo ""
  log_warn "Recording started. Press Ctrl+C to stop."
  echo ""

  local ffmpeg_opts=(
    "-f" "x11grab"
    "-i" "$DISPLAY+0,0"
  )

  # Add audio if not disabled
  if [ "$DISABLE_AUDIO" = false ]; then
    ffmpeg_opts+=(
      "-f" "pulse"
      "-i" "default"
    )
  fi

  ffmpeg_opts+=(
    "-vf" "scale=$resolution:force_original_aspect_ratio=decrease"
    "-c:v" "libx264"
    "-preset" "fast"
    "-crf" "23"
    "-r" "$fps"
    "-c:a" "aac"
    "-b:a" "128k"
    "-ar" "48000"
    "$output_file"
  )

  if [ "$VERBOSE" = true ]; then
    ffmpeg "${ffmpeg_opts[@]}"
  else
    ffmpeg "${ffmpeg_opts[@]}" 2>&1 | grep -E "frame=|Duration|time=" || true
  fi

  if [ $? -eq 0 ]; then
    log_success "Recording completed: $output_file"
    return 0
  else
    log_error "Recording failed"
    return 1
  fi
}

record_with_obs() {
  log_info "OBS recording not yet fully implemented"
  log_warn "Please manually record using OBS Studio with these settings:"
  echo ""
  echo "  Video Bitrate: 3500 kbps"
  echo "  Audio Bitrate: 128 kbps"
  echo "  Audio Sample Rate: 48000 Hz"
  echo "  Codec: H.264"
  echo ""
  log_info "After recording, save output as: $1"
  return 0
}

normalize_audio() {
  local input_file="$1"

  if ! command -v ffmpeg-normalize &> /dev/null; then
    log_warn "ffmpeg-normalize not found, skipping audio normalization"
    log_warn "Install with: pip install ffmpeg-normalize"
    return 0
  fi

  log_info "Normalizing audio..."

  local temp_file="${input_file}.normalized.mp4"
  ffmpeg-normalize "$input_file" \
    -o "$temp_file" \
    -of mp4 \
    -acodec aac \
    -b:a 128k \
    -ar 48000

  if [ $? -eq 0 ]; then
    mv "$temp_file" "$input_file"
    log_success "Audio normalized: $input_file"
  else
    log_error "Audio normalization failed"
    rm -f "$temp_file"
    return 1
  fi
}

generate_metadata() {
  local output_file="$1"
  local title="$2"
  local timestamp=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
  local basename=$(basename "$output_file" .mp4)

  # Create metadata file
  local metadata_file="${output_file%.*}.metadata.json"

  cat > "$metadata_file" << EOF
{
  "title": "$title",
  "filename": "$(basename "$output_file")",
  "path": "$output_file",
  "recorded_at": "$timestamp",
  "preset": "$PRESET",
  "tool": "$TOOL",
  "duration": "$DURATION",
  "includes_audio": $([ "$DISABLE_AUDIO" = false ] && echo "true" || echo "false"),
  "tutorial_slug": "$(sanitize_filename "$title")",
  "status": "raw",
  "next_steps": [
    "Edit video in preferred editor",
    "Run GitHub Actions workflow for processing",
    "Update VIDEO_TUTORIALS.md with links"
  ]
}
EOF

  log_success "Metadata file created: $metadata_file"
}

create_output_dirs() {
  local raw_dir="$OUTPUT_DIR/videos/raw"
  mkdir -p "$raw_dir"
  echo "$raw_dir"
}

################################################################################
# Main Script
################################################################################

main() {
  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
      -t|--title)
        TITLE="$2"
        shift 2
        ;;
      -d|--duration)
        DURATION="$2"
        shift 2
        ;;
      -p|--preset)
        PRESET="$2"
        shift 2
        ;;
      -o|--output)
        OUTPUT_DIR="$2"
        shift 2
        ;;
      -T|--tool)
        TOOL="$2"
        shift 2
        ;;
      --disable-audio)
        DISABLE_AUDIO=true
        shift
        ;;
      --cursor-follow)
        CURSOR_FOLLOW=true
        shift
        ;;
      -v|--verbose)
        VERBOSE=true
        shift
        ;;
      -h|--help)
        show_usage
        exit 0
        ;;
      --list-presets)
        show_presets
        exit 0
        ;;
      *)
        log_error "Unknown option: $1"
        echo ""
        show_usage
        exit 1
        ;;
    esac
  done

  # Validate required arguments
  if [ -z "$TITLE" ]; then
    log_error "Title is required"
    echo ""
    show_usage
    exit 1
  fi

  echo ""
  log_info "ShadowCypher Tutorial Recording Script"
  echo ""

  # Check dependencies
  check_dependencies || exit 1
  echo ""

  # Validate preset
  validate_preset || exit 1
  echo ""

  # Parse preset values
  IFS=',' read -r resolution fps bitrate <<< "${PRESETS[$PRESET]}"

  # Create output directory
  output_dir=$(create_output_dirs)
  log_success "Output directory: $output_dir"
  echo ""

  # Generate output filename
  filename="$(sanitize_filename "$TITLE").mp4"
  output_file="$output_dir/$filename"

  if [ -f "$output_file" ]; then
    log_warn "File already exists: $output_file"
    read -p "Overwrite? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      log_info "Cancelled"
      exit 0
    fi
  fi

  # Display recording summary
  echo "Recording Configuration:"
  echo "  Title: $TITLE"
  echo "  Preset: $PRESET ($resolution @ ${fps}fps)"
  echo "  Tool: $TOOL"
  echo "  Output: $output_file"
  echo "  Audio: $([ "$DISABLE_AUDIO" = false ] && echo "enabled" || echo "disabled")"
  if [ -n "$DURATION" ]; then
    echo "  Duration: $DURATION"
  fi
  echo ""

  # Start recording
  log_info "Starting recording in 3 seconds..."
  sleep 3
  echo ""

  case "$TOOL" in
    ffmpeg)
      record_with_ffmpeg "$output_file" "$resolution" "$fps"
      ;;
    obs)
      record_with_obs "$output_file"
      ;;
    *)
      log_error "Unknown tool: $TOOL"
      exit 1
      ;;
  esac

  if [ $? -ne 0 ]; then
    exit 1
  fi

  echo ""

  # Post-processing
  if [ -f "$output_file" ]; then
    # Check file size
    file_size=$(du -h "$output_file" | cut -f1)
    log_info "Recorded file size: $file_size"
    echo ""

    # Optionally normalize audio
    if [ "$DISABLE_AUDIO" = false ]; then
      read -p "Normalize audio? (y/n) " -n 1 -r
      echo ""
      if [[ $REPLY =~ ^[Yy]$ ]]; then
        normalize_audio "$output_file"
        echo ""
      fi
    fi

    # Generate metadata
    generate_metadata "$output_file" "$TITLE"
    echo ""

    log_success "Tutorial recorded successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Edit video in your preferred video editor"
    echo "  2. Export as MP4 with same settings"
    echo "  3. Commit to videos/raw/ directory"
    echo "  4. Push to trigger video processing workflow"
    echo ""
    echo "Tutorial file: $output_file"
  else
    log_error "Output file not created"
    exit 1
  fi
}

# Run main function
main "$@"
