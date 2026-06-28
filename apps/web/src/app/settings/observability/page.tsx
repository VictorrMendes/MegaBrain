"use client"

import { useState } from "react"
import { Activity, Clock, ShieldAlert, CheckCircle2, AlertTriangle, Zap, ServerCrash } from "lucide-react"

const MOCK_LOGS = [
  { id: 1, type: "sync_success", provider: "Google Workspace", message: "Successfully synced calendar events", time: "2 mins ago", latency: "340ms" },
  { id: 2, type: "capability_exec", provider: "Google Workspace", message: "Executed calendar.list_events", time: "15 mins ago", latency: "210ms" },
  { id: 3, type: "oauth_refresh", provider: "Google Workspace", message: "Token refreshed automatically", time: "1 hour ago", latency: "150ms" },
  { id: 4, type: "sync_error", provider: "Weather", message: "API Rate limit exceeded", time: "2 hours ago", latency: "800ms" },
]

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
        <div className="rounded-xl border border-white/10 bg-black/20 p-5">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="h-4 w-4 text-emerald-500" />
            <h3 className="text-sm font-medium text-white">System Health</h3>
          </div>
          <p className="text-2xl font-semibold text-white">99.9%</p>
          <p className="text-xs text-white/40 mt-1">Uptime last 30 days</p>
        </div>
        
        <div className="rounded-xl border border-white/10 bg-black/20 p-5">
          <div className="flex items-center gap-2 mb-2">
            <ShieldAlert className="h-4 w-4 text-amber-500" />
            <h3 className="text-sm font-medium text-white">OAuth Refresh Errors</h3>
          </div>
          <p className="text-2xl font-semibold text-white">0</p>
          <p className="text-xs text-white/40 mt-1">In the last 24 hours</p>
        </div>
        
        <div className="rounded-xl border border-white/10 bg-black/20 p-5">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="h-4 w-4 text-blue-500" />
            <h3 className="text-sm font-medium text-white">Avg. API Latency</h3>
          </div>
          <p className="text-2xl font-semibold text-white">215ms</p>
          <p className="text-xs text-white/40 mt-1">Across all integrations</p>
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
          
          <div className="divide-y divide-white/5">
            {MOCK_LOGS.filter(l => filter === "all" || l.type.includes("error")).map(log => (
              <div key={log.id} className="p-4 flex items-start justify-between hover:bg-white/5 transition-colors">
                <div className="flex items-start gap-3">
                  {log.type.includes("error") ? (
                    <ServerCrash className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
                  ) : log.type.includes("success") ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" />
                  ) : (
                    <Activity className="h-5 w-5 text-blue-500 shrink-0 mt-0.5" />
                  )}
                  
                  <div>
                    <p className="text-sm font-medium text-white/90">{log.message}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs font-medium text-white/50">{log.provider}</span>
                      <span className="text-xs text-white/40 border border-white/10 rounded px-1.5 py-0.5">{log.type}</span>
                    </div>
                  </div>
                </div>
                
                <div className="text-right shrink-0">
                  <div className="flex items-center gap-1.5 text-xs text-white/40 justify-end">
                    <Clock className="h-3 w-3" /> {log.time}
                  </div>
                  <div className="text-xs text-white/30 mt-1 font-mono">{log.latency}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
