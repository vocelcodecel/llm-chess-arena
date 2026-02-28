import React from 'react'

export default function GameSelector({ games, onSelect }) {
  if (!games || games.length === 0) return null

  return (
    <div>
      <h2 style={{ marginBottom: '8px', fontSize: '18px' }}>📂 Games</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '200px', overflowY: 'auto' }}>
        {games.map((g) => (
          <button
            key={g.game_num}
            onClick={() => onSelect(g)}
            style={{
              background: '#2a2a4a',
              border: '1px solid #444',
              borderRadius: '4px',
              color: '#e0e0e0',
              padding: '6px 10px',
              cursor: 'pointer',
              textAlign: 'left',
              fontSize: '12px',
            }}
          >
            #{g.game_num} {g.white} vs {g.black} → <strong>{g.result}</strong> ({g.reason}, {g.total_moves} moves)
          </button>
        ))}
      </div>
    </div>
  )
}
