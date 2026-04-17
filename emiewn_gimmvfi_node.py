import os
import sys
import torch
import types
import collections
import re
import typing
import logging

import folder_paths
import comfy.model_management as mm
from comfy.utils import ProgressBar, load_torch_file

from contextlib import nullcontext
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

GIMMVFI_PACK_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "ComfyUI-GIMM-VFI"
))


def _ensure_gimmvfi_path():
    """Add GIMM-VFI pack to sys.path if not already there."""
    if GIMMVFI_PACK_DIR not in sys.path:
        sys.path.insert(0, GIMMVFI_PACK_DIR)



class softsplat_func(torch.autograd.Function):
    """Pure PyTorch forward splatting - no cupy needed."""

    @staticmethod
    @torch.amp.custom_fwd(device_type="cuda", cast_inputs=torch.float32)
    def forward(ctx, tenIn, tenFlow):
        B, C, H, W = tenIn.shape
        tenOut = tenIn.new_zeros([B, C, H, W])

        gridY, gridX = torch.meshgrid(
            torch.arange(H, device=tenIn.device, dtype=tenFlow.dtype),
            torch.arange(W, device=tenIn.device, dtype=tenFlow.dtype),
            indexing='ij'
        )

        fltX = gridX.unsqueeze(0) + tenFlow[:, 0, :, :]
        fltY = gridY.unsqueeze(0) + tenFlow[:, 1, :, :]

        intNWX = torch.floor(fltX).long()
        intNWY = torch.floor(fltY).long()
        intNEX = intNWX + 1
        intNEY = intNWY
        intSWX = intNWX
        intSWY = intNWY + 1
        intSEX = intNWX + 1
        intSEY = intNWY + 1

        fltNW = (intSEX.float() - fltX) * (intSEY.float() - fltY)
        fltNE = (fltX - intSWX.float()) * (intSWY.float() - fltY)
        fltSW = (intNEX.float() - fltX) * (fltY - intNEY.float())
        fltSE = (fltX - intNWX.float()) * (fltY - intNWY.float())

        batchIdx = torch.arange(B, device=tenIn.device).view(B, 1, 1).expand(B, H, W)

        for cornX, cornY, weight in [
            (intNWX, intNWY, fltNW),
            (intNEX, intNEY, fltNE),
            (intSWX, intSWY, fltSW),
            (intSEX, intSEY, fltSE),
        ]:
            mask = (cornX >= 0) & (cornX < W) & (cornY >= 0) & (cornY < H)
            validB = batchIdx[mask]
            validX = cornX[mask]
            validY = cornY[mask]
            validW = weight[mask]

            for c in range(C):
                vals = tenIn[:, c, :, :][mask] * validW
                tenOut[:, c, :, :].index_put_(
                    (validB, validY, validX),
                    vals,
                    accumulate=True,
                )

        ctx.save_for_backward(tenIn, tenFlow)
        return tenOut

    @staticmethod
    @torch.amp.custom_bwd(device_type="cuda")
    def backward(ctx, tenOutgrad):
        tenIn, tenFlow = ctx.saved_tensors
        tenIngrad = tenIn.new_zeros(tenIn.shape) if ctx.needs_input_grad[0] else None
        tenFlowgrad = tenFlow.new_zeros(tenFlow.shape) if ctx.needs_input_grad[1] else None
        return tenIngrad, tenFlowgrad


