from collections import Counter, defaultdict
from typing import Dict, List, Any, Tuple
from pathlib import Path
import statistics

from pptx import Presentation
from pptx.util import Pt, Emu
import fitz  # PyMuPDF
from docx import Document


def analyze_font_fingerprint(file_path: str, file_type: str) -> dict:
    """
    Analyze font consistency and detect formatting anomalies.
    
    Args:
        file_path: Path to the file
        file_type: 'pptx', 'pdf', or 'docx'
    
    Returns:
        Dict with consistency analysis, dominant fonts, and anomalies
    """
    if file_type == "pptx":
        return _analyze_pptx_fonts(file_path)
    elif file_type == "pdf":
        return _analyze_pdf_fonts(file_path)
    elif file_type == "docx":
        return _analyze_docx_fonts(file_path)
    else:
        return {
            "overall_consistency": "Unknown",
            "confidence": 0.0,
            "dominant_fonts": {},
            "font_anomalies": [],
            "spacing_anomalies": []
        }


def _analyze_pptx_fonts(file_path: str) -> dict:
    """Analyze font fingerprint for PPTX files."""
    prs = Presentation(file_path)
    dominant_fonts = {}
    font_anomalies = []
    spacing_anomalies = []
    
    for slide_idx, slide in enumerate(prs.slides):
        slide_num = slide_idx + 1
        slide_fonts = []
        slide_spacings = []
        
        # Extract all font runs and spacing from this slide
        for shape in slide.shapes:
            if not hasattr(shape, "text_frame"):
                continue
            
            for para_idx, paragraph in enumerate(shape.text_frame.paragraphs):
                # Collect spacing info
                if paragraph.space_before is not None:
                    slide_spacings.append(("before", int(paragraph.space_before)))
                if paragraph.space_after is not None:
                    slide_spacings.append(("after", int(paragraph.space_after)))
                
                para_fonts = []
                for run in paragraph.runs:
                    font_info = _extract_font_info_pptx(run)
                    if font_info:
                        slide_fonts.append(font_info)
                        para_fonts.append(font_info)
                
                # Detect font mixing within a single paragraph
                if len(para_fonts) > 1:
                    para_font_families = [f["family"] for f in para_fonts]
                    if len(set(para_font_families)) > 1:
                        font_anomalies.append({
                            "location": f"Slide {slide_num}, paragraph {para_idx + 1}",
                            "expected_font": para_font_families[0],
                            "found_font": ", ".join(set(para_font_families[1:])),
                            "severity": "medium"
                        })
        
        # Determine dominant font for this slide
        if slide_fonts:
            font_counter = Counter([f["signature"] for f in slide_fonts])
            dominant_sig = font_counter.most_common(1)[0][0]
            dominant_fonts[f"slide_{slide_num}"] = dominant_sig
            
            # Flag runs that deviate from dominant
            for font_info in slide_fonts:
                if font_info["signature"] != dominant_sig and font_counter[font_info["signature"]] < 3:
                    # Only flag if it's rare (appears less than 3 times)
                    if not any(a.get("found_font") == font_info["family"] for a in font_anomalies):
                        font_anomalies.append({
                            "location": f"Slide {slide_num}",
                            "expected_font": dominant_sig,
                            "found_font": font_info["signature"],
                            "severity": "low"
                        })
        
        # Detect spacing anomalies
        if len(slide_spacings) > 2:
            spacing_values = [v for _, v in slide_spacings]
            median_spacing = statistics.median(spacing_values)
            
            for spacing_type, value in slide_spacings:
                if median_spacing > 0 and value > median_spacing * 2:
                    spacing_anomalies.append({
                        "location": f"Slide {slide_num}",
                        "expected_spacing": f"{int(median_spacing / 12700)}pt",
                        "found_spacing": f"{int(value / 12700)}pt",
                        "severity": "low"
                    })
                    break  # Only report once per slide
    
    # Calculate overall consistency
    overall_consistency, confidence = _calculate_consistency(
        dominant_fonts, font_anomalies, spacing_anomalies
    )
    
    return {
        "overall_consistency": overall_consistency,
        "confidence": confidence,
        "dominant_fonts": dominant_fonts,
        "font_anomalies": font_anomalies[:10],  # Limit to top 10
        "spacing_anomalies": spacing_anomalies[:10]
    }


