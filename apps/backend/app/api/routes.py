import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.runtime import (
    ai_analysis_service,
    ai_chat_service,
    connection_analyzer_service,
    device_discovery_service,
    monitor_runtime,
    process_monitor_service,
)
from app.schemas import AIChatRequest

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/api/v1/bootstrap")
async def bootstrap():
    return await monitor_runtime.bootstrap()


@router.get("/api/v1/devices")
async def devices():
    return await device_discovery_service.scan()


@router.get("/api/v1/processes")
async def processes():
    return await process_monitor_service.scan()


@router.get("/api/v1/connections")
async def connections():
    return await connection_analyzer_service.scan()


@router.get("/api/v1/ai/analysis")
async def ai_analysis():
    telemetry = monitor_runtime.latest
    history = monitor_runtime.history
    devices, processes, connections = await asyncio.gather(
        device_discovery_service.scan(),
        process_monitor_service.scan(),
        connection_analyzer_service.scan(),
    )
    return await ai_analysis_service.analyze(
        telemetry=telemetry,
        history=history,
        devices=devices,
        processes=processes,
        connections=connections,
    )


@router.post("/api/v1/ai/chat")
async def ai_chat(payload: AIChatRequest):
    telemetry = monitor_runtime.latest
    history = monitor_runtime.history
    devices, processes, connections = await asyncio.gather(
        device_discovery_service.scan(),
        process_monitor_service.scan(),
        connection_analyzer_service.scan(),
    )
    analysis = await ai_analysis_service.analyze(
        telemetry=telemetry,
        history=history,
        devices=devices,
        processes=processes,
        connections=connections,
    )
    return await ai_chat_service.answer(
        message=payload.message,
        telemetry=telemetry,
        devices=devices,
        processes=processes,
        connections=connections,
        analysis=analysis,
        provider=payload.provider,
    )


@router.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await monitor_runtime.register(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await monitor_runtime.unregister(websocket)
    except Exception:
        await monitor_runtime.unregister(websocket)