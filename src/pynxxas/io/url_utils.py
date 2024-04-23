import os
import sys
import pathlib
import urllib.parse
import urllib.request
from typing import Union, NamedTuple


class ParsedUrlType(NamedTuple):
    path: str
    internal_path: str


UrlType = Union[str, pathlib.Path, urllib.parse.ParseResult, ParsedUrlType]


_WIN32 = sys.platform == "win32"


def as_url(url: UrlType) -> ParsedUrlType:
    if isinstance(url, ParsedUrlType):
        return url

    if isinstance(url, urllib.parse.ParseResult):
        parsed = url
    else:
        url_str = str(url)
        parsed = urllib.parse.urlparse(url_str)
        if not parsed.scheme or (_WIN32 and len(parsed.scheme) == 1):
            url_str = "file://" + os.path.abspath(url_str).replace("\\", "/")
            parsed = urllib.parse.urlparse(url_str)

    if parsed.scheme != "file":
        raise ValueError("URL is not a file")

    if parsed.netloc:
        path = f"{parsed.netloc}{parsed.path}"
    else:
        path = parsed.path

    query = urllib.parse.parse_qs(parsed.query)
    internal_path = query.get("path", [""])[0]

    return ParsedUrlType(path=path, internal_path=internal_path)
