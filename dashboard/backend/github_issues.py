"""
github_issues.py — Cliente GitHub para sincronização de tickets com Issues + Projects V2.
Uso interno pelo sistema de tickets do EvoNexus.
"""
import os
import json
import threading
import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib import request as _urllib_request, error as _urllib_error
from typing import Optional

# Carregar .env se rodando fora do contexto do Flask
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass

logger = logging.getLogger(__name__)

_API_BASE = "https://api.github.com"
_TIMEOUT = 15

# Cache do node_id do Project V2 (resolve uma vez, guarda em memória)
_project_node_id_cache: Optional[str] = None
_cache_lock = threading.Lock()

ORG = "Automacao-Software"
PROJECT_NUMBER = 2
ASSIGNEES = ["eduardomrj"]

REPOS_ALLOWLIST = {
    "Automacao-Software/go-control-erp",
    "Automacao-Software/go-control-platform",
    "Automacao-Software/go-control-admin",
    "Automacao-Software/go-control-auth",
    "Automacao-Software/go-control-account",
    "Automacao-Software/go-control-sdk",
    "Automacao-Software/go-control-app-template",
    "Automacao-Software/go-payment-hub",
    "Automacao-Software/go-message",
    "Automacao-Software/go-produtos",
    "Automacao-Software/go-pessoas",
    "Automacao-Software/go-cobranca",
}

STATUS_LABELS = {
    "open": [],
    "in_progress": ["status:in-progress"],
    "blocked": ["status:blocked"],
    "review": ["status:review"],
    "resolved": [],
    "closed": [],
    "archived": [],
}

STATUS_TO_GITHUB = {
    "open": ("open", None),
    "in_progress": ("open", None),
    "blocked": ("open", None),
    "review": ("open", None),
    "resolved": ("closed", "completed"),
    "closed": ("closed", "not_planned"),
    "archived": ("closed", "not_planned"),
}

# Project V2 — campo Status
STATUS_FIELD_ID = "PVTSSF_lADODjM7ec4Ba3pazhVsIuA"
STATUS_TO_PROJECT_OPTION = {
    "open":        "f75ad846",  # Backlog
    "in_progress": "47fc9ee4",  # In progress
    "blocked":     "47fc9ee4",  # In progress
    "review":      "df73e18b",  # In review
    "resolved":    "98236657",  # Done
    "closed":      "98236657",  # Done
    "archived":    "98236657",  # Done
}


# --------------- HTTP helpers ---------------

def _token() -> str:
    """Lê GITHUB_TOKEN do env. Levanta RuntimeError se ausente."""
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if not tok:
        raise RuntimeError("GITHUB_TOKEN não está definido no ambiente")
    return tok


