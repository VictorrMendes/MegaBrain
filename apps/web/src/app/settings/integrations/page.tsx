"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api"
import { useWorkspace } from "@/context/WorkspaceContext"
import { ToyBrick, Plus, Globe, Check, AlertCircle, ChevronRight, Activity, Zap, RefreshCw, Trash2, Settings2 } from "lucide-react"

export default function IntegrationsSettingsPage() {
  const { current: workspace } = useWorkspace()
  const [available, setAvailable] = useState<any[]>([])
  const [connected, setConnected] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (workspace) {
      fetchIntegrations(workspace.id)
    }
  }, [workspace?.id])

  const fetchIntegrations = async (wsId: string) => {
    try {
      const [avail, conn] = await Promise.all([
        api.listAvailableIntegrations(),
        api.listIntegrations(wsId).catch(() => [])
      ])
      setAvailable(avail)
      setConnected(conn)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleConnect = (slug: string) => {
    if (!workspace) return
    window.location.href = `/api/integrations/oauth/connect/${workspace.id}/${slug}`
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Connected Accounts</h1>
        <p className="text-white/60 text-sm mt-1">
          Manage integrations and connected external services.
        </p>
      </div>

      <div className="space-y-4">
        <h2 className="text-lg font-medium text-white flex items-center gap-2">
          <Globe className="h-5 w-5 text-white/50" />
          Active Connections
        </h2>

        {loading ? (
          <div className="text-sm text-white/50">Loading...</div>
        ) : connected.length === 0 ? (
          <div className="rounded-xl border border-dashed border-white/20 p-8 text-center">
            <ToyBrick className="mx-auto h-8 w-8 text-white/20 mb-3" />
            <p className="text-sm font-medium text-white/70">No connected accounts</p>
            <p className="text-xs text-white/40 mt-1">Connect a service below to grant the assistant new capabilities.</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {connected.map((conn) => (
              <div key={conn.id} className="rounded-xl border border-white/10 bg-black/40 p-5 transition-colors hover:bg-black/60">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/5 border border-white/10 text-xl font-bold">
                      {conn.icon || conn.slug.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <h3 className="font-medium text-white">{conn.name}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-500">
                          <Check className="h-3 w-3" /> Healthy
                        </span>
                        <span className="text-xs text-white/40">Last sync: 2m ago</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button className="rounded-md p-2 text-white/50 hover:bg-white/10 hover:text-white transition-colors" title="Sync Now">
                      <RefreshCw className="h-4 w-4" />
                    </button>
                    <button className="rounded-md p-2 text-white/50 hover:bg-white/10 hover:text-white transition-colors" title="Settings">
                      <Settings2 className="h-4 w-4" />
                    </button>
                    <button className="rounded-md p-2 text-white/50 hover:bg-red-500/10 hover:text-red-500 transition-colors" title="Disconnect">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="space-y-4 pt-6 border-t border-white/10">
        <h2 className="text-lg font-medium text-white flex items-center gap-2">
          <Plus className="h-5 w-5 text-white/50" />
          Available Services
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {available.filter(a => !connected.some(c => c.slug === a.slug)).map((provider) => (
            <div key={provider.slug} className="group rounded-xl border border-white/10 bg-black/20 p-5 transition-all hover:bg-white/5 hover:border-white/20">
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white/5 border border-white/10 text-lg font-bold group-hover:bg-white/10 transition-colors">
                  {provider.icon || provider.slug.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1">
                  <h3 className="font-medium text-white text-sm">{provider.name}</h3>
                  <p className="text-xs text-white/50 mt-1 line-clamp-2 leading-relaxed">
                    {provider.description}
                  </p>
                  
                  <div className="mt-4 flex items-center gap-2">
                    {provider.slug === 'google' ? (
                      <button 
                        onClick={() => handleConnect(provider.slug)}
                        className="flex items-center gap-1.5 rounded-md bg-white px-3 py-1.5 text-xs font-medium text-black hover:bg-white/90 transition-colors"
                      >
                        Connect via OAuth <ChevronRight className="h-3 w-3" />
                      </button>
                    ) : (
                      <button 
                        onClick={() => handleConnect(provider.slug)}
                        className="flex items-center gap-1.5 rounded-md bg-white/10 px-3 py-1.5 text-xs font-medium text-white hover:bg-white/20 transition-colors"
                      >
                        Configure <ChevronRight className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
