"use client";

import { useEffect, useState } from "react";
import { api, type AvailablePlugin, type WorkspacePlugin } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import { Badge, type BadgeVariant, Button, Spinner } from "@/components/ui";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/Dialog";
import {
  BellIcon,
  CalendarIcon,
  CheckCircle2Icon,
  ChevronRightIcon,
  CloudIcon,
  DatabaseIcon,
  HomeIcon,
  PlugIcon,
  SearchIcon,
  ToggleLeftIcon,
  ToggleRightIcon,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Category metadata
// ─────────────────────────────────────────────────────────────

const CATEGORY_META: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  data:          { label: "Dados",          icon: <DatabaseIcon  size={14} />, color: "text-accent" },
  notifications: { label: "Notificações",   icon: <BellIcon      size={14} />, color: "text-status-warning" },
  smart_home:    { label: "Casa Inteligente",icon: <HomeIcon      size={14} />, color: "text-status-success" },
  productivity:  { label: "Produtividade",  icon: <CalendarIcon  size={14} />, color: "text-status-info" },
  general:       { label: "Geral",          icon: <CloudIcon     size={14} />, color: "text-content-muted" },
};

function categoryVariant(cat: string): BadgeVariant {
  if (cat === "data")          return "info";
  if (cat === "notifications") return "warning";
  if (cat === "smart_home")    return "success";
  if (cat === "productivity")  return "active";
  return "muted";
}

// ─────────────────────────────────────────────────────────────
// Plugin config dialog
// ─────────────────────────────────────────────────────────────

