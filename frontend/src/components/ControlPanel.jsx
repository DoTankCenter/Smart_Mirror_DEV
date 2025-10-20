import { useState } from 'react'
import './ControlPanel.css'

export default function ControlPanel({ config, onChange }) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className={`control-panel ${isExpanded ? 'expanded' : ''}`}>
      <button
        className="toggle-button"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isExpanded ? 'Ô£ò' : 'ÔÜÖ'}
      </button>

      {isExpanded && (
        <div className="controls">
          <h3>Physics Controls</h3>

          <div className="control-group">
            <label>
              Gravity
              <span className="value">{config.gravity.toFixed(2)}</span>
            </label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={config.gravity}
              onChange={(e) => onChange('gravity', parseFloat(e.target.value))}
            />
          </div>

          <div className="control-group">
            <label>
              Bounciness
              <span className="value">{config.restitution.toFixed(2)}</span>
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={config.restitution}
              onChange={(e) => onChange('restitution', parseFloat(e.target.value))}
            />
          </div>

          <div className="control-group">
            <label>
              Friction
              <span className="value">{config.friction.toFixed(3)}</span>
            </label>
            <input
              type="range"
              min="0"
              max="0.1"
              step="0.005"
              value={config.friction}
              onChange={(e) => onChange('friction', parseFloat(e.target.value))}
            />
          </div>

          <div className="control-group">
            <label>
              Similar Items Count
              <span className="value">{config.bubbleCount}</span>
            </label>
            <input
              type="range"
              min="1"
              max="10"
              step="1"
              value={config.bubbleCount}
              onChange={(e) => onChange('bubbleCount', parseInt(e.target.value))}
            />
          </div>

          <div className="control-group">
            <label>
              Main Bubble Size
              <span className="value">{config.mainBubbleSize}px</span>
            </label>
            <input
              type="range"
              min="40"
              max="150"
              step="10"
              value={config.mainBubbleSize}
              onChange={(e) => onChange('mainBubbleSize', parseInt(e.target.value))}
            />
          </div>

          <div className="control-group">
            <label>
              Satellite Bubble Size
              <span className="value">{config.satelliteBubbleSize}px</span>
            </label>
            <input
              type="range"
              min="15"
              max="60"
              step="5"
              value={config.satelliteBubbleSize}
              onChange={(e) => onChange('satelliteBubbleSize', parseInt(e.target.value))}
            />
          </div>
        </div>
      )}
    </div>
  )
}
