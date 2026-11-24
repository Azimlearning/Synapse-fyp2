"""POST /ingest: upload one PDF. The request is multipart/form-data; the response is IngestResponse.

An upload that cannot be ingested (not a PDF, no text, a failed model call) still answers 200 with
status "failed" and the reason: the request itself was well formed. A malformed request (no file,
wrong type, too large) is a 400 with the error envelope.
"""

from fastapi import APIRouter, Request, Response, UploadFile

from api.core.errors import BadRequest, NotFound
from api.genui.generated import IngestResponse
from api.ingestion.pipeline import ingest_pdf, remove_document
from api.ingestion.types import doc_id_for

router = APIRouter()

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
_PDF_MAGIC = b"%PDF-"


@router.post("/ingest")
async def ingest(file: UploadFile, request: Request) -> IngestResponse:
    container = request.app.state.container
    name = file.filename or "upload.pdf"
    if not name.lower().endswith(".pdf"):
        raise BadRequest("Only PDF files can be ingested.")
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise BadRequest(f"The file is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    if not raw.startswith(_PDF_MAGIC):
        raise BadRequest("The file does not look like a PDF.")

    result = await ingest_pdf(raw, name, container.ingest_deps)
    if result.status == "ready":  # keep the original beside the stores, named by its content hash
        container.uploads_dir.mkdir(parents=True, exist_ok=True)
        (container.uploads_dir / f"{doc_id_for(raw)}.pdf").write_bytes(raw)
    return IngestResponse(
        docId=result.doc_id,
        title=result.title,
        status="ready" if result.status == "ready" else "failed",
        chunkCount=result.chunk_count,
        error=result.error,
    )


@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(doc_id: str, request: Request) -> Response:
    """Remove a document from every store (passages, vectors, its graph edges and the nodes only it mentioned) and its kept PDF.
    Retrieval reads the stores on every question, so the next answer no longer sees it. The notes (the vault) are compiled
    separately and keep what they had until they are rebuilt."""
    container = request.app.state.container
    deps = container.ingest_deps
    if deps.docs.get_document(doc_id) is None:
        raise NotFound("No such document.")
    remove_document(doc_id, deps)
    deps.graph.save()
    deps.vectors.save()
    kept = container.uploads_dir / f"{doc_id}.pdf"
    if kept.exists():
        kept.unlink()
    return Response(status_code=204)
