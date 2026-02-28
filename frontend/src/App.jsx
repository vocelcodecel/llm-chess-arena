import React, { useState, useEffect, useCallback } from 'react'
import Board from './components/Board'
import Leaderboard from './components/Leaderboard'
import MoveList from './components/MoveList'
import GameSelector from './components/GameSelector'
import { fetchStandings, fetchGames, startTournament, connectWebSocket } from './api'

export default function App() {
  const [standings, setStandings] = useState([])
  const [games, setGames] = useState([])
  const [currentFen, setCurrentFen] = useState('start')
  const [currentWhite, setCurrentWhite] = useState('')
  const [currentBlack, setCurrentBlack] = useState('')
  const [moves, setMoves] = useState([])
  const [running, setRunning] = useState(false)
  const [gameInfo, setGameInfo] = useState('')

  const handleWsMessage = useCallback((event) => {
    if (event.type === 'move') {
      setCurrentFen(event.fen)
      setMoves((prev) => [...prev, {
        san: event.san,
        uci: event.uci,
        side: event.side,
        agent: event.agent,
        fallback: event.fallback,
      }])
    } else if (event.type === 'game_start') {
      setMoves([])
      setCurrentFen('start')
      setCurrentWhite(event.white)
      setCurrentBlack(event.black)
      setGameInfo(`Game ${event.game_num}/${event.total_games}`)
    } else if (event.type === 'tournament_complete') {
      setStandings(event.standings)
      setRunning(false)
      setGameInfo('Tournament complete!')
      fetchGames().then(setGames)
    }
  }, [])

  useEffect(() => {
    fetchStandings().then(setStandings)
    fetchGames().then(setGames)
    const ws = connectWebSocket(handleWsMessage)
    return () => ws.close()
  }, [handleWsMessage])

  const handleStart = async () => {
    setRunning(true)
    setStandings([])
    setGames([])
    setMoves([])
    setCurrentFen('start')
    setGameInfo('Starting...')
    await startTournament()
  }

  return (
    <div style={{
      maxWidth: '1200px',
      margin: '0 auto',
      padding: '24px',
    }}>
      {/* Header */}
      <div style={{
        textAlign: 'center',
        marginBottom: '32px',
      }}>
        <h1 style={{ fontSize: '36px', marginBottom: '4px' }}>♟️ LLM Chess Arena</h1>
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
            }}
          >
            🏁 Start Tournament
          </button>
        )}
        {gameInfo && (
          <div style={{ marginTop: '8px', fontSize: '14px', color: '#ffd700' }}>{gameInfo}</div>
        )}
      </div>

      {/* Main layout */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 440px 1fr',
        gap: '24px',
        alignItems: 'start',
      }}>
        {/* Left: Leaderboard + Games */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <Leaderboard standings={standings} />
          <GameSelector games={games} onSelect={(g) => setGameInfo(`Viewing game #${g.game_num}`)} />
        </div>

        {/* Center: Board */}
        <Board fen={currentFen} white={currentWhite} black={currentBlack} />

        {/* Right: Move list */}
        <MoveList moves={moves} />
      </div>
    </div>
  )
}
