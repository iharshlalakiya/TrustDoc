"""
Module 9 — Multi-Axis Risk Score Calculator.

Implements a calibrated 4-axis scoring system that analyzes:
1. Metadata Integrity
2. Content Consistency
3. Visual Authenticity
4. Compliance Risk

Each axis is scored 0-100 based on severity-weighted flags from multiple modules.
"""

import logging
from typing import Literal, List, Dict, Any

logger = logging.getLogger(__name__)

RiskLevel = Literal["Low", "Medium", "High"]
ConfidenceLevel = Literal["High", "Medium", "Low"]


def calculate_risk_score(module_results: dict) -> dict:
    """
    Compute multi-axis risk score from module results.
    
    Args:
        module_results: Dict of module results from the analysis pipeline
    
    Returns:
        Dict with overall_score, risk_level, confidence_level, axes breakdown, and calibration warnings
    """
    # Calculate each axis score
    axes = {
        "metadata_integrity": _calculate_metadata_axis(module_results),
        "content_consistency": _calculate_content_axis(module_results),
        "visual_authenticity": _calculate_visual_axis(module_results),
        "compliance_risk": _calculate_compliance_axis(module_results)
    }
    
    # Calculate overall score (average of 4 axes)
    axis_scores = [axes[axis]["score"] for axis in axes]
    overall_score = int(round(sum(axis_scores) / len(axis_scores)))
    
    # Determine risk level
    risk_level = _classify_risk(overall_score)
    
    # Check for miscalibration and calculate confidence
    miscalibration_warnings = _detect_miscalibration(module_results)
    confidence_level = _calculate_confidence(module_results, axis_scores)
    
    # Calculate forgery probability
    forgery_probability = min(overall_score / 100.0 * 0.85, 0.85)
    
    result = {
        "overall_score": overall_score,
        "risk_level": risk_level,
        "confidence_level": confidence_level,
        "forgery_probability": round(forgery_probability, 4),
        "axes": axes
    }
    
    # Add calibration warnings if present
    if miscalibration_warnings:
        result["calibration_warnings"] = miscalibration_warnings
    
    return result


def _detect_miscalibration(module_results: dict) -> List[Dict[str, Any]]:
    """Detect modules that may be miscalibrated based on flag rate.
    
    Returns:
        List of warning dicts with module name, flag rate, and message
    """
    warnings = []
    
    for module_name in ["module2_ocr", "module3_fingerprint", "heatmap"]:
        module_result = module_results.get(module_name, {})
        if isinstance(module_result, dict) and not module_result.get("error"):
            flag_rate = _check_module_flag_rate(module_result, module_name)
            
            if flag_rate > 0.4:
                warnings.append({
                    "module": module_name,
                    "flag_rate": round(flag_rate * 100, 1),
                    "message": (
                        f"This module's flag rate ({round(flag_rate * 100, 1)}%) is unusually high "
                        "and may indicate a calibration issue rather than genuine tampering. "
                        "Recommend manual review of this specific module's findings."
                    )
                })
    
    return warnings


def _calculate_metadata_axis(module_results: dict) -> dict:
    """Calculate Metadata Integrity axis score."""
    score = 0
    factors = []
    
    # Module 5: Metadata analysis
    module5 = module_results.get("module5_metadata", {})
    
    if isinstance(module5, dict):
        # Check metadata integrity level
        integrity = module5.get("metadata_integrity", "High")
        if integrity == "Low":
            score += 25
            factors.append("Low metadata integrity detected")
        elif integrity == "Medium":
            score += 12
            factors.append("Medium metadata integrity concerns")
        
        # Check for suspicious patterns
        suspicious = module5.get("suspicious_patterns", [])
        if isinstance(suspicious, list):
            for pattern in suspicious[:3]:  # Limit to top 3
                score += 12
                factors.append(f"Suspicious pattern: {pattern}")
        
        # Check for modified timestamps
        if module5.get("timeline_anomalies"):
            score += 15
            factors.append("Timeline anomalies detected")
    
    score = min(score, 100)
    
    return {
        "score": score,
        "contributing_factors": factors if factors else ["No metadata issues detected"]
    }


