"""
Extract only the actual configuration content from raw session logs.
Start at the line containing show running-config / display current-configuration (or startup/saved).
End at 'return' (Huawei) or 'end' (Cisco).
Removes pagination and noisy comments within that range.
Command phrases are defined once; regex and substring checks are derived from them.
"""

import re
from typing import Optional, Tuple

# Single source of truth: phrases that start a config block (lowercase for matching).
# Add or change here only; regex and vendor detection are derived from this.
CONFIG_COMMAND_PHRASES: Tuple[str, ...] = (
    "display current-configuration",
    "display saved-configuration",
    "show running-config",
    "show startup-config",
)

# Build regex from CONFIG_COMMAND_PHRASES (single source of truth)
def _build_config_command_regex(phrases: Tuple[str, ...]) -> "re.Pattern":
    escaped = [re.escape(phrase) for phrase in phrases]
    pattern = "|".join(escaped)
    return re.compile(pattern, re.IGNORECASE)

RE_CONFIG_COMMAND = _build_config_command_regex(CONFIG_COMMAND_PHRASES)


# Normalize: unicode dashes and line endings so regex matches reliably
def _normalize_text(raw: str) -> str:
    if not raw:
        return raw
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    for u in ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212", "\u2015"):
        text = text.replace(u, "-")
    return text


def _detect_vendor(raw_text: str) -> str:
    """Return 'huawei', 'cisco', or 'unknown'. Uses CONFIG_COMMAND_PHRASES + content hints."""
    raw_lower = raw_text.lower()
    for phrase in CONFIG_COMMAND_PHRASES:
        if phrase in raw_lower:
            if phrase.startswith("display "):
                return "huawei"
            if phrase.startswith("show "):
                return "cisco"
    if re.search(r"#\s*sysname\s+", raw_text) or re.search(r"#\s*version\s+", raw_text):
        return "huawei"
    if re.search(r"^\s*version\s+\d+", raw_text, re.MULTILINE | re.IGNORECASE):
        return "cisco"
    if "Building configuration" in raw_text or "Current configuration :" in raw_text:
        return "cisco"
    return "unknown"


def _line_has_config_command(line: str) -> bool:
    """True if line contains any config command (regex first, then substring from CONFIG_COMMAND_PHRASES)."""
    if RE_CONFIG_COMMAND.search(line):
        return True
    line_lower = line.lower()
    for phrase in CONFIG_COMMAND_PHRASES:
        if phrase in line_lower:
            return True
    return False


def _find_config_command_line(lines: list, normalized_lines: Optional[list] = None) -> Optional[int]:
    """Return index of first line that contains any of the four config commands."""
    search_list = normalized_lines if normalized_lines is not None and len(normalized_lines) == len(lines) else lines
    for i, line in enumerate(search_list):
        if _line_has_config_command(line):
            return i
    return None


def _extract_huawei(raw_text: str) -> str:
    """
    Huawei: start at line containing display current-configuration or display saved-configuration.
    End at line that is exactly 'return' or at shell prompt <...> / [...].
    """
    raw_text = _normalize_text(raw_text)
    lines = raw_text.splitlines()
    start_idx = _find_config_command_line(lines)
    if start_idx is None:
        return ""

    end_idx: Optional[int] = None
    for i in range(start_idx, len(lines)):
        stripped = lines[i].strip()
        if stripped == "return":
            end_idx = i + 1  # include 'return'
            break
        if re.match(r"^<[\w\-]+>", stripped) or re.match(r"^\[[\w\-]+\]", stripped):
            end_idx = i  # exclude next prompt
            break
    if end_idx is None:
        end_idx = len(lines)

    selected = lines[start_idx : end_idx]
    out = []
    for line in selected:
        s = line.strip()
        if re.match(r"^\s*----\s*More\s*----\s*$", line, re.IGNORECASE):
            continue
        if re.match(r"!\s*Software Version\s+", s, re.IGNORECASE):
            continue
        if re.match(r"!\s*.*Version\s+.*\d+\.\d+", s, re.IGNORECASE) and "configuration" not in s.lower():
            continue
        out.append(line)
    return "\n".join(out)


def _extract_cisco(raw_text: str) -> str:
    """
    Cisco: start at line containing show running-config or show startup-config.
    Skip immediately following 'Building configuration...' and 'Current configuration : ... bytes'.
    End at line that is exactly 'end'.
    """
    raw_text = _normalize_text(raw_text)
    lines = raw_text.splitlines()
    cmd_idx = _find_config_command_line(lines)
    if cmd_idx is None:
        return ""

    start_idx = cmd_idx
    # Skip header lines right after the command
    for i in range(cmd_idx + 1, min(cmd_idx + 10, len(lines))):
        stripped = lines[i].strip()
        if re.match(r"Building configuration\.\.\.", stripped, re.IGNORECASE):
            continue
        if re.match(r"Current configuration\s*:\s*\d+\s*bytes", stripped, re.IGNORECASE):
            continue
        if stripped:
            start_idx = i
            break

    end_idx: Optional[int] = None
    for i in range(start_idx, len(lines)):
        stripped = lines[i].strip()
        if stripped == "end":
            end_idx = i + 1
            break
    if end_idx is None:
        end_idx = len(lines)

    selected = lines[start_idx : end_idx]
    out = []
    for line in selected:
        s = line.strip()
        if re.search(r"!\s*Last configuration change at\s+", s, re.IGNORECASE):
            continue
        if re.search(r"!\s*NTPI\s+", s, re.IGNORECASE):
            continue
        if re.search(r"!\s*Time:\s*[\w\-\:]+\s+\d{4}", s, re.IGNORECASE):
            continue
        out.append(line)
    return "\n".join(out)


def extract_config_content(raw_log_text: str) -> str:
    """
    Extract only the config block from raw session log.
    Start: first line containing show running-config | display current-configuration | show startup-config | display saved-configuration.
    End: 'return' (Huawei) or 'end' (Cisco).
    If no such block is found, returns empty string (caller may fall back to raw).
    """
    if not raw_log_text or not isinstance(raw_log_text, str):
        return raw_log_text or ""

    raw_log_text = _normalize_text(raw_log_text)
    vendor = _detect_vendor(raw_log_text)
    if vendor == "huawei":
        return _extract_huawei(raw_log_text)
    if vendor == "cisco":
        return _extract_cisco(raw_log_text)
    # Unknown vendor: still try to find any config command and slice until return/end
    lines = raw_log_text.splitlines()
    cmd_idx = _find_config_command_line(lines)
    if cmd_idx is None:
        return ""
    raw_lower = raw_log_text.lower()
    for phrase in CONFIG_COMMAND_PHRASES:
        if phrase in raw_lower:
            if phrase.startswith("display "):
                return _extract_huawei(raw_log_text)
            if phrase.startswith("show "):
                return _extract_cisco(raw_log_text)
            break
    # Generic: from command line until "return" or "end"
    end_idx = None
    for i in range(cmd_idx, len(lines)):
        s = lines[i].strip()
        if s == "return" or s == "end":
            end_idx = i + 1 if s == "end" else i
            break
    if end_idx is None:
        end_idx = len(lines)
    return "\n".join(lines[cmd_idx : end_idx])
