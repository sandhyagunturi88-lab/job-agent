"""WebSocket stream of graph state to the client.

Pushes a snapshot on connect, then whenever the thread's checkpoint advances
(node finished, interrupt raised, run resumed elsewhere — e.g. approved on
another device). Phase 4 swaps polling for checkpointer LISTEN/NOTIFY."""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.routers.runs import snapshot_payload

router = APIRouter()

POLL_SECONDS = 1.5


@router.websocket("/ws/runs/{thread_id}")
async def run_updates(websocket: WebSocket, thread_id: str) -> None:
    await websocket.accept()
    graph = websocket.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}
    last_checkpoint_id: str | None = None
    try:
        while True:
            snap = await graph.aget_state(config)
            checkpoint_id = (snap.config or {}).get("configurable", {}).get("checkpoint_id")
            if checkpoint_id != last_checkpoint_id:
                last_checkpoint_id = checkpoint_id
                await websocket.send_json(await snapshot_payload(graph, thread_id))
            await asyncio.sleep(POLL_SECONDS)
    except WebSocketDisconnect:
        return
