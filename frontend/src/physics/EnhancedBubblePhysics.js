import Matter from 'matter-js'

export default class EnhancedBubblePhysics {
  constructor(width, height, config = {}) {
    this.engine = Matter.Engine.create()
    this.world = this.engine.world

    this.width = width
    this.height = height

    // Configure physics
    this.engine.gravity.y = config.gravity || 0.3

    // Bubble storage with fade states
    this.bubbles = new Map() // garmentId -> { main, satellites, fadeState, age }

    // Configuration
    this.config = {
      restitution: config.restitution || 0.8,
      friction: config.friction || 0.01,
      mainBubbleSize: config.mainBubbleSize || 80,
      satelliteBubbleSize: config.satelliteBubbleSize || 30,
      spawnDuration: 20, // frames to fade in
      fadeDuration: 15,  // frames to fade out
      maxVelocity: 15,   // clamp velocity to prevent chaos
      ...config
    }

    // Spawn/fade tracking
    this.pendingGarments = new Map() // garmentId -> frame_count

    this.addBoundaries()

    // Start engine with fixed timestep for stability
    this.runner = Matter.Runner.create({
      isFixed: true,
      delta: 1000 / 60 // 60 FPS
    })
    Matter.Runner.run(this.runner, this.engine)
  }

  addBoundaries() {
    const thickness = 50
    const options = { isStatic: true, friction: 0, restitution: 0.9 }

    const boundaries = [
      Matter.Bodies.rectangle(this.width / 2, -thickness / 2, this.width, thickness, options),
      Matter.Bodies.rectangle(this.width / 2, this.height + thickness / 2, this.width, thickness, options),
      Matter.Bodies.rectangle(-thickness / 2, this.height / 2, thickness, this.height, options),
      Matter.Bodies.rectangle(this.width + thickness / 2, this.height / 2, thickness, this.height, options)
    ]

    Matter.Composite.add(this.world, boundaries)
  }

  updateGarments(garments) {
    const currentIds = new Set(garments.map(g => g.garment_id))

    // Update pending garments (spawn stability check)
    for (const garment of garments) {
      const id = garment.garment_id

      if (!this.bubbles.has(id)) {
        // New garment - add to pending
        if (!this.pendingGarments.has(id)) {
          this.pendingGarments.set(id, { count: 1, data: garment })
        } else {
          const pending = this.pendingGarments.get(id)
          pending.count++
          pending.data = garment

          // Spawn after stability threshold
          if (pending.count >= 3) {
            this.createBubble(garment)
            this.pendingGarments.delete(id)
          }
        }
      } else {
        // Existing bubble - update data
        this.updateBubble(garment)
        this.bubbles.get(id).age++
      }
    }

    // Mark missing bubbles for fade-out
    for (const [id, bubble] of this.bubbles.entries()) {
      if (!currentIds.has(id)) {
        if (bubble.fadeState === 'visible') {
          bubble.fadeState = 'fading_out'
          bubble.fadeProgress = 0
        }
      }
    }

    // Update fade states and remove fully faded
    this.updateFadeStates()

    // Clamp velocities to prevent chaos
    this.clampVelocities()

    // Clean up old pending garments
    for (const [id, pending] of this.pendingGarments.entries()) {
      if (!currentIds.has(id)) {
        this.pendingGarments.delete(id)
      }
    }
  }

  createBubble(garment) {
    const personOffset = garment.person_id * 250

    // Spawn position with some randomness
    const spawnX = Math.random() * this.width * 0.6 + this.width * 0.2 + personOffset
    const spawnY = Math.random() * 150 + 100

    // Create main bubble
    const mainBubble = Matter.Bodies.circle(
      spawnX,
      spawnY,
      this.config.mainBubbleSize,
      {
        restitution: this.config.restitution,
        friction: this.config.friction,
        density: 0.001,
        frictionAir: 0.02, // Air resistance for smoother motion
        collisionFilter: {
          group: -(garment.person_id + 1), // Negative group = same group doesn't collide
          category: 0x0001,
          mask: 0xFFFF
        },
        plugin: {
          garmentData: garment,
          bubbleType: 'main'
        }
      }
    )

    // Create satellite bubbles
    const satellites = []
    const satelliteCount = Math.min(garment.similar_items?.length || 0, this.config.bubbleCount || 5)

    for (let i = 0; i < satelliteCount; i++) {
      const angle = (i / satelliteCount) * Math.PI * 2
      const distance = this.config.mainBubbleSize + this.config.satelliteBubbleSize + 30

      const satellite = Matter.Bodies.circle(
        spawnX + Math.cos(angle) * distance,
        spawnY + Math.sin(angle) * distance,
        this.config.satelliteBubbleSize,
        {
          restitution: this.config.restitution,
          friction: this.config.friction,
          density: 0.0005,
          frictionAir: 0.02,
          collisionFilter: {
            group: -(garment.person_id + 1),
            category: 0x0002,
            mask: 0xFFFF
          },
          plugin: {
            similarItem: garment.similar_items[i],
            parentId: garment.garment_id,
            bubbleType: 'satellite'
          }
        }
      )

      // Spring constraint
      const constraint = Matter.Constraint.create({
        bodyA: mainBubble,
        bodyB: satellite,
        length: distance,
        stiffness: 0.008,
        damping: 0.1
      })

      Matter.Composite.add(this.world, constraint)
      satellites.push({ body: satellite, constraint })
    }

    Matter.Composite.add(this.world, [mainBubble, ...satellites.map(s => s.body)])

    this.bubbles.set(garment.garment_id, {
      main: mainBubble,
      satellites,
      fadeState: 'spawning',
      fadeProgress: 0,
      age: 0
    })
  }

