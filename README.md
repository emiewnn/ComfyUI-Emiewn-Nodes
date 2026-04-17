# ComfyUI-Emiewn-Nodes

A collection of custom nodes for [ComfyUI](https://github.com/comfyanonymous/ComfyUI).

## Nodes

### Emiewn Img Paste
Paste images directly from your clipboard or drag & drop into ComfyUI. Supports instant preview with resolution display.

### Emiewn Quick Crop
Interactive crop tool with a visual overlay. Select a region on your image and apply — the workflow pauses for your input and resumes automatically.

### Emiewn Nearest I2V Res
Finds the closest WAN 2.2 Image-to-Video compatible resolution bucket for your input image while preserving aspect ratio. Supports configurable base resolution.

### Emiewn Load GIMM-VFI
Loads a [GIMM-VFI](https://github.com/GSeanCDAT/GIMM-VFI) frame interpolation model. Includes a built-in pure PyTorch softsplat implementation (no cupy required). Models are auto-downloaded from HuggingFace on first use.

### Emiewn GIMM-VFI Interpolate
Interpolates between frames using GIMM-VFI for smooth slow-motion or frame rate upscaling. Supports configurable interpolation factor and optional optical flow output.

## Installation

1. Clone this repository into your `ComfyUI/custom_nodes/` directory:
   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/YOUR_USERNAME/ComfyUI-Emiewn-Nodes.git
   ```

2. Restart ComfyUI.

## Dependencies

- **GIMM-VFI nodes** require [ComfyUI-GIMM-VFI](https://github.com/kijai/ComfyUI-GIMM-VFI) to be installed in your `custom_nodes` folder (used for model configs and utilities).
- Models are automatically downloaded to `ComfyUI/models/interpolation/gimm-vfi/` on first use.

## License

MIT
