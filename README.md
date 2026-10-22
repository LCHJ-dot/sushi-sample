# Ancient Wisdom Shorts — Automated Video Pipeline

An end-to-end pipeline that turns a **script** into a **finished short video**:
voiceover → SVG ink-wash motion graphics → headless screen recording → ffmpeg mux.

## What it produces
A 90-second sample episode on **Su Shi (苏轼)**, rendered at 1920×1080 (H.264 + AAC)
with SAPI Chinese voiceover and synced subtitles.

## Pipeline
1. **Voiceover** — Windows SAPI (pywin32), measure real duration → derive timeline
2. **Animation** — procedural SVG ink-wash (feTurbulence / feDisplacementMap / feGaussianBlur)
3. **Capture** — Playwright drives Edge for headless frame rendering
4. **Mux** — ffmpeg combines audio + video + subtitles

## Files
- `苏轼-样片.html` — interactive preview (5 scenes, auto-play & clean modes)
- `build_video.py` — render pipeline
- `01-苏轼-样片脚本.html` — script + storyboard
- `frames/` — public-domain source paintings (Met Museum Open Access)

## Run
```bash
python build_video.py   # Windows: needs Edge + ffmpeg + pywin32
```

## Notes
- Art assets are public domain (Met Museum Open Access).
- Voiceover uses Windows SAPI; swap in any TTS engine for production use.
- The rendered `.mp4` is excluded from git (large binary) — see `.gitignore`.
