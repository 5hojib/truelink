from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from .exceptions import InvalidURLException, UnsupportedProviderException
from .resolvers import (
    AkmFilesResolver,
    BerkasDriveResolver,
    BuzzHeavierResolver,
    DevUploadsResolver,
    DoodStreamResolver,
    FichierResolver,
    FilePressResolver,
    FuckingFastResolver,
    GitHubResolver,
    GoFileResolver,
    HxFileResolver,
    KrakenFilesResolver,
    LinkBoxResolver,
    LulaCloudResolver,
    MediaFileResolver,
    MediaFireResolver,
    Mp4UploadResolver,
    OneDriveResolver,
    OsdnResolver,
    PCloudResolver,
    PixelDrainResolver,
    QiwiResolver,
    RacatyResolver,
    SendCmResolver,
    ShrdskResolver,
    SolidFilesResolver,
    StreamHubResolver,
    StreamtapeResolver,
    StreamvidResolver,
    SwissTransferResolver,
    TeraboxResolver,
    TmpSendResolver,
    UploadEeResolver,
    UploadHavenResolver,
    WeTransferResolver,
    YandexDiskResolver,
)

if TYPE_CHECKING:
    from .types import FolderResult, LinkResult


class TrueLinkResolver:
    """Main resolver class for extracting direct download links"""

    def __init__(self):
        self._resolvers: dict[str, type] = {
            # Existing from before
            "buzzheavier.com": BuzzHeavierResolver,
            "lulacloud.com": LulaCloudResolver,
            "fuckingfast.co": FuckingFastResolver,
            # Newly added resolvers
            "yadi.sk": YandexDiskResolver,
            "disk.yandex.": YandexDiskResolver,  # Catches disk.yandex.com, disk.yandex.ru etc.
            "devuploads.com": DevUploadsResolver,  # Main domain for devuploads
            "devuploads.net": DevUploadsResolver,  # Alias
            "uploadhaven.com": UploadHavenResolver,
            "mediafile.cc": MediaFileResolver,
            "mediafire.com": MediaFireResolver,
            "osdn.net": OsdnResolver,
            "github.com": GitHubResolver,  # For release links
            "hxfile.co": HxFileResolver,
            "1drv.ms": OneDriveResolver,  # OneDrive short links
            "onedrive.live.com": OneDriveResolver,  # OneDrive direct/shared links
            "pixeldrain.com": PixelDrainResolver,
            "pixeldra.in": PixelDrainResolver,  # Alias
            "streamtape.com": StreamtapeResolver,
            "streamtape.co": StreamtapeResolver,
            "streamtape.cc": StreamtapeResolver,
            "streamtape.to": StreamtapeResolver,
            "streamtape.net": StreamtapeResolver,
            "streamta.pe": StreamtapeResolver,
            "streamtape.xyz": StreamtapeResolver,
            "racaty.net": RacatyResolver,
            "racaty.io": RacatyResolver,  # Alias
            "1fichier.com": FichierResolver,
            "solidfiles.com": SolidFilesResolver,
            "krakenfiles.com": KrakenFilesResolver,
            "upload.ee": UploadEeResolver,
            "gofile.io": GoFileResolver,
            "send.cm": SendCmResolver,
            "tmpsend.com": TmpSendResolver,
            "easyupload.io": BaseResolver,  # Placeholder, original script had easyupload.io but no function
            "streamvid.net": StreamvidResolver,
            "shrdsk.me": ShrdskResolver,
            "u.pcloud.link": PCloudResolver,  # pCloud short links
            "pcloud.com": PCloudResolver,  # Main domain for shares if not short link
            "qiwi.gg": QiwiResolver,
            "mp4upload.com": Mp4UploadResolver,
            "berkasdrive.com": BerkasDriveResolver,
            "swisstransfer.com": SwissTransferResolver,
            "akmfiles.com": AkmFilesResolver,
            "akmfls.xyz": AkmFilesResolver,  # Alias
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
            "streamhub.ink": StreamHubResolver,
            "streamhub.to": StreamHubResolver,
            "linkbox.to": LinkBoxResolver,
            "lbx.to": LinkBoxResolver,  # Alias
            "teltobx.net": LinkBoxResolver,  # Alias
            "telbx.net": LinkBoxResolver,  # Alias
            "filepress.net": FilePressResolver,  # Assuming .net, original had 'filepress' in domain
            "filepress.com": FilePressResolver,  # Common TLD
            "filepress.org": FilePressResolver,  # Common TLD
            "wetransfer.com": WeTransferResolver,
            "we.tl": WeTransferResolver,  # Alias
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
            # R.I.P section from original - these will raise UnsupportedProviderException by default
            # "anonfiles.com": BaseResolver, # Example of how to mark as "known but unsupported"
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

    def resolve_sync(self, url: str) -> LinkResult | FolderResult:
        """
        Synchronous version of resolve()

        Args:
            url: The URL to resolve

        Returns:
            A LinkResult or FolderResult object.
        """
        return asyncio.run(self.resolve(url))

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
