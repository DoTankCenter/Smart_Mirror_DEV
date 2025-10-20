import { useState, useEffect, useRef } from 'react'
import EnhancedBubbleCanvas from './components/EnhancedBubbleCanvas'
import ControlPanel from './components/ControlPanel'
import SettingsPanel from './components/SettingsPanel'
import DebugPanel from './components/DebugPanel'
import CameraStream from './utils/CameraStream'
import './App.css'

function App() {
  const [garments, setGarments] = useState([])
  const [isConnected, setIsConnected] = useState(false)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isDebugOpen, setIsDebugOpen] = useState(false)
  const [debugInfo, setDebugInfo] = useState(null)
  const [physicsConfig, setPhysicsConfig] = useState({
    gravity: 0.3,
    restitution: 0.8,
    friction: 0.01,
    bubbleCount: 5,
    mainBubbleSize: 80,
    satelliteBubbleSize: 30
  })

  const cameraStreamRef = useRef(null)

  useEffect(() => {
    // Initialize camera stream
    cameraStreamRef.current = new CameraStream('ws://localhost:8000/ws/camera-stream')

    cameraStreamRef.current.onConnect = () => {
      console.log('Connected to backend')
      setIsConnected(true)
    }

    cameraStreamRef.current.onDisconnect = () => {
      console.log('Disconnected from backend')
      setIsConnected(false)
    }

    cameraStreamRef.current.onGarments = (garmentsData) => {
      setGarments(garmentsData)
    }

    cameraStreamRef.current.onDebugInfo = (info) => {
      setDebugInfo(info)
    }

    cameraStreamRef.current.connect()

    return () => {
      cameraStreamRef.current?.disconnect()
    }
  }, [])

  const handleConfigChange = (key, value) => {
    setPhysicsConfig(prev => ({ ...prev, [key]: value }))
  }

  return (
    <div className="app">
      <div className="status-indicator">
        <div className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}></div>
        <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
        <span className="garment-count">{garments.length} garments detected</span>
      </div>

      <div className="top-buttons">
        <button
          className="debug-button"
          onClick={() => setIsDebugOpen(!isDebugOpen)}
          title="Toggle Debug Panel"
        >
          Debug
        </button>
        <button
          className="settings-button"
          onClick={() => setIsSettingsOpen(true)}
          title="Open Settings"
        >
          Settings
        </button>
      </div>

      <EnhancedBubbleCanvas
        garments={garments}
        config={physicsConfig}
      />

      <ControlPanel
        config={physicsConfig}
        onChange={handleConfigChange}
      />

      <SettingsPanel
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />

      {isDebugOpen && (
        <DebugPanel
          debugInfo={debugInfo}
          cameraStream={cameraStreamRef.current}
          onClose={() => setIsDebugOpen(false)}
        />
      )}
    </div>
  )
}

export default App