def softsplat_pytorch(tenIn, tenFlow, tenMetric, strMode, return_norm=False):
    """Pure PyTorch softsplat function - drop-in replacement."""
    assert strMode.split("-")[0] in ["sum", "avg", "linear", "softmax"]

    if strMode == "sum":
        assert tenMetric is None
    if strMode == "avg":
        assert tenMetric is None
    if strMode.split("-")[0] == "linear":
        assert tenMetric is not None
    if strMode.split("-")[0] == "softmax":
        assert tenMetric is not None

    if strMode == "avg":
        tenIn = torch.cat(
            [tenIn, tenIn.new_ones([tenIn.shape[0], 1, tenIn.shape[2], tenIn.shape[3]])],
            1,
        )
    elif strMode.split("-")[0] == "linear":
        tenIn = torch.cat([tenIn * tenMetric, tenMetric], 1)
    elif strMode.split("-")[0] == "softmax":
        tenIn = torch.cat([tenIn * tenMetric.exp(), tenMetric.exp()], 1)

    tenOut = softsplat_func.apply(tenIn, tenFlow)

    if strMode.split("-")[0] in ["avg", "linear", "softmax"]:
        tenNormalize = tenOut[:, -1:, :, :]

        if len(strMode.split("-")) == 1:
            tenNormalize = tenNormalize + 0.0000001
        elif strMode.split("-")[1] == "addeps":
            tenNormalize = tenNormalize + 0.0000001
        elif strMode.split("-")[1] == "zeroeps":
            tenNormalize[tenNormalize == 0.0] = 1.0
        elif strMode.split("-")[1] == "clipeps":
            tenNormalize = tenNormalize.clip(0.0000001, None)

        if return_norm:
            return tenOut[:, :-1, :, :], tenNormalize

        tenOut = tenOut[:, :-1, :, :] / tenNormalize

    return tenOut


def _patch_softsplat_module():
    """
    Create a fake 'softsplat' module in sys.modules so that when GIMM-VFI's
    gimmvfi_r.py does 'from .modules.softsplat import softsplat', it gets
    our pure PyTorch version instead of the cupy-dependent one.
    """
    mod_key = "gimmvfi.generalizable_INR.modules.softsplat"

    if mod_key not in sys.modules:
        fake_mod = types.ModuleType(mod_key)
        fake_mod.softsplat = softsplat_pytorch
        fake_mod.softsplat_func = softsplat_func
        sys.modules[mod_key] = fake_mod
        log.info("[Emiewn] Patched softsplat module with pure PyTorch implementation (no cupy needed)")


_gimmvfi_deps_cache = None


def _lazy_import_gimmvfi():
    """Lazily import all GIMM-VFI modules at runtime, with cupy patched out."""
    global _gimmvfi_deps_cache
    if _gimmvfi_deps_cache is not None:
        return _gimmvfi_deps_cache

    _ensure_gimmvfi_path()

    _patch_softsplat_module()

    import yaml
    from omegaconf import OmegaConf

    from gimmvfi.generalizable_INR.gimmvfi_r import GIMMVFI_R
    from gimmvfi.generalizable_INR.gimmvfi_f import GIMMVFI_F
    from gimmvfi.generalizable_INR.configs import GIMMVFIConfig
    from gimmvfi.generalizable_INR.raft import RAFT
    from gimmvfi.generalizable_INR.flowformer.core.FlowFormer.LatentCostFormer.transformer import FlowFormer
    from gimmvfi.generalizable_INR.flowformer.configs.submission import get_cfg
    from gimmvfi.utils.utils import InputPadder, RaftArgs, easydict_to_dict

    _gimmvfi_deps_cache = {
        "yaml": yaml,
        "OmegaConf": OmegaConf,
        "GIMMVFI_R": GIMMVFI_R,
        "GIMMVFI_F": GIMMVFI_F,
        "GIMMVFIConfig": GIMMVFIConfig,
        "RAFT": RAFT,
        "FlowFormer": FlowFormer,
        "get_cfg": get_cfg,
        "InputPadder": InputPadder,
        "RaftArgs": RaftArgs,
        "easydict_to_dict": easydict_to_dict,
    }
    return _gimmvfi_deps_cache


def _lazy_import_flow_viz():
    """Lazily import flow visualization utilities."""
    _ensure_gimmvfi_path()
    from gimmvfi.utils.flow_viz import flow_to_image
    return flow_to_image