def _analyze_pdf_fonts(file_path: str) -> dict:
    """Analyze font fingerprint for PDF files."""
    doc = fitz.open(file_path)
    dominant_fonts = {}
    font_anomalies = []
    spacing_anomalies = []
    
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_num = page_idx + 1
        page_fonts = []
        
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if block.get("type") != 0:  # Skip non-text blocks
                continue
            
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    font_info = _extract_font_info_pdf(span)
                    if font_info:
                        page_fonts.append(font_info)
        
        # Determine dominant font for this page
        if page_fonts:
            font_counter = Counter([f["signature"] for f in page_fonts])
            dominant_sig = font_counter.most_common(1)[0][0]
            dominant_fonts[f"page_{page_num}"] = dominant_sig
            
            # Flag fonts that deviate significantly
            for font_info in page_fonts:
                if font_info["signature"] != dominant_sig and font_counter[font_info["signature"]] < 3:
                    if not any(a.get("found_font") == font_info["family"] for a in font_anomalies):
                        font_anomalies.append({
                            "location": f"Page {page_num}",
                            "expected_font": dominant_sig,
                            "found_font": font_info["signature"],
                            "severity": "low"
                        })
    
    doc.close()
    
    # Calculate overall consistency
    overall_consistency, confidence = _calculate_consistency(
        dominant_fonts, font_anomalies, spacing_anomalies
    )
    
    return {
        "overall_consistency": overall_consistency,
        "confidence": confidence,
        "dominant_fonts": dominant_fonts,
        "font_anomalies": font_anomalies[:10],
        "spacing_anomalies": spacing_anomalies[:10]
    }


def _analyze_docx_fonts(file_path: str) -> dict:
    """Analyze font fingerprint for DOCX files."""
    doc = Document(file_path)
    dominant_fonts = {}
    font_anomalies = []
    spacing_anomalies = []
    
    # Group paragraphs by section (simplified: just sequential blocks)
    section_fonts = []
    section_spacings = []
    section_num = 1
    
    for para_idx, paragraph in enumerate(doc.paragraphs):
        # Collect spacing info
        if paragraph.paragraph_format.space_before is not None:
            section_spacings.append(("before", int(paragraph.paragraph_format.space_before)))
        if paragraph.paragraph_format.space_after is not None:
            section_spacings.append(("after", int(paragraph.paragraph_format.space_after)))
        
        para_fonts = []
        for run in paragraph.runs:
            font_info = _extract_font_info_docx(run)
            if font_info:
                section_fonts.append(font_info)
                para_fonts.append(font_info)
        
        # Detect font mixing within a paragraph
        if len(para_fonts) > 1:
            para_font_families = [f["family"] for f in para_fonts]
            if len(set(para_font_families)) > 1:
                font_anomalies.append({
                    "location": f"Paragraph {para_idx + 1}",
                    "expected_font": para_font_families[0],
                    "found_font": ", ".join(set(para_font_families[1:])),
                    "severity": "medium"
                })
        
        # Every 10 paragraphs, analyze as a section
        if (para_idx + 1) % 10 == 0 or para_idx == len(doc.paragraphs) - 1:
            if section_fonts:
                font_counter = Counter([f["signature"] for f in section_fonts])
                dominant_sig = font_counter.most_common(1)[0][0]
                dominant_fonts[f"section_{section_num}"] = dominant_sig
                section_num += 1
                section_fonts = []
            
            # Check spacing anomalies
            if len(section_spacings) > 2:
                spacing_values = [v for _, v in section_spacings]
                median_spacing = statistics.median(spacing_values)
                
                for spacing_type, value in section_spacings:
                    if median_spacing > 0 and value > median_spacing * 2:
                        spacing_anomalies.append({
                            "location": f"Section {section_num - 1}",
                            "expected_spacing": f"{int(median_spacing / 12700)}pt",
                            "found_spacing": f"{int(value / 12700)}pt",
                            "severity": "low"
                        })
                        break
                
                section_spacings = []
    
    # Calculate overall consistency
    overall_consistency, confidence = _calculate_consistency(
        dominant_fonts, font_anomalies, spacing_anomalies
    )
    
    return {
        "overall_consistency": overall_consistency,
        "confidence": confidence,
        "dominant_fonts": dominant_fonts,
        "font_anomalies": font_anomalies[:10],
        "spacing_anomalies": spacing_anomalies[:10]
    }


