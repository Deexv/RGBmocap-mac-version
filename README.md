# RGB MoCap for Mac (Apple Silicon)

A macOS (Apple Silicon) port of [toyxyz/RGBMocap](https://github.com/toyxyz/toyxyz_RGBMocap),
trimmed to the essentials: **video motion capture** with the GVHMR pipeline and
**export to Blender** (FBX / BVH / portable .blend bundle), plus live bone
streaming into Blender. Windows-only and optional heavy backends (Unreal Live
Link, MAMMA, PromptHMR, GEM-X, SAM 3.1, PEAR live capture, ExMR, FlowHMR, Face
tracking) were removed.

Based on the upstream `macos_support` branch: models run on the GPU through
PyTorch **MPS**, the native motion-correction module is compiled for **arm64**
(SSE intrinsics translated to NEON via sse2neon), and the 3D viewport falls
back to NumPy skinning below OpenGL 4.3 (macOS provides OpenGL 4.1).

## What is included

- **GVHMR reconstruction**: track -> (pva) -> features -> gvhmr, with optional
  HTD Refine, FootMR ankle refinement, HandFlow finger inference and motion
  contact correction (native arm64 module).
- **Multi-person**: Find People (YOLO + OSNet ReID) and per-person batch jobs.
- **Export**: BVH, FBX (Mixamo/Humanoid52), portable Blender project bundle
  (video + camera + baked armature), and character retargeting.
- **Blender streaming**: the `blender_addon/rgbmocap_bone_stream.py` addon
  receives live bone data over a local socket (port 49168).
- **RIFE** frame interpolation (optional weights) runs on Apple Silicon.

## Requirements

- Apple Silicon Mac (M1/M2/M3/M4/M5), macOS 14 or newer.
- Xcode command line tools, CMake 3.24+, FFmpeg, Git:

  ```sh
  xcode-select --install
  brew install cmake ffmpeg git
  ```

- About 2.5 GiB for the runtimes plus model weights (GVHMR set with add-ons is
  roughly 15 GiB; the base GVHMR-only set is smaller).
- Blender 4.5+ / 5.x for the Blender project export and retargeting
  (`/Applications/Blender.app` is found automatically, or set `RGBMOCAP_BLENDER`).

## Install and run

```sh
git clone https://github.com/Deexv/RGBmocap-mac-version.git
cd RGBmocap-mac-version
./install.sh          # pinned uv -> private CPython 3.10 -> hash-checked arm64 wheels
./RGBMoCap.sh         # launch the app
```

`./install.sh --verify-all` performs a full runtime check. Models are prepared
in the app's Model Manager (registered SMPL-X files need your own account).

## Pipeline on MPS

`mocap/mps_compat.py` is installed by every worker on macOS: it redirects
CUDA device moves to MPS, answers the memory queries used for batch planning
and Resource Safety from `torch.mps`, and patches the few ops where MPS differs
(strided conv views, grid_sample border padding). See `docs/MACOS.md` for the
full upstream notes and measured timings (tested upstream on an M5 Max).

## Project layout

- `mocap/` — application and inference pipeline (GVHMR + export).
- `blender_addon/` — Blender bone-stream receiver addon.
- `installer/runtime-lock-macos.json` — pinned Apple Silicon wheels
  (shared / gui / hand / htd groups; ~0.7 GiB download).
- `third_party/` — vendored GVHMR, HTD-Refine, FootMR, HandFlow, OSNet, RIFE,
  KimodoMotionCorrection (built at install with sse2neon).
- `docs/MACOS.md` — upstream macOS guide (status table, known limitations).

## Removed relative to upstream

Windows installers (`*.cmd`, `git_bootstrap.ps1`), Unreal plugin + Live Link
sender, UE5 mannequin retarget profiles, MAMMA / PromptHMR / GEM-X / SAM 3.1 /
PEAR / ExMR / FlowHMR / Face tracking backends and their runtime lock files,
the Windows prebuilt motion-correction `.pyd`, and the Linux-specific lock
files. BVH/FBX export never needed the removed UE5 paths.

## License

Same as upstream (see LICENSE and THIRD_PARTY_NOTICES.md). Third-party model
weights keep their own licenses and registration requirements.
