"""One HTTP session for every outbound call ProspectSignal makes.

Outbound calls go only to official open-data hosts (Brønnøysundregistrene, and for maintainers rebuilding the
bundled reference data, SSB and Kartverket). TLS certificates are verified against the operating system's trust
store via ``truststore``. Many Windows machines (antivirus or corporate HTTPS inspection) trust a root that is in
the OS store but not in certifi's bundle; verification is never switched off.
"""

from __future__ import annotations

import ssl

import requests
from requests.adapters import HTTPAdapter

from . import __version__

USER_AGENT = f"ProspectSignal/{__version__} (+https://github.com/UlrikErlingsen/b2b-prospecting)"


class _OsTrustAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        try:
            import truststore
        except ImportError:  # pragma: no cover - truststore is a declared dependency
            return super().init_poolmanager(*args, **kwargs)
        kwargs["ssl_context"] = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        return super().init_poolmanager(*args, **kwargs)


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    session.mount("https://", _OsTrustAdapter())
    return session
