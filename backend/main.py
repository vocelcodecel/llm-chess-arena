"""FastAPI server for LLM Chess Arena."""

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from agents import DEFAULT_AGENTS, AgentConfig
from tournament import Tournament
from game import GameResult

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

arena: Optional[Tournament] = None
connected_clients: list[WebSocket] = []
tournament_running = False


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="LLM Chess Arena")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Broadcast helpers
# ---------------------------------------------------------------------------

async def broadcast(event: dict):
    """Send event to all connected WebSocket clients."""
    data = json.dumps(event)
    disconnected = []
    for ws in connected_clients:
        try:
            await ws.send_text(data)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        connected_clients.remove(ws)


def sync_broadcast(event: dict):
    """Schedule broadcast from sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(broadcast(event))
    except RuntimeError:
        pass


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/api/agents")
def get_agents():
    return [
        {"name": a.name, "provider": a.provider, "model": a.model, "personality_file": a.personality_file}
        for a in DEFAULT_AGENTS
    ]


@app.get("/api/standings")
def get_standings():
    if arena is None:
        return []
    return arena.get_standings()


@app.get("/api/games")
def get_games():
    if arena is None:
        return []
    return arena.games


@app.get("/api/games/{game_num}/pgn")
def get_game_pgn(game_num: int):
    games_dir = Path(__file__).parent / "games"
    for f in games_dir.glob(f"game_{game_num:03d}_*.pgn"):
        return {"pgn": f.read_text()}
    return {"error": "Game not found"}


@app.get("/api/status")
def get_status():
    return {
        "running": tournament_running,
        "current_game": arena.current_game if arena else None,
        "total_games": len(arena.games) if arena else 0,
    }


@app.post("/api/tournament/start")
async def start_tournament():
    global arena, tournament_running

    if tournament_running:
        return {"error": "Tournament already running"}

    arena = Tournament(agents=DEFAULT_AGENTS)
    tournament_running = True

    # Run in background thread (LLM calls are blocking)
    asyncio.get_event_loop().run_in_executor(None, _run_tournament)

    return {"status": "started", "total_pairings": len(arena.generate_pairings())}


def _run_tournament():
    global tournament_running

    def on_move(record):
        sync_broadcast({
            "type": "move",
            "ply": record.ply,
            "side": record.side,
            "agent": record.agent,
            "uci": record.uci,
            "san": record.san,
            "fen": record.fen_after,
            "fallback": record.fallback,
            "attempts": record.attempts,
        })

    def on_game_start(num, total, white, black):
        sync_broadcast({
            "type": "game_start",
            "game_num": num,
            "total_games": total,
            "white": white,
            "black": black,
        })

    def on_game_end(game_record):
        sync_broadcast({
            "type": "game_end",
            "game_num": game_record["game_num"],
            "result": game_record["result"],
            "reason": game_record["reason"],
            "white": game_record["white"],
            "black": game_record["black"],
            "total_moves": game_record["total_moves"],
            "standings": arena.get_standings(),
        })

    try:
        arena.run_full_tournament(on_move=on_move, on_game_start=on_game_start, on_game_end=on_game_end)
        sync_broadcast({"type": "tournament_complete", "standings": arena.get_standings()})
    finally:
        tournament_running = False


# ---------------------------------------------------------------------------
# WebSocket for live updates
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    try:
        while True:
            await ws.receive_text()  # keep alive
    except WebSocketDisconnect:
        connected_clients.remove(ws)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
