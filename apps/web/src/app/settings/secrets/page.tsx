"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api"
import { Shield, Key, Check, Plus, Trash2 } from "lucide-react"

export default function SecretsPage() {
  const [providers, setProviders] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  const [newProvider, setNewProvider] = useState("")
  const [newClientId, setNewClientId] = useState("")
  const [newClientSecret, setNewClientSecret] = useState("")

  useEffect(() => {
    fetchProviders()
  }, [])

  const fetchProviders = async () => {
    try {
      const res = await api.get("/api/admin/secrets")
      setProviders(res.data.providers || [])
    } catch (error) {
      console.error("Failed to fetch secrets", error)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!newProvider || !newClientId || !newClientSecret) return

    try {
      await api.post("/api/admin/secrets", {
        provider: newProvider.toLowerCase(),
        payload: {
          client_id: newClientId,
          client_secret: newClientSecret
        }
      })
      
      setNewProvider("")
      setNewClientId("")
      setNewClientSecret("")
      fetchProviders()
    } catch (error) {
      console.error("Failed to save secret", error)
    }
  }

  const handleDelete = async (provider: string) => {
    try {
      await api.delete(`/api/admin/secrets/${provider}`)
      fetchProviders()
    } catch (error) {
      console.error("Failed to delete secret", error)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Secrets Vault</h1>
        <p className="text-white/60 text-sm mt-1">
          Manage OAuth credentials and API keys. Secrets are stored securely in the database encrypted by the Master Key.
        </p>
      </div>

      <div className="grid gap-6">
        <div className="rounded-xl border border-white/10 bg-black/40 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Plus className="h-5 w-5 text-white/80" />
            <h2 className="text-lg font-medium text-white">Add New Secret</h2>
          </div>
          
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <label className="text-xs font-medium text-white/70">Provider ID</label>
              <input 
                type="text" 
                placeholder="e.g. google"
                value={newProvider}
                onChange={e => setNewProvider(e.target.value)}
                className="w-full rounded-md border border-white/10 bg-black/50 px-3 py-2 text-sm text-white placeholder:text-white/30 focus:border-white/30 focus:outline-none"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-medium text-white/70">Client ID / Key</label>
              <input 
                type="text" 
                placeholder="Client ID"
                value={newClientId}
                onChange={e => setNewClientId(e.target.value)}
                className="w-full rounded-md border border-white/10 bg-black/50 px-3 py-2 text-sm text-white placeholder:text-white/30 focus:border-white/30 focus:outline-none"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-medium text-white/70">Client Secret</label>
              <input 
                type="password" 
                placeholder="Client Secret"
                value={newClientSecret}
                onChange={e => setNewClientSecret(e.target.value)}
                className="w-full rounded-md border border-white/10 bg-black/50 px-3 py-2 text-sm text-white placeholder:text-white/30 focus:border-white/30 focus:outline-none"
              />
            </div>
          </div>
          <div className="mt-4 flex justify-end">
            <button 
              onClick={handleSave}
              className="rounded-md bg-white px-4 py-2 text-sm font-medium text-black hover:bg-white/90 transition-colors"
            >
              Save Secret
            </button>
          </div>
        </div>

        <div className="space-y-3">
          <h2 className="text-lg font-medium text-white">Stored Secrets</h2>
          {loading ? (
            <div className="text-white/50 text-sm">Loading secrets...</div>
          ) : providers.length === 0 ? (
            <div className="rounded-xl border border-white/5 bg-white/5 p-8 text-center text-sm text-white/50">
              No secrets stored yet.
            </div>
          ) : (
            <div className="grid gap-3">
              {providers.map(provider => (
                <div key={provider} className="flex items-center justify-between rounded-xl border border-white/10 bg-black/20 p-4">
                  <div className="flex items-center gap-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10">
                      <Shield className="h-5 w-5 text-emerald-500" />
                    </div>
                    <div>
                      <h3 className="font-medium text-white capitalize">{provider}</h3>
                      <div className="flex items-center gap-1 text-xs text-white/50">
                        <Key className="h-3 w-3" /> Encrypted Payload
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-1 text-xs font-medium text-emerald-500">
                      <Check className="h-3 w-3" /> Secure
                    </span>
                    <button 
                      onClick={() => handleDelete(provider)}
                      className="rounded-md p-2 text-white/50 hover:bg-red-500/10 hover:text-red-500 transition-colors"
                      title="Delete Secret"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
