"""Regression test for the 2026-06-12 Tesla Owner API outage.

On 2026-06-12 Tesla's Owner API began returning HTTP 403 ("forbidden, see
.../fleet-api") to any client that did not negotiate TLS 1.3. teslapy 2.9.2
fixed this by mounting a ``TLSAdapter`` that pins the connection to TLS 1.3.

These tests fail loudly if a future dependency change drops teslapy below 2.9.2
or otherwise stops enforcing TLS 1.3 -- instead of the bridge silently
403-crash-looping in production again (which is exactly what happened, undetected,
for two weeks).
"""
import ssl

import teslapy


def _https_min_tls(tesla):
    """The minimum TLS version the teslapy session will negotiate for HTTPS.

    teslapy 2.9.2 enforces this via urllib3's ``ssl_minimum_version`` pool kwarg
    on its ``TLSAdapter`` (older builds used a pinned ``ssl_context``); support
    both shapes so the test tracks intent, not implementation detail.
    """
    adapter = tesla.get_adapter("https://owner-api.teslamotors.com/")
    kw = adapter.poolmanager.connection_pool_kw
    if kw.get("ssl_minimum_version") is not None:
        return kw["ssl_minimum_version"]
    ctx = kw.get("ssl_context")
    return ctx.minimum_version if ctx is not None else None


def test_teslapy_ships_tls_adapter():
    assert hasattr(teslapy, "TLSAdapter"), (
        "teslapy is missing TLSAdapter (requires >=2.9.2); "
        "Tesla Owner API will reject every request with HTTP 403"
    )


def test_https_requests_pin_tls_1_3():
    tesla = teslapy.Tesla("regression@example.com")
    try:
        min_tls = _https_min_tls(tesla)
        assert min_tls == ssl.TLSVersion.TLSv1_3, (
            f"teslapy https adapter negotiates down to {min_tls!r}; "
            "Tesla Owner API requires TLS 1.3 since 2026-06-12"
        )
    finally:
        tesla.close()
