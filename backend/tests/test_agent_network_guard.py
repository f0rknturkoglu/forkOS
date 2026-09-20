"""Ağ koruması sözleşmesi (§116/§118).

Korumanın iki yönü de kilitlenir: DIŞ host/adresler engellenir, ama testlerin
bağlanmak zorunda olduğu altyapı (loopback ve yapılandırılmış test veritabanı
host'u) serbest kalır. İkinci yön Compose içinde kritiktir: DB host'u `db-test`
olduğu ve `connect` adımı çözümlenmiş bir IP gördüğü için, adı tanımayan bir
allowlist tüm taşıma testlerini düşürür.
"""

from __future__ import annotations

import contextlib
import socket

import pytest
from sqlalchemy.engine import make_url

from app.config import settings
from tests.agent_test_utils import (  # noqa: F401  (autouse ağ koruması)
    _allowed_network_hosts,
    forbid_outbound_network,
)

# Bu testler yalnızca soket katmanını inceler; veritabanına dokunmaz.
pytestmark = pytest.mark.no_database


def test_external_dns_resolution_is_blocked() -> None:
    with pytest.raises(AssertionError, match="dış DNS"):
        socket.getaddrinfo("example.com", 443)


def test_external_hostname_connection_is_blocked() -> None:
    with socket.socket() as sock, pytest.raises(AssertionError, match="dış ağ"):
        sock.connect(("example.com", 443))


def test_never_resolved_external_address_is_blocked() -> None:
    """Hiçbir onaylı çözümlemeden çıkmamış bir IP bağlanamaz."""
    with socket.socket() as sock, pytest.raises(AssertionError, match="dış ağ"):
        sock.connect(("93.184.216.34", 80))


def test_loopback_and_test_database_host_stay_allowed() -> None:
    allowed = _allowed_network_hosts()
    assert "127.0.0.1" in allowed
    assert "localhost" in allowed
    # Testlerin gerçekten bağlandığı host; koruma bunu engellemez.
    assert make_url(settings.database_url).host in allowed


def test_test_database_host_resolves_and_connects() -> None:
    """DB host'u çözümlenebilmeli ve çözümlenen adres korumadan geçmeli.

    Compose içinde host `db-test`'tir; bu adım engellenirse hiçbir taşıma testi
    veritabanına bağlanamaz.
    """
    host = make_url(settings.database_url).host
    infos = socket.getaddrinfo(host, 5432, type=socket.SOCK_STREAM)
    addresses = {str(info[4][0]) for info in infos if isinstance(info[4], tuple) and info[4]}
    assert addresses, "test veritabanı host'u çözümlenemedi"
    for address in addresses:
        with socket.socket() as sock:
            sock.settimeout(0.5)
            # Bağlantı reddi (OSError) kabul; yasak olan korumanın engellemesi.
            with contextlib.suppress(OSError):
                sock.connect((address, 1))