def _extract_font_info_pptx(run) -> dict:
    """Extract font information from a PPTX run."""
    try:
        font = run.font
        family = font.name if font.name else "Default"
        size = int(font.size.pt) if font.size else 12
        bold = font.bold if font.bold is not None else False
        italic = font.italic if font.italic is not None else False
        
        signature = f"{family} {size}pt"
        if bold:
            signature += " Bold"
        if italic:
            signature += " Italic"
        
        return {
            "family": family,
            "size": size,
            "bold": bold,
            "italic": italic,
            "signature": signature
        }
    except:
        return None


def _extract_font_info_pdf(span: dict) -> dict:
    """Extract font information from a PDF span."""
    try:
        font_name = span.get("font", "Unknown")
        size = int(span.get("size", 12))
        flags = span.get("flags", 0)
        
        # Parse flags: bit 0 = superscript, bit 1 = italic, bit 2 = serifed, bit 4 = bold
        bold = bool(flags & 16)
        italic = bool(flags & 2)
        
        # Clean font name (remove subset prefix like "ABCDEF+")
        if "+" in font_name:
            font_name = font_name.split("+", 1)[1]
        
        signature = f"{font_name} {size}pt"
        if bold:
            signature += " Bold"
        if italic:
            signature += " Italic"
        
        return {
            "family": font_name,
            "size": size,
            "bold": bold,
            "italic": italic,
            "signature": signature
        }
    except:
        return None


def _extract_font_info_docx(run) -> dict:
    """Extract font information from a DOCX run."""
    try:
        font = run.font
        family = font.name if font.name else "Default"
        size = int(font.size.pt) if font.size else 12
        bold = font.bold if font.bold is not None else False
        italic = font.italic if font.italic is not None else False
        
        signature = f"{family} {size}pt"
        if bold:
            signature += " Bold"
        if italic:
            signature += " Italic"
        
        return {
            "family": family,
            "size": size,
            "bold": bold,
            "italic": italic,
            "signature": signature
        }
    except:
        return None


def _calculate_consistency(
    dominant_fonts: dict, font_anomalies: list, spacing_anomalies: list
) -> Tuple[str, float]:
    """
    Calculate overall consistency rating and confidence.
    
    Returns:
        Tuple of (consistency_level, confidence_score)
    """
    total_anomalies = len(font_anomalies) + len(spacing_anomalies)
    pages_count = len(dominant_fonts)
    
    if pages_count == 0:
        return "Unknown", 0.0
    
    # Check if dominant fonts are consistent across pages/slides
    dominant_values = list(dominant_fonts.values())
    unique_dominants = len(set(dominant_values))
    
    # Calculate anomaly ratio
    anomaly_ratio = total_anomalies / max(pages_count, 1)
    
    # Determine consistency level
    if anomaly_ratio > 2.0 or unique_dominants > pages_count * 0.7:
        consistency = "Inconsistent"
        confidence = 0.85
    elif anomaly_ratio > 0.5 or unique_dominants > pages_count * 0.3:
        consistency = "Mixed"
        confidence = 0.75
    else:
        consistency = "Consistent"
        confidence = 0.90
    
    return consistency, confidence
