"""Simplified MIME type guessing module.

This module provides basic MIME type guessing functionality.

Main function:
- guess_type(url) -- guess the MIME type and encoding of a URL
"""

from __future__ import annotations

import os
import posixpath
import urllib.parse

__all__ = ["guess_type"]


def guess_type(url: str) -> tuple[str | None, str | None]:
    """Guess the type of a file based on its URL or path."""
    p = urllib.parse.urlparse(url)

    if p.scheme and len(p.scheme) > 1:
        if p.scheme == "data":
            comma = url.find(",")
            if comma < 0:
                return None, None
            semi = url.find(";", 0, comma)
            mime_type = url[:semi] if semi >= 0 else url[:comma]
            if "=" in mime_type or "/" not in mime_type:
                mime_type = "text/plain"
            return mime_type, None

        base, ext = posixpath.splitext(p.path)
    else:
        base, ext = os.path.splitext(url)

    ext = ext.lower()

    while ext in _suffix_map:
        base, ext = os.path.splitext(base + _suffix_map[ext])
        ext = ext.lower()

    if ext in _encodings_map:
        encoding = _encodings_map[ext]
        base, ext = os.path.splitext(base)
        ext = ext.lower()
    else:
        encoding = None

    return _types_map.get(ext), encoding


_suffix_map = {
    ".svgz": ".svg.gz",
    ".tgz": ".tar.gz",
    ".taz": ".tar.gz",
    ".tz": ".tar.gz",
    ".tbz2": ".tar.bz2",
    ".txz": ".tar.xz",
}

_encodings_map = {
    ".gz": "gzip",
    ".Z": "compress",
    ".bz2": "bzip2",
    ".xz": "xz",
    ".br": "br",
}

