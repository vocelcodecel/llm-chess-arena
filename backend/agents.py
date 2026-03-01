"""LLM agent adapter — translates board state into a move."""

import logging
import os
import random
import time
from pathlib import Path
from dataclasses import dataclass, field

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import chess
import anthropic
import openai

log = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

# ---------------------------------------------------------------------------
# Agent definitions
# ---------------------------------------------------------------------------

@dataclass
class AgentConfig:
    name: str
    provider: str          # "anthropic" | "openai" | "openai_reasoning"
    model: str             # e.g. "claude-opus-4-6" or "o3-mini"
    personality_file: str  # filename inside prompts/
    temperature: float = 0.7
    max_retries: int = 3
    thinking: bool = False          # Anthropic extended thinking
    thinking_budget: int = 4096     # token budget for thinking
    reasoning_effort: str = "medium"  # OpenAI reasoning models: low/medium/high
    stats: dict = field(default_factory=lambda: {
        "illegal_attempts": 0,
        "random_fallbacks": 0,
    })


DEFAULT_AGENTS = [
    AgentConfig("Magnus Chatbot",  "anthropic", "claude-opus-4-6",   "aggressive.txt", temperature=0.8),
    AgentConfig("Stockfished",     "anthropic", "claude-sonnet-4-6", "cautious.txt",   temperature=0.3),
    AgentConfig("GPTambit",        "openai",    "gpt-5.3-codex",    "gambit.txt",      temperature=0.9),
    AgentConfig("Haiku Blitz",      "anthropic", "claude-haiku-4-5",  "blitz.txt",       temperature=0.6),
    AgentConfig("Deep Think",      "anthropic", "claude-sonnet-4-6", "thinker.txt",    temperature=1.0, thinking=True, thinking_budget=4096),
    AgentConfig("o3 Mastermind",   "openai_reasoning", "o3-mini",    "mastermind.txt",  reasoning_effort="medium"),
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
    replay = chess.Board()
    for m in board.move_stack:
        move_history.append(replay.san(m))
        replay.push(m)
    move_history = move_history[-10:]

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
    log.debug("[%s] Calling Anthropic %s (thinking=%s)", config.name, config.model, config.thinking)
    client = anthropic.Anthropic()

    kwargs = dict(
        model=config.model,
        messages=[{"role": "user", "content": prompt}],
    )

    if config.thinking:
        kwargs["max_tokens"] = config.thinking_budget + 256
        kwargs["temperature"] = 1  # required for extended thinking
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": config.thinking_budget}
    else:
        kwargs["max_tokens"] = 16
        kwargs["temperature"] = config.temperature

    resp = client.messages.create(**kwargs)

    # With thinking enabled, the text block comes after the thinking block
    for block in resp.content:
        if block.type == "text":
            text = block.text.strip().lower()
            log.debug("[%s] Anthropic returned: %s", config.name, text)
            return text

    return ""


def _call_openai(prompt: str, config: AgentConfig) -> str:
    log.debug("[%s] Calling OpenAI %s", config.name, config.model)
    client = openai.OpenAI()
    resp = client.chat.completions.create(
        model=config.model,
        max_tokens=16,
        temperature=config.temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.choices[0].message.content.strip().lower()
    log.debug("[%s] OpenAI returned: %s", config.name, text)
    return text


def _call_openai_reasoning(prompt: str, config: AgentConfig) -> str:
    log.debug("[%s] Calling OpenAI reasoning %s (effort=%s)", config.name, config.model, config.reasoning_effort)
    client = openai.OpenAI()
    resp = client.chat.completions.create(
        model=config.model,
        max_completion_tokens=1024,
        reasoning_effort=config.reasoning_effort,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.choices[0].message.content.strip().lower()
    log.debug("[%s] OpenAI reasoning returned: %s", config.name, text)
    return text


# ---------------------------------------------------------------------------
# Main entry: get_move
# ---------------------------------------------------------------------------

def get_move(board: chess.Board, config: AgentConfig) -> tuple[chess.Move, dict]:
    """Return (move, metadata) for the given board state and agent config."""

    legal_moves = list(board.legal_moves)

    # Random agent — no LLM call
    if config.provider == "random":
        move = random.choice(legal_moves)
        log.info("[%s] Random move: %s", config.name, move.uci())
        return move, {"raw": move.uci(), "attempts": 0, "fallback": False}

    personality = _load_personality(config.personality_file)
    prompt = build_prompt(board, personality)

    callers = {
        "anthropic": _call_anthropic,
        "openai": _call_openai,
        "openai_reasoning": _call_openai_reasoning,
    }
    caller = callers[config.provider]

    for attempt in range(1, config.max_retries + 1):
        try:
            raw = caller(prompt, config)
            raw = raw.replace("```", "").replace("`", "").strip().split()[0]

            move = chess.Move.from_uci(raw)
            if move in legal_moves:
                log.info("[%s] Move: %s (attempt %d)", config.name, raw, attempt)
                return move, {"raw": raw, "attempts": attempt, "fallback": False}

            try:
                move = board.parse_san(raw)
                if move in legal_moves:
                    log.info("[%s] Move (SAN→UCI): %s (attempt %d)", config.name, raw, attempt)
                    return move, {"raw": raw, "attempts": attempt, "fallback": False}
            except ValueError:
                pass

            log.warning("[%s] Illegal move '%s' (attempt %d/%d)", config.name, raw, attempt, config.max_retries)
            config.stats["illegal_attempts"] += 1

        except Exception as e:
            log.error("[%s] API error on attempt %d: %s", config.name, attempt, e)
            config.stats["illegal_attempts"] += 1
            time.sleep(0.5)

    config.stats["random_fallbacks"] += 1
    move = random.choice(legal_moves)
    log.warning("[%s] All retries exhausted → random fallback: %s", config.name, move.uci())
    return move, {"raw": "RANDOM_FALLBACK", "attempts": config.max_retries, "fallback": True}
