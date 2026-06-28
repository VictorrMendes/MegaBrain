"use client"

import { useEffect, useState } from "react"
import { Play, Brain, Check, ShieldAlert, Cpu, Bot, ArrowRight, Loader2, AlertTriangle, ChevronDown, ChevronRight, XCircle, FastForward } from "lucide-react"

interface TraceEvent {
  trace_id: string
  workspace_id: string
  timestamp: string
  engine: string
  stage: string
  status: string
  duration_ms: number
  metadata: Record<string, any>
}

// Group events by trace_id
interface TraceGroup {
  trace_id: string
  started_at: string
  completed_at?: string
  status: string // 'running', 'completed', 'failed'
  events: TraceEvent[]
}

const ENGINE_ICONS: Record<string, React.ReactNode> = {
  Orchestrator: <Brain className="w-4 h-4 text-purple-400" />,
  ContextBuilder: <Cpu className="w-4 h-4 text-blue-400" />,
  IntentRouter: <ArrowRight className="w-4 h-4 text-emerald-400" />,
  DecisionEngine: <ShieldAlert className="w-4 h-4 text-amber-400" />,
  CapabilityExecutor: <Bot className="w-4 h-4 text-cyan-400" />,
  LLMProvider: <Brain className="w-4 h-4 text-pink-400" />,
  LearningEngine: <Check className="w-4 h-4 text-green-400" />,
}

const STATUS_ICONS: Record<string, React.ReactNode> = {
  running: <Loader2 className="w-4 h-4 animate-spin text-blue-400" />,
  completed: <Check className="w-4 h-4 text-emerald-400" />,
  failed: <XCircle className="w-4 h-4 text-red-400" />,
  skipped: <FastForward className="w-4 h-4 text-zinc-400" />
}

export default function RuntimePage() {
  const [traces, setTraces] = useState<TraceGroup[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // 1. Fetch history
    fetch('/api/runtime/history?limit=300')
      .then(res => res.json())
      .then((historyEvents: TraceEvent[]) => {
        // Group by trace
        const groups = new Map<string, TraceGroup>()
        
        historyEvents.forEach(evt => {
          if (!groups.has(evt.trace_id)) {
            groups.set(evt.trace_id, {
              trace_id: evt.trace_id,
              started_at: evt.timestamp,
              status: evt.stage === "trace.completed" ? "completed" : evt.stage === "trace.failed" ? "failed" : "running",
              events: []
            })
          }
          const group = groups.get(evt.trace_id)!
          group.events.push(evt)
          if (evt.stage === "trace.completed") {
            group.status = "completed"
            group.completed_at = evt.timestamp
          } else if (evt.stage === "trace.failed") {
            group.status = "failed"
            group.completed_at = evt.timestamp
          }
        })
        
        setTraces(Array.from(groups.values()).reverse()) // Newest first
        setIsLoading(false)
      })
      .catch(err => {
        console.error("Failed to load trace history", err)
        setIsLoading(false)
      })

    // 2. Connect SSE
    const evtSource = new EventSource('/api/runtime/stream')
    
    evtSource.onmessage = (e) => {
      const evt: TraceEvent = JSON.parse(e.data)
      setTraces(prev => {
        const newTraces = [...prev]
        const existingIdx = newTraces.findIndex(t => t.trace_id === evt.trace_id)
        
        if (existingIdx >= 0) {
          // Update existing group
          const group = { ...newTraces[existingIdx], events: [...newTraces[existingIdx].events, evt] }
          if (evt.stage === "trace.completed") {
            group.status = "completed"
            group.completed_at = evt.timestamp
          } else if (evt.stage === "trace.failed") {
            group.status = "failed"
            group.completed_at = evt.timestamp
          }
          newTraces[existingIdx] = group
        } else {
          // New group (prepend)
          newTraces.unshift({
            trace_id: evt.trace_id,
            started_at: evt.timestamp,
            status: "running",
            events: [evt]
          })
        }
        
        // Keep only last 100 traces
        return newTraces.slice(0, 100)
      })
    }

    return () => evtSource.close()
  }, [])

  return (
    <div className="space-y-8 pb-20">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Runtime</h1>
        <p className="text-white/60 text-sm mt-1">
          Monitor the live execution of the Cognitive Orchestrator.
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-[400px]">
          <Loader2 className="w-8 h-8 animate-spin text-white/20" />
        </div>
      ) : traces.length === 0 ? (
        <div className="rounded-xl border border-white/10 bg-black/40 p-12 flex flex-col items-center justify-center text-center h-[400px]">
           <Brain className="h-8 w-8 text-white/20 mb-4" />
           <p className="text-sm text-white/80 font-medium">No executions yet</p>
           <p className="text-xs text-white/50 mt-2 max-w-sm">Interact with Khonshu to see the real-time cognitive trace.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {traces.map(trace => (
            <TraceBlock key={trace.trace_id} trace={trace} />
          ))}
        </div>
      )}
    </div>
  )
}

