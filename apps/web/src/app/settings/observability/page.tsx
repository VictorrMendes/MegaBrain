"use client"

import { useState, useEffect } from "react"
import { Activity, Clock, ShieldAlert, CheckCircle2, AlertTriangle, Zap, ServerCrash } from "lucide-react"

interface Metrics {
  system_health: string;
  oauth_refresh_errors: number;
  avg_api_latency: number;
}

interface LogEntry {
  event: string;
  level: string;
  timestamp: string;
  [key: string]: any;
}

export default function ObservabilityPage() {
  const [filter, setFilter] = useState("all")
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [logs, setLogs] = useState<LogEntry[]>([])
  
  useEffect(() => {
    // Fetch metrics
    const fetchMetrics = async () => {
      try {
        const res = await fetch("/api/observability/metrics")
        if (res.ok) {
          const data = await res.json()
          setMetrics(data)
        }
      } catch (err) {
        console.error("Failed to fetch metrics", err)
      }
    }
    
    fetchMetrics()
    const interval = setInterval(fetchMetrics, 30000)
    
    return () => clearInterval(interval)
  }, [])
  
  useEffect(() => {
    // Connect SSE for logs (replaces WebSocket to avoid proxy issues)
    const eventSource = new EventSource("/api/observability/logs/stream")
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as LogEntry
        setLogs(prev => {
          // Keep only last 100 logs to prevent memory leaks
          const newLogs = [data, ...prev]
          return newLogs.slice(0, 100)
        })
      } catch (e) {
        console.error("Error parsing log", e)
      }
    }
    
    return () => {
      eventSource.close()
    }
  }, [])

  const filteredLogs = logs.filter(log => {
    if (filter === "errors") {
      return log.level === "error" || log.level === "warning" || log.level === "warn"
    }
    return true
  })
  
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Observability</h1>
        <p className="text-white/60 text-sm mt-1">
          Monitor system health, integration logs, and cognitive orchestrator events.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl border border-white/10 bg-black/20 p-5 opacity-90">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="h-4 w-4 text-emerald-500" />
            <h3 className="text-sm font-medium text-white">System Health</h3>
          </div>
          <p className="text-2xl font-semibold text-white">
            {metrics ? (metrics.system_health === "healthy" ? "Healthy" : "Degraded") : "--"}
          </p>
          <p className="text-xs text-white/40 mt-1">Core services status</p>
        </div>
        
        <div className="rounded-xl border border-white/10 bg-black/20 p-5 opacity-90">
          <div className="flex items-center gap-2 mb-2">
            <ShieldAlert className="h-4 w-4 text-amber-500" />
            <h3 className="text-sm font-medium text-white">OAuth Refresh Errors</h3>
          </div>
          <p className="text-2xl font-semibold text-white">{metrics ? metrics.oauth_refresh_errors : "--"}</p>
          <p className="text-xs text-white/40 mt-1">Accounts requiring re-auth</p>
        </div>
        
        <div className="rounded-xl border border-white/10 bg-black/20 p-5 opacity-90">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="h-4 w-4 text-blue-500" />
            <h3 className="text-sm font-medium text-white">Avg. API Latency</h3>
          </div>
          <p className="text-2xl font-semibold text-white">{metrics ? `${metrics.avg_api_latency.toFixed(1)}ms` : "--"}</p>
          <p className="text-xs text-white/40 mt-1">Execution phase average</p>
        </div>
      </div>

      <div className="space-y-4 pt-4">
        <h2 className="text-lg font-medium text-white flex items-center gap-2">
          Integration Logs
        </h2>
        
        <div className="rounded-xl border border-white/10 bg-black/40 flex flex-col overflow-hidden h-[500px]">
          <div className="flex items-center gap-4 border-b border-white/10 p-3 bg-white/5 shrink-0">
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
          
          <div className="p-4 flex-1 overflow-y-auto font-mono text-xs">
            {filteredLogs.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center opacity-50">
                <Activity className="h-8 w-8 text-white mb-4 animate-pulse" />
                <p className="text-sm text-white font-medium">Listening for events...</p>
                <p className="text-xs text-white/50 mt-2">Logs will appear here as integrations execute.</p>
              </div>
            ) : (
              <div className="space-y-1">
                {filteredLogs.map((log, i) => (
                  <div key={i} className="flex items-start gap-3 py-1 border-b border-white/5 last:border-0 hover:bg-white/5 px-2 -mx-2 rounded transition-colors break-all">
                    <span className="text-white/40 whitespace-nowrap shrink-0">
                      {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : "--:--:--"}
                    </span>
                    <span className={`uppercase font-bold w-12 shrink-0 ${
                      log.level === "error" ? "text-red-400" :
                      log.level === "warning" || log.level === "warn" ? "text-amber-400" :
                      log.level === "info" ? "text-blue-400" : "text-white/50"
                    }`}>
                      {log.level || "INFO"}
                    </span>
                    <span className="text-white/90 font-medium">
                      {log.event}
                    </span>
                    {Object.keys(log).filter(k => !["event", "level", "timestamp"].includes(k)).length > 0 && (
                      <span className="text-white/40">
                        {JSON.stringify(Object.fromEntries(
                          Object.entries(log).filter(([k]) => !["event", "level", "timestamp"].includes(k))
                        ))}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
