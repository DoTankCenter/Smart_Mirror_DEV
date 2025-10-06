import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import BubblePhysics from '../physics/BubblePhysics'
import './BubbleCanvas.css'

export default function BubbleCanvas({ garments, config }) {
  const canvasRef = useRef(null)
  const sceneRef = useRef(null)
  const physicsRef = useRef(null)
  const bubbleMeshesRef = useRef(new Map())

  useEffect(() => {
    // Setup Three.js scene
    const canvas = canvasRef.current
    const width = window.innerWidth
    const height = window.innerHeight

    // Scene
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0a0a0a)
    sceneRef.current = scene

    // Camera
    const camera = new THREE.OrthographicCamera(
      0, width, 0, height, 0.1, 1000
    )
    camera.position.z = 10

    // Renderer
    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true
    })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
    scene.add(ambientLight)

    const pointLight = new THREE.PointLight(0xffffff, 0.8)
    pointLight.position.set(width / 2, height / 2, 100)
    scene.add(pointLight)

    // Initialize physics
    physicsRef.current = new BubblePhysics(width, height, config)

    // Animation loop
    let animationId
    const animate = () => {
      animationId = requestAnimationFrame(animate)

      // Update bubble meshes based on physics
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
    }
  }, [])

  // Update physics when garments change
  useEffect(() => {
    if (physicsRef.current && garments) {
      physicsRef.current.updateGarments(garments)
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

      // Main bubble
      if (!bubbleMeshesRef.current.has(mainId)) {
        const mesh = createBubbleMesh(
          bubble.main.circleRadius,
          bubble.main.plugin.garmentData
        )
        bubbleMeshesRef.current.set(mainId, mesh)
        sceneRef.current.add(mesh)
      }

      const mainMesh = bubbleMeshesRef.current.get(mainId)
      mainMesh.position.x = bubble.main.position.x
      mainMesh.position.y = window.innerHeight - bubble.main.position.y

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
      })
    })

    // Remove meshes for bubbles that no longer exist
    for (const [id, mesh] of bubbleMeshesRef.current.entries()) {
      if (!currentMeshIds.has(id)) {
        sceneRef.current.remove(mesh)
        mesh.geometry.dispose()
        mesh.material.dispose()
        bubbleMeshesRef.current.delete(id)
      }
    }
  }

  const createBubbleMesh = (radius, garmentData) => {
    const geometry = new THREE.CircleGeometry(radius, 64)

    // Create gradient material
    const canvas = document.createElement('canvas')
    canvas.width = 256
    canvas.height = 256
    const ctx = canvas.getContext('2d')

    // Radial gradient
    const gradient = ctx.createRadialGradient(128, 128, 0, 128, 128, 128)
    const color = garmentData.color
    gradient.addColorStop(0, `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.9)`)
    gradient.addColorStop(0.5, `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.7)`)
    gradient.addColorStop(1, `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.3)`)

    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, 256, 256)

    const texture = new THREE.CanvasTexture(canvas)
    const material = new THREE.MeshBasicMaterial({
      map: texture,
      transparent: true,
      opacity: 0.9
    })

    const mesh = new THREE.Mesh(geometry, material)

    // Add glow effect
    const glowGeometry = new THREE.CircleGeometry(radius * 1.2, 64)
    const glowMaterial = new THREE.MeshBasicMaterial({
      color: new THREE.Color(color[0] / 255, color[1] / 255, color[2] / 255),
      transparent: true,
      opacity: 0.2
    })
    const glow = new THREE.Mesh(glowGeometry, glowMaterial)
    glow.position.z = -0.1
    mesh.add(glow)

    // Add category label sprite
    const label = createTextSprite(garmentData.category, 20)
    label.position.y = 0
    label.position.z = 1
    mesh.add(label)

    return mesh
  }

  const createSatelliteBubbleMesh = (radius, similarItem) => {
    const geometry = new THREE.CircleGeometry(radius, 32)

    // Soft gradient for satellites
    const material = new THREE.MeshBasicMaterial({
      color: 0x4a9eff,
      transparent: true,
      opacity: 0.6
    })

    const mesh = new THREE.Mesh(geometry, material)

    // Add small glow
    const glowGeometry = new THREE.CircleGeometry(radius * 1.3, 32)
    const glowMaterial = new THREE.MeshBasicMaterial({
      color: 0x6bb6ff,
      transparent: true,
      opacity: 0.15
    })
    const glow = new THREE.Mesh(glowGeometry, glowMaterial)
    glow.position.z = -0.1
    mesh.add(glow)

    return mesh
  }

  const createTextSprite = (text, fontSize = 20) => {
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    canvas.width = 256
    canvas.height = 64

    ctx.font = `bold ${fontSize}px Arial`
    ctx.fillStyle = 'white'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(text.toUpperCase(), 128, 32)

    const texture = new THREE.CanvasTexture(canvas)
    const material = new THREE.SpriteMaterial({ map: texture })
    const sprite = new THREE.Sprite(material)
    sprite.scale.set(100, 25, 1)

    return sprite
  }

  return <canvas ref={canvasRef} className="bubble-canvas" />
}
