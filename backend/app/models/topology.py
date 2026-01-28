from pydantic import BaseModel
from typing import Dict, List, Optional, Any

class TopologyLayoutUpdate(BaseModel):
    """Model for updating topology layout (positions and links)"""
    positions: Dict[str, Dict[str, float]]  # {node_id: {x: float, y: float}}
    links: List[Dict[str, Any]]  # List of link objects with a, b, type, label, etc.
    node_labels: Optional[Dict[str, str]] = None  # {node_id: label}
    node_roles: Optional[Dict[str, str]] = None  # {node_id: role}
