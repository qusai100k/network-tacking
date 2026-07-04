import asyncio
import json
from collections import deque
from datetime import datetime, timezone
from typing import Optional

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.config import settings
from app.models import Base
from app.repositories.telemetry_repository import TelemetryRepository
from app.schemas import AlertRecord, BootstrapPayload, TelemetrySnapshot
from app.services.alert_service import AlertEvaluator
from app.services.network_service import NetworkCollector


def _envelope_json(telemetry: TelemetrySnapshot, alerts: list[AlertRecord]) -> str:
    payload = {
        "telemetry": json.loads(telemetry.model_dump_json()),
        "alerts": [json.loads(alert.model_dump_json()) for alert in alerts],
    }
    return json.dumps(payload)


class MonitorRuntime:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory
        self._collector = NetworkCollector()
        self._alert_evaluator = AlertEvaluator()
        self._clients: set[WebSocket] = set()
        self._clients_lock = asyncio.Lock()
        self._history: deque[TelemetrySnapshot] = deque(maxlen=settings.history_limit)
        self._latest: Optional[TelemetrySnapshot] = None
        self._task: Optional[asyncio.Task] = None
        self._running = False

    @property
    def latest(self) -> Optional[TelemetrySnapshot]:
        return self._latest

    @property
    def history(self) -> list[TelemetrySnapshot]:
        return list(self._history)

    async def start(self, engine: AsyncEngine) -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with self._session_factory() as session:
            repository = TelemetryRepository(session)
            self._history = deque(
                await repository.get_history(settings.history_limit),
                maxlen=settings.history_limit,
            )
            if self._history:
                self._latest = self._history[-1]

        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None

    async def bootstrap(self) -> BootstrapPayload:
        async with self._session_factory() as session:
            repository = TelemetryRepository(session)
            alerts = await repository.get_recent_alerts()

        return BootstrapPayload(
            latest=self._latest,
            history=list(self._history),
            alerts=alerts,
        )

    async def register(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._clients_lock:
            self._clients.add(websocket)
        if self._latest is not None:
            try:
                await websocket.send_text(_envelope_json(self._latest, []))
            except Exception:
                pass

    async def unregister(self, websocket: WebSocket) -> None:
        async with self._clients_lock:
            self._clients.discard(websocket)

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except Exception:
                pass
            await asyncio.sleep(settings.refresh_interval_seconds)

    async def _tick(self) -> None:
        snapshot = await self._collector.collect()
        new_alerts = self._alert_evaluator.evaluate(snapshot)

        persisted_alerts: list[AlertRecord] = []
        async with self._session_factory() as session:
            repository = TelemetryRepository(session)
            await repository.add_sample(snapshot)
            await repository.prune_samples(settings.history_limit)

            for kind, severity, message in new_alerts:
                record = await repository.add_alert_if_new(
                    kind=kind,
                    severity=severity,
                    message=message,
                )
                if record:
                    persisted_alerts.append(record)

        self._latest = snapshot
        self._history.append(snapshot)

        await self._broadcast(snapshot, persisted_alerts)

    async def _broadcast(self, snapshot: TelemetrySnapshot, alerts: list[AlertRecord]) -> None:
        if not self._clients:
            return

        message = _envelope_json(snapshot, alerts)
        stale: list[WebSocket] = []

        async with self._clients_lock:
            clients = list(self._clients)

        for client in clients:
            try:
                await client.send_text(message)
            except Exception:
                stale.append(client)

        if stale:
            async with self._clients_lock:
                for client in stale:
                    self._clients.discard(client)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)