  updateBubble(garment) {
    const bubble = this.bubbles.get(garment.garment_id)
    if (!bubble) return

    // Update garment data
    bubble.main.plugin.garmentData = garment

    // Update similar items if changed
    if (garment.similar_items && garment.similar_items.length > 0) {
      bubble.satellites.forEach((sat, i) => {
        if (i < garment.similar_items.length) {
          sat.body.plugin.similarItem = garment.similar_items[i]
        }
      })
    }
  }

  updateFadeStates() {
    const toRemove = []

    for (const [id, bubble] of this.bubbles.entries()) {
      if (bubble.fadeState === 'spawning') {
        bubble.fadeProgress++
        if (bubble.fadeProgress >= this.config.spawnDuration) {
          bubble.fadeState = 'visible'
        }
      } else if (bubble.fadeState === 'fading_out') {
        bubble.fadeProgress++
        if (bubble.fadeProgress >= this.config.fadeDuration) {
          toRemove.push(id)
        }
      }
    }

    // Remove fully faded bubbles
    for (const id of toRemove) {
      this.removeBubble(id)
    }
  }

  removeBubble(garmentId) {
    const bubble = this.bubbles.get(garmentId)
    if (!bubble) return

    // Remove constraints
    bubble.satellites.forEach(sat => {
      Matter.Composite.remove(this.world, sat.constraint)
    })

    // Remove bodies
    Matter.Composite.remove(this.world, bubble.main)
    bubble.satellites.forEach(sat => {
      Matter.Composite.remove(this.world, sat.body)
    })

    this.bubbles.delete(garmentId)
  }

  clampVelocities() {
    const maxVel = this.config.maxVelocity

    for (const bubble of this.bubbles.values()) {
      // Clamp main bubble
      const mainVel = bubble.main.velocity
      const mainSpeed = Math.sqrt(mainVel.x ** 2 + mainVel.y ** 2)

      if (mainSpeed > maxVel) {
        Matter.Body.setVelocity(bubble.main, {
          x: (mainVel.x / mainSpeed) * maxVel,
          y: (mainVel.y / mainSpeed) * maxVel
        })
      }

      // Clamp satellites
      bubble.satellites.forEach(sat => {
        const satVel = sat.body.velocity
        const satSpeed = Math.sqrt(satVel.x ** 2 + satVel.y ** 2)

        if (satSpeed > maxVel) {
          Matter.Body.setVelocity(sat.body, {
            x: (satVel.x / satSpeed) * maxVel,
            y: (satVel.y / satSpeed) * maxVel
          })
        }
      })
    }
  }

  getBubbles() {
    return this.bubbles
  }

  getFadeAlpha(bubble) {
    if (bubble.fadeState === 'spawning') {
      return bubble.fadeProgress / this.config.spawnDuration
    } else if (bubble.fadeState === 'fading_out') {
      return 1 - (bubble.fadeProgress / this.config.fadeDuration)
    }
    return 1.0
  }

  updateConfig(newConfig) {
    this.config = { ...this.config, ...newConfig }

    if (newConfig.gravity !== undefined) {
      this.engine.gravity.y = newConfig.gravity
    }

    // Update existing bubbles
    for (const bubble of this.bubbles.values()) {
      if (newConfig.restitution !== undefined) {
        bubble.main.restitution = newConfig.restitution
        bubble.satellites.forEach(sat => {
          sat.body.restitution = newConfig.restitution
        })
      }
      if (newConfig.friction !== undefined) {
        bubble.main.friction = newConfig.friction
        bubble.satellites.forEach(sat => {
          sat.body.friction = newConfig.friction
        })
      }
    }
  }

  destroy() {
    Matter.Runner.stop(this.runner)
    Matter.Engine.clear(this.engine)
  }
}
