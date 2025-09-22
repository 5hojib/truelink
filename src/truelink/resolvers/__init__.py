"""Resolvers for various providers."""

from __future__ import annotations

from .base import BaseResolver
from .buzzheavier import BuzzHeavierResolver
from .fichier import FichierResolver
from .fuckingfast import FuckingFastResolver
from .gofile import GoFileResolver
from .linkbox import LinkBoxResolver
from .linkvertise import LinkvertiseResolver  # added linkvertise
from .lulacloud import LulaCloudResolver
from .mediafile import MediaFileResolver
from .mediafire import MediaFireResolver
from .onedrive import OneDriveResolver
from .pcloud import PCloudResolver
from .pixeldrain import PixelDrainResolver
from .ranoz import RanozResolver
from .streamtape import StreamtapeResolver
from .swisstransfer import SwissTransferResolver
from .terabox import TeraboxResolver
from .tmpsend import TmpSendResolver
from .uploadee import UploadEeResolver
from .yandexdisk import YandexDiskResolver
from .xham import XhamResolver
from .spankbang import SpankBangResolver

__all__ = [
    "BaseResolver",
    "BuzzHeavierResolver",
    "FichierResolver",
    "FuckingFastResolver",
    "GoFileResolver",
    "LinkBoxResolver",
    "LinkvertiseResolver",  # added linkvertise
    "LulaCloudResolver",
    "MediaFileResolver",
    "MediaFireResolver",
    "OneDriveResolver",
    "PCloudResolver",
    "PixelDrainResolver",
    "RanozResolver",
    "StreamtapeResolver",
    "SwissTransferResolver",
    "TeraboxResolver",
    "TmpSendResolver",
    "UploadEeResolver",
    "YandexDiskResolver",
    "XhamResolver",
    "SpankBangResolver",
]
