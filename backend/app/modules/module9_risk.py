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
        Dict with overall_score, risk_level, confidence_level, axes breakdown
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
    
    # Calculate confidence level based on module agreement
    confidence_level = _calculate_confidence(module_results, axis_scores)
    
    # Calculate forgery probability
    forgery_probability = min(overall_score / 100.0 * 0.85, 0.85)
    
    return {
        "overall_score": overall_score,
        "risk_level": risk_level,
        "confidence_level": confidence_level,
        "forgery_probability": round(forgery_probability, 4),
        "axes": axes
    }


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
    """Calculate Visual Authenticity axis score."""
    score = 0
    factors = []
    
    # Module 3: Font fingerprint
    module3 = module_results.get("module3_fingerprint", {})
    
    if isinstance(module3, dict):
        consistency = module3.get("overall_consistency", "Consistent")
        
        if consistency == "Inconsistent":
            score += 25
            factors.append("Inconsistent font usage detected")
        elif consistency == "Mixed":
            score += 12
            factors.append("Mixed font patterns found")
        
        # Font anomalies
        font_anomalies = module3.get("font_anomalies", [])
        if isinstance(font_anomalies, list):
            for anomaly in font_anomalies[:5]:
                if isinstance(anomaly, dict):
                    severity = anomaly.get("severity", "low")
                    location = anomaly.get("location", "Unknown")
                    if severity == "high":
                        score += 15
                        factors.append(f"Critical font anomaly at {location}")
                    elif severity == "medium":
                        score += 8
                        factors.append(f"Font mismatch at {location}")
                    else:
                        score += 3
                        factors.append(f"Minor font variation at {location}")
        
        # Spacing anomalies
        spacing_anomalies = module3.get("spacing_anomalies", [])
        if isinstance(spacing_anomalies, list) and len(spacing_anomalies) > 0:
            score += len(spacing_anomalies) * 3
            factors.append(f"{len(spacing_anomalies)} spacing irregularities detected")
    
    # Module 8: Heatmap (high-intensity tamper regions)
    module8 = module_results.get("heatmap", {})
    
    if isinstance(module8, dict):
        pages = module8.get("pages", [])
        high_intensity_count = 0
        medium_intensity_count = 0
        
        for page in pages:
            if isinstance(page, dict):
                boxes = page.get("boxes", [])
                page_num = page.get("page_number", 0)
                
                for box in boxes:
                    if isinstance(box, dict):
                        intensity = box.get("intensity", "low")
                        if intensity == "high":
                            high_intensity_count += 1
                            reason = box.get("reason", "Unknown")
                            factors.append(f"High-risk region on page {page_num}: {reason}")
                        elif intensity == "medium":
                            medium_intensity_count += 1
        
        score += high_intensity_count * 20
        score += medium_intensity_count * 8
        
        if medium_intensity_count > 0 and high_intensity_count == 0:
            factors.append(f"{medium_intensity_count} medium-risk regions detected")
    
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
    Calculate confidence level based on module agreement.
    
    Args:
        module_results: Dict of module results
        axis_scores: List of 4 axis scores
    
    Returns:
        "High", "Medium", or "Low" confidence level
    """
    # Count successfully executed modules
    successful_modules = 0
    for module_name in ["module2_ocr", "module3_fingerprint", "module5_metadata", 
                        "module6_content", "module7_compliance", "heatmap"]:
        module_result = module_results.get(module_name, {})
        if isinstance(module_result, dict) and not module_result.get("error"):
            successful_modules += 1
    
    # Calculate spread of axis scores
    if len(axis_scores) > 0:
        max_score = max(axis_scores)
        min_score = min(axis_scores)
        spread = max_score - min_score
    else:
        spread = 0
    
    # Determine confidence
    if successful_modules >= 5 and spread <= 20:
        return "High"
    elif successful_modules >= 3 and spread <= 40:
        return "Medium"
    else:
        return "Low"


def _classify_risk(score: int) -> RiskLevel:
    """Map a 0-100 score to a risk level."""
    if score <= 30:
        return "Low"
    elif score <= 60:
        return "Medium"
    else:
        return "High"
