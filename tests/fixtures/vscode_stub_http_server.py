from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput
from openagentic_sdk.server.http_server import OpenAgenticHttpServer
from openagentic_sdk.sessions.store import FileSessionStore


class _Provider:
    name = "vscode-stub-provider"

    async def complete(self, **kwargs):  # noqa: ANN003
        _ = kwargs
        return ModelOutput(assistant_text="ok", tool_calls=(), usage={"total_tokens": 1}, raw=None)


def main() -> int:
    root = Path.cwd() / ".vscode-stub"
    store = FileSessionStore(root_dir=root)
    opts = OpenAgenticOptions(
        provider=_Provider(),
        model="m",
        api_key="x",
        cwd=str(Path.cwd()),
        project_dir=str(Path.cwd()),
        session_store=store,
        permission_gate=PermissionGate(permission_mode="bypass"),
    )

    httpd = OpenAgenticHttpServer(options=opts, host="127.0.0.1", port=0).serve_forever()
    port = int(httpd.server_address[1])
    sys.stdout.write(str(port) + "\n")
    sys.stdout.flush()

    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        return 0
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
