from .emiewn_node import EmiewnImgPaste, EmiewnImgCrop
from .emiewn_bucket_node import EmiewnNearestI2VRes
from .emiewn_gimmvfi_node import EmiewnLoadGIMMVFI, EmiewnGIMMVFIInterpolate

NODE_CLASS_MAPPINGS = {
    "EmiewnImgPaste": EmiewnImgPaste,
    "EmiewnImgCrop": EmiewnImgCrop,
    "EmiewnNearestI2VRes": EmiewnNearestI2VRes,
    "EmiewnLoadGIMMVFI": EmiewnLoadGIMMVFI,
    "EmiewnGIMMVFIInterpolate": EmiewnGIMMVFIInterpolate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EmiewnImgPaste": "Emiewn Img Paste",
    "EmiewnImgCrop": "Emiewn Quick Crop",
    "EmiewnNearestI2VRes": "Emiewn Nearest I2V Res",
    "EmiewnLoadGIMMVFI": "Emiewn Load GIMM-VFI",
    "EmiewnGIMMVFIInterpolate": "Emiewn GIMM-VFI Interpolate",
}

WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]