class EmiewnLoadGIMMVFI:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ([
                    "gimmvfi_r_arb_lpips_fp32.safetensors",
                    "gimmvfi_f_arb_lpips_fp32.safetensors"
                ],),
            },
            "optional": {
                "precision": (["fp32", "bf16", "fp16"], {"default": "fp32"}),
                "torch_compile": ("BOOLEAN", {"default": False, "tooltip": "Compile part of the model with torch.compile (requires Triton)"}),
            },
        }

    RETURN_TYPES = ("GIMMVIF_MODEL",)
    RETURN_NAMES = ("gimmvfi_model",)
    FUNCTION = "loadmodel"
    CATEGORY = "Emiewn"
    DESCRIPTION = "Loads a GIMM-VFI frame interpolation model from ComfyUI/models/interpolation/gimm-vfi"

    def loadmodel(self, model, precision="fp32", torch_compile=False):
        deps = _lazy_import_gimmvfi()
        yaml = deps["yaml"]
        OmegaConf = deps["OmegaConf"]
        GIMMVFI_R = deps["GIMMVFI_R"]
        GIMMVFI_F = deps["GIMMVFI_F"]
        GIMMVFIConfig = deps["GIMMVFIConfig"]
        RAFT = deps["RAFT"]
        FlowFormer = deps["FlowFormer"]
        get_cfg = deps["get_cfg"]
        RaftArgs = deps["RaftArgs"]
        easydict_to_dict = deps["easydict_to_dict"]

        device = mm.get_torch_device()
        offload_device = mm.unet_offload_device()

        dtype_map = {
            "bf16": torch.bfloat16,
            "fp16": torch.float16,
            "fp32": torch.float32,
        }
        dtype = dtype_map.get(precision, torch.float32)

        download_path = os.path.join(folder_paths.models_dir, 'interpolation', 'gimm-vfi')
        model_path = os.path.join(download_path, model)

        if not os.path.exists(model_path):
            log.info(f"Downloading GIMM-VFI model to: {model_path}")
            from huggingface_hub import snapshot_download
            snapshot_download(
                repo_id="Kijai/GIMM-VFI_safetensors",
                allow_patterns=[f"*{model}*"],
                local_dir=download_path,
                local_dir_use_symlinks=False,
            )

        configs_dir = os.path.join(GIMMVFI_PACK_DIR, "configs", "gimmvfi")

        if "gimmvfi_r" in model:
            config_path = os.path.join(configs_dir, "gimmvfi_r_arb.yaml")
            flow_model = "raft-things_fp32.safetensors"
        elif "gimmvfi_f" in model:
            config_path = os.path.join(configs_dir, "gimmvfi_f_arb.yaml")
            flow_model = "flowformer_sintel_fp32.safetensors"

        flow_model_path = os.path.join(download_path, flow_model)

        if not os.path.exists(flow_model_path):
            log.info(f"Downloading flow model to: {flow_model_path}")
            from huggingface_hub import snapshot_download
            snapshot_download(
                repo_id="Kijai/GIMM-VFI_safetensors",
                allow_patterns=[f"*{flow_model}*"],
                local_dir=download_path,
                local_dir_use_symlinks=False,
            )

        with open(config_path) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        config = easydict_to_dict(config)
        config = OmegaConf.create(config)
        arch_defaults = GIMMVFIConfig.create(config.arch)
        config = OmegaConf.merge(arch_defaults, config.arch)

        if "gimmvfi_r" in model:
            gimmvfi_model = GIMMVFI_R(dtype, config)
            raft_args = RaftArgs(
                small=False,
                mixed_precision=False,
                alternate_corr=False
            )
            raft_model = RAFT(raft_args)
            raft_sd = load_torch_file(flow_model_path)
            raft_model.load_state_dict(raft_sd, strict=True)
            raft_model.to(dtype).to(device)
            flow_estimator = raft_model
        elif "gimmvfi_f" in model:
            gimmvfi_model = GIMMVFI_F(dtype, config)
            cfg = get_cfg()
            flowformer = FlowFormer(cfg.latentcostformer)
            flowformer_sd = load_torch_file(flow_model_path)
            flowformer.load_state_dict(flowformer_sd, strict=True)
            flow_estimator = flowformer.to(dtype).to(device)

        sd = load_torch_file(model_path)
        gimmvfi_model.load_state_dict(sd, strict=False)

        gimmvfi_model.flow_estimator = flow_estimator
        gimmvfi_model = gimmvfi_model.eval().to(dtype).to(device)

        if torch_compile:
            gimmvfi_model = torch.compile(gimmvfi_model)

        return (gimmvfi_model,)


