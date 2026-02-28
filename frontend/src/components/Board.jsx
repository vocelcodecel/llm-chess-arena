import React from 'react'
import { Chessboard } from 'react-chessboard'

export default function Board({ fen, white, black }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
      <div style={{ fontSize: '14px', opacity: 0.7 }}>⬛ {black || 'Black'}</div>
      <Chessboard
        position={fen || 'start'}
        boardWidth={420}
        arePiecesDraggable={false}
        customDarkSquareStyle={{ backgroundColor: '#779952' }}
        customLightSquareStyle={{ backgroundColor: '#edeed1' }}
      />
      <div style={{ fontSize: '14px', opacity: 0.7 }}>⬜ {white || 'White'}</div>
    </div>
  )
}
