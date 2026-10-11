# Zero-Trust Quarantine & Prompt Injection Security SOP

## 1. Objective
Establish defense-in-depth against malicious file execution, automated malware isolation, and indirect prompt injection attacks targeting the dual-plane assistant.

## 2. Sandbox Constraints
1. **Directory Isolation**:
   - Downloads and incoming untrusted files land exclusively in `storage/quarantine/sandbox/`.
   - Execution permissions stripped (files treated strictly as binary read-only streams).
2. **Signature & Heuristic Malware Detection**:
   - Evaluates file stream against known threat signatures, including standard EICAR test string:
     `X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*`
   - Immediately locks infected files into `storage/quarantine/locked/` with timestamped forensic metadata.
   - Raises an alert signal to the Go Orchestrator and broadcasts an incident event to the Frontend.
3. **Indirect Prompt Injection Defense**:
   - Pre-execution scanning inspects user and retrieved RAG context for hazardous injection tokens:
     - System override delimiters: `[SYSTEM]`, `IGNORE PREVIOUS INSTRUCTIONS`, `<|im_start|>system`
     - Command execution syntax: `powershell -enc`, `cmd.exe /c`, `rmdir /s /q`, `format [A-Z]:`, `chmod +x`
   - Blocks poisoned prompts before passing them to downstream workers or LLM inference.
