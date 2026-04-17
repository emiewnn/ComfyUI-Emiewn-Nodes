import torch

BUCKET_OPTIONS = {
    (416, 960),
    (448, 864),
    (480, 832),
    (512, 768),
    (544, 704),
    (576, 672),
    (608, 640),
    (640, 608),
    (672, 576),
    (704, 544),
    (768, 512),
    (832, 480),
    (864, 448),
    (960, 416),
}


def find_nearest_bucket(h, w, resolution=640):
    """Find the nearest WAN 2.2 I2V compatible bucket size that preserves aspect ratio."""
    min_metric = float('inf')
    best_bucket = None
    for (bucket_h, bucket_w) in BUCKET_OPTIONS:
        metric = abs(h * bucket_w - w * bucket_h)
        if metric <= min_metric:
            min_metric = metric
            best_bucket = (bucket_h, bucket_w)

    if best_bucket is None:
        best_bucket = (640, 640)

    if resolution != 640:
        scale_factor = resolution / 640.0
        scaled_height = round(best_bucket[0] * scale_factor / 16) * 16
        scaled_width = round(best_bucket[1] * scale_factor / 16) * 16
        best_bucket = (scaled_height, scaled_width)

    return best_bucket


class EmiewnNearestI2VRes:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE", {"tooltip": "Image to find nearest I2V bucket size for"}),
                "base_resolution": ("INT", {
                    "default": 640,
                    "min": 64,
                    "max": 2048,
                    "step": 16,
                    "tooltip": "Target base resolution (default 640 for WAN 2.2)"
                }),
            },
        }

    RETURN_TYPES = ("INT", "INT",)
    RETURN_NAMES = ("width", "height",)
    FUNCTION = "process"
    CATEGORY = "Emiewn"
    DESCRIPTION = "Finds the closest WAN 2.2 I2V compatible resolution bucket for the input image while preserving aspect ratio"

    def process(self, image, base_resolution):
        H, W = image.shape[1], image.shape[2]
        new_height, new_width = find_nearest_bucket(H, W, resolution=base_resolution)
        return (new_width, new_height,)
