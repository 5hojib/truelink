from __future__ import annotations

from .base import BaseResolver

# from .yandex import YandexDiskResolver
from .buzzheavier import BuzzHeavierResolver

# from .uploadhaven import UploadHavenResolver
from .fuckingfast import FuckingFastResolver

# from .devuploads import DevUploadsResolver
from .lulacloud import LulaCloudResolver

# from .mediafile import MediaFileResolver
# from .mediafire import MediaFireResolver

__all__ = [
    "BaseResolver",
    # 'YandexDiskResolver',
    "BuzzHeavierResolver",
    # 'UploadHavenResolver',
    "FuckingFastResolver",
    # 'DevUploadsResolver',
    "LulaCloudResolver",
    # 'MediaFileResolver',
    # 'MediaFireResolver',
]
