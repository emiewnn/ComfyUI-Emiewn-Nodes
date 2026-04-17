import torch
import numpy as np
from PIL import Image, ImageOps
import folder_paths
import server
import random

def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0)[None,]

class EmiewnImgPaste:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"image": ("STRING", {"default": "", "multiline": False})}}
    RETURN_TYPES = ("IMAGE", "MASK")
    FUNCTION = "load_image"
    CATEGORY = "Emiewn"
    def load_image(self, image):
        image_path = folder_paths.get_annotated_filepath(image)
        i = Image.open(image_path)
        i = ImageOps.exif_transpose(i)
        image_rgb = i.convert("RGB")
        image = pil2tensor(image_rgb)
        mask = torch.zeros((64,64), dtype=torch.float32, device="cpu")
        if 'A' in i.getbands():
            mask = 1. - torch.from_numpy(np.array(i.getchannel('A')).astype(np.float32) / 255.0)
        return (image, mask)

class EmiewnImgCrop:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "bypass_node": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "crop_data": ("STRING", {"default": "", "multiline": False}),
            },
            "hidden": { "unique_id": "UNIQUE_ID", }
        }
    RETURN_TYPES = ("IMAGE", "INT", "INT")
    RETURN_NAMES = ("image", "width", "height")
    FUNCTION = "process_crop"
    CATEGORY = "Emiewn"

    def process_crop(self, image, bypass_node=False, crop_data="", unique_id=None, **kwargs):
        if bypass_node:
            _, h, w, _ = image.shape
            return (image, w, h)

        if crop_data and isinstance(crop_data, str) and "," in crop_data:
            try:
                vals = list(map(int, crop_data.split(',')))
                if len(vals) == 4:
                    x, y, w, h = vals
                    pil_img = tensor2pil(image)
                    img_w, img_h = pil_img.size
                    x, y = max(0, x), max(0, y)
                    w, h = min(w, img_w - x), min(h, img_h - y)
                    if w > 0 and h > 0:
                        return (pil2tensor(pil_img.crop((x, y, x + w, y + h))), w, h)
            except Exception: pass


        pil_img = tensor2pil(image)
        temp_filename = f"emiewn_crop_{random.randint(0, 1000000)}.png"
        pil_img.save(f"{folder_paths.get_temp_directory()}/{temp_filename}")
        server.PromptServer.instance.send_sync("emiewn.crop_request", {
            "node_id": unique_id, "image_url": f"/view?filename={temp_filename}&type=temp"
        })

        raise Exception("Emiewn Crop: Workflow paused for user input.")