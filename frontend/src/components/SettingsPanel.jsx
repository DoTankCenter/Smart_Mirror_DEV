import { useState, useEffect } from 'react'
import './SettingsPanel.css'

export default function SettingsPanel({ isOpen, onClose }) {
  const [settings, setSettings] = useState({
    dataset_directory: '',
    metadata_file: '',
    conf_threshold: 0.5,
    max_similar_items: 10
  })
  const [indexStatus, setIndexStatus] = useState({
    indexed: false,
    total_items: 0,
    current_directory: ''
  })
  const [loading, setLoading] = useState(false)
  const [indexing, setIndexing] = useState(false)
  const [message, setMessage] = useState({ text: '', type: '' })

  useEffect(() => {
    if (isOpen) {
      loadSettings()
      loadIndexStatus()
    }
  }, [isOpen])

  const loadSettings = async () => {
    try {
      const response = await fetch('http://localhost:8000/settings')
      if (response.ok) {
        const data = await response.json()
        setSettings(data)
      }
    } catch (error) {
      console.error('Error loading settings:', error)
      showMessage('Failed to load settings', 'error')
    }
  }

  const loadIndexStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/index-status')
      if (response.ok) {
        const data = await response.json()
        setIndexStatus(data)
      }
    } catch (error) {
      console.error('Error loading index status:', error)
    }
  }

  const handleSaveSettings = async () => {
    setLoading(true)
    setMessage({ text: '', type: '' })

    try {
      const response = await fetch('http://localhost:8000/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings),
      })

      const data = await response.json()

      if (response.ok) {
        showMessage(data.message || 'Settings saved successfully!', 'success')
        setSettings(data.settings)
        loadIndexStatus()
      } else {
        showMessage(data.error || 'Failed to save settings', 'error')
      }
    } catch (error) {
      console.error('Error saving settings:', error)
      showMessage('Failed to save settings', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleIndexLibrary = async () => {
    setIndexing(true)
    setMessage({ text: '', type: '' })

    try {
      const response = await fetch('http://localhost:8000/index-library', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ directory: settings.dataset_directory }),
      })

      const data = await response.json()

      if (response.ok) {
        showMessage(data.message || 'Library indexed successfully!', 'success')
        loadIndexStatus()
      } else {
        showMessage(data.error || 'Failed to index library', 'error')
      }
    } catch (error) {
      console.error('Error indexing library:', error)
      showMessage('Failed to index library', 'error')
    } finally {
      setIndexing(false)
    }
  }

  const showMessage = (text, type) => {
    setMessage({ text, type })
    setTimeout(() => setMessage({ text: '', type: '' }), 5000)
  }

  const handleInputChange = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }))
  }

  if (!isOpen) return null

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-panel" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>Settings</h2>
          <button className="close-button" onClick={onClose}>
            X
          </button>
        </div>

        <div className="settings-content">
          {message.text && (
            <div className={`message ${message.type}`}>
              {message.text}
            </div>
          )}

          <div className="settings-section">
            <h3>Dataset Configuration</h3>

            <div className="setting-item">
              <label>Dataset Directory</label>
              <input
                type="text"
                value={settings.dataset_directory}
                onChange={(e) => handleInputChange('dataset_directory', e.target.value)}
                placeholder="e.g., C:\path\to\dataset or image_library"
              />
              <small>Path to folder containing fashion images</small>
            </div>

            <div className="setting-item">
              <label>Metadata File</label>
              <input
                type="text"
                value={settings.metadata_file}
                onChange={(e) => handleInputChange('metadata_file', e.target.value)}
                placeholder="metadata.json"
              />
              <small>JSON file with image descriptions and categories</small>
            </div>

            <div className="index-status">
              <div className="status-row">
                <span>Index Status:</span>
                <span className={indexStatus.indexed ? 'status-active' : 'status-inactive'}>
                  {indexStatus.indexed ? 'Indexed' : 'Not Indexed'}
                </span>
              </div>
              <div className="status-row">
                <span>Total Images:</span>
                <span>{indexStatus.total_items}</span>
              </div>
              <div className="status-row">
                <span>Current Directory:</span>
                <span className="directory-path">{indexStatus.current_directory || 'None'}</span>
              </div>
            </div>

            <button
              className="index-button"
              onClick={handleIndexLibrary}
              disabled={indexing || !settings.dataset_directory}
            >
              {indexing ? 'Indexing...' : 'Index Library'}
            </button>
          </div>

          <div className="settings-section">
            <h3>Model Configuration</h3>

            <div className="setting-item">
              <label>
                Confidence Threshold
                <span className="value">{settings.conf_threshold?.toFixed(2)}</span>
              </label>
              <input
                type="range"
                min="0.1"
                max="1.0"
                step="0.05"
                value={settings.conf_threshold || 0.5}
                onChange={(e) => handleInputChange('conf_threshold', parseFloat(e.target.value))}
              />
              <small>Minimum confidence for garment detection (higher = stricter)</small>
            </div>

            <div className="setting-item">
              <label>
                Max Similar Items
                <span className="value">{settings.max_similar_items}</span>
              </label>
              <input
                type="range"
                min="1"
                max="20"
                step="1"
                value={settings.max_similar_items || 10}
                onChange={(e) => handleInputChange('max_similar_items', parseInt(e.target.value))}
              />
              <small>Maximum number of similar items to search</small>
            </div>
          </div>
        </div>

        <div className="settings-footer">
          <button className="cancel-button" onClick={onClose}>
            Cancel
          </button>
          <button
            className="save-button"
            onClick={handleSaveSettings}
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  )
}
