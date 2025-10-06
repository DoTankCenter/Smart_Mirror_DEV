import Matter from 'matter-js'

export default class BubblePhysics {
  constructor(width, height, config = {}) {
    // Create engine
    this.engine = Matter.Engine.create()
    this.world = this.engine.world

    this.width = width
    this.height = height

    // Configure physics
    this.engine.gravity.y = config.gravity || 0.3

    // Store bubble bodies
    this.bubbles = new Map() // garmentId -> { main: body, satellites: [bodies] }

    // Configuration
    this.config = {
      restitution: config.restitution || 0.8,
      friction: config.friction || 0.01,
      mainBubbleSize: config.mainBubbleSize || 80,
      satelliteBubbleSize: config.satelliteBubbleSize || 30,
      ...config
    }

    // Add boundaries (invisible walls)
    this.addBoundaries()

    // Start engine
    this.runner = Matter.Runner.create()
    Matter.Runner.run(this.runner, this.engine)
  }

  addBoundaries() {
    const thickness = 50
    const options = { isStatic: true, friction: 0, restitution: 0.9 }

    const boundaries = [
      // Top
      Matter.Bodies.rectangle(this.width / 2, -thickness / 2, this.width, thickness, options),
      // Bottom
      Matter.Bodies.rectangle(this.width / 2, this.height + thickness / 2, this.width, thickness, options),
      // Left
      Matter.Bodies.rectangle(-thickness / 2, this.height / 2, thickness, this.height, options),
      // Right
      Matter.Bodies.rectangle(this.width + thickness / 2, this.height / 2, thickness, this.height, options)
    ]

    Matter.Composite.add(this.world, boundaries)
  }

  updateGarments(garments) {
    const currentIds = new Set(garments.map(g => g.garment_id))

    // Remove bubbles for garments that no longer exist
    for (const [id, bubble] of this.bubbles.entries()) {
      if (!currentIds.has(id)) {
        this.removeBubble(id)
      }
    }

    // Add or update bubbles for each garment
    garments.forEach(garment => {
      if (this.bubbles.has(garment.garment_id)) {
        this.updateBubble(garment)
      } else {
        this.createBubble(garment)
      }
    })
  }

  createBubble(garment) {
    const personOffset = garment.person_id * 200

    // Create main bubble (represents the detected garment)
    const mainBubble = Matter.Bodies.circle(
      Math.random() * this.width * 0.6 + this.width * 0.2 + personOffset,
      Math.random() * 100 + 50,
      this.config.mainBubbleSize,
      {
        restitution: this.config.restitution,
        friction: this.config.friction,
        density: 0.001,
        collisionFilter: {
          group: -garment.person_id, // Same person's bubbles don't collide
          category: 0x0001,
          mask: 0xFFFF
        },
        render: {
          fillStyle: `rgb(${garment.color[0]}, ${garment.color[1]}, ${garment.color[2]})`
        },
        plugin: {
          garmentData: garment
        }
      }
    )

    // Create satellite bubbles (similar items from library)
    const satellites = []
    const satelliteCount = Math.min(garment.similar_items?.length || 0, this.config.bubbleCount || 5)

    for (let i = 0; i < satelliteCount; i++) {
      const angle = (i / satelliteCount) * Math.PI * 2
      const distance = this.config.mainBubbleSize + this.config.satelliteBubbleSize + 20

      const satellite = Matter.Bodies.circle(
        mainBubble.position.x + Math.cos(angle) * distance,
        mainBubble.position.y + Math.sin(angle) * distance,
        this.config.satelliteBubbleSize,
        {
          restitution: this.config.restitution,
          friction: this.config.friction,
          density: 0.0005,
          collisionFilter: {
            group: -garment.person_id,
            category: 0x0002,
            mask: 0xFFFF
          },
          plugin: {
            similarItem: garment.similar_items[i],
            parentId: garment.garment_id
          }
        }
      )

      // Create constraint (spring) connecting satellite to main bubble
      const constraint = Matter.Constraint.create({
        bodyA: mainBubble,
        bodyB: satellite,
        length: distance,
        stiffness: 0.01,
        damping: 0.05
      })

      Matter.Composite.add(this.world, constraint)
      satellites.push({ body: satellite, constraint })
    }

    Matter.Composite.add(this.world, [mainBubble, ...satellites.map(s => s.body)])

    this.bubbles.set(garment.garment_id, {
      main: mainBubble,
      satellites
    })
  }

  updateBubble(garment) {
    const bubble = this.bubbles.get(garment.garment_id)
    if (!bubble) return

    // Update garment data
    bubble.main.plugin.garmentData = garment

    // Update similar items if changed
    if (garment.similar_items && garment.similar_items.length > 0) {
      const currentSatelliteCount = bubble.satellites.length
      const newSatelliteCount = Math.min(garment.similar_items.length, this.config.bubbleCount || 5)

      // Update existing satellites
      bubble.satellites.forEach((sat, i) => {
        if (i < newSatelliteCount) {
          sat.body.plugin.similarItem = garment.similar_items[i]
        }
      })
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

  getBubbles() {
    return this.bubbles
  }

  updateConfig(newConfig) {
    this.config = { ...this.config, ...newConfig }

    if (newConfig.gravity !== undefined) {
      this.engine.gravity.y = newConfig.gravity
    }

    // Update existing bubbles if necessary
    for (const bubble of this.bubbles.values()) {
      if (newConfig.restitution !== undefined) {
        bubble.main.restitution = newConfig.restitution
        bubble.satellites.forEach(sat => {
          sat.body.restitution = newConfig.restitution
        })
      }
    }
  }

  destroy() {
    Matter.Runner.stop(this.runner)
    Matter.Engine.clear(this.engine)
  }
}
