from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class WwwAuthenticate:
    scheme: str
    params: dict[str, str]


def parse_www_authenticate(header_value: str) -> dict[str, object]:
    """Parse a single WWW-Authenticate challenge.

    This is intentionally small but robust enough for MCP OAuth usage where the
    server returns `WWW-Authenticate: Bearer ...` with parameters like
    `resource_metadata`, `scope`, and `error`.
    """

    raw = str(header_value or "").strip()
    if not raw:
        return {"scheme": "", "params": {}}

    # Split scheme from parameter section.
    if " " not in raw:
        return {"scheme": raw.lower(), "params": {}}
    scheme, rest = raw.split(" ", 1)
    scheme = scheme.strip().lower()
    rest = rest.strip()

    params: dict[str, str] = {}
    i = 0
    n = len(rest)
    while i < n:
        # Skip commas/whitespace.
        while i < n and rest[i] in " \t,":
            i += 1
        if i >= n:
            break

        # Parse key.
        k0 = i
        while i < n and rest[i] not in "=, \t":
            i += 1
        key = rest[k0:i].strip()
        if not key:
            break

        # Skip whitespace.
        while i < n and rest[i] in " \t":
            i += 1
        if i >= n or rest[i] != "=":
            # Malformed; stop.
            break
        i += 1
        while i < n and rest[i] in " \t":
            i += 1
        if i >= n:
            params[key] = ""
            break

        # Parse value (quoted-string or token).
        if rest[i] == '"':
            i += 1
            out = []
            while i < n:
                ch = rest[i]
                i += 1
                if ch == '"':
                    break
                if ch == "\\" and i < n:
                    out.append(rest[i])
                    i += 1
                    continue
                out.append(ch)
            params[key] = "".join(out)
        else:
            v0 = i
            while i < n and rest[i] not in ",":
                i += 1
            params[key] = rest[v0:i].strip()

        # Continue; next iteration skips separators.

    return {"scheme": scheme, "params": params}


def protected_resource_metadata_urls(resource_url: str) -> list[str]:
    """Build an ordered list of OAuth Protected Resource Metadata URLs (RFC 9728).

    MCP uses PRM to discover authorization servers from a protected resource URL.
    We implement the path-aware insertion form plus a root fallback.
    """

    u = str(resource_url or "").strip()
    p = urlparse(u)
    if not p.scheme or not p.netloc:
        return []
    root = f"{p.scheme}://{p.netloc}"
    path = p.path or ""
    out: list[str] = []
    if path and path != "/":
        out.append(f"{root}/.well-known/oauth-protected-resource{path}")
    out.append(f"{root}/.well-known/oauth-protected-resource")
    # De-dupe while preserving order.
    seen: set[str] = set()
    uniq: list[str] = []
    for x in out:
        if x in seen:
            continue
        seen.add(x)
        uniq.append(x)
    return uniq


def authorization_server_metadata_urls(issuer: str) -> list[str]:
    """Build an ordered list of OAuth Authorization Server Metadata URLs.

    Matches the common RFC 8414 insertion form and OIDC fallbacks that MCP
    clients probe.
    """

    u = str(issuer or "").strip()
    p = urlparse(u)
    if not p.scheme or not p.netloc:
        return []
    root = f"{p.scheme}://{p.netloc}"
    path = p.path or ""

    out: list[str] = []
    if path and path != "/":
        out.append(f"{root}/.well-known/oauth-authorization-server{path}")
        out.append(f"{root}/.well-known/openid-configuration{path}")
        out.append(f"{u.rstrip('/')}/.well-known/openid-configuration")
    out.append(f"{root}/.well-known/oauth-authorization-server")
    out.append(f"{root}/.well-known/openid-configuration")

    seen: set[str] = set()
    uniq: list[str] = []
    for x in out:
        if x in seen:
            continue
        seen.add(x)
        uniq.append(x)
    return uniq
