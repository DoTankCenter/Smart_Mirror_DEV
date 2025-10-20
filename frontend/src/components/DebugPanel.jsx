import { useState, useEffect } from 'react'
import './DebugPanel.css'

export default function DebugPanel({ debugInfo, cameraStream, onClose }) {
  const [backendStatus, setBackendStatus] = useState({ status: 'checking', data: null })
  const [showCameraPreview, setShowCameraPreview] = useState(true)

  useEffect(() => {
    checkBackendStatus()
    const interval = setInterval(checkBackendStatus, 5000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (cameraStream) {
      cameraStream.setDebugMode(showCameraPreview)
    }
  }, [showCameraPreview, cameraStream])

  const checkBackendStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/health')
      console.log('Health check response:', response.status, response.ok)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()
      console.log('Health check data:', data)
      setBackendStatus({ status: 'ok', data })
    } catch (error) {
      console.error('Backend status check failed:', error)
      setBackendStatus({ status: 'error', data: null })
    }
  }

  const checkIndexStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/index-status')
      const data = await response.json()
      return data
    } catch (error) {
      return null
    }
  }

  const [indexStatus, setIndexStatus] = useState(null)

  useEffect(() => {
    checkIndexStatus().then(setIndexStatus)
  }, [])

  return (
    <div className="debug-panel">
      <div className="debug-header">
        <h3>Debug Panel</h3>
        <button className="close-btn" onClick={onClose}>X</button>
      </div>

      <div className="debug-content">
        <div className="debug-section">
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px'}}>
            <h4 style={{margin: 0}}>Backend Status</h4>
            <button
              onClick={checkBackendStatus}
              style={{
                padding: '4px 12px',
                fontSize: '11px',
                background: 'rgba(78, 205, 196, 0.2)',
                border: '1px solid rgba(78, 205, 196, 0.3)',
                color: '#4ecdc4',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Refresh
            </button>
          </div>
          <div className={`status-badge ${backendStatus.status}`}>
            {backendStatus.status === 'ok' ? 'Connected' :
             backendStatus.status === 'error' ? 'Disconnected' : 'Checking...'}
          </div>
          {backendStatus.data && (
            <div className="status-details">
              <div>Status: {backendStatus.data.status || 'unknown'}</div>
              <div>Segmenter: {backendStatus.data.segmenter_ready ? 'Ready' : 'Not Ready'}</div>
              <div>Search: {backendStatus.data.search_ready ? 'Ready' : 'Not Ready'}</div>
            </div>
          )}
          {backendStatus.status === 'error' && (
            <div className="status-details">
              <div style={{color: '#ff4757'}}>Cannot connect to backend at http://localhost:8000</div>
            </div>
          )}
        </div>

        <div className="debug-section">
          <h4>Index Status</h4>
          {indexStatus ? (
            <div className="status-details">
              <div>Indexed: {indexStatus.indexed ? 'Yes' : 'No'}</div>
              <div>Total Items: {indexStatus.total_items}</div>
              <div>Directory: <code>{indexStatus.current_directory}</code></div>
            </div>
          ) : (
            <div>Loading...</div>
          )}
        </div>

        <div className="debug-section">
          <h4>Camera Stream</h4>
          <div className="toggle-container">
            <label>
              <input
                type="checkbox"
                checked={showCameraPreview}
                onChange={(e) => setShowCameraPreview(e.target.checked)}
              />
              Show Camera Preview
            </label>
          </div>
          {debugInfo && (
            <div className="status-details">
              <div>Frames Sent: {debugInfo.frameCount}</div>
              <div>Last Response: {debugInfo.lastResponse || 'None'}</div>
              <div>Garments Detected: {debugInfo.garmentsDetected}</div>
            </div>
          )}
        </div>

        {debugInfo && debugInfo.garmentData && debugInfo.garmentData.length > 0 && (
          <div className="debug-section">
            <h4>Detected Garments</h4>
            <div className="garment-list">
              {debugInfo.garmentData.map((garment, idx) => (
                <div key={idx} className="garment-item">
                  <div>ID: {garment.garment_id}</div>
                  <div>Category: {garment.category}</div>
                  <div>Color: {garment.color_hex}</div>
                  <div>Confidence: {(garment.confidence * 100).toFixed(1)}%</div>
                  {garment.thumbnail && (
                    <img
                      src={garment.thumbnail}
                      alt="Garment"
                      style={{ width: '60px', height: '60px', objectFit: 'cover', borderRadius: '4px', marginTop: '4px' }}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="debug-section">
          <h4>Troubleshooting</h4>
          <div className="troubleshooting">
            {backendStatus.status === 'error' && (
              <div className="error-msg">Backend not running. Start with: <code>python backend/main.py</code></div>
            )}
            {backendStatus.data && !backendStatus.data.segmenter_ready && (
              <div className="error-msg">Segmenter not ready. Check if yolov8n-seg.pt model exists.</div>
            )}
            {indexStatus && !indexStatus.indexed && (
              <div className="warning-msg">No images indexed. Configure dataset in Settings and click Index Library.</div>
            )}
            {debugInfo && debugInfo.frameCount > 10 && debugInfo.garmentsDetected === 0 && (
              <div className="warning-msg">No garments detected. Try:
                <ul>
                  <li>Ensure good lighting</li>
                  <li>Stand 2-3 meters from camera</li>
                  <li>Wear visible clothing</li>
                  <li>Lower confidence threshold in Settings</li>
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
