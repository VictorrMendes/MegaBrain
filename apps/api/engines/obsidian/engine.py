from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kernel.logger import get_logger
from models.obsidian import ObsidianLink, ObsidianNote
from schemas.obsidian import ObsidianNoteInput

if TYPE_CHECKING:
    from engines.rag import RAGEngine

logger = get_logger(__name__)

_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_TAG_RE = re.compile(r"^tags:\s*\[([^\]]*)\]", re.MULTILINE)
_TAG_LIST_RE = re.compile(r"^-\s+(.+)$", re.MULTILINE)
_HEADING_RE = re.compile(r"^#+\s+(.+)$", re.MULTILINE)


@dataclass
class SyncStats:
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    errors: list[str] = field(default_factory=list)


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract frontmatter dict and body (content without frontmatter)."""
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return {}, content
    raw = m.group(1)
    body = content[m.end():]
    fm: dict = {}
    for line in raw.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm, body


def _extract_tags(frontmatter: dict, raw_fm: str) -> list[str]:
    tags: list[str] = []
    # inline: tags: [tag1, tag2]
    m = _TAG_RE.search(raw_fm)
    if m:
        tags = [t.strip().strip('"').strip("'") for t in m.group(1).split(",") if t.strip()]
    # list style: - tag
    elif "tags" in frontmatter:
        tags = _TAG_LIST_RE.findall(raw_fm)
    return tags


def _extract_title(path: str, body: str) -> str:
    m = _HEADING_RE.search(body)
    if m:
        return m.group(1).strip()
    stem = PurePosixPath(path).stem
    return stem.replace("_", " ").replace("-", " ")


def _extract_wikilinks(content: str) -> list[tuple[str, str | None]]:
    """Return list of (target, link_text|None)."""
    return [(m.group(1).strip(), m.group(2)) for m in _WIKILINK_RE.finditer(content)]


def _resolve_target(source_path: str, raw_target: str, known_paths: set[str]) -> str:
    """Resolve a [[wikilink]] target to a known note path, or return normalized slug."""
    # exact match
    if raw_target in known_paths:
        return raw_target
    # match by stem (filename without extension)
    stem = raw_target.lower().replace(" ", "_")
    for p in known_paths:
        if PurePosixPath(p).stem.lower() == raw_target.lower():
            return p
        if PurePosixPath(p).stem.lower() == stem:
            return p
    # unresolved — return as-is (note may not be synced yet)
    return raw_target


class ObsidianEngine:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        rag_engine: RAGEngine,
    ) -> None:
        self._sessions = session_factory
        self._rag = rag_engine

    async def sync(
        self,
        workspace_id: UUID,
        notes: list[ObsidianNoteInput],
    ) -> SyncStats:
        stats = SyncStats()

        async with self._sessions() as session:
            # Load existing notes for this workspace
            result = await session.execute(
                select(ObsidianNote).where(ObsidianNote.workspace_id == workspace_id)
            )
            existing: dict[str, ObsidianNote] = {n.path: n for n in result.scalars()}
            known_paths = set(existing.keys()) | {n.path for n in notes}

        for note_input in notes:
            try:
                await self._sync_note(workspace_id, note_input, existing, known_paths, stats)
            except Exception as exc:
                logger.error("obsidian.sync.error", path=note_input.path, error=str(exc))
                stats.errors.append(f"{note_input.path}: {exc}")

        logger.info(
            "obsidian.sync.done",
            workspace_id=str(workspace_id),
            added=stats.added,
            updated=stats.updated,
            unchanged=stats.unchanged,
            errors=len(stats.errors),
        )
        return stats

    async def _sync_note(
        self,
        workspace_id: UUID,
        note_input: ObsidianNoteInput,
        existing: dict[str, ObsidianNote],
        known_paths: set[str],
        stats: SyncStats,
    ) -> None:
        fm_raw_match = _FRONTMATTER_RE.match(note_input.content)
        fm_raw = fm_raw_match.group(1) if fm_raw_match else ""
        frontmatter, body = _parse_frontmatter(note_input.content)
        tags = _extract_tags(frontmatter, fm_raw)
        title = _extract_title(note_input.path, body)
        wikilinks = _extract_wikilinks(note_input.content)

        async with self._sessions() as session:
            existing_note = existing.get(note_input.path)

            # Skip if content unchanged (same mtime)
            if (
                existing_note
                and note_input.last_modified
                and existing_note.last_modified
                and note_input.last_modified <= existing_note.last_modified
            ):
                stats.unchanged += 1
                return

            if existing_note:
                existing_note.title = title
                existing_note.content = note_input.content
                existing_note.tags = tags
                existing_note.frontmatter = frontmatter
                existing_note.last_modified = note_input.last_modified
                existing_note.updated_at = datetime.utcnow()
                note = existing_note
                stats.updated += 1
            else:
                note = ObsidianNote(
                    workspace_id=workspace_id,
                    path=note_input.path,
                    title=title,
                    content=note_input.content,
                    tags=tags,
                    frontmatter=frontmatter,
                    last_modified=note_input.last_modified,
                )
                session.add(note)
                stats.added += 1

            await session.flush()

            # Upsert links: delete old, insert new
            await session.execute(
                delete(ObsidianLink).where(
                    ObsidianLink.workspace_id == workspace_id,
                    ObsidianLink.source_path == note_input.path,
                )
            )
            for raw_target, link_text in wikilinks:
                resolved = _resolve_target(note_input.path, raw_target, known_paths)
                session.add(ObsidianLink(
                    workspace_id=workspace_id,
                    source_path=note_input.path,
                    target_path=resolved,
                    link_text=link_text,
                ))

            await session.commit()
            if existing_note:
                await session.refresh(existing_note)
            else:
                await session.refresh(note)
            note_id = note.id

        # Ingest into RAG (fire-and-forget errors)
        try:
            doc = await self._rag.ingest(
                workspace_id=workspace_id,
                filename=note_input.path,
                content=note_input.content,
                content_type="text/markdown",
            )
            async with self._sessions() as session:
                result = await session.execute(
                    select(ObsidianNote).where(ObsidianNote.id == note_id)
                )
                n = result.scalar_one_or_none()
                if n:
                    n.document_id = doc.id
                    await session.commit()
        except Exception as exc:
            logger.warning("obsidian.rag.error", path=note_input.path, error=str(exc))

    async def get_graph(self, workspace_id: UUID) -> dict:
        async with self._sessions() as session:
            notes_result = await session.execute(
                select(ObsidianNote).where(ObsidianNote.workspace_id == workspace_id)
            )
            notes = notes_result.scalars().all()

            links_result = await session.execute(
                select(ObsidianLink).where(ObsidianLink.workspace_id == workspace_id)
            )
            links = links_result.scalars().all()

        nodes = [
            {"id": n.path, "title": n.title, "tags": n.tags or [], "path": n.path}
            for n in notes
        ]
        edges = [
            {"source": lk.source_path, "target": lk.target_path, "link_text": lk.link_text}
            for lk in links
        ]
        return {"nodes": nodes, "edges": edges}

    async def list_notes(self, workspace_id: UUID) -> list[ObsidianNote]:
        async with self._sessions() as session:
            result = await session.execute(
                select(ObsidianNote)
                .where(ObsidianNote.workspace_id == workspace_id)
                .order_by(ObsidianNote.path)
            )
            return list(result.scalars().all())
