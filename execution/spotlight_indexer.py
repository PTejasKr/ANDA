"""
Spotlight Search and System Indexer for ANDA.
Indexes installed Windows applications, games (Steam, Epic, GOG, Start Menu),
system utilities, and documents. Provides real-time math evaluation, unit
conversion, and graceful web search fallback.
"""

from __future__ import annotations

import ast
import math
import os
import re
import subprocess
import sys
import urllib.parse
import webbrowser
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class SpotlightItem:
    category: str       # "GAME", "APP", "MATH", "SETTING", "FILE", "WEB"
    title: str          # e.g., "Cyberpunk 2077"
    subtitle: str       # e.g., "C:\ProgramData\...\Cyberpunk 2077.lnk"
    action_type: str    # "launch_app", "open_setting", "math", "open_file", "web_search"
    target: str         # File path, system URI, math result, or search URL
    confidence: float = 1.0


class SafeMathEvaluator(ast.NodeVisitor):
    """Safely evaluates basic arithmetic expressions without arbitrary code execution."""
    ALLOWED_OPERATORS = {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b if b != 0 else float('inf'),
        ast.FloorDiv: lambda a, b: a // b if b != 0 else float('inf'),
        ast.Mod: lambda a, b: a % b if b != 0 else float('inf'),
        ast.Pow: lambda a, b: a ** b if abs(b) <= 100 else float('inf'),
        ast.USub: lambda a: -a,
        ast.UAdd: lambda a: +a,
    }

    ALLOWED_FUNCTIONS = {
        "sqrt": math.sqrt,
        "abs": abs,
        "round": round,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
    }

    ALLOWED_CONSTANTS = {
        "pi": math.pi,
        "e": math.e,
    }

    def evaluate(self, expr: str) -> Optional[float]:
        clean = expr.strip().replace("^", "**")
        # Handle percentage format: "15% of 850" -> "0.15 * 850"
        pct_match = re.match(r"^(\d+(?:\.\d+)?)\s*%\s*(?:of)?\s*(\d+(?:\.\d+)?)$", clean, re.IGNORECASE)
        if pct_match:
            try:
                rate = float(pct_match.group(1)) / 100.0
                base = float(pct_match.group(2))
                return rate * base
            except Exception:
                return None

        # Quick pre-validation to avoid parsing arbitrary words
        if not re.search(r"[\d\+\-\*\/\%\^]|sqrt|pi|abs|round", clean, re.IGNORECASE):
            return None

        try:
            tree = ast.parse(clean, mode='eval')
            return self.visit(tree.body)
        except Exception:
            return None

    def visit(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        elif isinstance(node, ast.BinOp):
            op_func = self.ALLOWED_OPERATORS.get(type(node.op))
            if not op_func:
                raise ValueError("Unsupported operator")
            return op_func(self.visit(node.left), self.visit(node.right))
        elif isinstance(node, ast.UnaryOp):
            op_func = self.ALLOWED_OPERATORS.get(type(node.op))
            if not op_func:
                raise ValueError("Unsupported unary operator")
            return op_func(self.visit(node.operand))
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id.lower() in self.ALLOWED_FUNCTIONS:
                func = self.ALLOWED_FUNCTIONS[node.func.id.lower()]
                args = [self.visit(a) for a in node.args]
                return float(func(*args))
        elif isinstance(node, ast.Name) and node.id.lower() in self.ALLOWED_CONSTANTS:
            return float(self.ALLOWED_CONSTANTS[node.id.lower()])
        raise ValueError("Invalid AST expression")


class SpotlightEngine:
    """Spotlight indexing & search engine for applications, games, and web search."""

    def __init__(self):
        self.indexed_apps: Dict[str, SpotlightItem] = {}
        self.indexed_files: Dict[str, SpotlightItem] = {}
        self.math_evaluator = SafeMathEvaluator()
        self.is_indexed = False

    def build_index(self) -> int:
        """Indexes Start Menu shortcuts, game libraries, and Windows native tools."""
        apps: Dict[str, SpotlightItem] = {}

        # 1. Native Windows System Tools & Settings
        system_tools = {
            "calculator": ("calc", "APP", "Windows Native Calculator"),
            "calc": ("calc", "APP", "Windows Native Calculator"),
            "notepad": ("notepad", "APP", "Text Editor"),
            "task manager": ("taskmgr", "SETTING", "Process and Resource Monitor"),
            "taskmgr": ("taskmgr", "SETTING", "Process and Resource Monitor"),
            "command prompt": ("cmd", "APP", "Windows Command Line"),
            "cmd": ("cmd", "APP", "Windows Command Line"),
            "powershell": ("powershell", "APP", "PowerShell Automation Shell"),
            "terminal": ("wt", "APP", "Windows Terminal"),
            "paint": ("mspaint", "APP", "Classic Image Painter"),
            "file explorer": ("explorer", "APP", "File Management System"),
            "explorer": ("explorer", "APP", "File Management System"),
            "control panel": ("control", "SETTING", "System Control Center"),
            "sound settings": ("ms-settings:sound", "SETTING", "Audio & Volume Controls"),
            "volume": ("ms-settings:sound", "SETTING", "Audio & Volume Controls"),
            "display settings": ("ms-settings:display", "SETTING", "Display Resolution & HDR"),
            "bluetooth": ("ms-settings:bluetooth", "SETTING", "Bluetooth & Connected Devices"),
            "wifi settings": ("ms-settings:network-wifi", "SETTING", "Network & Internet"),
            "windows update": ("ms-settings:windowsupdate", "SETTING", "OS Software Updates"),
            "storage settings": ("ms-settings:storagesense", "SETTING", "Disk Space & Clean Up"),
        }
        for name, (target, cat, desc) in system_tools.items():
            act = "open_setting" if cat == "SETTING" else "launch_app"
            apps[name] = SpotlightItem(
                category=cat,
                title=name.title(),
                subtitle=desc,
                action_type=act,
                target=target,
                confidence=1.0,
            )

        # 2. Windows Start Menu Directories & Desktop Paths
        search_roots = [
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%USERPROFILE%\Desktop"),
            r"C:\Users\Public\Desktop",
            r"C:\Program Files (x86)\Steam\steamapps\common",
            r"D:\SteamLibrary\steamapps\common",
            r"E:\SteamLibrary\steamapps\common",
            r"C:\Program Files\Epic Games",
            r"D:\Games",
            r"C:\Games",
        ]

        game_keywords = ["game", "cyberpunk", "witcher", "steam", "epic", "gog", "riot", "valorant", "roblox", "minecraft", "fortnite", "elden", "gta"]

        for root_dir in search_roots:
            if not os.path.exists(root_dir):
                continue
            for cur_root, _, files in os.walk(root_dir):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in [".lnk", ".exe", ".url"]:
                        raw_name = os.path.splitext(f)[0]
                        clean_name = raw_name.lower().replace(" - shortcut", "").strip()
                        full_path = os.path.join(cur_root, f)

                        is_game = any(k in clean_name or k in cur_root.lower() for k in game_keywords)
                        cat = "GAME" if is_game else "APP"

                        if clean_name not in apps:
                            apps[clean_name] = SpotlightItem(
                                category=cat,
                                title=raw_name,
                                subtitle=full_path,
                                action_type="launch_app",
                                target=full_path,
                                confidence=0.95 if is_game else 0.90,
                            )

        self.indexed_apps = apps
        self.is_indexed = True
        return len(self.indexed_apps)

    def search(self, query: str, max_results: int = 5) -> List[SpotlightItem]:
        """Performs Spotlight search across math, system apps, games, and web search fallback."""
        q = (query or "").strip()
        if not q:
            return []

        results: List[SpotlightItem] = []
        lower_q = q.lower()

        # 1. Quick Math & Calculation Engine
        math_val = self.math_evaluator.evaluate(q)
        if math_val is not None:
            # Format nicely
            if isinstance(math_val, float) and math_val.is_integer():
                formatted = str(int(math_val))
            else:
                formatted = f"{math_val:.4f}".rstrip("0").rstrip(".")
            results.append(SpotlightItem(
                category="MATH",
                title=f"{q} = {formatted}",
                subtitle="Instant Calculation Result (Press Enter to Copy)",
                action_type="math",
                target=formatted,
                confidence=1.0,
            ))

        # 2. Unit & Currency Conversion
        conv_item = self._check_conversion(q)
        if conv_item:
            results.append(conv_item)

        # 3. System Applications & Games Search
        # Strip common launch prefixes: "open ", "play ", "launch ", "start "
        clean_target = lower_q
        for prefix in ["open a game ", "open the game ", "play the game ", "launch the game ", "open ", "play ", "launch ", "start ", "run "]:
            if clean_target.startswith(prefix):
                clean_target = clean_target[len(prefix):].strip()
                break

        matched_apps: List[SpotlightItem] = []
        for name, item in self.indexed_apps.items():
            if name == clean_target:
                matched_apps.insert(0, item)
            elif clean_target in name or name in clean_target:
                matched_apps.append(item)

        # Append matching local apps & games
        for app in matched_apps[:4]:
            if app not in results:
                results.append(app)

        # 4. Web Search Fallback
        # If user explicitly asks for web search or if no exact local item found
        search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}"
        web_item = SpotlightItem(
            category="WEB",
            title=f"Search the web for '{q}'",
            subtitle="Search Google in Default Web Browser",
            action_type="web_search",
            target=search_url,
            confidence=0.5,
        )

        # If no local apps/math matched, web item is primary
        results.append(web_item)

        return results[:max_results]

    def _check_conversion(self, query: str) -> Optional[SpotlightItem]:
        lower = query.lower().strip()
        # Temp: "32 c to f"
        m = re.match(r"^(\d+(?:\.\d+)?)\s*(c|f)\s+(?:in|to)\s+(c|f)$", lower)
        if m:
            val = float(m.group(1))
            from_u = m.group(2)
            to_u = m.group(3)
            if from_u == "c" and to_u == "f":
                res = (val * 9 / 5) + 32
                return SpotlightItem(
                    category="MATH",
                    title=f"{val}°C = {res:.1f}°F",
                    subtitle="Temperature Conversion",
                    action_type="math",
                    target=f"{res:.1f}°F",
                )
            elif from_u == "f" and to_u == "c":
                res = (val - 32) * 5 / 9
                return SpotlightItem(
                    category="MATH",
                    title=f"{val}°F = {res:.1f}°C",
                    subtitle="Temperature Conversion",
                    action_type="math",
                    target=f"{res:.1f}°C",
                )

        # Distance: "10 km to miles"
        m = re.match(r"^(\d+(?:\.\d+)?)\s*(km|miles|mi)\s+(?:in|to)\s*(km|miles|mi)$", lower)
        if m:
            val = float(m.group(1))
            from_u = m.group(2)
            to_u = m.group(3)
            if from_u == "km" and to_u in ["miles", "mi"]:
                res = val * 0.621371
                return SpotlightItem(
                    category="MATH",
                    title=f"{val} km = {res:.2f} miles",
                    subtitle="Length Conversion",
                    action_type="math",
                    target=f"{res:.2f} miles",
                )
            elif from_u in ["miles", "mi"] and to_u == "km":
                res = val / 0.621371
                return SpotlightItem(
                    category="MATH",
                    title=f"{val} miles = {res:.2f} km",
                    subtitle="Length Conversion",
                    action_type="math",
                    target=f"{res:.2f} km",
                )

        return None

    def execute_item(self, item: SpotlightItem) -> Dict[str, Any]:
        """Executes the selected Spotlight item (launches local app, runs math, or opens web)."""
        if item.action_type == "launch_app":
            try:
                if os.path.exists(item.target):
                    os.startfile(item.target)
                    return {"status": "success", "message": f"Launched {item.title}", "item": item}
                else:
                    # Try subprocess.Popen for command names like calc, notepad
                    subprocess.Popen(item.target, shell=True)
                    return {"status": "success", "message": f"Launched {item.title}", "item": item}
            except Exception as e:
                # Graceful fallback to web search if local launch fails
                fallback_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(item.title)}"
                webbrowser.open(fallback_url)
                return {"status": "fallback", "message": f"Opened web search for {item.title}: {e}", "item": item}

        elif item.action_type == "open_setting":
            try:
                os.startfile(item.target)
                return {"status": "success", "message": f"Opened {item.title}", "item": item}
            except Exception:
                try:
                    subprocess.Popen(f"cmd /c start {item.target}", shell=True)
                    return {"status": "success", "message": f"Opened {item.title}", "item": item}
                except Exception as e:
                    return {"status": "error", "message": str(e), "item": item}

        elif item.action_type == "math":
            return {"status": "success", "message": f"Calculation: {item.target}", "item": item}

        elif item.action_type == "web_search":
            try:
                webbrowser.open(item.target)
                return {"status": "success", "message": f"Opened web search: {item.target}", "item": item}
            except Exception as e:
                return {"status": "error", "message": str(e), "item": item}

        return {"status": "unknown", "message": "Unrecognized action", "item": item}
