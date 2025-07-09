# ruff: noqa: F405, F403
from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

from .exceptions import InvalidURLException, UnsupportedProviderException
from .resolvers import *

if TYPE_CHECKING:
    from .types import FolderResult, LinkResult


class TrueLinkResolver:
    """Main resolver class for extracting direct download links"""

    def __init__(self):
        self._resolvers: dict[str, type] = {
            # Buzzheavier
            "buzzheavier.com": BuzzHeavierResolver,
            # Lulacloud
            "lulacloud.com": LulaCloudResolver,
            # FuckingFast
            "fuckingfast.co": FuckingFastResolver,
            # Yandex
            "yadi.sk": YandexDiskResolver,
            "disk.yandex.": YandexDiskResolver,
            # Devupload
            "devuploads.com": DevUploadsResolver,
            "devuploads.net": DevUploadsResolver,
            # UploadHaven
            "uploadhaven.com": UploadHavenResolver,
            # Meduafile
            "mediafile.cc": MediaFileResolver,
            # MediaFire
            "mediafire.com": MediaFireResolver,
            # hxfile
            "hxfile.co": HxFileResolver,
            # OneDrive
            "1drv.ms": OneDriveResolver,
            "onedrive.live.com": OneDriveResolver,
            # pixel drains
            "pixeldrain.com": PixelDrainResolver,
            "pixeldra.in": PixelDrainResolver,
            # streamtape
            "streamtape.com": StreamtapeResolver,
            "streamtape.co": StreamtapeResolver,
            "streamtape.cc": StreamtapeResolver,
            "streamtape.to": StreamtapeResolver,
            "streamtape.net": StreamtapeResolver,
            "streamta.pe": StreamtapeResolver,
            "streamtape.xyz": StreamtapeResolver,
            # 1fichier
            "1fichier.com": FichierResolver,
            # Krakenfiles
            "krakenfiles.com": KrakenFilesResolver,
            # upload ee
            "upload.ee": UploadEeResolver,
            # Gofile
            "gofile.io": GoFileResolver,
            # tmpsend
            "tmpsend.com": TmpSendResolver,
            # pcloud
            "u.pcloud.link": PCloudResolver,
            "pcloud.com": PCloudResolver,
            # qiwi
            "qiwi.gg": QiwiResolver,
            # Swisstrensfer
            "swisstransfer.com": SwissTransferResolver,
            # DoodStream
            "dood.watch": DoodStreamResolver,
            "doodstream.com": DoodStreamResolver,
            "dood.to": DoodStreamResolver,
            "dood.so": DoodStreamResolver,
            "dood.cx": DoodStreamResolver,
            "dood.la": DoodStreamResolver,
            "dood.ws": DoodStreamResolver,
            "dood.sh": DoodStreamResolver,
            "doodstream.co": DoodStreamResolver,
            "dood.pm": DoodStreamResolver,
            "dood.wf": DoodStreamResolver,
            "dood.re": DoodStreamResolver,
            "dood.video": DoodStreamResolver,
            "dooood.com": DoodStreamResolver,
            "dood.yt": DoodStreamResolver,
            "doods.yt": DoodStreamResolver,
            "dood.stream": DoodStreamResolver,
            "doods.pro": DoodStreamResolver,
            "ds2play.com": DoodStreamResolver,
            "d0o0d.com": DoodStreamResolver,
            "ds2video.com": DoodStreamResolver,
            "do0od.com": DoodStreamResolver,
            "d000d.com": DoodStreamResolver,
            "vide0.net": DoodStreamResolver,
            # linkbox
            "linkbox.to": LinkBoxResolver,
            "lbx.to": LinkBoxResolver,
            "linkbox.cloud": LinkBoxResolver,
            "teltobx.net": LinkBoxResolver,
            "telbx.net": LinkBoxResolver,
            # file press
            "filepress": FilePressResolver,
            # wWeTransfer
            "wetransfer.com": WeTransferResolver,
            "we.tl": WeTransferResolver,
            # terabox
            "terabox.com": TeraboxResolver,
            "nephobox.com": TeraboxResolver,
            "4funbox.com": TeraboxResolver,
            "mirrobox.com": TeraboxResolver,
            "momerybox.com": TeraboxResolver,
            "teraboxapp.com": TeraboxResolver,
            "1024tera.com": TeraboxResolver,
            "terabox.app": TeraboxResolver,
            "gibibox.com": TeraboxResolver,
            "goaibox.com": TeraboxResolver,
            "terasharelink.com": TeraboxResolver,
            "teraboxlink.com": TeraboxResolver,
            "freeterabox.com": TeraboxResolver,
            "1024terabox.com": TeraboxResolver,
            "teraboxshare.com": TeraboxResolver,
            "terafileshare.com": TeraboxResolver,
            "terabox.club": TeraboxResolver,
        }

    def _get_resolver(self, url: str):
        """Get appropriate resolver for URL"""
        domain = urlparse(url).hostname
        if not domain:
            raise InvalidURLException("Invalid URL: No domain found")

        for pattern, resolver_class in self._resolvers.items():
            if pattern in domain:
                return resolver_class()

        raise UnsupportedProviderException(f"No resolver found for domain: {domain}")

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """
        Resolve a URL to direct download link(s) and return as a LinkResult or FolderResult object.

        Args:
            url: The URL to resolve

        Returns:
            A LinkResult or FolderResult object.

        Raises:
            InvalidURLException: If URL is invalid
            UnsupportedProviderException: If provider is not supported
            ExtractionFailedException: If extraction fails
        """
        resolver_instance = self._get_resolver(url)
        async with resolver_instance:
            return await resolver_instance.resolve(url)

    def is_supported(self, url: str) -> bool:
        """
        Check if URL is supported

        Args:
            url: The URL to check

        Returns:
            True if supported, False otherwise
        """
        try:
            self._get_resolver(url)
            return True
        except UnsupportedProviderException:
            return False

    def get_supported_domains(self) -> list:
        """
        Get list of supported domains

        Returns:
            List of supported domain patterns
        """
        return list(self._resolvers.keys())
