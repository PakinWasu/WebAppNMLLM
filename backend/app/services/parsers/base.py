"""Base parser class for network device configuration parsers"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any


class BaseParser(ABC):
    """Base class for vendor-specific configuration parsers"""
    
    @abstractmethod
    def detect_vendor(self, content: str) -> bool:
        """Detect if this parser can handle the given configuration content"""
        pass
    
    @abstractmethod
    def parse(self, content: str, filename: str) -> Dict[str, Any]:
        """
        Parse configuration content and return structured data
        
        Returns:
            Dictionary containing all parsed sections:
            - device_overview
            - interfaces
            - vlans
            - stp
            - routing
            - neighbors
            - mac_arp
            - security
            - ha
        """
        pass
    
    @abstractmethod
    def extract_device_overview(self, content: str) -> Dict[str, Any]:
        """Extract device overview information"""
        pass
    
    @abstractmethod
    def extract_interfaces(self, content: str) -> List[Dict[str, Any]]:
        """Extract interface information"""
        pass
    
    @abstractmethod
    def extract_vlans(self, content: str) -> Dict[str, Any]:
        """Extract VLAN information"""
        pass
    
    @abstractmethod
    def extract_stp(self, content: str) -> Dict[str, Any]:
        """Extract Spanning Tree Protocol information"""
        pass
    
    @abstractmethod
    def extract_routing(self, content: str) -> Dict[str, Any]:
        """Extract routing protocol information"""
        pass
    
    @abstractmethod
    def extract_neighbors(self, content: str) -> List[Dict[str, Any]]:
        """Extract neighbor discovery information (CDP/LLDP)"""
        pass
    
    @abstractmethod
    def extract_mac_arp(self, content: str) -> Dict[str, Any]:
        """Extract MAC address table and ARP table information"""
        pass
    
    @abstractmethod
    def extract_security(self, content: str) -> Dict[str, Any]:
        """Extract security and management information"""
        pass
    
    @abstractmethod
    def extract_ha(self, content: str) -> Dict[str, Any]:
        """Extract High Availability information (EtherChannel, HSRP, VRRP)"""
        pass

