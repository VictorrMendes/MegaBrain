"use client"

import { useState } from "react"
import { Play, Brain, Check, ShieldAlert, Cpu, Bot, ArrowRight, Loader2 } from "lucide-react"

export default function RuntimePage() {
  const [prompt, setPrompt] = useState("")
  const [simulating, setSimulating] = useState(false)
  const [result, setResult] = useState<any>(null)

  const handleSimulate = async () => {
    if (!prompt.trim()) return
    setSimulating(true)
    setResult(null)
    
    // Simulate delay
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    // Mock simulation result showing the orchestrator's capability plan
    setResult({
      intent: "Criar um evento no calendário",
      plan: [
        { 
          step: 1, 
          capability: "calendar.list_events", 
          mutability: "READ", 
          policy: "SILENT",
          reason: "Verificar a disponibilidade no horário desejado."
        },
        { 
          step: 2, 
          capability: "calendar.create_event", 
          mutability: "WRITE", 
          policy: "APPROVAL_REQUIRED",
          reason: "Criar a reunião com o cliente."
        }
      ]
    })
    
    setSimulating(false)
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Runtime & Cognitive Simulator</h1>
        <p className="text-white/60 text-sm mt-1">
          Test how the Cognitive Orchestrator maps natural language to integration capabilities and enforces security policies.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Simulator Input */}
        <div className="space-y-4">
          <h2 className="text-lg font-medium text-white flex items-center gap-2">
            <Bot className="h-5 w-5 text-white/50" />
            Simulate Instruction
          </h2>
          
          <div className="rounded-xl border border-white/10 bg-black/40 p-5 space-y-4">
            <div>
              <label className="block text-sm font-medium text-white/70 mb-2">User Prompt</label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Ex: Marca uma reunião amanhã às 14h com o time de design e cancela a de hoje..."
                className="w-full h-32 rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-white/30 focus:border-white/30 focus:outline-none focus:ring-1 focus:ring-white/30 resize-none transition-all"
              />
            </div>
            
            <button
              onClick={handleSimulate}
              disabled={simulating || !prompt.trim()}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-white px-4 py-2.5 text-sm font-medium text-black transition-colors hover:bg-white/90 disabled:opacity-50"
            >
              {simulating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {simulating ? "Simulating Orchestrator..." : "Run Cognitive Simulation"}
            </button>
          </div>
        </div>

        {/* Simulation Result */}
        <div className="space-y-4">
          <h2 className="text-lg font-medium text-white flex items-center gap-2">
            <Cpu className="h-5 w-5 text-white/50" />
            Execution Plan
          </h2>
          
          {simulating ? (
            <div className="rounded-xl border border-dashed border-white/20 p-12 flex flex-col items-center justify-center text-center h-[264px]">
              <Brain className="h-8 w-8 text-white/20 mb-4 animate-pulse" />
              <p className="text-sm text-white/50">Mapping intent to capabilities...</p>
            </div>
          ) : result ? (
            <div className="rounded-xl border border-white/10 bg-black/40 p-5 space-y-6">
              <div>
                <p className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-1">Detected Intent</p>
                <p className="text-sm text-white font-medium">{result.intent}</p>
              </div>
              
              <div className="space-y-3">
                <p className="text-xs font-semibold text-white/40 uppercase tracking-wider">Capability Resolution Plan</p>
                
                {result.plan.map((step: any, idx: number) => (
                  <div key={idx} className="relative rounded-lg border border-white/5 bg-white/5 p-4 flex gap-4">
                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/10 text-[10px] font-bold text-white">
                      {step.step}
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-mono text-white/90">{step.capability}</span>
                        {step.mutability === "READ" ? (
                          <span className="rounded bg-blue-500/20 px-1.5 py-0.5 text-[10px] font-medium text-blue-400">READ</span>
                        ) : step.mutability === "WRITE" ? (
                          <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-medium text-amber-400">WRITE</span>
                        ) : (
                          <span className="rounded bg-red-500/20 px-1.5 py-0.5 text-[10px] font-medium text-red-400">DELETE</span>
                        )}
                      </div>
                      <p className="text-xs text-white/50">{step.reason}</p>
                      
                      <div className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-black/50 border border-white/5 px-2.5 py-1">
                        {step.policy === "SILENT" ? (
                          <>
                            <Check className="h-3 w-3 text-emerald-500" />
                            <span className="text-[10px] font-medium text-white/70">Silent Execution</span>
                          </>
                        ) : (
                          <>
                            <ShieldAlert className="h-3 w-3 text-amber-500" />
                            <span className="text-[10px] font-medium text-white/70">User Approval Required</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-white/20 p-12 flex flex-col items-center justify-center text-center h-[264px]">
              <p className="text-sm text-white/50">Run a simulation to see the orchestrated capability plan.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