def _calculate_content_axis(module_results: dict) -> dict:
    """Calculate Content Consistency axis score."""
    score = 0
    factors = []
    
    # Module 6: Content consistency
    module6 = module_results.get("module6_content", {})
    
    if isinstance(module6, dict):
        # Check contradictions
        contradictions = module6.get("contradictions", [])
        if isinstance(contradictions, list):
            for contradiction in contradictions:
                if isinstance(contradiction, dict):
                    severity = contradiction.get("severity", "medium")
                    if severity == "high":
                        score += 25
                        factors.append(f"Critical contradiction: {contradiction.get('claim', 'Unknown')}")
                    elif severity == "medium":
                        score += 12
                        factors.append(f"Contradiction found: {contradiction.get('claim', 'Unknown')}")
                    else:
                        score += 5
                        factors.append(f"Minor inconsistency: {contradiction.get('claim', 'Unknown')}")
        
        # Check unverified stats
        unverified = module6.get("unverified_external_stats", [])
        if isinstance(unverified, list):
            for stat in unverified[:3]:
                score += 8
                factors.append(f"Unverified claim: {stat}")
    
    # Module 7: Compliance
    module7 = module_results.get("module7_compliance", {})
    
    if isinstance(module7, dict):
        # Check compliance issues
        issues = module7.get("issues", [])
        if isinstance(issues, list):
            for issue in issues:
                if isinstance(issue, dict):
                    severity = issue.get("severity", "medium")
                    if severity == "high":
                        score += 20
                        factors.append(f"Compliance violation: {issue.get('type', 'Unknown')}")
                    elif severity == "medium":
                        score += 10
                        factors.append(f"Compliance concern: {issue.get('type', 'Unknown')}")
    
    score = min(score, 100)
    
    return {
        "score": score,
        "contributing_factors": factors if factors else ["Content appears consistent"]
    }


def _calculate_visual_axis(module_results: dict) -> dict:
    """Calculate Visual Authenticity axis score with category grouping."""
    score = 0
    factors = []
    
    # Track flag categories and their max severity
    category_severities = {}  # {category: max_severity_value}
    
    # Module 3: Font fingerprint
    module3 = module_results.get("module3_fingerprint", {})
    
    if isinstance(module3, dict):
        consistency = module3.get("overall_consistency", "Consistent")
        
        if consistency == "Inconsistent":
            category_severities["font_consistency"] = 25
            factors.append("Inconsistent font usage detected")
        elif consistency == "Mixed":
            category_severities["font_consistency"] = 12
            factors.append("Mixed font patterns found")
        
        # Font anomalies - group by category, take MAX severity
        font_anomalies = module3.get("font_anomalies", [])
        if isinstance(font_anomalies, list) and len(font_anomalies) > 0:
            # Find the highest severity among all font anomalies
            max_severity = 0
            for anomaly in font_anomalies:
                if isinstance(anomaly, dict):
                    severity = anomaly.get("severity", "low")
                    if severity == "high":
                        max_severity = max(max_severity, 15)
                    elif severity == "medium":
                        max_severity = max(max_severity, 8)
                    else:
                        max_severity = max(max_severity, 3)
            
            if max_severity > 0:
                category_severities["font_anomalies"] = max_severity
                factors.append(f"{len(font_anomalies)} font variation(s) detected")
        
        # Spacing anomalies - group into single category
        spacing_anomalies = module3.get("spacing_anomalies", [])
        if isinstance(spacing_anomalies, list) and len(spacing_anomalies) > 0:
            category_severities["spacing_anomalies"] = 3 * min(len(spacing_anomalies), 3)  # Cap contribution
            factors.append(f"{len(spacing_anomalies)} spacing irregularit{'y' if len(spacing_anomalies)==1 else 'ies'}")
    
    # Module 8: Heatmap (high-intensity tamper regions)
    module8 = module_results.get("heatmap", {})
    
    if isinstance(module8, dict):
        pages = module8.get("pages", [])
        high_intensity_boxes = []
        medium_intensity_boxes = []
        
        for page in pages:
            if isinstance(page, dict):
                boxes = page.get("boxes", [])
                page_num = page.get("page_number", 0)
                
                for box in boxes:
                    if isinstance(box, dict):
                        intensity = box.get("intensity", "low")
                        if intensity == "high":
                            high_intensity_boxes.append((page_num, box.get("reason", "Unknown")))
                        elif intensity == "medium":
                            medium_intensity_boxes.append((page_num, box.get("reason", "Unknown")))
        
        # Group tamper regions by category
        if high_intensity_boxes:
            category_severities["high_tamper_regions"] = 20
            # Show up to 2 examples
            for page_num, reason in high_intensity_boxes[:2]:
                factors.append(f"High-risk region on page {page_num}: {reason}")
            if len(high_intensity_boxes) > 2:
                factors.append(f"+ {len(high_intensity_boxes) - 2} more high-risk region(s)")
        
        if medium_intensity_boxes:
            category_severities["medium_tamper_regions"] = 8
            if not high_intensity_boxes:  # Only show if no high-intensity
                factors.append(f"{len(medium_intensity_boxes)} medium-risk region(s) detected")
    
    # Sum across distinct categories (not individual flags)
    score = sum(category_severities.values())
    score = min(score, 100)
    
    return {
        "score": score,
        "contributing_factors": factors if factors else ["Visual elements appear authentic"]
    }


