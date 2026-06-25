from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from core.dependencies import get_rag_engine
from engines.rag import RAGEngine
from schemas.document import DocumentResponse

router = APIRouter(
    prefix="/workspaces/{workspace_id}/documents",
    tags=["documents"],
)

_ALLOWED_CONTENT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "application/octet-stream",
}
_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/", response_model=DocumentResponse, status_code=201)
async def upload_document(
    workspace_id: UUID,
    file: UploadFile,
    rag_engine: RAGEngine = Depends(get_rag_engine),
):
    content_bytes = await file.read()

    if len(content_bytes) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 5 MB limit")

    try:
        text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")

    if not text.strip():
        raise HTTPException(status_code=400, detail="File is empty")

    content_type = file.content_type or "text/plain"

    doc = await rag_engine.ingest(
        workspace_id=workspace_id,
        filename=file.filename or "document.txt",
        content=text,
        content_type=content_type,
    )
    return doc


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    workspace_id: UUID,
    rag_engine: RAGEngine = Depends(get_rag_engine),
):
    return await rag_engine.list_documents(workspace_id)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    workspace_id: UUID,
    document_id: UUID,
    rag_engine: RAGEngine = Depends(get_rag_engine),
):
    docs = await rag_engine.list_documents(workspace_id)
    if not any(d.id == document_id for d in docs):
        raise HTTPException(status_code=404, detail="Document not found")
    await rag_engine.delete_document(document_id)
