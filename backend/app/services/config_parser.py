"""Main config parser service that routes to vendor-specific parsers"""

from typing import Dict, Any, Optional
from .parsers.cisco import CiscoParser
from .parsers.huawei import HuaweiParser


class ConfigParser:
    """Main parser service that detects vendor and routes to appropriate parser"""
    
    def __init__(self):
        # Put HuaweiParser first because it has more specific patterns
        # and CiscoParser might match Huawei configs incorrectly
        self.parsers = [
            HuaweiParser(),  # Check Huawei first (more specific)
            CiscoParser(),   # Then check Cisco
        ]
    
    def parse_config(self, content: str, filename: str) -> Optional[Dict[str, Any]]:
        """
        Parse configuration content and return structured data
        
        Args:
            content: Configuration file content as string
            filename: Original filename (for fallback device name extraction)
        
        Returns:
            Dictionary with parsed data or None if no parser matches
        """
        # Try each parser to detect vendor
        for parser in self.parsers:
            if parser.detect_vendor(content):
                try:
                    parsed_data = parser.parse(content, filename)
                    # Add vendor info
                    parsed_data["vendor"] = self._get_vendor_name(parser)
                    return parsed_data
                except Exception as e:
                    # Log error but continue
                    print(f"Error parsing config with {type(parser).__name__}: {e}")
                    return None
        
        return None
    
    def extract_device_name(self, content: str, filename: str) -> str:
        """
        Extract device name from config content or filename
        
        Args:
            content: Configuration file content
            filename: Original filename
        
        Returns:
            Device name string
        """
        import re
        import os
        
        # Try to extract from prompt in log files (e.g., <ACC1>display...)
        prompt_match = re.search(r'<(\S+)>', content)
        if prompt_match:
            device_name = prompt_match.group(1)
            # Remove common suffixes that might be in prompt
            device_name = device_name.split()[0] if ' ' in device_name else device_name
            return device_name
        
        # Try to extract from config content
        # Cisco hostname
        hostname_match = re.search(r'hostname\s+(\S+)', content, re.IGNORECASE)
        if hostname_match:
            return hostname_match.group(1)
        
        # Huawei sysname
        sysname_match = re.search(r'sysname\s+(\S+)', content, re.IGNORECASE)
        if sysname_match:
            return sysname_match.group(1)
        
        # Try from comment
        device_match = re.search(r'!.*DEVICE:\s*(\S+)', content, re.IGNORECASE)
        if device_match:
            return device_match.group(1)
        
        # Fallback to filename (remove extension and common prefixes)
        base_name = os.path.splitext(filename)[0]
        # Remove common prefixes like "2026-01-11_topo_real"
        base_name = re.sub(r'^\d{4}-\d{2}-\d{2}_[^_]+_real', '', base_name)
        return base_name if base_name else os.path.splitext(filename)[0]
    
    def _get_vendor_name(self, parser) -> str:
        """Get vendor name string from parser instance"""
        parser_name = type(parser).__name__.lower()
        if "cisco" in parser_name:
            return "cisco"
        elif "huawei" in parser_name:
            return "huawei"
        else:
            return "unknown"