function PluginConfigDialog({
  plugin,
  workspace,
  onClose,
  onSaved,
}: {
  plugin:    AvailablePlugin;
  workspace: WorkspacePlugin | null;
  onClose:   () => void;
  onSaved:   (p: WorkspacePlugin) => void;
}) {
  const { current: ws } = useWorkspace();
  const [config,  setConfig]  = useState<Record<string, string>>(workspace?.config ?? {});
  const [enabled, setEnabled] = useState(workspace?.is_enabled ?? true);
  const [saving,  setSaving]  = useState(false);

  function setField(name: string, value: string) {
    setConfig((prev) => ({ ...prev, [name]: value }));
  }

  async function save() {
    if (!ws) return;
    setSaving(true);
    try {
      const saved = workspace
        ? await api.upsertPlugin(ws.id, plugin.name, config, enabled)
        : await api.upsertPlugin(ws.id, plugin.name, config, enabled);
      onSaved(saved);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent title={plugin.name.replace(/_/g, " ")}>
        <p className="text-xs text-content-muted mb-4">{plugin.description}</p>

        {plugin.config_fields.length > 0 && (
          <div className="space-y-3 mb-4">
            {plugin.config_fields.map((f) => (
              <div key={f.name}>
                <label className="block text-xs text-content-secondary mb-1.5">
                  {f.label}
                  {f.required && <span className="text-status-error ml-1">*</span>}
                </label>
                <input
                  type={f.type === "password" ? "password" : f.type === "url" ? "url" : "text"}
                  value={config[f.name] ?? ""}
                  onChange={(e) => setField(f.name, e.target.value)}
                  placeholder={f.placeholder}
                  className={cn(
                    "w-full rounded-lg border px-3 py-2 text-sm",
                    "border-[var(--border-default)] bg-[var(--surface-base)]",
                    "text-content-primary placeholder:text-content-placeholder",
                    "focus:outline-none focus:border-[var(--border-accent)]",
                  )}
                />
              </div>
            ))}
          </div>
        )}

        {/* Enable toggle */}
        <div className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-subtle)] px-3 py-2.5">
          <span className="text-xs text-content-secondary">Ativado neste workspace</span>
          <button
            onClick={() => setEnabled((v) => !v)}
            className={cn("transition-colors", enabled ? "text-status-success" : "text-content-muted")}
          >
            {enabled
              ? <ToggleRightIcon size={22} />
              : <ToggleLeftIcon  size={22} />}
          </button>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={saving}>Cancelar</Button>
          <Button onClick={save} disabled={saving}>
            {saving && <Spinner size="sm" className="mr-2" />}
            Salvar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─────────────────────────────────────────────────────────────
// Plugin card
// ─────────────────────────────────────────────────────────────

function PluginCard({
  plugin,
  workspace,
  onClick,
}: {
  plugin:    AvailablePlugin;
  workspace: WorkspacePlugin | null;
  onClick:   () => void;
}) {
  const catMeta = CATEGORY_META[plugin.category] ?? CATEGORY_META.general;
  const isActive = workspace?.is_enabled === true;

  return (
    <button
      onClick={onClick}
      className={cn(
        "group w-full rounded-xl border p-4 text-left transition-all",
        isActive
          ? "border-accent-subtle bg-accent-dim hover:border-accent"
          : "border-[var(--border-subtle)] bg-[var(--surface-raised)] hover:border-[var(--border-default)]",
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className={cn("rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-subtle)] p-2", catMeta.color)}>
          {catMeta.icon}
        </div>
        {isActive ? (
          <CheckCircle2Icon size={14} className="text-status-success mt-0.5" />
        ) : (
          <ChevronRightIcon size={14} className="text-content-muted mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity" />
        )}
      </div>

      <p className="text-sm font-medium text-content-primary mb-0.5 capitalize">
        {plugin.name.replace(/_/g, " ")}
      </p>
      <p className="text-xs text-content-muted leading-relaxed line-clamp-2 mb-3">
        {plugin.description}
      </p>

      <div className="flex items-center gap-1.5">
        <Badge variant={categoryVariant(plugin.category)} size="sm">
          {catMeta.label}
        </Badge>
        {isActive && (
          <Badge variant="success" size="sm">ativo</Badge>
        )}
        {plugin.config_fields.length === 0 && (
          <Badge variant="muted" size="sm">sem config</Badge>
        )}
      </div>
    </button>
  );
}

// ─────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────

export function IntegrationsPage() {
  const { current: workspace, loading: wsLoading } = useWorkspace();
  const [available,   setAvailable]   = useState<AvailablePlugin[]>([]);
  const [workspacePs, setWorkspacePs] = useState<WorkspacePlugin[]>([]);
  const [loading,     setLoading]     = useState(false);
  const [configFor,   setConfigFor]   = useState<AvailablePlugin | null>(null);
  const [query,       setQuery]       = useState("");

  useEffect(() => {
    if (!workspace) return;
    setLoading(true);
    Promise.all([
      api.listAvailablePlugins(workspace.id),
      api.listWorkspacePlugins(workspace.id),
    ])
      .then(([avail, ws]) => {
        setAvailable(avail);
        setWorkspacePs(ws);
      })
      .finally(() => setLoading(false));
  }, [workspace?.id]);

  function getWorkspacePlugin(name: string): WorkspacePlugin | null {
    return workspacePs.find((p) => p.plugin_name === name) ?? null;
  }

  function handleSaved(saved: WorkspacePlugin) {
    setWorkspacePs((prev) => {
      const exists = prev.find((p) => p.id === saved.id);
      if (exists) return prev.map((p) => (p.id === saved.id ? saved : p));
      return [...prev, saved];
    });
    setConfigFor(null);
  }

  const filtered = available.filter((p) =>
    !query.trim() ||
    p.name.includes(query.toLowerCase()) ||
    p.description.toLowerCase().includes(query.toLowerCase()),
  );

  const byCategory = filtered.reduce<Record<string, AvailablePlugin[]>>((acc, p) => {
    const cat = p.category ?? "general";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(p);
    return acc;
  }, {});

  const activeCount = workspacePs.filter((p) => p.is_enabled).length;

  if (wsLoading || loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="md" />
      </div>
    );
  }

  return (
    <>
      <div className="h-full overflow-y-auto">
        <div className="mx-auto max-w-3xl px-6 py-8">

          {/* Header */}
          <div className="mb-6 flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <PlugIcon size={14} className="text-content-muted" />
                <h1 className="text-md font-semibold text-content-primary">Integrações</h1>
              </div>
              <p className="text-xs text-content-muted">
                {available.length} plugins disponíveis · {activeCount} ativos
              </p>
            </div>
          </div>

          {/* Search */}
          <div className="relative mb-6">
            <SearchIcon size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-content-muted" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filtrar integrações…"
              className={cn(
                "w-full rounded-lg border py-2 pl-9 pr-3 text-sm",
                "border-[var(--border-default)] bg-[var(--surface-raised)]",
                "text-content-primary placeholder:text-content-placeholder",
                "focus:outline-none focus:border-[var(--border-accent)]",
              )}
            />
          </div>

          {/* Grid by category */}
          {Object.entries(byCategory).map(([cat, plugins]) => {
            const catMeta = CATEGORY_META[cat] ?? CATEGORY_META.general;
            return (
              <div key={cat} className="mb-8">
                <div className="flex items-center gap-2 mb-3">
                  <span className={catMeta.color}>{catMeta.icon}</span>
                  <h2 className="text-[11px] font-semibold uppercase tracking-widest text-content-muted">
                    {catMeta.label}
                  </h2>
                </div>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {plugins.map((p) => (
                    <PluginCard
                      key={p.name}
                      plugin={p}
                      workspace={getWorkspacePlugin(p.name)}
                      onClick={() => setConfigFor(p)}
                    />
                  ))}
                </div>
              </div>
            );
          })}

          {filtered.length === 0 && (
            <p className="py-16 text-center text-sm text-content-muted">
              Nenhuma integração encontrada.
            </p>
          )}

        </div>
      </div>

      {configFor && (
        <PluginConfigDialog
          plugin={configFor}
          workspace={getWorkspacePlugin(configFor.name)}
          onClose={() => setConfigFor(null)}
          onSaved={handleSaved}
        />
      )}
    </>
  );
}
