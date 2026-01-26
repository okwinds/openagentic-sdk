from __future__ import annotations

import threading
from dataclasses import dataclass

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.server.http_server import OpenAgenticHttpServer


@dataclass(frozen=True, slots=True)
class AgentCoreAddress:
    host: str
    port: int


class AgentCoreSidecar:
    def __init__(self, *, options: OpenAgenticOptions, host: str = "127.0.0.1", port: int = 0) -> None:
        self._options = options
        self._host = host
        self._port = int(port)
        self._httpd = None
        self._thread: threading.Thread | None = None

    def start(self) -> AgentCoreAddress:
        if self._httpd is not None:
            raise RuntimeError("AgentCoreSidecar already started")

        server = OpenAgenticHttpServer(options=self._options, host=self._host, port=self._port)
        httpd = server.serve_forever()
        self._httpd = httpd
        addr = httpd.server_address
        host = str(addr[0])
        port = int(addr[1])

        t = threading.Thread(target=httpd.serve_forever, name=f"oa-agentcore:{host}:{port}", daemon=True)
        self._thread = t
        t.start()
        return AgentCoreAddress(host=host, port=port)

    def close(self) -> None:
        httpd = self._httpd
        if httpd is None:
            return
        try:
            httpd.shutdown()
        finally:
            try:
                httpd.server_close()
            finally:
                self._httpd = None

