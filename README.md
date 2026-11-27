<div align="center">

# RGB MoCap for Mac — Free AI Video Motion Capture (Apple Silicon)

**Turn any video into 3D human animation — natively on your M-series Mac.**

AI motion capture from monocular RGB video, rebuilt for macOS Apple Silicon.
Reconstruct body motion with GVHMR, refine feet and fingers, then export to
Blender (FBX / BVH / .blend bundle) or stream bones live — 100% locally,
no cloud, no subscription, no NVIDIA GPU required.

[Quick start](#install-and-run) · [Workflow](#how-it-works) · [Memory guide](#memory-guide-16-gb-macs) · [Troubleshooting](#troubleshooting) · [Credits](#credits--license)

</div>

---

https://github.com/Deexv/RGBmocap-mac-version/releases/download/demo-media/rgbmocap-demo.mp4

<video src="docs/media/rgbmocap-demo.mp4" controls muted width="100%"></video>

*RGB MoCap running on a MacBook Pro (M1 Pro, 16 GB): drag a video in, reconstruct 3D human motion, review it in the viewport, and export to Blender.*
([download the clip](https://github.com/Deexv/RGBmocap-mac-version/releases/download/demo-media/rgbmocap-demo.mp4))

## What is this?

A macOS (Apple Silicon) port of [toyxyz's RGBMocap](https://github.com/toyxyz/toyxyz_RGBMocap),
trimmed to the essentials: **video motion capture** with the
[GVHMR](https://github.com/zju3dv/GVHMR) pipeline and **Blender export**.
Windows-only and optional heavy backends (Unreal Live Link, MAMMA, PromptHMR,
GEM-X, SAM 3.1, PEAR live capture, ExMR, FlowHMR, Face tracking) were removed,
so the whole thing fits a Mac.

- **Works without CUDA** — models run on the GPU through PyTorch **MPS**
  (`mocap/mps_compat.py` redirects CUDA calls to Metal).
- **Native arm64** — the motion-correction C++ module is compiled with NEON
  (SSE intrinsics translated via sse2neon); the 3D viewport falls back to
  NumPy skinning below OpenGL 4.3 (macOS provides 4.1).
- **Private and offline** — every model, every stage, runs on your machine.

## Features

- **GVHMR reconstruction**: track → (PVA) → features → GVHMR, with optional
  **HTD Refine** (temporal consistency), **FootMR** (ankle/foot angles),
  **HandFlow** (finger tracking) and contact-based **motion correction**
  (foot/palm sliding reduction with editable contact timings).
- **Multi-person videos**: **Find person** (YOLO detection + OSNet re-ID)
  discovers everyone in the clip; pick one or several people, each gets their
  own take and export.
- **Export everywhere Blender is**: BVH, FBX (Mixamo / Humanoid52), and a
  portable **.blend project bundle** (video + camera + baked armature in one
  file). Character retargeting to Mixamo FBX / VRM / PMX is included.
- **Live bone streaming to Blender**: the bundled add-on
  (`blender_addon/rgbmocap_bone_stream.py`) receives bone data over a local
  socket during playback, then bakes it into Blender Actions.
- **RIFE frame interpolation**: optionally interpolate videos below 30 fps
  before reconstruction (runs on Apple Silicon).
- **Projects**: save work with separate results per model; side-by-side
  video/viewport MP4 export via **File > Export Preview**.

## Requirements

- Apple Silicon Mac (M1 / M2 / M3 / M4), macOS 14 or newer.
  **Tested on a MacBook Pro M1 Pro with 16 GB of unified memory.**
- Xcode command line tools, CMake 3.24+, FFmpeg, Git:

  ```sh
  xcode-select --install
  brew install cmake ffmpeg git
  ```

- Disk: about 2.5 GiB for runtimes plus model weights
  (the GVHMR set with add-ons is roughly 15 GiB).
- Blender 4.5+ / 5.x for project export and retargeting
  (`/Applications/Blender.app` is found automatically, or set `RGBMOCAP_BLENDER`).

## Install and run

```sh
git clone https://github.com/Deexv/RGBmocap-mac-version.git
cd RGBmocap-mac-version
./install.sh          # pinned uv -> private CPython 3.10 -> hash-checked arm64 wheels
./RGBMoCap.sh         # launch the app
```

`./install.sh --verify-all` performs a full runtime check. To update, close
the app and run `./update.sh` from the same folder.

AI weights are downloaded **inside the app** via **Model Manager** (most are
public auto-downloads; SMPL-X body files require your own free registration).

## How it works

1. **Prepare models once**: open Model Manager and click **Download All** for
   the GVHMR workflow (YOLO, OSNet, HMR2, ViTPose, GVHMR, SMPL-X, PVA, FootMR,
   HandFlow files).
2. **Open a video**: **File > Open Video**, or just drag & drop an MP4/MOV.
3. **(Optional) Find person**: for multi-person clips, click **Find person**,
   then check who you want to reconstruct. For a single person you can skip
   this and go straight to Reconstruct 3D.
4. **Reconstruct 3D**: the pipeline runs locally on MPS; watch progress in
   Console. Refinements (HTD / FootMR / HandFlow) are checkboxes.
5. **Review & correct**: scrub the timeline, edit foot/palm contacts if
   needed, apply Motion Correction.
6. **Export**: **File > Export...** for BVH/FBX/Blender bundle, retarget to a
   character, or stream bones live into Blender.

In Blender 5.0+, the [Toyxyz Blender Retargeter](https://github.com/toyxyz/toyxyz-blender-retargeter)
add-on can transfer exported animation to another humanoid rig.

## Memory guide (16 GB Macs)

16 GB of unified memory is enough for the full GVHMR pipeline — with one
caveat learned the hard way on an M1 Pro:

> **If the app is terminated by macOS while processing** ("closed because the
> system ran out of memory"), open **Processing Resources → Resource Mode →
> Low Memory** and run the job again. Low Memory uses CPU loading/offloading:
> slower, but it keeps the peak GPU working set down and lets long jobs
> finish. Closing other large apps (browsers, Blender) before reconstructing
> also helps.

- **Resource Mode > Automatic** (default) uses the fast path when memory
  permits and switches supported stages to Low Memory when needed. On a
  16 GB Mac, selecting Low Memory *before* a long reconstruction is the
  reliable choice.
- **Resource Safety** (on by default) stops jobs when system RAM runs low
  instead of letting macOS kill the app. Automatic batching and OOM handling
  stay active either way.
- MPS reports out-of-memory as a plain error, so CUDA-style automatic OOM
  retry does not run — that is why the Resource Mode setting matters more on
  macOS than on Windows.

## Pipeline on MPS

`mocap/mps_compat.py` is installed by every worker on macOS. It redirects
CUDA device moves to MPS, answers the memory queries used for batch planning
and Resource Safety from `torch.mps`, and patches the few ops where MPS
differs (strided conv views, `grid_sample` border padding). See
[docs/MACOS.md](docs/MACOS.md) for the full upstream notes and measured
timings.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| App killed during reconstruction | **Processing Resources → Resource Mode → Low Memory**, free some RAM, retry. See [Memory guide](#memory-guide-16-gb-macs). |
| "Prepare person detection models" when clicking Find person | Open Model Manager → GVHMR tab → download the missing **Person Identity / OSNet** model (fixed in this fork; earlier builds dead-ended here). |
| Models show "Missing" | Model Manager → select the GVHMR workflow tab → **Download All**. SMPL-X needs manual registration and import. |
| Install fails | Check `xcode-select`, CMake ≥ 3.24 and FFmpeg are installed; rerun `./install.sh`; `./install.sh --verify-all` diagnoses. |
| Blender not found | Install Blender 4.5+ under /Applications or `export RGBMOCAP_BLENDER=/path/to/blender`. |

## Project layout

- `mocap/` — application and inference pipeline (GVHMR + export).
- `blender_addon/` — Blender bone-stream receiver add-on.
- `installer/runtime-lock-macos.json` — pinned Apple Silicon wheels
  (shared / gui / hand / htd groups; ~0.7 GiB download).
- `third_party/` — vendored GVHMR, HTD-Refine, FootMR, HandFlow, OSNet, RIFE,
  KimodoMotionCorrection (built at install with sse2neon).
- `docs/` — user guide, macOS notes, citations, validation.

## Changes in this fork

Based on upstream's `macos_support` branch, additionally:

- Trimmed to the GVHMR pipeline + Blender export; removed Unreal/Windows
  installers, MAMMA, PromptHMR, GEM-X, SAM 3.1, PEAR, ExMR, FlowHMR and face
  tracking backends with their runtime locks.
- Fixed drag-and-drop video loading (removed-widget crash) and the
  **Find person** Model Manager dead-end.
- Verified end-to-end on MacBook Pro M1 Pro / 16 GB, including the Low Memory
  recovery path.
- 44 automated tests (GUI regression suite + model manager + streaming).

## Credits & license

- **Original RGB MoCap** by **[toyxyz](https://github.com/toyxyz)** —
  [github.com/toyxyz/toyxyz_RGBMocap](https://github.com/toyxyz/toyxyz_RGBMocap).
  All credit for the application, the pipeline integration and the original
  macOS/`macos_support` work belongs to them. This fork only trims it for the
  Mac and fixes Mac-specific bugs.
- Core research: **GVHMR** (SIGGRAPH Asia 2024, Zhejiang University 3DV),
  **HTD-Refine**, **FootMR**, HandFlow, **YOLO**, **OSNet**, **RIFE** and the
  SMPL-X body model — see [docs/CITATIONS.md](docs/CITATIONS.md) and
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for papers, authors and terms.
- License: MIT, same as upstream (see [LICENSE](LICENSE)). Third-party model
  weights keep their own licenses and registration requirements.

<p align="center">Built on excellent research. If RGB MoCap helps your work,
star the <a href="https://github.com/toyxyz/toyxyz_RGBMocap">original project</a> too.</p>