_types_map = {
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".epub": "application/epub+zip",
    ".gz": "application/gzip",
    ".json": "application/json",
    ".webmanifest": "application/manifest+json",
    ".doc": "application/msword",
    ".dot": "application/msword",
    ".wiz": "application/msword",
    ".nq": "application/n-quads",
    ".nt": "application/n-triples",
    ".bin": "application/octet-stream",
    ".a": "application/octet-stream",
    ".dll": "application/octet-stream",
    ".exe": "application/octet-stream",
    ".o": "application/octet-stream",
    ".obj": "application/octet-stream",
    ".so": "application/octet-stream",
    ".oda": "application/oda",
    ".ogx": "application/ogg",
    ".pdf": "application/pdf",
    ".p7c": "application/pkcs7-mime",
    ".ps": "application/postscript",
    ".ai": "application/postscript",
    ".eps": "application/postscript",
    ".trig": "application/trig",
    ".m3u": "application/vnd.apple.mpegurl",
    ".m3u8": "application/vnd.apple.mpegurl",
    ".xls": "application/vnd.ms-excel",
    ".xlb": "application/vnd.ms-excel",
    ".eot": "application/vnd.ms-fontobject",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pot": "application/vnd.ms-powerpoint",
    ".ppa": "application/vnd.ms-powerpoint",
    ".pps": "application/vnd.ms-powerpoint",
    ".pwz": "application/vnd.ms-powerpoint",
    ".odg": "application/vnd.oasis.opendocument.graphics",
    ".odp": "application/vnd.oasis.opendocument.presentation",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".rar": "application/vnd.rar",
    ".wasm": "application/wasm",
    ".7z": "application/x-7z-compressed",
    ".bcpio": "application/x-bcpio",
    ".cpio": "application/x-cpio",
    ".csh": "application/x-csh",
    ".deb": "application/x-debian-package",
    ".dvi": "application/x-dvi",
    ".gtar": "application/x-gtar",
    ".hdf": "application/x-hdf",
    ".h5": "application/x-hdf5",
    ".latex": "application/x-latex",
    ".mif": "application/x-mif",
    ".cdf": "application/x-netcdf",
    ".nc": "application/x-netcdf",
    ".p12": "application/x-pkcs12",
    ".php": "application/x-httpd-php",
    ".pfx": "application/x-pkcs12",
    ".ram": "application/x-pn-realaudio",
    ".pyc": "application/x-python-code",
    ".pyo": "application/x-python-code",
    ".rpm": "application/x-rpm",
    ".sh": "application/x-sh",
    ".shar": "application/x-shar",
    ".swf": "application/x-shockwave-flash",
    ".sv4cpio": "application/x-sv4cpio",
    ".sv4crc": "application/x-sv4crc",
    ".tar": "application/x-tar",
    ".tcl": "application/x-tcl",
    ".tex": "application/x-tex",
    ".texi": "application/x-texinfo",
    ".texinfo": "application/x-texinfo",
    ".roff": "application/x-troff",
    ".t": "application/x-troff",
    ".tr": "application/x-troff",
    ".man": "application/x-troff-man",
    ".me": "application/x-troff-me",
    ".ms": "application/x-troff-ms",
    ".ustar": "application/x-ustar",
    ".src": "application/x-wais-source",
    ".xsl": "application/xml",
    ".rdf": "application/xml",
    ".wsdl": "application/xml",
    ".xpdl": "application/xml",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".zip": "application/zip",
    ".3gp": "audio/3gpp",
    ".3gpp": "audio/3gpp",
    ".3g2": "audio/3gpp2",
    ".3gpp2": "audio/3gpp2",
    ".aac": "audio/aac",
    ".adts": "audio/aac",
    ".loas": "audio/aac",
    ".ass": "audio/aac",
    ".au": "audio/basic",
    ".snd": "audio/basic",
    ".flac": "audio/flac",
    ".mka": "audio/matroska",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".mp2": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".opus": "audio/opus",
    ".aif": "audio/x-aiff",
    ".aifc": "audio/x-aiff",
    ".aiff": "audio/x-aiff",
    ".ra": "audio/x-pn-realaudio",
    ".wav": "audio/vnd.wave",
    ".otf": "font/otf",
    ".ttf": "font/ttf",
    ".weba": "audio/webm",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".avif": "image/avif",
    ".bmp": "image/bmp",
    ".emf": "image/emf",
    ".fits": "image/fits",
    ".g3": "image/g3fax",
    ".gif": "image/gif",
    ".ief": "image/ief",
    ".jp2": "image/jp2",
    ".jpg": "image/jpeg",
    ".jpe": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".jpm": "image/jpm",
    ".jpx": "image/jpx",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".t38": "image/t38",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".tfx": "image/tiff-fx",
    ".ico": "image/vnd.microsoft.icon",
    ".webp": "image/webp",
    ".wmf": "image/wmf",
    ".ras": "image/x-cmu-raster",
    ".pnm": "image/x-portable-anymap",
    ".pbm": "image/x-portable-bitmap",
    ".pgm": "image/x-portable-graymap",
    ".ppm": "image/x-portable-pixmap",
    ".rgb": "image/x-rgb",
    ".xbm": "image/x-xbitmap",
    ".xpm": "image/x-xpixmap",
    ".xwd": "image/x-xwindowdump",
    ".eml": "message/rfc822",
    ".mht": "message/rfc822",
    ".mhtml": "message/rfc822",
    ".nws": "message/rfc822",
    ".gltf": "model/gltf+json",
    ".glb": "model/gltf-binary",
    ".stl": "model/stl",
    ".css": "text/css",
    ".csv": "text/csv",
    ".html": "text/html",
    ".htm": "text/html",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".n3": "text/n3",
    ".txt": "text/plain",
    ".bat": "text/plain",
    ".c": "text/plain",
    ".h": "text/plain",
    ".ksh": "text/plain",
    ".pl": "text/plain",
    ".srt": "text/plain",
    ".rtx": "text/richtext",
    ".tsv": "text/tab-separated-values",
    ".vtt": "text/vtt",
    ".py": "text/x-python",
    ".rst": "text/x-rst",
    ".etx": "text/x-setext",
    ".sgm": "text/x-sgml",
    ".sgml": "text/x-sgml",
    ".vcf": "text/x-vcard",
    ".xml": "text/xml",
    ".mkv": "video/matroska",
    ".mk3d": "video/matroska-3d",
    ".mp4": "video/mp4",
    ".mpeg": "video/mpeg",
    ".m1v": "video/mpeg",
    ".mpa": "video/mpeg",
    ".mpe": "video/mpeg",
    ".mpg": "video/mpeg",
    ".ogv": "video/ogg",
    ".mov": "video/quicktime",
    ".qt": "video/quicktime",
    ".webm": "video/webm",
    ".avi": "video/vnd.avi",
    ".m4v": "video/x-m4v",
    ".wmv": "video/x-ms-wmv",
    ".movie": "video/x-sgi-movie",
    ".rtf": "application/rtf",
    ".apk": "application/vnd.android.package-archive",
    ".midi": "audio/midi",
    ".mid": "audio/midi",
    ".pict": "image/pict",
    ".pct": "image/pict",
    ".pic": "image/pict",
    ".xul": "text/xul",
}
