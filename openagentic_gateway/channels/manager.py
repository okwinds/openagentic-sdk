from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from .registry import ChannelRegistry
from .types import ChannelAccountSnapshot


@dataclass(frozen=True, slots=True)
class ChannelRuntimeSnapshot:
    channels: dict[str, ChannelAccountSnapshot]
    channel_accounts: dict[str, dict[str, ChannelAccountSnapshot]]


class ChannelManager:
    def __init__(self, *, registry: ChannelRegistry) -> None:
        self._registry = registry
        self._aborts: dict[tuple[str, str], asyncio.Event] = {}
        self._tasks: dict[tuple[str, str], asyncio.Task[None]] = {}
        self._runtimes: dict[tuple[str, str], ChannelAccountSnapshot] = {}

    def _get_snapshot(self, channel_id: str, account_id: str) -> ChannelAccountSnapshot:
        return self._runtimes.get((channel_id, account_id)) or ChannelAccountSnapshot(account_id=account_id)

    def _set_snapshot(self, channel_id: str, account_id: str, patch: ChannelAccountSnapshot) -> ChannelAccountSnapshot:
        self._runtimes[(channel_id, account_id)] = patch
        return patch

    async def start_channel(self, channel_id: str, *, account_id: str | None = None) -> None:
        plugin = self._registry.get(channel_id)
        if plugin is None:
            return

        account_ids: list[str]
        if account_id:
            account_ids = [account_id]
        else:
            lister = getattr(plugin, "list_account_ids", None)
            account_ids = list(lister()) if callable(lister) else ["default"]

        for aid in account_ids:
            key = (str(plugin.id), str(aid))
            if key in self._tasks:
                continue

            abort = asyncio.Event()
            self._aborts[key] = abort
            self._set_snapshot(
                str(plugin.id),
                str(aid),
                ChannelAccountSnapshot(
                    account_id=str(aid),
                    running=True,
                    last_error=None,
                    last_start_at=time.time(),
                ),
            )

            async def _runner(*, _plugin: Any, _channel: str, _account: str, _abort: asyncio.Event) -> None:
                try:
                    starter = getattr(_plugin, "start_account", None)
                    if callable(starter):
                        await starter(account_id=_account, abort=_abort)
                except asyncio.CancelledError:
                    raise
                except Exception as e:  # noqa: BLE001
                    self._set_snapshot(
                        _channel,
                        _account,
                        ChannelAccountSnapshot(
                            account_id=_account,
                            running=False,
                            last_error=str(e) or "channel_error",
                            last_stop_at=time.time(),
                        ),
                    )
                finally:
                    self._aborts.pop((_channel, _account), None)
                    self._tasks.pop((_channel, _account), None)
                    cur = self._get_snapshot(_channel, _account)
                    if cur.running:
                        self._set_snapshot(
                            _channel,
                            _account,
                            ChannelAccountSnapshot(
                                account_id=_account,
                                running=False,
                                last_error=cur.last_error,
                                last_start_at=cur.last_start_at,
                                last_stop_at=time.time(),
                            ),
                        )

            task = asyncio.create_task(_runner(_plugin=plugin, _channel=str(plugin.id), _account=str(aid), _abort=abort))
            self._tasks[key] = task

    async def stop_channel(self, channel_id: str, *, account_id: str | None = None) -> None:
        plugin = self._registry.get(channel_id)
        if plugin is None:
            return

        ids: list[str]
        if account_id:
            ids = [account_id]
        else:
            known = {aid for (cid, aid) in self._tasks.keys() if cid == str(plugin.id)}
            lister = getattr(plugin, "list_account_ids", None)
            if callable(lister):
                known.update([str(x) for x in lister()])
            ids = sorted(known) if known else ["default"]

        stopper = getattr(plugin, "stop_account", None)
        for aid in ids:
            key = (str(plugin.id), str(aid))
            abort = self._aborts.get(key)
            if abort is not None:
                abort.set()

            if callable(stopper):
                try:
                    await stopper(account_id=str(aid))
                except Exception:
                    pass

            task = self._tasks.get(key)
            if task is not None:
                try:
                    await asyncio.wait_for(task, timeout=2.0)
                except asyncio.TimeoutError:
                    task.cancel()
                except Exception:
                    pass

            cur = self._get_snapshot(str(plugin.id), str(aid))
            self._set_snapshot(
                str(plugin.id),
                str(aid),
                ChannelAccountSnapshot(
                    account_id=str(aid),
                    running=False,
                    last_error=cur.last_error,
                    last_start_at=cur.last_start_at,
                    last_stop_at=time.time(),
                ),
            )

    def get_runtime_snapshot(self) -> dict[str, Any]:
        channels: dict[str, ChannelAccountSnapshot] = {}
        channel_accounts: dict[str, dict[str, ChannelAccountSnapshot]] = {}

        for plugin in self._registry.list_plugins():
            cid = str(getattr(plugin, "id", "") or "").strip()
            if not cid:
                continue
            per_account: dict[str, ChannelAccountSnapshot] = {}
            for (c2, aid), snap in self._runtimes.items():
                if c2 != cid:
                    continue
                per_account[aid] = snap
            if per_account:
                channel_accounts[cid] = dict(per_account)
                # default channel summary: any running account.
                running = any(s.running for s in per_account.values())
                channels[cid] = ChannelAccountSnapshot(account_id="*", running=running)
            else:
                channels[cid] = ChannelAccountSnapshot(account_id="*", running=False)

        return {"channels": channels, "channel_accounts": channel_accounts}

