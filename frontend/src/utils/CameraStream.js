export default class CameraStream {
  constructor(wsUrl) {
    this.wsUrl = wsUrl
    this.ws = null
    this.stream = null
    this.videoElement = null
    this.canvas = null
    this.isStreaming = false
    this.debugMode = false
    this.frameCount = 0
    this.lastResponseTime = null

    this.onConnect = null
    this.onDisconnect = null
    this.onGarments = null
    this.onDebugInfo = null
  }

  setDebugMode(enabled) {
    this.debugMode = enabled
    if (this.videoElement && enabled) {
      this.videoElement.style.cssText = 'position: fixed; top: 80px; left: 20px; width: 320px; height: 240px; z-index: 1000; border: 2px solid #4ecdc4; border-radius: 8px;'
      document.body.appendChild(this.videoElement)
    } else if (this.videoElement && !enabled) {
      if (this.videoElement.parentElement) {
        this.videoElement.parentElement.removeChild(this.videoElement)
      }
    }
  }

  getVideoElement() {
    return this.videoElement
  }

  async connect() {
    try {
      // Get camera stream
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user'
        }
      })

      // Create hidden video element
      this.videoElement = document.createElement('video')
      this.videoElement.srcObject = this.stream
      this.videoElement.autoplay = true
      this.videoElement.playsInline = true

      // Create canvas for frame capture
      this.canvas = document.createElement('canvas')

      // Wait for video to be ready
      await new Promise((resolve) => {
        this.videoElement.onloadedmetadata = () => {
          this.canvas.width = this.videoElement.videoWidth
          this.canvas.height = this.videoElement.videoHeight
          resolve()
        }
      })

      // Connect to WebSocket
      this.ws = new WebSocket(this.wsUrl)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.isStreaming = true
        if (this.onConnect) this.onConnect()
        this.startStreaming()
      }

      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        this.lastResponseTime = Date.now()

        if (this.debugMode && this.onDebugInfo) {
          this.onDebugInfo({
            frameCount: this.frameCount,
            garmentsDetected: data.garments ? data.garments.length : 0,
            lastResponse: new Date().toLocaleTimeString(),
            garmentData: data.garments
          })
        }

        if (data.garments && this.onGarments) {
          this.onGarments(data.garments)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      this.ws.onclose = () => {
        console.log('WebSocket closed')
        this.isStreaming = false
        if (this.onDisconnect) this.onDisconnect()
      }

    } catch (error) {
      console.error('Error connecting camera:', error)
      alert('Could not access camera. Please grant camera permissions.')
    }
  }

  startStreaming() {
    const sendFrame = () => {
      if (!this.isStreaming || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
        return
      }

      // Capture frame from video
      const ctx = this.canvas.getContext('2d')
      ctx.drawImage(this.videoElement, 0, 0)

      // Convert to base64
      const frameData = this.canvas.toDataURL('image/jpeg', 0.8)

      // Send to backend
      this.ws.send(JSON.stringify({ frame: frameData }))
      this.frameCount++

      if (this.debugMode) {
        console.log(`Frame ${this.frameCount} sent to backend`)
      }

      // Send next frame (throttle to ~10 FPS for processing)
      setTimeout(sendFrame, 100)
    }

    sendFrame()
  }

  disconnect() {
    this.isStreaming = false

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop())
      this.stream = null
    }

    if (this.videoElement) {
      this.videoElement.srcObject = null
      this.videoElement = null
    }
  }
}
