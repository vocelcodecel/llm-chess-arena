"""LLM agent adapter — translates board state into a move."""

import os
import random
import time
from pathlib import Path
from dataclasses import dataclass, field

import chess
import anthropic
import openai

PROMPTS_DIR = Path(__file__).parent / "prompts"

# ---------------------------------------------------------------------------
# Agent definitions
# ---------------------------------------------------------------------------

@dataclass
class AgentConfig:
    name: str
    provider: str          # "anthropic" | "openai" | "random"
    model: str             # e.g. "claude-opus-4-6" or "gpt-5.3-codex"
    personality_file: str  # filename inside prompts/
    temperature: float = 0.7
    max_retries: int = 3
    stats: dict = field(default_factory=lambda: {
        "illegal_attempts": 0,
        "random_fallbacks": 0,
    })


DEFAULT_AGENTS = [
    AgentConfig("Magnus Chatbot",  "anthropic", "claude-opus-4-6",   "aggressive.txt", temperature=0.8),
    AgentConfig("Stockfished",     "anthropic", "claude-sonnet-4-6", "cautious.txt",   temperature=0.3),
    AgentConfig("GPTambit",        "openai",    "gpt-5.3-codex",    "gambit.txt",      temperature=0.9),
    AgentConfig("Random Randy",    "random",    "",                  "",                temperature=0.0),
]


def _load_personality(filename: str) -> str:
    if not filename:
        return ""
    return (PROMPTS_DIR / filename).read_text().strip()


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_prompt(board: chess.Board, personality: str) -> str:
    legal_moves = [board.san(m) for m in board.legal_moves]
    legal_uci = [m.uci() for m in board.legal_moves]
    side = "White" if board.turn == chess.WHITE else "Black"

    # Last few moves for context
    move_history = []
    temp_board = board.copy()
    moves = list(board.move_stack)
    replay = chess.Board()
    for m in moves[-10:]:
        move_history.append(replay.san(m))
        replay.push(m)

    prompt = f"""{personality}

You are playing {side}.

Current position (FEN):
{board.fen()}

Recent moves: {', '.join(move_history[-10:]) if move_history else 'Game start'}

Legal moves (SAN): {', '.join(legal_moves)}
Legal moves (UCI): {', '.join(legal_uci)}

Choose your next move. You MUST reply with EXACTLY one move in UCI format (e.g. e2e4, g1f3, e7e8q).
Do NOT include any other text, explanation, or formatting. Just the move."""

    return prompt


# ---------------------------------------------------------------------------
# LLM callers
# ---------------------------------------------------------------------------

def _call_anthropic(prompt: str, config: AgentConfig) -> str:
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=config.model,
        max_tokens=16,
        temperature=config.temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip().lower()


def _call_openai(prompt: str, config: AgentConfig) -> str:
    client = openai.OpenAI()
    resp = client.chat.completions.create(
        model=config.model,
        max_tokens=16,
        temperature=config.temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip().lower()


# ---------------------------------------------------------------------------
# Main entry: get_move
# ---------------------------------------------------------------------------

def get_move(board: chess.Board, config: AgentConfig) -> tuple[chess.Move, dict]:
    """Return (move, metadata) for the given board state and agent config."""

    legal_moves = list(board.legal_moves)

    # Random agent — no LLM call
    if config.provider == "random":
        move = random.choice(legal_moves)
        return move, {"raw": move.uci(), "attempts": 0, "fallback": False}

    personality = _load_personality(config.personality_file)
    prompt = build_prompt(board, personality)

    caller = _call_anthropic if config.provider == "anthropic" else _call_openai

    for attempt in range(1, config.max_retries + 1):
        try:
            raw = caller(prompt, config)
            # Clean up common LLM noise
            raw = raw.replace("```", "").replace("`", "").strip().split()[0]

            # Try parsing as UCI
            move = chess.Move.from_uci(raw)
            if move in legal_moves:
                return move, {"raw": raw, "attempts": attempt, "fallback": False}

            # Maybe they gave SAN?
            try:
                move = board.parse_san(raw)
                if move in legal_moves:
                    return move, {"raw": raw, "attempts": attempt, "fallback": False}
            except ValueError:
                pass

            config.stats["illegal_attempts"] += 1

        except Exception as e:
            config.stats["illegal_attempts"] += 1
            time.sleep(0.5)

    # All retries exhausted — random fallback
    config.stats["random_fallbacks"] += 1
    move = random.choice(legal_moves)
    return move, {"raw": "RANDOM_FALLBACK", "attempts": config.max_retries, "fallback": True}
