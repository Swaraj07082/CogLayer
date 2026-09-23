import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  EDGE_PATHS,
  NODE_META,
  READ_STEPS,
  WRITE_STEPS,
  type EdgeId,
  type LearnStep,
  type NodeId,
  type PathKind,
} from './steps'
import './LearnPage.css'

type ArchitectureCanvasProps = {
  step: LearnStep
  path: PathKind
  packetKey: number
}

function edgeGeometry(x1: number, y1: number, x2: number, y2: number) {
  const dx = x2 - x1
  const dy = y2 - y1
  const len = Math.hypot(dx, dy) || 1
  const ux = dx / len
  const uy = dy / len
  // Pull tip back so the arrowhead sits before the node
  const tipX = x2 - ux * 1.8
  const tipY = y2 - uy * 1.8
  const baseX = tipX - ux * 2.2
  const baseY = tipY - uy * 2.2
  const px = -uy
  const py = ux
  const wing = 1.1
  return {
    line: { x1, y1, x2: baseX, y2: baseY },
    arrow: `${tipX},${tipY} ${baseX + px * wing},${baseY + py * wing} ${baseX - px * wing},${baseY - py * wing}`,
  }
}

function ArchitectureCanvas({ step, path, packetKey }: ArchitectureCanvasProps) {
  const activeNodeSet = useMemo(() => new Set(step.activeNodes), [step])
  const activeEdgeSet = useMemo(() => new Set(step.activeEdges), [step])

  const packetStyle = useMemo(() => {
    if (!step.packet) return undefined
    const from = NODE_META[step.packet.from]
    const to = NODE_META[step.packet.to]
    return {
      ['--pkt-x1' as string]: `${from.x}%`,
      ['--pkt-y1' as string]: `${from.y}%`,
      ['--pkt-x2' as string]: `${to.x}%`,
      ['--pkt-y2' as string]: `${to.y}%`,
    }
  }, [step.packet])

  return (
    <div className={`arch-canvas path-${path}`} aria-hidden>
      <div className="arch-grid" />
      <svg className="arch-edges" viewBox="0 0 100 70" preserveAspectRatio="none">
        {(Object.keys(EDGE_PATHS) as EdgeId[]).map((id) => {
          const e = EDGE_PATHS[id]
          const on = activeEdgeSet.has(id)
          const geo = edgeGeometry(e.x1, e.y1, e.x2, e.y2)
          return (
            <g key={id} className={on ? 'edge-group is-on' : 'edge-group'}>
              <line
                x1={geo.line.x1}
                y1={geo.line.y1}
                x2={geo.line.x2}
                y2={geo.line.y2}
                className={on ? 'edge edge-on' : 'edge'}
              />
              <polygon
                points={geo.arrow}
                className={on ? 'edge-arrow edge-arrow-on' : 'edge-arrow'}
              />
            </g>
          )
        })}
      </svg>

      {(Object.keys(NODE_META) as NodeId[]).map((id, i) => {
        const n = NODE_META[id]
        const on = activeNodeSet.has(id)
        const tilt = ((i % 3) - 1) * 0.9
        return (
          <div
            key={id}
            className={`arch-node kind-${n.kind}${on ? ' is-active' : ''}`}
            style={{
              left: `${n.x}%`,
              top: `${n.y}%`,
              ['--tilt' as string]: `${tilt}deg`,
            }}
          >
            <span className="arch-node-label">{n.label}</span>
            <span className="arch-node-sub">{n.sub}</span>
          </div>
        )
      })}

      {step.packet && (
        <div key={packetKey} className="arch-packet" style={packetStyle} />
      )}
    </div>
  )
}

