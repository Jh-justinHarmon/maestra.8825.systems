"""
Smart PDF Handler for Maestra Backend

Handles Smart PDF export requests via API.
"""

import sys
import uuid
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Optional imports - these may not exist in production
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "maestra_core"))
    from smart_pdf_export import export_smart_pdf
    from smart_pdf_import import import_smart_pdf
    HAS_SMART_PDF = True
except ImportError:
    logger.warning("Smart PDF modules not available")
    HAS_SMART_PDF = False
    export_smart_pdf = None
    import_smart_pdf = None

from models import (
    SmartPDFExportRequest,
    SmartPDFExportResponse,
    SmartPDFImportRequest,
    SmartPDFImportResponse
)


async def export_smart_pdf_handler(request: SmartPDFExportRequest) -> SmartPDFExportResponse:
    """
    Handle Smart PDF export request.
    
    Args:
        request: Export request with template data
    
    Returns:
        Export response with download URL and metadata
    """
    trace_id = str(uuid.uuid4())
    
    logger.info(f"[{trace_id}] Smart PDF export request: {request.output_filename}")
    
    try:
        # Determine output path
        output_dir = Path(__file__).parent.parent.parent.parent / "output" / "smart_pdfs"
        output_path = output_dir / request.output_filename
        
        # Ensure .pdf extension
        if not output_path.suffix == '.pdf':
            output_path = output_path.with_suffix('.pdf')
        
        # Export
        result = export_smart_pdf(
            template_data=request.template_data,
            output_path=str(output_path),
            edge_config=request.edge_config,
            library_path=None  # TODO: Get from config
        )
        
        if not result.get('success'):
            raise Exception("Export failed")
        
        # Generate download URL (relative to API base)
        download_url = f"/api/maestra/smart-pdf/download/{output_path.name}"
        
        logger.info(f"[{trace_id}] Export successful: {result['manifest']['pdf_id']}")
        
        return SmartPDFExportResponse(
            success=True,
            pdf_id=result['manifest']['pdf_id'],
            download_url=download_url,
            file_size_bytes=result['file_size_bytes'],
            manifest_version=result['manifest']['manifest_version'],
            library_entry_id=result.get('library_entry_id'),
            trace_id=trace_id
        )
        
    except Exception as e:
        logger.error(f"[{trace_id}] Export failed: {e}", exc_info=True)
        raise


async def import_smart_pdf_handler(request: SmartPDFImportRequest) -> SmartPDFImportResponse:
    """
    Handle Smart PDF import request.
    
    Args:
        request: Import request with PDF URL/path
    
    Returns:
        Import response with template data and metadata
    """
    trace_id = str(uuid.uuid4())
    
    logger.info(f"[{trace_id}] Smart PDF import request: {request.pdf_url}")
    
    try:
        # Resolve PDF path (could be URL or local path)
        # For now, assume local path
        pdf_path = Path(request.pdf_url)
        
        if not pdf_path.exists():
            # Try relative to output directory
            output_dir = Path(__file__).parent.parent.parent.parent / "output" / "smart_pdfs"
            pdf_path = output_dir / Path(request.pdf_url).name
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {request.pdf_url}")
        
        # Import
        result = import_smart_pdf(
            pdf_path=str(pdf_path),
            validate_schema=request.validate_schema,
            library_path=None  # TODO: Get from config
        )
        
        if not result.get('success'):
            raise Exception("Import failed")
        
        logger.info(f"[{trace_id}] Import successful: {result['manifest']['pdf_id']}")
        
        return SmartPDFImportResponse(
            success=True,
            template_data=result['template_data'],
            pdf_id=result['manifest']['pdf_id'],
            manifest_version=result['manifest']['manifest_version'],
            library_entry_id=result.get('library_entry_id'),
            imported_at=result['imported_at'],
            trace_id=trace_id
        )
        
    except Exception as e:
        logger.error(f"[{trace_id}] Import failed: {e}", exc_info=True)
        raise
