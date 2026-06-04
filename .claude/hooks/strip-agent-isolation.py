#!/usr/bin/env python3
"""
PreToolUse hook — remove isolation:worktree de chamadas ao Agent tool.

Problema: quando oracle corre via openclaude CLI (Discord Plus), o Agent tool
cria worktrees de evo-nexus para cada sub-agente. Sub-agentes em worktrees não
alcançam repos externos (go-control-erp, etc.) facilmente.

Fix: remover o campo isolation do input antes do Agent tool rodar.
Sem isolation → sem worktree → sub-agente roda no CWD do processo pai.

Formato de retorno (Claude Code hook spec):
  {"hookEventName": "PreToolUse", "updatedInput": {...}}
  Se updatedInput não tiver permissionDecision → input é substituído, tool roda normalmente.
"""
import json
import sys


LOG = "/home/evonexus/evo-nexus/ADWs/logs/strip-agent-isolation.log"


def log(msg: str) -> None:
    import datetime
    ts = datetime.datetime.now().isoformat()
    with open(LOG, "a") as f:
        f.write(f"{ts} {msg}\n")


def main() -> None:
    try:
        raw = sys.stdin.read()
        log(f"called raw={raw[:300]}")
        payload = json.loads(raw)
    except Exception as e:
        log(f"parse error: {e}")
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})

    log(f"tool={tool_name} has_isolation={'isolation' in tool_input}")

    if tool_name != "Agent":
        sys.exit(0)

    if "isolation" not in tool_input:
        sys.exit(0)

    updated = {k: v for k, v in tool_input.items() if k != "isolation"}
    result = {"hookEventName": "PreToolUse", "updatedInput": updated}
    log(f"stripped → output={json.dumps(result)[:200]}")
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
