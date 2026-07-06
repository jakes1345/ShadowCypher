# ShadowCypher Video Tutorials

A comprehensive index of video tutorials for ShadowCypher, covering setup, configuration, security features, and advanced usage.

## Tutorial Directory

### Getting Started

| Tutorial | Duration | Level | Links | Status |
|----------|----------|-------|-------|--------|
| Installation & Initial Setup | 8-12 min | Beginner | [YouTube](#) \| [Transcript](#) | Planned |
| First Login & Dashboard Overview | 6-8 min | Beginner | [YouTube](#) \| [Transcript](#) | Planned |
| Security Profile Configuration | 10-15 min | Intermediate | [YouTube](#) \| [Transcript](#) | Planned |

### Feature Guides

| Tutorial | Duration | Level | Links | Status |
|----------|----------|-------|-------|--------|
| Guardian Vault: Password Management | 12-15 min | Intermediate | [YouTube](#) \| [Transcript](#) | Planned |
| Threat Intelligence Feed Integration | 10-12 min | Intermediate | [YouTube](#) \| [Transcript](#) | Planned |
| Incident Response Automation | 14-18 min | Advanced | [YouTube](#) \| [Transcript](#) | Planned |
| Cryptographic Key Management | 15-20 min | Advanced | [YouTube](#) \| [Transcript](#) | Planned |
| Audit Trails & Compliance Reporting | 10-12 min | Intermediate | [YouTube](#) \| [Transcript](#) | Planned |

### Platform-Specific

| Tutorial | Duration | Level | Links | Status |
|----------|----------|-------|-------|--------|
| Android App Installation & Configuration | 8-10 min | Beginner | [YouTube](#) \| [Transcript](#) | Planned |
| Web Dashboard Deep Dive | 15-20 min | Intermediate | [YouTube](#) \| [Transcript](#) | Planned |
| CLI Tools & Advanced Operations | 12-15 min | Advanced | [YouTube](#) \| [Transcript](#) | Planned |

### Administration

| Tutorial | Duration | Level | Links | Status |
|----------|----------|-------|-------|--------|
| User Access Control & Permissions | 10-12 min | Advanced | [YouTube](#) \| [Transcript](#) | Planned |
| Backup & Recovery Procedures | 12-15 min | Intermediate | [YouTube](#) \| [Transcript](#) | Planned |
| Troubleshooting Common Issues | 15-20 min | All Levels | [YouTube](#) \| [Transcript](#) | Planned |

## Video Specifications

### Recording Standards

- **Resolution**: 1920x1080 (1080p) or 2560x1440 (1440p)
- **Frame Rate**: 30 fps (60 fps for fast-paced content)
- **Bitrate**: 2500-5000 kbps (6000+ kbps for 1440p)
- **Audio**: 128 kbps, 48 kHz, stereo
- **Format**: MP4 (H.264 codec)

### Thumbnail Standards

- **Size**: 1280x720 pixels
- **Format**: PNG or JPEG
- **Style**: Consistent branding with ShadowCypher logo
- **Text**: Clear, readable, high contrast
- **File Naming**: `[video-slug]-thumbnail.png`

### Subtitle Requirements

- **Format**: VTT (WebVTT) or SRT
- **Language**: English (en-US)
- **Encoding**: UTF-8
- **Timing**: Accurate to within 100ms
- **Style Guide**: Follow video terminology and product naming conventions

## Publishing Workflow

1. **Record**: Use `record-tutorial.sh` to standardize recording process
2. **Edit**: Edit video in preferred editor (Adobe Premiere, DaVinci Resolve, FFmpeg)
3. **Process**: Run GitHub Actions workflow to:
   - Encode video to optimized formats
   - Generate thumbnail from keyframe
   - Extract auto-generated captions
   - Upload to hosting platform
4. **Publish**: Update this index with video links and metadata
5. **Promote**: Share on YouTube, documentation, and community channels

## CI/CD Pipeline

Videos are automatically processed and published via the `video-ci.yml` GitHub Actions workflow:

- Trigger: Push to `videos/` directory or pull request with video changes
- Processing: Automated encoding, optimization, and subtitle generation
- Hosting: Upload to configured platform (YouTube, self-hosted, etc.)
- Metadata: Automatically update `VIDEO_TUTORIALS.md` with links and timestamps

See `.github/workflows/video-ci.yml` for detailed workflow configuration.

## Video Recording Guide

### Using `record-tutorial.sh`

Quick recording with sensible defaults:

```bash
./record-tutorial.sh --title "Installation & Setup" --duration 10m
```

With custom settings:

```bash
./record-tutorial.sh \
  --title "Guardian Vault Setup" \
  --preset 1080p-30fps \
  --tool ffmpeg \
  --duration 15m \
  --output videos/guardian-vault-setup.mp4
```

See `record-tutorial.sh --help` for all options and presets.

## Requesting a Tutorial

To request a new tutorial:

1. Open an issue with title: `[Tutorial Request] Topic Name`
2. Describe the topic and target audience
3. Suggest difficulty level and estimated duration
4. Add `tutorial-request` label
5. Core team will evaluate and prioritize

## Difficulty Levels

- **Beginner**: Basic product usage, no prerequisites
- **Intermediate**: Assumes familiarity with product basics, may cover integration topics
- **Advanced**: Requires technical knowledge, covers architecture or customization
- **All Levels**: Useful regardless of experience

## Video Metadata Format

Each video index entry includes:

- **Title**: Clear, descriptive title
- **Duration**: Approximate length (min-max range)
- **Level**: Beginner, Intermediate, Advanced, or All Levels
- **YouTube URL**: Direct link to published video
- **Transcript URL**: Text transcript for accessibility
- **Timestamps**: Section markers for key content
- **Status**: Planned, In Progress, Published, Archived

## Transcript Standards

Transcripts must:

- Be accurate and complete
- Use proper punctuation and capitalization
- Include speaker identification for multi-speaker content
- Mark non-speech audio (music, sound effects) in [brackets]
- Include [INAUDIBLE] for unclear sections
- Follow accessible language principles (avoid jargon where possible)

## Timestamps Format

Timestamps allow viewers to jump to relevant sections:

```
0:00 - Introduction
1:30 - Installation Steps
3:45 - Initial Configuration
8:20 - First Security Scan
10:45 - Conclusion
```

## Future Enhancements

- [ ] Interactive chapter markers in YouTube uploads
- [ ] Multiple language subtitle generation
- [ ] Video analytics integration
- [ ] Viewer feedback collection
- [ ] Tutorial difficulty voting system
- [ ] Automated video sitemap for SEO

## Support

For questions about video content or recording process:

- Check existing tutorials and transcripts
- Open an issue with `tutorial` label
- Contact: [support contact or documentation link]

---

**Last Updated**: 2026-07-05  
**Maintained By**: ShadowCypher Team  
**Total Tutorials**: 0 Published | 13 Planned
