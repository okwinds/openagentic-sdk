# WebFetch SSRF Protections

## Summary

`WebFetch` is an HTTP(S) fetch tool intended for use by agents. To reduce SSRF risk by default, it blocks requests to loopback and private networks unless explicitly allowed.

## Protections

When `allow_private_networks=False` (default):

- Only `http`/`https` schemes are allowed.
- Hostnames `localhost` and `*.localhost` are blocked.
- Literal IP hosts are blocked if they are private, loopback, or link-local.
- Redirects are handled manually and each hop is re-validated.
- Hostnames are resolved and blocked if any resolved IP is private, loopback, or link-local (mitigates DNS rebinding / “hostname → 127.0.0.1” cases).

## Escape Hatch

If you need to fetch internal resources (e.g., in a controlled environment), set `allow_private_networks=True`.

## Notes

- Hostname resolution uses `socket.getaddrinfo` under the hood and is test-injectable via the module-level `_getaddrinfo`.
- Blocking is conservative: if a hostname resolves to multiple addresses, any private/loopback/link-local address triggers a block.

