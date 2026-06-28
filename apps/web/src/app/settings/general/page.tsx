export default function GeneralSettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">General</h1>
        <p className="text-white/60 text-sm mt-1">
          System Information.
        </p>
      </div>
      
      <div className="rounded-xl border border-white/10 bg-black/40 p-6 space-y-4">
        <div>
          <p className="text-sm font-semibold text-white/50">Version</p>
          <p className="text-sm text-white">Khonshu Cognitive OS 1.0.0-beta</p>
        </div>
        <div>
          <p className="text-sm font-semibold text-white/50">Environment</p>
          <p className="text-sm text-white">Production</p>
        </div>
      </div>
    </div>
  )
}
