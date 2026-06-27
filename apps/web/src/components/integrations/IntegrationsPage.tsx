"use client";

import { useCallback, useEffect, useState } from "react";
import {
  api,
  type AvailableIntegration,
  type Integration,
  type IntegrationHealth,
  type LifeContextSnapshot,
  type SyncRecord,
} from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import { Badge, Button, Spinner } from "@/components/ui";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/Dialog";
import {
  ActivityIcon,
  CheckCircle2Icon,
  ChevronDownIcon,
  ChevronRightIcon,
  CloudOffIcon,
  GlobeIcon,
  HeartPulseIcon,
  LinkIcon,
  RefreshCwIcon,
  SatelliteIcon,
  Trash2Icon,
  ZapIcon,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

function healthColor(h: IntegrationHealth) {
  if (h === "healthy") return "text-status-success";
  if (h === "degraded") return "text-status-warning";
  if (h === "unhealthy") return "text-status-error";
  return "text-content-muted";
}

function healthLabel(h: IntegrationHealth) {
  if (h === "healthy") return "saudável";
  if (h === "degraded") return "degradado";
  if (h === "unhealthy") return "falho";
  return "desconhecido";
}

function relativeTime(iso: string | null) {
  if (!iso) return "nunca";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "agora";
  if (mins < 60) return `${mins}m atrás`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h atrás`;
  return `${Math.floor(hrs / 24)}d atrás`;
}

// ─────────────────────────────────────────────────────────────
// Connect dialog
// ─────────────────────────────────────────────────────────────

function ConnectDialog({
  provider,
  onClose,
  onConnected,
}: {
  provider: AvailableIntegration;
  onClose: () => void;
  onConnected: (i: Integration) => void;
}) {
  const { current: ws } = useWorkspace();
  const [config, setConfig] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function setField(k: string, v: string) {
    setConfig((prev) => ({ ...prev, [k]: v }));
  }

  async function connect() {
    if (!ws) return;
    setSaving(true);
    setError(null);
    try {
      const result = await api.connectIntegration(ws.id, provider.slug, config);
      onConnected(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao conectar");
    } finally {
      setSaving(false);
    }
  }

  const knownFields: Record<string, { label: string; type?: string; placeholder?: string }[]> = {
    docker: [
      { label: "Socket path", placeholder: "/var/run/docker.sock" },
    ],
    weather: [
      { label: "location", type: "text", placeholder: "Sao Paulo" },
    ],
  };

  const fields = knownFields[provider.slug] ?? [];

  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent title={`Conectar ${provider.name}`}>
        <p className="text-xs text-content-muted mb-4">{provider.description}</p>

        {fields.length > 0 && (
          <div className="space-y-3 mb-4">
            {fields.map((f) => (
              <div key={f.label}>
                <label className="block text-xs text-content-secondary mb-1.5 capitalize">
                  {f.label}
                </label>
                <input
                  type={f.type === "password" ? "password" : "text"}
                  value={config[f.label.toLowerCase()] ?? ""}
                  onChange={(e) => setField(f.label.toLowerCase(), e.target.value)}
                  placeholder={f.placeholder ?? ""}
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

        {fields.length === 0 && (
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-subtle)] px-3 py-2.5 text-xs text-content-muted mb-4">
            Esta integração não requer configuração adicional.
          </div>
        )}

        {error && (
          <p className="text-xs text-status-error mb-3">{error}</p>
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={saving}>Cancelar</Button>
          <Button onClick={connect} disabled={saving}>
            {saving && <Spinner size="sm" className="mr-2" />}
            Conectar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─────────────────────────────────────────────────────────────
// Sync history row
// ─────────────────────────────────────────────────────────────

function SyncHistoryRow({ r }: { r: SyncRecord }) {
  const statusColor =
    r.status === "success" ? "text-status-success" :
    r.status === "partial" ? "text-status-warning" :
    r.status === "running" ? "text-accent" :
    "text-status-error";

  return (
    <div className="flex items-center gap-3 text-xs py-1.5 border-b border-[var(--border-subtle)] last:border-0">
      <span className={cn("w-14 font-medium", statusColor)}>{r.status}</span>
      <span className="text-content-muted w-16">{relativeTime(r.started_at)}</span>
      <span className="text-content-secondary">{r.items_synced} itens</span>
      {r.duration_ms && (
        <span className="text-content-muted ml-auto">{r.duration_ms}ms</span>
      )}
      {r.error_message && (
        <span className="text-status-error truncate max-w-[120px]" title={r.error_message}>
          {r.error_message}
        </span>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Connected integration card
// ─────────────────────────────────────────────────────────────

function IntegrationCard({
  integration,
  workspaceId,
  onDisconnected,
  onSynced,
}: {
  integration: Integration;
  workspaceId: string;
  onDisconnected: (id: string) => void;
  onSynced: (updated: Integration) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [checkingHealth, setCheckingHealth] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [history, setHistory] = useState<SyncRecord[]>([]);
  const [health, setHealth] = useState<IntegrationHealth>(integration.health);

  useEffect(() => {
    if (!expanded) return;
    api.getSyncHistory(workspaceId, integration.id, 5).then(setHistory).catch(() => {});
  }, [expanded, workspaceId, integration.id]);

  async function handleSync() {
    setSyncing(true);
    try {
      await api.syncIntegration(workspaceId, integration.id);
      const updated = await api.listIntegrations(workspaceId);
      const me = updated.find((i) => i.id === integration.id);
      if (me) onSynced(me);
      if (expanded) {
        api.getSyncHistory(workspaceId, integration.id, 5).then(setHistory).catch(() => {});
      }
    } finally {
      setSyncing(false);
    }
  }

  async function handleHealthCheck() {
    setCheckingHealth(true);
    try {
      const res = await api.checkIntegrationHealth(workspaceId, integration.id);
      setHealth(res.health);
    } finally {
      setCheckingHealth(false);
    }
  }

  async function handleDisconnect() {
    setDisconnecting(true);
    try {
      await api.disconnectIntegration(workspaceId, integration.id);
      onDisconnected(integration.id);
    } finally {
      setDisconnecting(false);
    }
  }

  const borderClass =
    health === "unhealthy" ? "border-status-error/40 bg-[var(--surface-raised)]" :
    health === "degraded"  ? "border-status-warning/40 bg-[var(--surface-raised)]" :
    integration.status === "active"
      ? "border-[var(--border-default)] bg-[var(--surface-raised)]"
      : "border-[var(--border-subtle)] bg-[var(--surface-subtle)] opacity-70";

  const healthBadgeCls =
    health === "healthy"   ? "bg-status-success/10 text-status-success border-status-success/20" :
    health === "degraded"  ? "bg-status-warning/10 text-status-warning border-status-warning/20" :
    health === "unhealthy" ? "bg-status-error/10 text-status-error border-status-error/20" :
    "bg-[var(--surface-subtle)] text-content-muted border-[var(--border-subtle)]";

  const lastSyncRecord = history[0] ?? null;

  return (
    <div className={cn("rounded-xl border transition-colors", borderClass)}>
      {/* Header */}
      <div className="flex items-center gap-3 p-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-subtle)] text-sm">
          {integration.icon || integration.slug.slice(0, 2).toUpperCase()}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5 flex-wrap">
            <span className="text-sm font-medium text-content-primary">{integration.name}</span>
            <span className={cn(
              "inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10px] font-medium",
              healthBadgeCls,
            )}>
              {healthLabel(health)}
            </span>
          </div>
          <span className="text-[11px] text-content-muted">
            sync {relativeTime(integration.last_sync_at)} · {integration.category}
          </span>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={handleSync}
            disabled={syncing}
            title="Sincronizar"
            className="rounded-lg p-1.5 text-content-muted hover:text-content-primary hover:bg-[var(--surface-subtle)] transition-colors disabled:opacity-40"
          >
            <RefreshCwIcon size={13} className={syncing ? "animate-spin" : ""} />
          </button>
          <button
            onClick={handleHealthCheck}
            disabled={checkingHealth}
            title="Health check"
            className="rounded-lg p-1.5 text-content-muted hover:text-content-primary hover:bg-[var(--surface-subtle)] transition-colors disabled:opacity-40"
          >
            <HeartPulseIcon size={13} />
          </button>
          <button
            onClick={handleDisconnect}
            disabled={disconnecting}
            title="Desconectar"
            className="rounded-lg p-1.5 text-content-muted hover:text-status-error hover:bg-[var(--surface-subtle)] transition-colors disabled:opacity-40"
          >
            <Trash2Icon size={13} />
          </button>
          <button
            onClick={() => setExpanded((v) => !v)}
            className="rounded-lg p-1.5 text-content-muted hover:text-content-primary hover:bg-[var(--surface-subtle)] transition-colors"
          >
            {expanded ? <ChevronDownIcon size={13} /> : <ChevronRightIcon size={13} />}
          </button>
        </div>
      </div>

      {/* Life context lines */}
      {integration.life_context_lines.length > 0 && (
        <div className="px-4 pb-3 -mt-1">
          {integration.life_context_lines.slice(0, 2).map((line, i) => (
            <p key={i} className="text-[11px] text-content-muted leading-relaxed truncate">
              {line}
            </p>
          ))}
        </div>
      )}

      {/* Expanded: sync history */}
      {expanded && (
        <div className="border-t border-[var(--border-subtle)] mx-4 pt-3 pb-4">
          {/* Last sync summary — latency + error prominent */}
          {lastSyncRecord && (
            <div className="mb-3">
              <div className="flex items-center gap-2 flex-wrap mb-1.5">
                <span className={cn(
                  "inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-medium",
                  lastSyncRecord.error_message
                    ? "bg-status-error/10 text-status-error border-status-error/20"
                    : "bg-status-success/10 text-status-success border-status-success/20",
                )}>
                  {lastSyncRecord.error_message ? "Falhou" : "Sucesso"}
                </span>
                {lastSyncRecord.duration_ms != null && (
                  <span className="text-[11px] text-content-muted">
                    <span className="font-medium text-content-secondary">{lastSyncRecord.duration_ms} ms</span>{" "}latência
                  </span>
                )}
                {lastSyncRecord.items_synced != null && lastSyncRecord.items_synced > 0 && (
                  <span className="text-[11px] text-content-muted">
                    <span className="font-medium text-content-secondary">{lastSyncRecord.items_synced}</span>{" "}itens
                  </span>
                )}
                {lastSyncRecord.items_failed != null && lastSyncRecord.items_failed > 0 && (
                  <span className="text-[11px] text-status-error">
                    <span className="font-medium">{lastSyncRecord.items_failed}</span>{" "}falhas
                  </span>
                )}
              </div>
              {lastSyncRecord.error_message && (
                <div className="rounded-md bg-status-error/5 border border-status-error/20 px-3 py-2 text-[11px] text-status-error font-mono">
                  {lastSyncRecord.error_message}
                </div>
              )}
            </div>
          )}

          <p className="text-[10px] font-semibold uppercase tracking-wider text-content-muted mb-2">
            Histórico de sync
          </p>
          {history.length === 0 ? (
            <p className="text-xs text-content-muted">Sem registros.</p>
          ) : (
            history.map((r) => <SyncHistoryRow key={r.id} r={r} />)
          )}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Available provider card
// ─────────────────────────────────────────────────────────────

function AvailableCard({
  provider,
  onConnect,
}: {
  provider: AvailableIntegration;
  onConnect: () => void;
}) {
  return (
    <button
      onClick={onConnect}
      className={cn(
        "group w-full rounded-xl border p-4 text-left transition-all",
        "border-[var(--border-subtle)] bg-[var(--surface-raised)]",
        "hover:border-[var(--border-default)] hover:bg-[var(--surface-overlay)]",
      )}
    >
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-subtle)] text-sm shrink-0">
          {provider.icon || provider.slug.slice(0, 2).toUpperCase()}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-content-primary mb-0.5">{provider.name}</p>
          <p className="text-[11px] text-content-muted line-clamp-2 leading-relaxed">
            {provider.description}
          </p>
        </div>
        <LinkIcon size={12} className="text-content-muted mt-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    </button>
  );
}

// ─────────────────────────────────────────────────────────────
// Life context panel
// ─────────────────────────────────────────────────────────────

function LifeContextPanel({ snapshot }: { snapshot: LifeContextSnapshot }) {
  const [open, setOpen] = useState(false);

  if (snapshot.lines.length === 0) return null;

  return (
    <div className="mb-6 rounded-xl border border-accent-subtle bg-accent-dim">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-4 py-3 text-left"
      >
        <SatelliteIcon size={13} className="text-accent shrink-0" />
        <span className="text-xs font-medium text-content-primary flex-1">
          Vida digital agora · {snapshot.integration_count} integração{snapshot.integration_count !== 1 ? "ões" : ""}
        </span>
        {open ? <ChevronDownIcon size={12} className="text-content-muted" /> : <ChevronRightIcon size={12} className="text-content-muted" />}
      </button>
      {open && (
        <div className="border-t border-accent-subtle px-4 pb-3 pt-2 space-y-1">
          {snapshot.lines.map((line, i) => (
            <p key={i} className="text-xs text-content-secondary leading-relaxed">
              • {line}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────

export function IntegrationsPage() {
  const { current: workspace, loading: wsLoading } = useWorkspace();
  const [connected, setConnected] = useState<Integration[]>([]);
  const [available, setAvailable] = useState<AvailableIntegration[]>([]);
  const [snapshot, setSnapshot] = useState<LifeContextSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [connectFor, setConnectFor] = useState<AvailableIntegration | null>(null);
  const [syncingAll, setSyncingAll] = useState(false);

  const load = useCallback(async () => {
    if (!workspace) return;
    setLoading(true);
    try {
      const [avail, conn] = await Promise.all([
        api.listAvailableIntegrations(),
        api.listIntegrations(workspace.id),
      ]);
      setAvailable(avail);
      setConnected(conn);
      if (conn.length > 0) {
        api.getLifeContextSnapshot(workspace.id).then(setSnapshot).catch(() => {});
      }
    } finally {
      setLoading(false);
    }
  }, [workspace?.id]);

  useEffect(() => { load(); }, [load]);

  async function handleSyncAll() {
    if (!workspace) return;
    setSyncingAll(true);
    try {
      await api.syncAllIntegrations(workspace.id);
      await load();
    } finally {
      setSyncingAll(false);
    }
  }

  function handleConnected(integration: Integration) {
    setConnected((prev) => {
      const exists = prev.find((i) => i.id === integration.id);
      if (exists) return prev.map((i) => (i.id === integration.id ? integration : i));
      return [...prev, integration];
    });
    setConnectFor(null);
  }

  function handleDisconnected(id: string) {
    setConnected((prev) => prev.filter((i) => i.id !== id));
  }

  function handleSynced(updated: Integration) {
    setConnected((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
  }

  const connectedSlugs = new Set(connected.map((i) => i.slug));
  const notConnected = available.filter((a) => !connectedSlugs.has(a.slug));

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
        <div className="mx-auto max-w-2xl px-6 py-8">

          {/* Header */}
          <div className="mb-6 flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <GlobeIcon size={14} className="text-content-muted" />
                <h1 className="text-md font-semibold text-content-primary">Life Platform</h1>
              </div>
              <p className="text-xs text-content-muted">
                {connected.length} conectadas · {available.length} disponíveis
              </p>
            </div>
            {connected.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleSyncAll}
                disabled={syncingAll}
              >
                {syncingAll
                  ? <Spinner size="sm" className="mr-1.5" />
                  : <ZapIcon size={12} className="mr-1.5" />}
                Sync all
              </Button>
            )}
          </div>

          {/* Life context snapshot */}
          {snapshot && <LifeContextPanel snapshot={snapshot} />}

          {/* Connected integrations */}
          {connected.length > 0 && (
            <div className="mb-8">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-content-muted mb-3 flex items-center gap-1.5">
                <CheckCircle2Icon size={10} />
                Conectadas
              </p>
              <div className="space-y-2">
                {connected.map((integration) => (
                  <IntegrationCard
                    key={integration.id}
                    integration={integration}
                    workspaceId={workspace!.id}
                    onDisconnected={handleDisconnected}
                    onSynced={handleSynced}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Available */}
          {notConnected.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-content-muted mb-3 flex items-center gap-1.5">
                <ActivityIcon size={10} />
                Disponíveis
              </p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {notConnected.map((provider) => (
                  <AvailableCard
                    key={provider.slug}
                    provider={provider}
                    onConnect={() => setConnectFor(provider)}
                  />
                ))}
              </div>
            </div>
          )}

          {available.length === 0 && connected.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center gap-3">
              <CloudOffIcon size={28} className="text-content-muted" />
              <p className="text-sm text-content-muted">
                Nenhuma integração registrada ainda.
              </p>
            </div>
          )}

        </div>
      </div>

      {connectFor && (
        <ConnectDialog
          provider={connectFor}
          onClose={() => setConnectFor(null)}
          onConnected={handleConnected}
        />
      )}
    </>
  );
}
