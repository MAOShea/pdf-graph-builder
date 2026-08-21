from pydantic import BaseModel, Field
from fastapi import Form
from typing import Optional, Union


def parse_form_flag(value: Optional[Union[str, bool]], *, default: bool = False) -> bool:
    """Parse a FastAPI Form bool (string or bool). Empty/omit → default."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    token = str(value).strip().lower()
    if token in ("1", "true", "yes", "on"):
        return True
    if token in ("", "0", "false", "no", "off"):
        return False
    return default


def skip_extract_llm(ingest_mode: Optional[str], scaffold_diff_llm: bool) -> bool:
    """Skip Ollama only for scaffold-diff when the opt-in flag is off.

    Bottom-up extract always calls the LLM (that mode *is* the extract).
    """
    if ingest_mode == "scaffold-diff":
        return not bool(scaffold_diff_llm)
    return False

class SourceScanExtractParams(BaseModel):
    source_url: Optional[str] = Field(None, description="Source URL")
    aws_access_key_id: Optional[str] = Field(None, description="AWS Access Key ID")
    aws_secret_access_key: Optional[str] = Field(None, description="AWS Secret Access Key")
    wiki_query: Optional[str] = Field(None, description="Wikipedia query")
    model: str = Field(..., description="Model name")
    gcs_bucket_name: Optional[str] = Field(None, description="GCS bucket name")
    gcs_bucket_folder: Optional[str] = Field(None, description="GCS bucket folder")
    source_type: Optional[str] = Field(None, description="Source type")
    gcs_project_id: Optional[str] = Field(None, description="GCS project ID")
    access_token: Optional[str] = Field(None, description="Access token")
    gcs_blob_filename: Optional[str] = Field(None, description="GCS blob filename")
    file_name: Optional[str] = Field(None, description="File name")
    allowedNodes: Optional[str] = Field(None, description="Allowed nodes")
    allowedRelationship: Optional[str] = Field(None, description="Allowed relationships")
    token_chunk_size: Optional[int] = Field(None, description="Token chunk size")
    chunk_overlap: Optional[int] = Field(None, description="Chunk overlap")
    chunks_to_combine: Optional[int] = Field(None, description="Chunks to combine")
    language: Optional[str] = Field(None, description="Language")
    retry_condition: Optional[str] = Field(None, description="Retry condition")
    additional_instructions: Optional[str] = Field(None, description="Additional instructions")
    embedding_provider: Optional[str] = Field(None, description="Embedding provider")
    embedding_model: Optional[str] = Field(None, description="Embedding model")
    ingest_mode: Optional[str] = Field(None, description="'scaffold-diff' for top-down diff against a pre-bootstrapped scaffold, or None for default bottom-up extraction")
    start_page: Optional[int] = Field(None, description="First PDF page to ingest (1-based, inclusive)")
    end_page: Optional[int] = Field(None, description="Last PDF page to ingest (1-based, inclusive)")
    section_phase: Optional[int] = Field(
        None,
        description="Max passage-sections.json phase to materialize and send to LLM (inclusive). Omit to use extract default.",
    )
    scaffold_diff_llm: bool = Field(
        False,
        description=(
            "Scaffold-diff Stage 2: run Ollama LLMGraphTransformer (CONFIRMS_SEED / flags). "
            "Default false — contracts (Stage 1) do not need it. Bottom-up extract ignores this and always calls the LLM."
        ),
    )

def get_source_scan_extract_params(
    source_url: Optional[str] = Form(None),
    aws_access_key_id: Optional[str] = Form(None),
    aws_secret_access_key: Optional[str] = Form(None),
    wiki_query: Optional[str] = Form(None),
    model: str = Form(...),
    gcs_bucket_name: Optional[str] = Form(None),
    gcs_bucket_folder: Optional[str] = Form(None),
    source_type: Optional[str] = Form(None),
    gcs_project_id: Optional[str] = Form(None),
    access_token: Optional[str] = Form(None),
    gcs_blob_filename: Optional[str] = Form(None),
    file_name: Optional[str] = Form(None),
    allowedNodes: Optional[str] = Form(None),
    allowedRelationship: Optional[str] = Form(None),
    token_chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
    chunks_to_combine: Optional[int] = Form(None),
    language: Optional[str] = Form(None),
    retry_condition: Optional[str] = Form(None),
    additional_instructions: Optional[str] = Form(None),
    embedding_provider: Optional[str] = Form(None),
    embedding_model: Optional[str] = Form(None),
    ingest_mode: Optional[str] = Form(None),
    start_page: Optional[int] = Form(None),
    end_page: Optional[int] = Form(None),
    section_phase: Optional[int] = Form(None),
    scaffold_diff_llm: Optional[str] = Form(None),
) -> SourceScanExtractParams:
    return SourceScanExtractParams(
        source_url=source_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        wiki_query=wiki_query,
        model=model,
        gcs_bucket_name=gcs_bucket_name,
        gcs_bucket_folder=gcs_bucket_folder,
        source_type=source_type,
        gcs_project_id=gcs_project_id,
        access_token=access_token,
        gcs_blob_filename=gcs_blob_filename,
        file_name=file_name,
        allowedNodes=allowedNodes,
        allowedRelationship=allowedRelationship,
        token_chunk_size=token_chunk_size,
        chunk_overlap=chunk_overlap,
        chunks_to_combine=chunks_to_combine,
        language=language,
        retry_condition=retry_condition,
        additional_instructions=additional_instructions,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        ingest_mode=ingest_mode,
        start_page=start_page,
        end_page=end_page,
        section_phase=section_phase,
        scaffold_diff_llm=parse_form_flag(scaffold_diff_llm, default=False),
    )