function TraceBlock({ trace }: { trace: TraceGroup }) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div className="rounded-xl border border-white/10 bg-zinc-900/50 overflow-hidden">
      {/* Header */}
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          {expanded ? <ChevronDown className="w-4 h-4 text-white/40" /> : <ChevronRight className="w-4 h-4 text-white/40" />}
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-white">Execution Trace</span>
              <span className="text-xs font-mono text-white/40">{trace.trace_id.split("-")[0]}</span>
            </div>
            <div className="text-xs text-white/50 mt-0.5">
              {new Date(trace.started_at).toISOString().split('T')[1].replace('Z', '')}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {trace.status === "running" && <Loader2 className="w-4 h-4 animate-spin text-blue-400" />}
          {trace.status === "completed" && <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Completed</span>}
          {trace.status === "failed" && <span className="text-xs px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20">Failed</span>}
        </div>
      </button>

      {/* Body */}
      {expanded && (
        <div className="p-4 border-t border-white/5 bg-black/20">
          <div className="space-y-3 pl-6 border-l border-white/10 ml-2">
            {trace.events.filter(e => e.stage.startsWith("step.")).map((step, idx) => (
              <StepBlock key={idx} step={step} />
            ))}
            {trace.events.filter(e => e.stage.startsWith("step.")).length === 0 && (
              <div className="text-xs text-white/40 italic">Waiting for steps...</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function StepBlock({ step }: { step: TraceEvent }) {
  const [showMetadata, setShowMetadata] = useState(false)
  const isStarted = step.stage === "step.started"
  const isCompleted = step.stage === "step.completed"
  
  // We'll render step.completed and step.failed with timings. step.started is just indicative.
  // Actually, to make it like DevTools, we should just show the step events chronologically.

  return (
    <div className="relative">
      {/* Connector dot */}
      <div className="absolute -left-[29px] top-1.5">
        <div className="bg-zinc-900 border border-white/20 rounded-full w-2 h-2" />
      </div>
      
      <div className="flex items-start gap-3">
        <div className="mt-0.5">
           {STATUS_ICONS[step.status] || <Brain className="w-4 h-4 text-white/40" />}
        </div>
        
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-white/90">{step.engine}</span>
            <span className="text-xs text-white/40 font-mono">({step.stage})</span>
            {step.duration_ms > 0 && (
              <span className="text-xs font-mono text-emerald-400/80 bg-emerald-500/10 px-1.5 py-0.5 rounded ml-auto">
                {step.duration_ms.toFixed(0)}ms
              </span>
            )}
          </div>
          
          {Object.keys(step.metadata).length > 0 && (
            <div className="mt-2">
              <button 
                onClick={() => setShowMetadata(!showMetadata)}
                className="text-xs flex items-center gap-1 text-white/50 hover:text-white/80 transition-colors"
              >
                {showMetadata ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                {showMetadata ? "Hide details" : "Show details"}
              </button>
              
              {showMetadata && (
                <div className="mt-2 p-3 rounded-lg bg-black/40 border border-white/5 overflow-x-auto">
                  <pre className="text-[10px] font-mono text-white/70">
                    {JSON.stringify(step.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