function navigate(to: string) {
  window.history.pushState({}, '', to)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

export function LearnPage() {
  const [path, setPath] = useState<PathKind>('read')
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(true)
  const [packetKey, setPacketKey] = useState(0)
  const pathRef = useRef(path)

  const steps = path === 'read' ? READ_STEPS : WRITE_STEPS
  const step = steps[Math.min(index, steps.length - 1)] ?? steps[0]
  const lastIndex = steps.length - 1

  useEffect(() => {
    document.documentElement.dataset.learnPath = path
    if (pathRef.current !== path) {
      pathRef.current = path
      setIndex(0)
      setPacketKey((k) => k + 1)
    }
  }, [path])

  useEffect(() => {
    document.documentElement.classList.add('learn-lock')
    document.body.classList.add('learn-lock')
    return () => {
      document.documentElement.classList.remove('learn-lock')
      document.body.classList.remove('learn-lock')
    }
  }, [])

  useEffect(() => {
    setPacketKey((k) => k + 1)
  }, [index])

  useEffect(() => {
    if (!playing) return undefined
    const id = window.setInterval(() => {
      setIndex((i) => (i >= lastIndex ? i : i + 1))
    }, 2800)
    return () => window.clearInterval(id)
  }, [playing, lastIndex])

  useEffect(() => {
    if (!playing || index < lastIndex) return undefined
    const id = window.setTimeout(() => setPlaying(false), 2800)
    return () => window.clearTimeout(id)
  }, [playing, index, lastIndex])

  const goPrev = useCallback(() => {
    setPlaying(false)
    setIndex((i) => Math.max(i - 1, 0))
  }, [])

  const goNext = useCallback(() => {
    setPlaying(false)
    setIndex((i) => Math.min(i + 1, lastIndex))
  }, [lastIndex])

  const togglePlay = useCallback(() => {
    setPlaying((wasPlaying) => {
      if (wasPlaying) return false
      setIndex((i) => (i >= lastIndex ? 0 : i))
      return true
    })
  }, [lastIndex])

  const restart = useCallback(() => {
    setIndex(0)
    setPacketKey((k) => k + 1)
    setPlaying(true)
  }, [])

  const selectPath = useCallback((next: PathKind) => {
    setPath(next)
    setIndex(0)
    setPlaying(true)
    setPacketKey((k) => k + 1)
  }, [])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement | null)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA') return
      if (e.key === ' ') {
        e.preventDefault()
        togglePlay()
      } else if (e.key === 'ArrowRight') {
        e.preventDefault()
        goNext()
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        goPrev()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [togglePlay, goNext, goPrev])

  return (
    <div className="learn-page">
      <header className="learn-top">
        <div className="learn-brand-block">
          <p className="learn-kicker">CogLayer</p>
          <h1>Architecture lab</h1>
        </div>
        <div className="learn-top-actions">
          <div className="path-toggle" role="tablist" aria-label="Path">
            <button
              type="button"
              role="tab"
              aria-selected={path === 'read'}
              className={path === 'read' ? 'is-on' : ''}
              onClick={() => selectPath('read')}
            >
              Read
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={path === 'write'}
              className={path === 'write' ? 'is-on' : ''}
              onClick={() => selectPath('write')}
            >
              Write
            </button>
          </div>
          <div className="learn-controls">
            <button type="button" className="ctrl" onClick={goPrev} disabled={index <= 0}>
              Prev
            </button>
            <button type="button" className="ctrl ctrl-primary" onClick={togglePlay}>
              {playing ? 'Pause' : 'Play'}
            </button>
            <button
              type="button"
              className="ctrl"
              onClick={goNext}
              disabled={index >= lastIndex}
            >
              Next
            </button>
            <button type="button" className="ctrl" onClick={restart}>
              Restart
            </button>
          </div>
          <button type="button" className="learn-link" onClick={() => navigate('/')}>
            ← Chat
          </button>
        </div>
      </header>

      <div className="learn-stage">
        <ArchitectureCanvas step={step} path={path} packetKey={packetKey} />

        <aside className="learn-caption" aria-live="polite">
          <p className="step-index">
            Step {index + 1}/{steps.length} · {path === 'read' ? 'Read' : 'Write'}
          </p>
          <h2>{step.title}</h2>
          <p className="step-caption">{step.caption}</p>
          <p className="step-why">
            <strong>Why:</strong> {step.why}
          </p>
          <div className="step-dots" role="tablist" aria-label="Steps">
            {steps.map((s, i) => (
              <button
                key={s.id}
                type="button"
                role="tab"
                title={s.title}
                aria-label={`Step ${i + 1}: ${s.title}`}
                aria-selected={i === index}
                className={i === index ? 'step-dot is-current' : 'step-dot'}
                onClick={() => {
                  setPlaying(false)
                  setIndex(i)
                }}
              />
            ))}
          </div>
          <p className="learn-hint">Space play/pause · ← → step</p>
        </aside>
      </div>
    </div>
  )
}