class EmiewnGIMMVFIInterpolate:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "gimmvfi_model": ("GIMMVIF_MODEL",),
                "images": ("IMAGE", {"tooltip": "Batch of images to interpolate between"}),
                "ds_factor": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 1.0, "step": 0.01}),
                "interpolation_factor": ("INT", {"default": 2, "min": 1, "max": 100, "step": 1}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
            "optional": {
                "output_flows": ("BOOLEAN", {"default": False, "tooltip": "Output the optical flow tensors"}),
            },
        }

    RETURN_TYPES = ("IMAGE", "IMAGE",)
    RETURN_NAMES = ("images", "flow_tensors",)
    FUNCTION = "interpolate"
    CATEGORY = "Emiewn"
    DESCRIPTION = "Interpolates between frames using GIMM-VFI for smooth slow-motion or frame rate upscaling"

    def interpolate(self, gimmvfi_model, images, ds_factor, interpolation_factor, seed, output_flows=False):
        import cv2

        deps = _lazy_import_gimmvfi()
        InputPadder = deps["InputPadder"]

        mm.soft_empty_cache()
        images = images.permute(0, 3, 1, 2)
        torch.manual_seed(seed)
        torch.cuda.manual_seed(seed)

        device = mm.get_torch_device()
        offload_device = mm.unet_offload_device()

        dtype = gimmvfi_model.dtype

        out_images_list = []
        flows = []
        start = 0
        end = images.shape[0] - 1
        pbar = ProgressBar(images.shape[0] - 1)

        autocast_device = mm.get_autocast_device(device)
        cast_context = torch.autocast(device_type=autocast_device, dtype=dtype) if dtype != torch.float32 else nullcontext()

        with cast_context:
            for j in tqdm(range(start, end)):
                I0 = images[j].unsqueeze(0)
                I2 = images[j + 1].unsqueeze(0)

                if j == start:
                    out_images_list.append(I0.squeeze(0).permute(1, 2, 0))

                padder = InputPadder(I0.shape, 32)
                I0, I2 = padder.pad(I0, I2)
                xs = torch.cat((I0.unsqueeze(2), I2.unsqueeze(2)), dim=2).to(device, non_blocking=True)

                batch_size = xs.shape[0]
                s_shape = xs.shape[-2:]

                coord_inputs = [
                    (
                        gimmvfi_model.sample_coord_input(
                            batch_size,
                            s_shape,
                            [1 / interpolation_factor * i],
                            device=xs.device,
                            upsample_ratio=ds_factor,
                        ),
                        None,
                    )
                    for i in range(1, interpolation_factor)
                ]
                timesteps = [
                    i * 1 / interpolation_factor * torch.ones(xs.shape[0]).to(xs.device)
                    for i in range(1, interpolation_factor)
                ]

                all_outputs = gimmvfi_model(xs, coord_inputs, t=timesteps, ds_factor=ds_factor)
                out_frames = [padder.unpad(im) for im in all_outputs["imgt_pred"]]
                out_flowts = [padder.unpad(f) for f in all_outputs["flowt"]]

                if output_flows:
                    flow_to_image = _lazy_import_flow_viz()
                    flowt_imgs = [
                        flow_to_image(
                            flowt.squeeze().detach().cpu().permute(1, 2, 0).numpy(),
                            convert_to_bgr=True,
                        )
                        for flowt in out_flowts
                    ]
                I1_pred_img = [
                    (I1_pred[0].detach().cpu().permute(1, 2, 0))
                    for I1_pred in out_frames
                ]

                for i in range(interpolation_factor - 1):
                    out_images_list.append(I1_pred_img[i])
                    if output_flows:
                        flows.append(flowt_imgs[i])

                out_images_list.append(
                    ((padder.unpad(I2)).squeeze().detach().cpu().permute(1, 2, 0))
                )
                pbar.update(1)

        image_tensors = torch.stack(out_images_list)
        image_tensors = image_tensors.cpu().float()

        rgb_images = [cv2.cvtColor(flow, cv2.COLOR_BGR2RGB) for flow in flows]

        if output_flows:
            flow_tensors = torch.stack([torch.from_numpy(image) for image in rgb_images])
            flow_tensors = flow_tensors / 255.0
            flow_tensors = flow_tensors.cpu().float()
        else:
            flow_tensors = torch.zeros(1, 64, 64, 3)

        return (image_tensors, flow_tensors)
