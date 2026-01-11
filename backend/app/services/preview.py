from pathlib import Path
from typing import Optional, Dict, Any
import base64
from PIL import Image
import io

# Try to import PDF libraries (optional dependencies)
try:
    from pdf2image import convert_from_bytes
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

MAX_PREVIEW_SIZE = (1200, 900)  # Max dimensions for image preview (increased for better quality)
TEXT_PREVIEW_LENGTH = 100000  # Characters for text preview (increased for full file display)


async def generate_preview(file_path: Path, content_type: str) -> Dict[str, Any]:
    """
    Generate preview for a file based on its content type.
    Returns dict with preview_type and preview_data.
    """
    if not file_path.exists():
        return {"preview_type": "error", "preview_data": "File not found"}
    
    # Read file content
    with open(file_path, 'rb') as f:
        file_content = f.read()
    
    # Handle different content types
    if content_type.startswith("image/"):
        return await _generate_image_preview(file_content)
    elif content_type == "application/pdf":
        return await _generate_pdf_preview(file_content)
    elif content_type.startswith("text/"):
        return await _generate_text_preview(file_content)
    else:
        return {"preview_type": "unsupported", "preview_data": f"Preview not available for {content_type}"}


async def _generate_image_preview(file_content: bytes) -> Dict[str, Any]:
    """Generate thumbnail preview for image"""
    try:
        image = Image.open(io.BytesIO(file_content))
        
        # Convert to RGB if necessary (for PNG with transparency)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        # Resize if larger than max size
        image.thumbnail(MAX_PREVIEW_SIZE, Image.Resampling.LANCZOS)
        
        # Convert to base64
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return {
            "preview_type": "image",
            "preview_data": f"data:image/jpeg;base64,{img_base64}",
            "width": image.width,
            "height": image.height
        }
    except Exception as e:
        return {"preview_type": "error", "preview_data": f"Failed to generate image preview: {str(e)}"}


async def _generate_pdf_preview(file_content: bytes) -> Dict[str, Any]:
    """Generate preview for PDF (first page as image)"""
    if not PDF_AVAILABLE:
        return {"preview_type": "unsupported", "preview_data": "PDF preview requires pdf2image library"}
    
    try:
        # Convert first page to image
        images = convert_from_bytes(file_content, first_page=1, last_page=1, dpi=150)
        if not images:
            return {"preview_type": "error", "preview_data": "Failed to extract PDF page"}
        
        image = images[0]
        
        # Resize if larger than max size
        image.thumbnail(MAX_PREVIEW_SIZE, Image.Resampling.LANCZOS)
        
        # Convert to base64
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return {
            "preview_type": "image",
            "preview_data": f"data:image/jpeg;base64,{img_base64}",
            "width": image.width,
            "height": image.height,
            "note": "First page preview"
        }
    except Exception as e:
        return {"preview_type": "error", "preview_data": f"Failed to generate PDF preview: {str(e)}"}


async def _generate_text_preview(file_content: bytes) -> Dict[str, Any]:
    """Generate text preview (first N characters)"""
    try:
        # Try to decode as UTF-8
        text = file_content.decode('utf-8', errors='replace')
        
        # Truncate if too long
        if len(text) > TEXT_PREVIEW_LENGTH:
            text = text[:TEXT_PREVIEW_LENGTH] + "..."
        
        return {
            "preview_type": "text",
            "preview_data": text,
            "truncated": len(file_content) > TEXT_PREVIEW_LENGTH
        }
    except Exception as e:
        return {"preview_type": "error", "preview_data": f"Failed to generate text preview: {str(e)}"}

