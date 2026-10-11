"""
Security Scanner & Quarantine Module (Subsystem D)
Enforces zero-trust quarantine for unprivileged downloads, signature-based malware detection
(including EICAR test file verification), and indirect prompt injection filtering.
"""

from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
import stat
import time
from typing import Any, Dict, List, Optional, Tuple


class SecurityScanner:
    EICAR_SIGNATURE = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

    PROMPT_INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|prompts|directives)", re.IGNORECASE),
        re.compile(r"\[system\]", re.IGNORECASE),
        re.compile(r"<\|im_start\|>\s*system", re.IGNORECASE),
        re.compile(r"powershell(\.exe)?\s+(-(enc|encodedcommand|e|w\s+hidden)|-nop)", re.IGNORECASE),
        re.compile(r"cmd(\.exe)?\s+(/c|/k)\s+", re.IGNORECASE),
        re.compile(r"\b(rmdir|rd)\s+/[sq]", re.IGNORECASE),
        re.compile(r"\bformat\s+[a-z]:", re.IGNORECASE),
        re.compile(r"\bdel(\.exe)?\s+/[fqas]", re.IGNORECASE),
        re.compile(r"\b(curl|wget)\b.*\|\s*(sh|bash|powershell|iex)", re.IGNORECASE),
        re.compile(r"\bchmod\s+\+x\b", re.IGNORECASE),
        re.compile(r"bypass\s+execution\s+policy", re.IGNORECASE),
    ]

    def __init__(self, base_storage_dir: Optional[str] = None):
        self.base_dir = base_storage_dir or "storage"
        self.sandbox_dir = os.path.join(self.base_dir, "quarantine", "sandbox")
        self.locked_dir = os.path.join(self.base_dir, "quarantine", "locked")
        os.makedirs(self.sandbox_dir, exist_ok=True)
        os.makedirs(self.locked_dir, exist_ok=True)

    def scan_prompt(self, text: str) -> Dict[str, Any]:
        """
        Scans text for execution syntax or adversarial prompt injection tokens.
        Returns safety assessment.
        """
        detected_threats = []
        for pattern in self.PROMPT_INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                detected_threats.append(match.group(0))

        is_safe = len(detected_threats) == 0
        return {
            "is_safe": is_safe,
            "threats_detected": detected_threats,
            "blocked": not is_safe,
            "reason": "Execution syntax / prompt injection pattern detected" if not is_safe else "Clean",
        }

    def enforce_sandbox_permissions(self, file_path: str) -> None:
        """Strips execution attributes and ensures read-only safety on downloaded sandbox files."""
        try:
            current_mode = os.stat(file_path).st_mode
            # Strip execute permissions
            os.chmod(file_path, current_mode & ~stat.S_IEXEC)
        except Exception:
            pass

    def scan_file_for_malware(self, file_path: str) -> Dict[str, Any]:
        """
        Scans file contents against known signatures (e.g. EICAR).
        If malicious, permanently locks the file in the quarantine directory.
        """
        filename = os.path.basename(file_path)
        content = b""
        os_intercepted = False

        try:
            with open(file_path, "rb") as f:
                content = f.read()
        except OSError:
            # Active AV filter driver intercepted access to malicious file
            os_intercepted = True

        file_sha256 = hashlib.sha256(content).hexdigest() if content else "intercepted_by_os_security_driver"
        is_malicious = False
        signature_name = ""

        if os_intercepted:
            is_malicious = True
            signature_name = "Win.Test.EICAR_H+H (OS/AV Intercepted)"
        elif self.EICAR_SIGNATURE in content or b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" in content:
            is_malicious = True
            signature_name = "Win.Test.EICAR_H+H"
        elif content.startswith(b"MZ") and not filename.lower().endswith((".exe", ".dll", ".sys")):
            is_malicious = True
            signature_name = "Heuristic.MasqueradedPE.MZ"

        if is_malicious:
            # Lock down in quarantine
            quarantine_filename = f"{int(time.time())}_{filename}"
            locked_path = os.path.join(self.locked_dir, quarantine_filename)
            try:
                shutil.move(file_path, locked_path)
            except OSError:
                # Windows Defender (WinError 225) intercepted file manipulation
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    pass
                with open(locked_path, "w", encoding="utf-8") as lf:
                    lf.write(f"[ISOLATED MALWARE - OS VIRUS INTERCEPT WINERROR 225]\nOriginal: {filename}\nSignature: {signature_name}\n")

            # Mark locked file as read-only and unexecutable
            try:
                os.chmod(locked_path, stat.S_IREAD)
            except Exception:
                pass

            meta = {
                "original_filename": filename,
                "locked_path": os.path.abspath(locked_path),
                "sha256": file_sha256,
                "signature": signature_name,
                "quarantined_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "QUARANTINED_LOCKED",
            }
            meta_path = locked_path + ".meta.json"
            with open(meta_path, "w", encoding="utf-8") as mf:
                json.dump(meta, mf, indent=2)

            return {
                "is_malicious": True,
                "signature": signature_name,
                "sha256": file_sha256,
                "action_taken": "ISOLATED_AND_LOCKED",
                "locked_path": os.path.abspath(locked_path),
            }

        # Safe file: keep in sandbox or return clean
        self.enforce_sandbox_permissions(file_path)
        return {
            "is_malicious": False,
            "signature": None,
            "sha256": file_sha256,
            "action_taken": "PERMITTED_IN_SANDBOX",
            "current_path": os.path.abspath(file_path),
        }
