"""Resolver for mega.nz URLs."""

from __future__ import annotations

import base64
import json
import re
from typing import ClassVar

import aiohttp
from Crypto.Cipher import AES

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import LinkResult

from .base import BaseResolver


# The following crypto functions are adapted from the mega.py library
# by odwyersoftware: https://github.com/odwyersoftware/mega.py
def base64_url_decode(data: str) -> bytes:
    """Decode base64 URL."""
    data += "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data)


def a32_to_str(a: list[int]) -> bytes:
    """Convert a list of 32-bit integers to a string."""
    return b"".join(x.to_bytes(4, "big") for x in a)


def base64_to_a32(s: str) -> list[int]:
    """Convert a base64 string to a list of 32-bit integers."""
    return str_to_a32(base64_url_decode(s))


def str_to_a32(b: bytes) -> list[int]:
    """Convert a string to a list of 32-bit integers."""
    if len(b) % 4:
        b += b"\0" * (4 - len(b) % 4)
    return [int.from_bytes(b[i : i + 4], "big") for i in range(0, len(b), 4)]


def decrypt_attr(attributes: bytes, key: list[int]) -> dict:
    """Decrypt file attributes."""
    key_str = a32_to_str(key)
    try:
        decrypted_attrs = AES.new(key_str, AES.MODE_ECB).decrypt(attributes)
        # MEGA adds "MEGA" and a null terminator to the JSON string.
        json_str = decrypted_attrs.decode("utf-8", errors="ignore").strip("\0")
        if json_str.startswith("MEGA"):
            return json.loads(json_str[4:])
    except (ValueError, json.JSONDecodeError):
        return {}
    return {}


class MegaResolver(BaseResolver):
    """Resolver for mega.nz URLs."""

    DOMAINS: ClassVar[list[str]] = ["mega.nz"]
    sequence_num = 0

    def _parse_url(self, url: str) -> tuple[str, str]:
        """Parse file id and key from url."""
        if "/file/" in url:
            match = re.search(r"/file/([\w-]+)#([\w-]+)", url)
            if match:
                return match.groups()
        elif "#!" in url:
            match = re.search(r"#!([\w-]+)!([\w-]+)", url)
            if match:
                return match.groups()
        msg = f"Invalid mega.nz URL: {url}"
        raise InvalidURLException(msg)

    async def _api_request(self, data: dict) -> dict | list:
        """Make a request to the MEGA API."""
        params = {"id": self.sequence_num}
        self.sequence_num += 1

        url = "https://g.api.mega.co.nz/cs"
        try:
            response = await self._post(url, params=params, json=[data])
            json_resp = await response.json()
        except (json.JSONDecodeError, aiohttp.ClientError) as e:
            msg = f"Failed to communicate with MEGA API: {e}"
            raise ExtractionFailedException(msg) from e

        if isinstance(json_resp, list) and json_resp:
            return json_resp[0]
        if isinstance(json_resp, int):
            msg = f"MEGA API returned an error code: {json_resp}"
            raise ExtractionFailedException(msg)
        return json_resp

    async def resolve(self, url: str) -> LinkResult:
        """Resolve mega.nz URL."""
        file_handle, file_key_b64 = self._parse_url(url)

        try:
            file_key = base64_to_a32(file_key_b64)
        except Exception as e:
            msg = f"Invalid file key in URL: {url}"
            raise InvalidURLException(msg) from e

        file_data = await self._api_request({"a": "g", "g": 1, "p": file_handle})

        if not isinstance(file_data, dict) or "g" not in file_data:
            msg = "Failed to retrieve file information from MEGA."
            raise ExtractionFailedException(msg)

        download_url = file_data["g"]
        size = file_data["s"]
        encrypted_attrs = base64_url_decode(file_data["at"])

        k = (
            file_key[0] ^ file_key[4],
            file_key[1] ^ file_key[5],
            file_key[2] ^ file_key[6],
            file_key[3] ^ file_key[7],
        )

        attrs = decrypt_attr(encrypted_attrs, k)
        filename = attrs.get("n")

        return LinkResult(url=download_url, filename=filename, size=size)
