import React, { useState, useEffect, useCallback, useRef } from 'react'
import Board from './components/Board'
import Leaderboard from './components/Leaderboard'
import MoveList from './components/MoveList'
import GameSelector from './components/GameSelector'
import GameHeader from './components/GameHeader'
import { fetchStandings, fetchGames, startTournament, connectWebSocket } from './api'

export default function App() {
  const [standings, setStandings] = useState([])
  const [games, setGames] = useState([])
  const [currentFen, setCurrentFen] = useState('start')
  const [currentWhite, setCurrentWhite] = useState('')
  const [currentBlack, setCurrentBlack] = useState('')
  const [moves, setMoves] = useState([])
  const [running, setRunning] = useState(false)
  const [gameNum, setGameNum] = useState(0)
  const [totalGames, setTotalGames] = useState(0)
  const [lastMove, setLastMove] = useState(null)
  const [gameResult, setGameResult] = useState(null)
  const [replayMode, setReplayMode] = useState(false)
  const [replayIndex, setReplayIndex] = useState(0)
  const [replayMoves, setReplayMoves] = useState([])
  const wsRef = useRef(null)

  const handleWsMessage = useCallback((event) => {
    if (event.type === 'move') {
      setCurrentFen(event.fen)
      setLastMove({ from: event.uci.slice(0, 2), to: event.uci.slice(2, 4) })
      setMoves((prev) => [...prev, {
        san: event.san,
        uci: event.uci,
        side: event.side,
        agent: event.agent,
        fallback: event.fallback,
        fen: event.fen,
      }])
      setGameResult(null)
      setReplayMode(false)
    } else if (event.type === 'game_start') {
      setMoves([])
      setCurrentFen('start')
      setLastMove(null)
      setCurrentWhite(event.white)
      setCurrentBlack(event.black)
      setGameNum(event.game_num)
      setTotalGames(event.total_games)
      setGameResult(null)
      setReplayMode(false)
    } else if (event.type === 'game_end') {
      setGameResult(event.result)
      fetchStandings().then(setStandings)
      fetchGames().then(setGames)
    } else if (event.type === 'tournament_complete') {
      setStandings(event.standings)
      setRunning(false)
      fetchGames().then(setGames)
    }
  }, [])

  useEffect(() => {
    fetchStandings().then(setStandings)
    fetchGames().then(setGames)
    wsRef.current = connectWebSocket(handleWsMessage)
    return () => wsRef.current?.close()
  }, [handleWsMessage])

  const handleStart = async () => {
    setRunning(true)
    setStandings([])
    setGames([])
    setMoves([])
    setCurrentFen('start')
    setLastMove(null)
    setGameResult(null)
    setReplayMode(false)
    await startTournament()
  }

  // Replay a completed game move by move
  const handleReplay = (game) => {
    if (!game.moves) return
    setReplayMode(true)
    setReplayMoves(game.moves)
    setReplayIndex(0)
    setCurrentFen('start')
    setLastMove(null)
    setCurrentWhite(game.white)
    setCurrentBlack(game.black)
    setMoves([])
    setGameResult(game.result)
    setGameNum(game.game_num)
  }

  const replayNext = () => {
    if (replayIndex < replayMoves.length) {
      const m = replayMoves[replayIndex]
      setCurrentFen(m.fen)
      setLastMove({ from: m.uci.slice(0, 2), to: m.uci.slice(2, 4) })
      setMoves((prev) => [...prev, m])
      setReplayIndex((i) => i + 1)
    }
  }

  const replayAll = () => {
    let idx = replayIndex
    const interval = setInterval(() => {
      if (idx >= replayMoves.length) {
        clearInterval(interval)
        return
      }
      const m = replayMoves[idx]
      setCurrentFen(m.fen)
      setLastMove({ from: m.uci.slice(0, 2), to: m.uci.slice(2, 4) })
      setMoves((prev) => [...prev, m])
      idx++
      setReplayIndex(idx)
    }, 600)
  }

  return (
    <div style={{
      maxWidth: '1200px',
      margin: '0 auto',
      padding: '24px',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '36px', marginBottom: '4px', color: '#fff' }}>♟️ LLM Chess Arena</h1>
        <p style={{ opacity: 0.5, fontSize: '14px' }}>Language models. Legal chess. Pure chaos.</p>
        {!running && (
          <button
            onClick={handleStart}
            style={{
              marginTop: '16px',
              padding: '12px 32px',
              fontSize: '16px',
              fontWeight: 'bold',
              background: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              transition: 'background 0.2s',
            }}
            onMouseOver={(e) => e.target.style.background = '#45a049'}
            onMouseOut={(e) => e.target.style.background = '#4CAF50'}
          >
            🏁 Start Tournament
          </button>
        )}
        {running && (
          <div style={{
            marginTop: '12px',
            padding: '8px 16px',
            background: '#2a2a4a',
            borderRadius: '8px',
            display: 'inline-block',
            fontSize: '14px',
            color: '#4CAF50',
          }}>
            ⏳ Tournament in progress...
          </div>
        )}
      </div>

      {/* Main layout */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '280px 1fr 240px',
        gap: '24px',
        alignItems: 'start',
      }}>
        {/* Left: Leaderboard + Games */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <Leaderboard standings={standings} />
          <GameSelector games={games} onSelect={handleReplay} />
        </div>

        {/* Center: Game header + Board */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
          <GameHeader
            white={currentWhite}
            black={currentBlack}
            gameNum={gameNum}
            totalGames={totalGames}
            result={gameResult}
            running={running}
          />
          <Board
            fen={currentFen}
            white={currentWhite}
            black={currentBlack}
            lastMove={lastMove}
          />
          {replayMode && (
            <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
              <button
                onClick={replayNext}
                disabled={replayIndex >= replayMoves.length}
                style={{
                  padding: '6px 16px',
                  background: '#3a3a5a',
                  color: '#e0e0e0',
                  border: '1px solid #555',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '13px',
                }}
              >
                ▶ Next Move
              </button>
              <button
                onClick={replayAll}
                disabled={replayIndex >= replayMoves.length}
                style={{
                  padding: '6px 16px',
                  background: '#3a3a5a',
                  color: '#e0e0e0',
                  border: '1px solid #555',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '13px',
                }}
              >
                ⏩ Play All
              </button>
              <span style={{ fontSize: '12px', opacity: 0.5, alignSelf: 'center' }}>
                {replayIndex}/{replayMoves.length}
              </span>
            </div>
          )}
        </div>

        {/* Right: Move list */}
        <MoveList moves={moves} />
      </div>
    </div>
  )
}
