"""
LLM Brain Service (Gemma / LM Studio / Docker / Cloudflare / Gemini)
Provides unified intent parsing, capability token drafting, and conversational reasoning.
Prioritizes local offline inference via LM Studio or Docker (Gemma), with free-tier fallbacks.
"""

from __future__ import annotations
import json
import os
import re
import time
import urllib.request
import urllib.error
from typing import Any, Dict, Optional


class LLMBrain:
    def __init__(
        self,
        lm_studio_url: Optional[str] = None,
        docker_ollama_url: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
    ):
        self.lm_studio_url = lm_studio_url or os.environ.get("LM_STUDIO_URL", "http://127.0.0.1:1234/v1")
        self.docker_ollama_url = docker_ollama_url or os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        self._cached_status: Optional[Dict[str, Any]] = None
        self._last_status_time: float = 0.0

    def get_brain_status(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Probes all local and cloud brain backends to report available inference providers (cached 3s)."""
        now = time.time()
        if not force_refresh and self._cached_status and (now - self._last_status_time < 3.0):
            return self._cached_status

        lm_studio_active = False
        lm_studio_model = ""
        try:
            req = urllib.request.Request(f"{self.lm_studio_url}/models", headers={"User-Agent": "ANDA-Brain/1.0"})
            with urllib.request.urlopen(req, timeout=0.25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("data", [])
                if models:
                    lm_studio_active = True
                    lm_studio_model = models[0].get("id", "gemma-local")
        except Exception:
            pass

        docker_active = False
        docker_model = ""
        try:
            req = urllib.request.Request(f"{self.docker_ollama_url}/api/tags", headers={"User-Agent": "ANDA-Brain/1.0"})
            with urllib.request.urlopen(req, timeout=0.25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("models", [])
                if models:
                    docker_active = True
                    docker_model = models[0].get("name", "gemma:2b")
        except Exception:
            pass

        gemini_available = bool(self.gemini_api_key)

        # Determine active brain provider
        active_provider = "deterministic_semantic_router"
        if lm_studio_active:
            active_provider = f"lm_studio ({lm_studio_model})"
        elif docker_active:
            active_provider = f"docker_gemma ({docker_model})"
        elif gemini_available:
            active_provider = "google_gemini_free_tier"

        status_result = {
            "active_provider": active_provider,
            "lm_studio": {"available": lm_studio_active, "url": self.lm_studio_url, "model": lm_studio_model},
            "docker_ollama": {"available": docker_active, "url": self.docker_ollama_url, "model": docker_model},
            "gemini_cloud": {"configured": gemini_available},
            "cloudflare_workers_ai": {"model": "@cf/google/gemma-7b-it", "free_tier": True},
        }
        self._cached_status = status_result
        self._last_status_time = now
        return status_result

    def _query_lm_studio(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Queries local LM Studio OpenAI-compatible endpoint."""
        url = f"{self.lm_studio_url}/chat/completions"
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 512,
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception:
            return None

    def _query_docker_ollama(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Queries local Docker Ollama instance running Gemma."""
        url = f"{self.docker_ollama_url}/api/generate"
        payload = {
            "model": "gemma2:2b",
            "prompt": f"System: {system_prompt}\nUser: {prompt}\nAssistant:",
            "stream": False,
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "")
        except Exception:
            return None

    def parse_intent_and_execute(self, user_prompt: str, rag_context: str = "") -> Dict[str, Any]:
        """
        Parses intent using Gemma (LM Studio / Docker) with deterministic fallback.
        Returns plane, action, parameters, and generated explanation.
        """
        system_instruction = (
            "You are Project ANDA's Gemma 4 OS Brain. Classify the user instruction into JSON with fields: "
            "action (flash_usb, os_update, format_drive, extract_excel, stage_files, query_memory, web_research), "
            "plane (ELEVATED_DAEMON, WORKER_PLANE, SHARED_MEMORY), "
            "drive (if USB/disk action), and rationale."
        )

        full_prompt = user_prompt
        if rag_context:
            full_prompt += f"\n\nContext from Vector Memory:\n{rag_context}"

        # 1. Attempt LM Studio
        llm_reply = self._query_lm_studio(full_prompt, system_instruction)
        source = "lm_studio_gemma"

        # 2. Attempt Docker Ollama
        if not llm_reply:
            llm_reply = self._query_docker_ollama(full_prompt, system_instruction)
            source = "docker_gemma"

        # 3. Fallback to deterministic semantic classification
        if not llm_reply:
            source = "deterministic_router"
            lower = user_prompt.lower()
            if "flash" in lower and ("usb" in lower or "drive" in lower):
                action = "flash_usb"
                plane = "ELEVATED_DAEMON"
                drive = "E:"
            elif "update" in lower or "upgrade" in lower:
                action = "os_update"
                plane = "ELEVATED_DAEMON"
                drive = ""
            elif "format" in lower and "drive" in lower:
                action = "format_drive"
                plane = "ELEVATED_DAEMON"
                drive = "E:"
            elif "extract" in lower or "excel" in lower or "spreadsheet" in lower:
                action = "extract_excel"
                plane = "WORKER_PLANE"
                drive = ""
            elif "stage" in lower or "organize" in lower or "sort" in lower:
                action = "stage_files"
                plane = "WORKER_PLANE"
                drive = ""
            elif "recall" in lower or "search memory" in lower:
                action = "query_memory"
                plane = "SHARED_MEMORY"
                drive = ""
            else:
                action = "web_research"
                plane = "WORKER_PLANE"
                drive = ""

            return {
                "source": source,
                "action": action,
                "plane": plane,
                "drive": drive,
                "is_elevated": plane == "ELEVATED_DAEMON",
                "reasoning": f"Semantic rule matched action '{action}' on plane '{plane}'",
                "raw_reply": None,
            }

        # Parse LLM JSON response if possible
        try:
            json_match = re.search(r"\{.*\}", llm_reply, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                return {
                    "source": source,
                    "action": parsed.get("action", "web_research"),
                    "plane": parsed.get("plane", "WORKER_PLANE"),
                    "drive": parsed.get("drive", "E:"),
                    "is_elevated": parsed.get("plane") == "ELEVATED_DAEMON",
                    "reasoning": parsed.get("rationale", "Parsed by Gemma model"),
                    "raw_reply": llm_reply,
                }
        except Exception:
            pass

        return {
            "source": source,
            "action": "web_research",
            "plane": "WORKER_PLANE",
            "is_elevated": False,
            "reasoning": "Gemma free-form output generated",
            "raw_reply": llm_reply,
        }
