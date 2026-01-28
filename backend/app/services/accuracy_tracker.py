"""Accuracy Tracking Service - Compares AI Output vs Human Final Version"""

from typing import Dict, Any, List
from datetime import datetime
import json


class AccuracyTracker:
    """Tracks accuracy by comparing AI draft vs Human verified version"""
    
    @staticmethod
    def calculate_accuracy(
        ai_draft: Dict[str, Any],
        verified_version: Dict[str, Any],
        reviewer: str
    ) -> Dict[str, Any]:
        """
        Calculate accuracy metrics by comparing AI draft with human verified version.
        
        Args:
            ai_draft: Original AI-generated analysis
            verified_version: Human-edited final version
            reviewer: Username of reviewer
        
        Returns:
            AccuracyMetrics dict with accuracy score and field changes
        """
        
        def flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
            """Flatten nested dictionary"""
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten_dict(v, new_key, sep=sep).items())
                elif isinstance(v, list):
                    # Handle lists by converting to string for comparison
                    items.append((new_key, json.dumps(v, sort_keys=True)))
                else:
                    items.append((new_key, v))
            return dict(items)
        
        # Flatten both dictionaries for comparison
        ai_flat = flatten_dict(ai_draft)
        verified_flat = flatten_dict(verified_version)
        
        # Get all unique keys
        all_keys = set(ai_flat.keys()) | set(verified_flat.keys())
        total_fields = len(all_keys)
        
        # Track changes
        field_changes = []
        corrected_fields = 0
        
        for key in all_keys:
            ai_value = ai_flat.get(key)
            verified_value = verified_flat.get(key)
            
            # Check if values differ
            if ai_value != verified_value:
                corrected_fields += 1
                change_type = "modified"
                
                if key not in ai_flat:
                    change_type = "added"
                elif key not in verified_flat:
                    change_type = "removed"
                
                field_changes.append({
                    "field": key,
                    "change_type": change_type,
                    "ai_value": ai_value,
                    "verified_value": verified_value
                })
        
        # Calculate accuracy score (percentage)
        accuracy_score = ((total_fields - corrected_fields) / total_fields * 100) if total_fields > 0 else 0.0
        
        return {
            "total_fields": total_fields,
            "corrected_fields": corrected_fields,
            "accuracy_score": round(accuracy_score, 2),
            "field_changes": field_changes,
            "verified_at": datetime.utcnow(),
            "verified_by": reviewer
        }
    
    @staticmethod
    def generate_diff_summary(
        ai_draft: Dict[str, Any],
        verified_version: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a summary of differences for UI display.
        
        Returns:
            Dict with summary statistics and key changes
        """
        
        accuracy_data = AccuracyTracker.calculate_accuracy(
            ai_draft, 
            verified_version, 
            "system"  # Placeholder, actual reviewer will be set during verification
        )
        
        # Categorize changes by type
        changes_by_type = {}
        for change in accuracy_data["field_changes"]:
            change_type = change["change_type"]
            if change_type not in changes_by_type:
                changes_by_type[change_type] = []
            changes_by_type[change_type].append(change)
        
        return {
            "total_changes": accuracy_data["corrected_fields"],
            "accuracy_score": accuracy_data["accuracy_score"],
            "changes_by_type": changes_by_type,
            "key_changes": accuracy_data["field_changes"][:10]  # Top 10 changes
        }


# Singleton instance
accuracy_tracker = AccuracyTracker()
