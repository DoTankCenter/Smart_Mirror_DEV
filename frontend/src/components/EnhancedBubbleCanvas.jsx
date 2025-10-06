import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import EnhancedBubblePhysics from '../physics/EnhancedBubblePhysics'
import './BubbleCanvas.css'

export default function EnhancedBubbleCanvas({ garments, config }) {
  const canvasRef = useRef(null)
  const sceneRef = useRef(null)
  const physicsRef = useRef(null)
  const bubbleMeshesRef = useRef(new Map())
  const lastProcessTimeRef = useRef(0)

  useEffect(() => {
    // Setup Three.js scene
    const canvas = canvasRef.current
    const width = window.innerWidth
    const height = window.innerHeight

    // Scene
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0a0a0a)
    sceneRef.current = scene

    // Camera (orthographic for 2D)
    const camera = new THREE.OrthographicCamera(
      0, width, 0, height, 0.1, 1000
    )
    camera.position.z = 10

    // Renderer with anti-aliasing
    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance'
    })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))

    // Lighting for glossy effect
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5)
    scene.add(ambientLight)

    const pointLight1 = new THREE.PointLight(0xffffff, 1.0)
    pointLight1.position.set(width / 2, height * 0.3, 200)
    scene.add(pointLight1)

    const pointLight2 = new THREE.PointLight(0x6366f1, 0.5)
    pointLight2.position.set(width * 0.2, height * 0.7, 150)
    scene.add(pointLight2)

    // Initialize enhanced physics
    physicsRef.current = new EnhancedBubblePhysics(width, height, config)

    // Animation loop - 60 FPS rendering
    let animationId
    const animate = () => {
      animationId = requestAnimationFrame(animate)

      // Update bubble meshes
      updateBubbleMeshes()

      renderer.render(scene, camera)
    }

    animate()

    // Handle window resize
    const handleResize = () => {
      const newWidth = window.innerWidth
      const newHeight = window.innerHeight

      camera.left = 0
      camera.right = newWidth
      camera.top = 0
      camera.bottom = newHeight
      camera.updateProjectionMatrix()

      renderer.setSize(newWidth, newHeight)
    }

    window.addEventListener('resize', handleResize)

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize)
      cancelAnimationFrame(animationId)
      physicsRef.current?.destroy()
      renderer.dispose()

      // Dispose all meshes
      bubbleMeshesRef.current.forEach(mesh => {
        mesh.geometry.dispose()
        if (mesh.material.map) mesh.material.map.dispose()
        mesh.material.dispose()
      })
    }
  }, [])

  // Update physics when garments change (throttled to ~30 FPS for ML processing)
  useEffect(() => {
    if (physicsRef.current && garments) {
      const now = Date.now()

      // Throttle to 30 FPS for physics updates (ML runs at 10 FPS)
      if (now - lastProcessTimeRef.current > 33) {
        physicsRef.current.updateGarments(garments)
        lastProcessTimeRef.current = now
      }
    }
  }, [garments])

  // Update physics config
  useEffect(() => {
    if (physicsRef.current) {
      physicsRef.current.updateConfig(config)
    }
  }, [config])

  const updateBubbleMeshes = () => {
    if (!physicsRef.current || !sceneRef.current) return

    const bubbles = physicsRef.current.getBubbles()
    const currentMeshIds = new Set()

    // Update or create meshes for each bubble
    bubbles.forEach((bubble, garmentId) => {
      const mainId = `main-${garmentId}`
      currentMeshIds.add(mainId)

      const fadeAlpha = physicsRef.current.getFadeAlpha(bubble)

      // Main bubble
      if (!bubbleMeshesRef.current.has(mainId)) {
        const mesh = createGlossyBubbleMesh(
          bubble.main.circleRadius,
          bubble.main.plugin.garmentData
        )
        bubbleMeshesRef.current.set(mainId, mesh)
        sceneRef.current.add(mesh)
      }

      const mainMesh = bubbleMeshesRef.current.get(mainId)
      mainMesh.position.x = bubble.main.position.x
      mainMesh.position.y = window.innerHeight - bubble.main.position.y

      // Update opacity for fade in/out
      mainMesh.material.opacity = fadeAlpha * 0.95
      if (mainMesh.children[0]) {
        mainMesh.children[0].material.opacity = fadeAlpha * 0.25 // Glow
      }

      // Satellite bubbles
      bubble.satellites.forEach((sat, index) => {
        const satId = `sat-${garmentId}-${index}`
        currentMeshIds.add(satId)

        if (!bubbleMeshesRef.current.has(satId)) {
          const mesh = createSatelliteBubbleMesh(
            sat.body.circleRadius,
            sat.body.plugin.similarItem
          )
          bubbleMeshesRef.current.set(satId, mesh)
          sceneRef.current.add(mesh)
        }

        const satMesh = bubbleMeshesRef.current.get(satId)
        satMesh.position.x = sat.body.position.x
        satMesh.position.y = window.innerHeight - sat.body.position.y

        satMesh.material.opacity = fadeAlpha * 0.7
        if (satMesh.children[0]) {
          satMesh.children[0].material.opacity = fadeAlpha * 0.2
        }
      })
    })

    // Remove meshes for bubbles that no longer exist
    for (const [id, mesh] of bubbleMeshesRef.current.entries()) {
      if (!currentMeshIds.has(id)) {
        sceneRef.current.remove(mesh)
        mesh.geometry.dispose()
        if (mesh.material.map) mesh.material.map.dispose()
        mesh.material.dispose()
        bubbleMeshesRef.current.delete(id)
      }
    }
  }

  const createGlossyBubbleMesh = (radius, garmentData) => {
    const geometry = new THREE.CircleGeometry(radius, 64)

    // Create glossy gradient texture
    const canvas = document.createElement('canvas')
    canvas.width = 512
    canvas.height = 512
    const ctx = canvas.getContext('2d')

    const color = garmentData.color

    // Radial gradient with highlight
    const gradient = ctx.createRadialGradient(200, 200, 0, 256, 256, 256)
    gradient.addColorStop(0, `rgba(255, 255, 255, 0.6)`) // Bright center (glossy highlight)
    gradient.addColorStop(0.3, `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.9)`)
    gradient.addColorStop(0.7, `rgba(${color[0] * 0.7}, ${color[1] * 0.7}, ${color[2] * 0.7}, 0.95)`)
    gradient.addColorStop(1, `rgba(${color[0] * 0.5}, ${color[1] * 0.5}, ${color[2] * 0.5}, 1.0)`)

    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, 512, 512)

    // Add specular highlight
    const highlightGradient = ctx.createRadialGradient(180, 180, 0, 180, 180, 100)
    highlightGradient.addColorStop(0, 'rgba(255, 255, 255, 0.5)')
    highlightGradient.addColorStop(1, 'rgba(255, 255, 255, 0)')
    ctx.fillStyle = highlightGradient
    ctx.fillRect(0, 0, 512, 512)

    const texture = new THREE.CanvasTexture(canvas)
    const material = new THREE.MeshBasicMaterial({
      map: texture,
      transparent: true,
      opacity: 0.95,
      side: THREE.DoubleSide
    })

    const mesh = new THREE.Mesh(geometry, material)

    // Add outer glow
    const glowGeometry = new THREE.CircleGeometry(radius * 1.3, 64)
    const glowMaterial = new THREE.MeshBasicMaterial({
      color: new THREE.Color(color[0] / 255, color[1] / 255, color[2] / 255),
      transparent: true,
      opacity: 0.25
    })
    const glow = new THREE.Mesh(glowGeometry, glowMaterial)
    glow.position.z = -0.1
    mesh.add(glow)

    // Add category label
    const label = createTextSprite(garmentData.category || 'GARMENT', 24)
    label.position.y = 0
    label.position.z = 1
    mesh.add(label)

    return mesh
  }

  const createSatelliteBubbleMesh = (radius, similarItem) => {
    const geometry = new THREE.CircleGeometry(radius, 48)

    // Create gradient for satellite (blue-purple theme)
    const canvas = document.createElement('canvas')
    canvas.width = 256
    canvas.height = 256
    const ctx = canvas.getContext('2d')

    const gradient = ctx.createRadialGradient(100, 100, 0, 128, 128, 128)
    gradient.addColorStop(0, 'rgba(255, 255, 255, 0.7)')
    gradient.addColorStop(0.4, 'rgba(99, 102, 241, 0.8)')
    gradient.addColorStop(1, 'rgba(79, 70, 229, 0.95)')

    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, 256, 256)

    const texture = new THREE.CanvasTexture(canvas)
    const material = new THREE.MeshBasicMaterial({
      map: texture,
      transparent: true,
      opacity: 0.7
    })

    const mesh = new THREE.Mesh(geometry, material)

    // Glow
    const glowGeometry = new THREE.CircleGeometry(radius * 1.4, 48)
    const glowMaterial = new THREE.MeshBasicMaterial({
      color: 0x6366f1,
      transparent: true,
      opacity: 0.2
    })
    const glow = new THREE.Mesh(glowGeometry, glowMaterial)
    glow.position.z = -0.1
    mesh.add(glow)

    return mesh
  }

  const createTextSprite = (text, fontSize = 24) => {
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    canvas.width = 512
    canvas.height = 128

    ctx.font = `bold ${fontSize}px Arial, sans-serif`
    ctx.fillStyle = 'white'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'

    // Add text shadow for better visibility
    ctx.shadowColor = 'rgba(0, 0, 0, 0.8)'
    ctx.shadowBlur = 8
    ctx.shadowOffsetX = 2
    ctx.shadowOffsetY = 2

    ctx.fillText(text.toUpperCase(), 256, 64)

    const texture = new THREE.CanvasTexture(canvas)
    const material = new THREE.SpriteMaterial({ map: texture })
    const sprite = new THREE.Sprite(material)
    sprite.scale.set(120, 30, 1)

    return sprite
  }

  return <canvas ref={canvasRef} className="bubble-canvas" />
}
