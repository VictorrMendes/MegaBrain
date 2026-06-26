from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class TraceContext:
    """Portable trace context para rastreamento de cadeias de execução.

    Inspirado no W3C Trace Context / OpenTelemetry sem dependência externa.

    Campos:
    - trace_id: estável em toda a cadeia (raiz → folhas)
    - span_id:  identifica esta unidade de trabalho específica
    - parent_span_id: liga ao span pai (None = raiz da trace)

    Relação com KhonshuEvent:
    - trace_id  ≈  event.trace_id   (propagado em derive())
    - span_id   ≈  event.id         (único por evento)
    - parent_span_id ≈ event.causation_id
    """

    trace_id: UUID = field(default_factory=uuid4)
    span_id: UUID = field(default_factory=uuid4)
    parent_span_id: UUID | None = None

    def child(self) -> TraceContext:
        """Cria um novo span dentro da mesma trace."""
        return TraceContext(
            trace_id=self.trace_id,
            parent_span_id=self.span_id,
        )

    def to_dict(self) -> dict:
        return {
            "trace_id": str(self.trace_id),
            "span_id": str(self.span_id),
            "parent_span_id": (
                str(self.parent_span_id) if self.parent_span_id else None
            ),
        }

    @classmethod
    def from_event_metadata(cls, metadata: dict) -> TraceContext:
        """Reconstrói o contexto a partir do metadata de um KhonshuEvent."""
        raw_trace = metadata.get("trace_id")
        raw_parent = metadata.get("parent_span_id")
        return cls(
            trace_id=UUID(raw_trace) if raw_trace else uuid4(),
            parent_span_id=UUID(raw_parent) if raw_parent else None,
        )

    @classmethod
    def root(cls) -> TraceContext:
        """Cria uma nova trace raiz (primeiro evento da cadeia)."""
        return cls()
