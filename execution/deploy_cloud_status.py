"""
Deterministic Execution Script: Cloud Deployment & Configuration Status
Audits Fly.io and Cloudflare Workers configurations, verifies binding definitions,
and tests connectivity to edge endpoints.
"""

import os
import sys
import json
import urllib.request
import urllib.error


def check_file_exists(path: str, description: str) -> bool:
    exists = os.path.isfile(path)
    status = "[OK]" if exists else "[MISSING]"
    print(f"  {status:<10} {description}: {path}")
    return exists


def verify_fly_config() -> bool:
    print("\n[*] Auditing Fly.io Configuration (fly.toml)...")
    if not os.path.exists("fly.toml"):
        print("  [FAIL] fly.toml not found!")
        return False

    with open("fly.toml", "r", encoding="utf-8") as f:
        content = f.read()

    checks = [
        ("app name defined", 'app = "' in content),
        ("internal port 8080", "internal_port = 8080" in content),
        ("health check path", "/api/system/status" in content),
        ("persistent mount", "destination = \"/app/storage\"" in content),
    ]

    all_ok = True
    for desc, passed in checks:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status:<10} {desc}")
        if not passed:
            all_ok = False
    return all_ok


def verify_cloudflare_config() -> bool:
    print("\n[*] Auditing Cloudflare Workers Configuration (cloudflare/wrangler.toml)...")
    wrangler_path = os.path.join("cloudflare", "wrangler.toml")
    if not os.path.exists(wrangler_path):
        print("  [FAIL] wrangler.toml not found!")
        return False

    with open(wrangler_path, "r", encoding="utf-8") as f:
        content = f.read()

    checks = [
        ("worker name defined", 'name = "anda-edge-worker"' in content),
        ("Workers AI binding [ai]", "[ai]" in content and "binding = \"AI\"" in content),
        ("Fly orchestrator proxy target", "FLY_ORCHESTRATOR_URL" in content),
        ("Default Gemma model defined", "@cf/google/gemma-7b-it" in content),
    ]

    all_ok = True
    for desc, passed in checks:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status:<10} {desc}")
        if not passed:
            all_ok = False
    return all_ok


def verify_docker_compose_config() -> bool:
    print("\n[*] Auditing Local Docker Compose Stack (docker-compose.yml)...")
    if not os.path.exists("docker-compose.yml"):
        print("  [FAIL] docker-compose.yml not found!")
        return False

    with open("docker-compose.yml", "r", encoding="utf-8") as f:
        content = f.read()

    checks = [
        ("Ollama Gemma service", "anda-gemma-brain" in content),
        ("Qdrant Vector DB service", "anda-qdrant-memory" in content),
        ("Go Orchestrator service", "anda-orchestrator" in content),
        ("Persistent volumes defined", "volumes:" in content),
    ]

    all_ok = True
    for desc, passed in checks:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status:<10} {desc}")
        if not passed:
            all_ok = False
    return all_ok


def probe_cloud_endpoint(url: str, name: str) -> None:
    print(f"\n[*] Probing {name} ({url})...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ANDA-StatusCheck/1.0"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = resp.read().decode("utf-8")
            print(f"  [ONLINE] HTTP {resp.status}: {data[:120]}...")
    except urllib.error.HTTPError as e:
        print(f"  [REACHABLE] HTTP {e.code} ({e.reason})")
    except Exception as e:
        print(f"  [OFFLINE / NOT DEPLOYED YET] {e}")


def main():
    print("=" * 70)
    print("PROJECT ANDA: CLOUD & EDGE DEPLOYMENT READINESS AUDIT")
    print("=" * 70)

    f_ok = verify_fly_config()
    cf_ok = verify_cloudflare_config()
    d_ok = verify_docker_compose_config()

    # Probe live endpoints if available
    probe_cloud_endpoint("http://127.0.0.1:8787/health", "Local Cloudflare Dev Server (Wrangler)")
    probe_cloud_endpoint("https://anda-omni-operator.fly.dev/api/system/status", "Fly.io Production Target")

    print("\n" + "=" * 70)
    if f_ok and cf_ok and d_ok:
        print(">>> ALL CLOUD CONFIGURATIONS VALIDATED AND READY FOR DEPLOYMENT <<<")
        print("To deploy to Cloudflare: cd cloudflare && npx wrangler deploy")
        print("To deploy to Fly.io     : fly deploy")
        print("To start local Docker   : docker compose up -d")
        print("=" * 70)
        return 0
    else:
        print(">>> CONFIGURATION VALIDATION FAILED <<<")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
