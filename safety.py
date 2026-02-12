"""Blocks destructive commands before execution."""

import re


class CommandSafety:
    DANGEROUS_PATTERNS = [
        (r"\brm\s+-rf\s+[/~\$]", "Recursive delete of root or home"),
        (r"\brm\s+-rf\s+/", "Recursive delete including root path"),
        (r"del\s+/[sq]\s+", "Delete with /s /q (tree wipe)"),
        (r"rd\s+/[sq]\s+", "Remove directory tree"),
        (r"\bformat\s+", "Disk format"),
        (r"Format-Volume", "Format volume"),
        (r"Clear-Disk", "Clear disk"),
        (r"Remove-Item\s+.*-Path\s+['\"]?[/\\]", "Remove from root or system path"),
        (r"dd\s+.*of=/dev/sd", "Raw disk write"),
        (r">\s*/dev/sd[a-z]", "Overwrite block device"),
        (r">\s*/dev/nvme", "Overwrite NVMe"),
        (r"\bshutdown\s+", "System shutdown"),
        (r"\breboot\b", "System reboot"),
        (r"Restart-Computer", "Restart computer"),
        (r"Stop-Computer", "Stop computer"),
        (r"Stop-Process\s+-Id\s+1", "Kill init process"),
        (r"\bbcdedit\s+", "Boot config edit"),
        (r"reg\s+delete", "Registry delete"),
        (r":\(\)\s*\{", "Fork bomb pattern"),
        (r"\$\s*\(\s*\$\s*\)", "Fork bomb ($())"),
        (r"Disable-WindowsOptionalFeature", "Disable Windows feature"),
        (r"wmic\s+diskdrive\s+delete", "Delete disk via WMIC"),
        (r"DROP\s+DATABASE", "Drop database"),
        (r"DROP\s+TABLE\s+.*\*", "Drop all tables"),
        (r"TRUNCATE\s+", "Truncate table"),
    ]

    DANGEROUS_SUBSTRINGS = [
        "rm -rf /",
        "rm -rf ~",
        "rm -rf /*",
        "rm -rf / ",
        "rm -rf $",
        "format c:",
        "format d:",
        "mkfs.ext",
        "mkfs.ntfs",
        ":(){ :|:& };:",
        "chmod -R 777 /",
        "chown -R",
    ]

    @classmethod
    def check(cls, cmd: str) -> tuple[bool, str]:
        """Returns (is_safe, block_reason). Empty block_reason means safe."""
        if not cmd or not cmd.strip():
            return True, ""
        cmd_lower = cmd.strip().lower()
        cmd_norm = " ".join(cmd.split())

        for substr in cls.DANGEROUS_SUBSTRINGS:
            if substr.lower() in cmd_lower:
                return False, f"Blocked: potentially destructive ({substr})"

        for pattern, reason in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, cmd_norm, re.IGNORECASE):
                return False, f"Blocked: {reason}"

        return True, ""