def _headers() -> dict:
    """Retorna headers padrão da API GitHub com o token."""
    return {
        "Authorization": f"Bearer {_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }


def _get(url: str) -> tuple[int, Optional[dict]]:
    """GET com urllib. Retorna (status_code, body)."""
    req = _urllib_request.Request(url, headers=_headers(), method="GET")
    try:
        with _urllib_request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.status, json.loads(resp.read())
    except _urllib_error.HTTPError as exc:
        try:
            body = json.loads(exc.read())
        except Exception:
            body = None
        return exc.code, body
    except Exception as exc:
        logger.warning("GitHub API GET %s failed: %s", url, exc)
        return 0, None


def _post(url: str, payload: dict) -> tuple[int, Optional[dict]]:
    """POST com urllib."""
    data = json.dumps(payload).encode()
    req = _urllib_request.Request(url, data=data, headers=_headers(), method="POST")
    try:
        with _urllib_request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.status, json.loads(resp.read())
    except _urllib_error.HTTPError as exc:
        try:
            body = json.loads(exc.read())
        except Exception:
            body = None
        return exc.code, body
    except Exception as exc:
        logger.warning("GitHub API POST %s failed: %s", url, exc)
        return 0, None


def _patch(url: str, payload: dict) -> tuple[int, Optional[dict]]:
    """PATCH com urllib."""
    data = json.dumps(payload).encode()
    req = _urllib_request.Request(url, data=data, headers=_headers(), method="PATCH")
    try:
        with _urllib_request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.status, json.loads(resp.read())
    except _urllib_error.HTTPError as exc:
        try:
            body = json.loads(exc.read())
        except Exception:
            body = None
        return exc.code, body
    except Exception as exc:
        logger.warning("GitHub API PATCH %s failed: %s", url, exc)
        return 0, None


def _graphql(query: str, variables: dict) -> tuple[int, Optional[dict]]:
    """POST para https://api.github.com/graphql."""
    url = f"{_API_BASE}/graphql"
    payload = {"query": query, "variables": variables}
    data = json.dumps(payload).encode()
    req = _urllib_request.Request(url, data=data, headers=_headers(), method="POST")
    try:
        with _urllib_request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.status, json.loads(resp.read())
    except _urllib_error.HTTPError as exc:
        try:
            body = json.loads(exc.read())
        except Exception:
            body = None
        return exc.code, body
    except Exception as exc:
        logger.warning("GitHub GraphQL failed: %s", exc)
        return 0, None


# --------------- Projects V2 ---------------

def get_project_node_id(org: str = ORG, project_number: int = PROJECT_NUMBER) -> Optional[str]:
    """Obtém o node_id do Project V2. Cacheia em memória (thread-safe)."""
    global _project_node_id_cache
    with _cache_lock:
        if _project_node_id_cache is not None:
            return _project_node_id_cache
    query = """
    query GetProjectId($org: String!, $num: Int!) {
      organization(login: $org) {
        projectV2(number: $num) {
          id
        }
      }
    }
    """
    status, body = _graphql(query, {"org": org, "num": project_number})
    if status != 200 or not body:
        logger.warning("get_project_node_id: status %d", status)
        return None
    try:
        node_id = body["data"]["organization"]["projectV2"]["id"]
        with _cache_lock:
            _project_node_id_cache = node_id
        return node_id
    except (KeyError, TypeError) as exc:
        logger.warning("get_project_node_id: parse error %s — body: %s", exc, body)
        return None


def add_issue_to_project(project_node_id: str, issue_node_id: str) -> Optional[str]:
    """Adiciona a issue ao Project V2. Retorna o project_item_id."""
    mutation = """
    mutation AddIssue($proj: ID!, $content: ID!) {
      addProjectV2ItemById(input: {projectId: $proj, contentId: $content}) {
        item { id }
      }
    }
    """
    status, body = _graphql(mutation, {"proj": project_node_id, "content": issue_node_id})
    if status != 200 or not body:
        logger.warning("add_issue_to_project: status %d", status)
        return None
    try:
        return body["data"]["addProjectV2ItemById"]["item"]["id"]
    except (KeyError, TypeError) as exc:
        logger.warning("add_issue_to_project: parse error %s — body: %s", exc, body)
        return None


def update_project_item_status(project_node_id: str, item_id: str, field_id: str, option_id: str) -> bool:
    """Atualiza o campo Status (singleSelect) de um item no Project V2."""
    mutation = """
    mutation UpdateStatus($proj: ID!, $item: ID!, $field: ID!, $val: String!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $proj, itemId: $item, fieldId: $field,
        value: { singleSelectOptionId: $val }
      }) { projectV2Item { id } }
    }
    """
    sc, data = _graphql(mutation, {"proj": project_node_id, "item": item_id, "field": field_id, "val": option_id})
    ok = sc == 200 and not (data or {}).get("errors")
    if not ok:
        logger.warning("update_project_item_status: sc=%d data=%s", sc, data)
    return ok


# --------------- Issues REST ---------------

def create_issue(repo: str, title: str, body: str,
                 labels: list[str], assignees: list[str] = ASSIGNEES) -> Optional[dict]:
    """Cria uma issue no repositório. Retorna o body completo (inclui number, node_id, html_url)."""
    url = f"{_API_BASE}/repos/{repo}/issues"
    payload = {
        "title": title,
        "body": body,
        "labels": labels,
        "assignees": assignees,
    }
    status, resp_body = _post(url, payload)
    if status not in (200, 201):
        logger.warning("create_issue(%s): status %d — %s", repo, status, resp_body)
        return None
    return resp_body


def update_issue(repo: str, issue_number: int, **fields) -> Optional[dict]:
    """PATCH de campos da issue. Passa só os campos em fields."""
    url = f"{_API_BASE}/repos/{repo}/issues/{issue_number}"
    status, body = _patch(url, fields)
    if status not in (200, 201):
        logger.warning("update_issue(%s #%d): status %d", repo, issue_number, status)
        return None
    return body


def close_issue(repo: str, issue_number: int, state_reason: str = "completed") -> Optional[dict]:
    """Fecha a issue. state_reason: 'completed' ou 'not_planned'."""
    return update_issue(repo, issue_number, state="closed", state_reason=state_reason)


def get_issue(repo: str, issue_number: int) -> tuple[int, Optional[dict]]:
    """Retorna (status_code, body). Status 404 = issue foi deletada."""
    url = f"{_API_BASE}/repos/{repo}/issues/{issue_number}"
    return _get(url)


# --------------- Sync principal ---------------

def sync_ticket_to_github(ticket_id: str) -> None:
    """Sincroniza um ticket EvoNexus com uma GitHub Issue.

    Cria a issue se não existir, atualiza se já existir.
    Erros são capturados, logados e salvos em sync_error — nunca propagam.
    """
    try:
        # Importação local para evitar import circular com models/app
        from models import Ticket, TicketGithubLink, db

        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            logger.warning("sync_ticket_to_github: ticket %s não encontrado", ticket_id)
            return

        if not ticket.github_repo:
            logger.debug("sync_ticket_to_github: ticket %s sem github_repo — skip", ticket_id)
            return

        repo = ticket.github_repo
        if repo not in REPOS_ALLOWLIST:
            logger.warning(
                "sync_ticket_to_github: repo '%s' não está na allowlist — skip", repo
            )
            return

        # Montar labels: priority + status
        labels = [f"priority:{ticket.priority}"] + STATUS_LABELS.get(ticket.status, [])
        body_text = ticket.description or ""

        link = TicketGithubLink.query.filter_by(ticket_id=ticket_id).first()

        if link is None:
            # --- CREATE ---
            result = create_issue(repo, ticket.title, body_text, labels)
            if not result:
                raise RuntimeError(f"create_issue falhou para repo {repo}")

            issue_number = result["number"]
            issue_node_id = result["node_id"]
            issue_url = result["html_url"]

            project_item_id = None
            project_node_id = get_project_node_id()
            if project_node_id:
                project_item_id = add_issue_to_project(project_node_id, issue_node_id)

            now = datetime.utcnow().isoformat()
            link = TicketGithubLink(
                ticket_id=ticket_id,
                github_repo=repo,
                issue_number=issue_number,
                issue_url=issue_url,
                project_item_id=project_item_id,
                last_synced_at=now,
                sync_error=None,
                created_at=now,
                updated_at=now,
            )
            db.session.add(link)
            db.session.commit()
            logger.info(
                "sync_ticket_to_github: ticket %s → issue %s#%d (project_item=%s)",
                ticket_id, repo, issue_number, project_item_id,
            )
            # Definir status no Project V2 logo após criação
            opt = STATUS_TO_PROJECT_OPTION.get(ticket.status)
            if opt and project_item_id and project_node_id:
                update_project_item_status(project_node_id, project_item_id, STATUS_FIELD_ID, opt)

        else:
            # --- UPDATE ---
            github_state, state_reason = STATUS_TO_GITHUB.get(ticket.status, ("open", None))
            update_kwargs: dict = {
                "title": ticket.title,
                "body": body_text,
                "labels": labels,
                "state": github_state,
            }
            if state_reason:
                update_kwargs["state_reason"] = state_reason

            update_issue(repo, link.issue_number, **update_kwargs)

            # Atualizar status no Project V2
            opt = STATUS_TO_PROJECT_OPTION.get(ticket.status)
            if opt and link.project_item_id:
                pnid = get_project_node_id()
                if pnid:
                    update_project_item_status(pnid, link.project_item_id, STATUS_FIELD_ID, opt)

            link.last_synced_at = datetime.utcnow().isoformat()
            link.sync_error = None
            link.updated_at = datetime.utcnow().isoformat()
            db.session.commit()
            logger.info(
                "sync_ticket_to_github: ticket %s → issue %s#%d atualizada",
                ticket_id, repo, link.issue_number,
            )

    except Exception as exc:
        logger.error("sync_ticket_to_github(%s) error: %s", ticket_id, exc)
        # Tentar salvar o erro no link
        try:
            from models import TicketGithubLink, db
            existing_link = TicketGithubLink.query.filter_by(ticket_id=ticket_id).first()
            if existing_link:
                existing_link.sync_error = str(exc)
                existing_link.updated_at = datetime.utcnow().isoformat()
                db.session.commit()
        except Exception as inner_exc:
            logger.error("sync_ticket_to_github: falha ao salvar sync_error: %s", inner_exc)
