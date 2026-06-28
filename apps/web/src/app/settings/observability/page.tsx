"use client"

import { useState } from "react"
import { Activity, Clock, ShieldAlert, CheckCircle2, AlertTriangle, Zap, ServerCrash } from "lucide-react"

export default function ObservabilityPage() {
  const [filter, setFilter] = useState("all")
  
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Observability</h1>
        <p className="text-white/60 text-sm mt-1">
          Monitor system health, integration logs, and cognitive orchestrator events.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl border border-white/10 bg-black/20 p-5 opacity-50">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="h-4 w-4 text-emerald-500" />
            <h3 className="text-sm font-medium text-white">System Health</h3>
          </div>
          <p className="text-2xl font-semibold text-white">--</p>
          <p className="text-xs text-white/40 mt-1">Metric not implemented</p>
        </div>
        
        <div className="rounded-xl border border-white/10 bg-black/20 p-5 opacity-50">
          <div className="flex items-center gap-2 mb-2">
            <ShieldAlert className="h-4 w-4 text-amber-500" />
            <h3 className="text-sm font-medium text-white">OAuth Refresh Errors</h3>
          </div>
          <p className="text-2xl font-semibold text-white">--</p>
          <p className="text-xs text-white/40 mt-1">Metric not implemented</p>
        </div>
        
        <div className="rounded-xl border border-white/10 bg-black/20 p-5 opacity-50">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="h-4 w-4 text-blue-500" />
            <h3 className="text-sm font-medium text-white">Avg. API Latency</h3>
          </div>
          <p className="text-2xl font-semibold text-white">--</p>
          <p className="text-xs text-white/40 mt-1">Metric not implemented</p>
        </div>
      </div>

      <div className="space-y-4 pt-4">
        <h2 className="text-lg font-medium text-white flex items-center gap-2">
          Integration Logs
        </h2>
        
        <div className="rounded-xl border border-white/10 bg-black/40 overflow-hidden">
          <div className="flex items-center gap-4 border-b border-white/10 p-3 bg-white/5">
            <button 
              onClick={() => setFilter("all")}
              className={`text-xs px-3 py-1.5 rounded-md transition-colors ${filter === "all" ? "bg-white/10 text-white" : "text-white/50 hover:text-white"}`}
            >
              All Events
            </button>
            <button 
              onClick={() => setFilter("errors")}
              className={`text-xs px-3 py-1.5 rounded-md transition-colors ${filter === "errors" ? "bg-white/10 text-white" : "text-white/50 hover:text-white"}`}
            >
              Errors & Warnings
            </button>
          </div>
          
          <div className="p-12 flex flex-col items-center justify-center text-center">
             <AlertTriangle className="h-8 w-8 text-amber-500 mb-4 opacity-70" />
             <p className="text-sm text-white/80 font-medium">Log streaming not implemented</p>
             <p className="text-xs text-white/50 mt-2">Backend telemetry events are not yet connected to this interface.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