def _calculate_compliance_axis(module_results: dict) -> dict:
    """Calculate Compliance Risk axis score."""
    score = 0
    factors = []
    
    # Module 7: Compliance review
    module7 = module_results.get("module7_compliance", {})
    
    if isinstance(module7, dict):
        risk_level = module7.get("risk_level", "Low")
        
        if risk_level == "High":
            score += 40
            factors.append("High compliance risk level")
        elif risk_level == "Medium":
            score += 20
            factors.append("Medium compliance risk level")
        elif risk_level == "Low":
            score += 5
            factors.append("Low compliance risk level")
        
        # Check specific issues
        issues = module7.get("issues", [])
        if isinstance(issues, list):
            for issue in issues[:5]:
                if isinstance(issue, dict):
                    issue_type = issue.get("type", "Unknown")
                    severity = issue.get("severity", "medium")
                    
                    if severity == "high":
                        score += 15
                        factors.append(f"Critical: {issue_type}")
                    elif severity == "medium":
                        score += 8
                        factors.append(f"Warning: {issue_type}")
                    else:
                        score += 3
        
        # Check flags
        flags = module7.get("flags", [])
        if isinstance(flags, list):
            for flag in flags[:3]:
                score += 5
                factors.append(f"Compliance flag: {flag}")
    
    score = min(score, 100)
    
    return {
        "score": score,
        "contributing_factors": factors if factors else ["No compliance issues detected"]
    }


def _calculate_confidence(module_results: dict, axis_scores: List[int]) -> ConfidenceLevel:
    """
    Calculate confidence level based on module agreement and calibration sanity checks.
    
    Args:
        module_results: Dict of module results
        axis_scores: List of 4 axis scores
    
    Returns:
        "High", "Medium", or "Low" confidence level
    """
    # Count successfully executed modules
    successful_modules = 0
    potentially_miscalibrated = []
    
    for module_name in ["module2_ocr", "module3_fingerprint", "module5_metadata", 
                        "module6_content", "module7_compliance", "heatmap"]:
        module_result = module_results.get(module_name, {})
        if isinstance(module_result, dict) and not module_result.get("error"):
            successful_modules += 1
            
            # BUG 4: Sanity check for miscalibration
            # If a module flags >40% of analyzed regions, it may be miscalibrated
            flag_rate = _check_module_flag_rate(module_result, module_name)
            if flag_rate > 0.4:
                potentially_miscalibrated.append({
                    "module": module_name,
                    "flag_rate": flag_rate
                })
    
    # Calculate spread of axis scores
    if len(axis_scores) > 0:
        max_score = max(axis_scores)
        min_score = min(axis_scores)
        spread = max_score - min_score
    else:
        spread = 0
    
    # Downgrade confidence if miscalibration detected
    if potentially_miscalibrated:
        return "Low"  # Miscalibration is a critical issue
    
    # Determine confidence based on module success and agreement
    if successful_modules >= 5 and spread <= 20:
        return "High"
    elif successful_modules >= 3 and spread <= 40:
        return "Medium"
    else:
        return "Low"


def _check_module_flag_rate(module_result: dict, module_name: str) -> float:
    """
    Check if a module is flagging an unusually high percentage of content.
    
    Returns:
        Flag rate (0.0 to 1.0) representing percentage of content flagged
    """
    if module_name == "module3_fingerprint":
        # Check font anomaly rate
        font_anomalies = module_result.get("font_anomalies", [])
        # If we have dominant fonts data, calculate ratio
        dominant_fonts = module_result.get("dominant_fonts", {})
        if dominant_fonts and font_anomalies:
            # Rough estimate: if >20 anomalies per page, likely miscalibrated
            pages = len(dominant_fonts)
            if pages > 0:
                anomalies_per_page = len(font_anomalies) / pages
                if anomalies_per_page > 20:
                    return min(1.0, anomalies_per_page / 50)  # Normalize to 0-1
    
    elif module_name == "heatmap":
        # Check heatmap box flagging rate
        pages = module_result.get("pages", [])
        if pages:
            total_boxes = sum(len(p.get("boxes", [])) for p in pages)
            total_pages = len(pages)
            if total_pages > 0:
                boxes_per_page = total_boxes / total_pages
                # If >15 flagged boxes per page on average, likely over-flagging
                if boxes_per_page > 15:
                    return min(1.0, boxes_per_page / 30)
    
    elif module_name == "module2_ocr":
        anomalies = module_result.get("anomalies_found", [])
        # If >10 OCR anomalies, may be miscalibrated
        if len(anomalies) > 10:
            return min(1.0, len(anomalies) / 20)
    
    return 0.0  # No miscalibration detected


def _classify_risk(score: int) -> RiskLevel:
    """Map a 0-100 score to a risk level."""
    if score <= 30:
        return "Low"
    elif score <= 60:
        return "Medium"
    else:
        return "High"
