#!/usr/bin/env python3
"""
lightforms.py -- Helper para operacoes comuns da API do LightForms v2
Uso: python3 ~/.claude/skills/lightforms/scripts/lightforms.py <comando> [args...]
"""

import sys
import os
import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from pathlib import Path

# ============================================================
# CONFIGURACAO
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = SCRIPT_DIR.parent / "config.env"


def load_config():
    """Carrega credenciais do config.env"""
    if not CONFIG_FILE.exists():
        print(f"Erro: Arquivo de credenciais nao encontrado: {CONFIG_FILE}")
        print()
        print("Crie o arquivo com:")
        print(f"  cat > {CONFIG_FILE} << 'EOF'")
        print("  LIGHTFORMS_BASE_URL=https://api.lightforms.io")
        print("  LIGHTFORMS_TOKEN=SEU_JWT_TOKEN_AQUI")
        print("  LIGHTFORMS_WORKSPACE_ID=SEU_WORKSPACE_ID_AQUI")
        print("  EOF")
        sys.exit(1)

    config = {}
    with open(CONFIG_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()

    base_url = config.get("LIGHTFORMS_BASE_URL", "")
    token = config.get("LIGHTFORMS_TOKEN", "")
    workspace_id = config.get("LIGHTFORMS_WORKSPACE_ID", "")

    if not base_url or not token:
        print(f"Erro: LIGHTFORMS_BASE_URL ou LIGHTFORMS_TOKEN nao configurados em {CONFIG_FILE}")
        sys.exit(1)

    return base_url.rstrip("/"), token, workspace_id


BASE_URL, TOKEN, DEFAULT_WORKSPACE_ID = load_config()


# ============================================================
# API CLIENT
# ============================================================

def api_request(method, endpoint, body=None, query_params=None, workspace_id=None):
    """Faz requisicao a API do LightForms"""
    url = f"{BASE_URL}/api/v2{endpoint}"

    if query_params:
        qs = urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote)
        url = f"{url}?{qs}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}",
    }

    ws_id = workspace_id or DEFAULT_WORKSPACE_ID
    if ws_id:
        headers["workspace-id"] = ws_id

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read().decode("utf-8")
            if not resp_body:
                return {}
            return json.loads(resp_body)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        try:
            error_json = json.loads(error_body)
            print(f"Erro {e.code}: {json.dumps(error_json, ensure_ascii=False, indent=2)}")
        except json.JSONDecodeError:
            print(f"Erro {e.code}: {error_body}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Erro de conexao: {e.reason}")
        sys.exit(1)


def api_get(endpoint, query_params=None, workspace_id=None):
    return api_request("GET", endpoint, query_params=query_params, workspace_id=workspace_id)


def api_post(endpoint, body=None, workspace_id=None):
    return api_request("POST", endpoint, body or {}, workspace_id=workspace_id)


def api_put(endpoint, body=None, workspace_id=None):
    return api_request("PUT", endpoint, body or {}, workspace_id=workspace_id)


def api_delete(endpoint, workspace_id=None):
    return api_request("DELETE", endpoint, workspace_id=workspace_id)


def pp(data):
    """Pretty print JSON"""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def truncate(text, max_len=80):
    """Trunca texto com reticencias"""
    text = str(text or "")
    return text[:max_len] + "..." if len(text) > max_len else text


# ============================================================
# COMANDOS — AUTH
# ============================================================

def cmd_me():
    """Mostra usuario autenticado"""
    print("Usuario autenticado:")
    print()
    result = api_get("/user")
    if "firstName" in result:
        print(f"  Nome:  {result.get('firstName', '')} {result.get('lastName', '')}")
        print(f"  Email: {result.get('email', '?')}")
        print(f"  ID:    {result.get('id', '?')}")
    else:
        pp(result)


def cmd_login(email, password):
    """Faz login e retorna token"""
    result = api_request("POST", "/auth/login", {"email": email, "password": password})
    token = result.get("access_token", "")
    if token:
        print(f"Token: {token}")
        print()
        print(f"Atualize o config.env com:")
        print(f"  LIGHTFORMS_TOKEN={token}")
    else:
        pp(result)


# ============================================================
# COMANDOS — WORKSPACE
# ============================================================

def cmd_workspaces():
    """Lista workspaces do usuario"""
    print("Workspaces:")
    print()
    result = api_get("/workspace")
    if isinstance(result, list):
        for ws in result:
            workspace = ws.get("workspace", ws)
            print(f"  {workspace.get('name', '?')} | ID: {workspace.get('id', '?')}")
    else:
        pp(result)


# ============================================================
# COMANDOS — FOLDER
# ============================================================

def cmd_folders():
    """Lista folders do workspace"""
    print("Folders:")
    print()
    result = api_get("/workspace/folders")
    if isinstance(result, list):
        for folder in result:
            form_count = len(folder.get("forms", []))
            print(f"  {folder.get('name', '?')} | {form_count} forms | ID: {folder.get('id', '?')}")
    else:
        pp(result)


def cmd_create_folder(*name_parts):
    """Cria folder"""
    name = " ".join(name_parts)
    if not name:
        print("Erro: Uso: lightforms.py create-folder <nome>")
        sys.exit(1)
    print(f"Criando folder '{name}'...")
    result = api_post("/folder", {"name": name})
    print(f"Folder criado! ID: {result.get('id', '?')}")
    pp(result)


# ============================================================
# COMANDOS — FORM
# ============================================================

def cmd_forms(page="1", limit="20"):
    """Lista forms do workspace"""
    print(f"Forms (pagina {page}):")
    print()
    result = api_get("/form", {"page": page, "limit": limit})
    forms = result.get("data", result) if isinstance(result, dict) else result
    if isinstance(forms, list):
        for form in forms:
            status = "ATIVO" if form.get("active") else "INATIVO"
            print(f"  [{status}] {truncate(form.get('name', '?'), 50)} | ID: {form.get('id', '?')}")
    else:
        pp(result)


def cmd_form(form_id):
    """Detalha um form com questoes"""
    result = api_get(f"/form/{form_id}")
    pp(result)


def cmd_create_form(name, extra_json=None):
    """Cria form"""
    body = {"name": name}
    if extra_json:
        try:
            extra = json.loads(extra_json)
            body.update(extra)
        except json.JSONDecodeError:
            print(f"Erro: JSON invalido: {extra_json}")
            sys.exit(1)
    print(f"Criando form '{name}'...")
    result = api_post("/form", body)
    print(f"Form criado! ID: {result.get('id', '?')}")
    pp(result)


def cmd_create_form_ai(*prompt_parts):
    """Cria form via AI prompt"""
    prompt = " ".join(prompt_parts)
    if not prompt:
        print("Erro: Uso: lightforms.py create-form-ai <prompt>")
        sys.exit(1)
    print(f"Criando form via AI...")
    result = api_post("/form/prompt", {"prompt": prompt})
    print(f"Form criado! ID: {result.get('id', '?')}")
    pp(result)


def cmd_duplicate_form(form_id):
    """Duplica form"""
    print(f"Duplicando form {form_id}...")
    result = api_post("/form/duplicate", {"form_id": form_id})
    print(f"Form duplicado! ID: {result.get('id', '?')}")
    pp(result)


def cmd_edit_form(form_id, body_json):
    """Edita form"""
    try:
        body = json.loads(body_json)
    except json.JSONDecodeError:
        print(f"Erro: JSON invalido: {body_json}")
        sys.exit(1)
    print(f"Editando form {form_id}...")
    result = api_put(f"/form/{form_id}", body)
    print("Form atualizado!")
    pp(result)


def cmd_toggle_form(form_id):
    """Ativa/desativa form"""
    print(f"Toggling form {form_id}...")
    result = api_put(f"/form/status/{form_id}")
    active = result.get("active", "?")
    print(f"Form {'ATIVADO' if active else 'DESATIVADO'}!")
    pp(result)


def cmd_delete_form(form_id):
    """Deleta form"""
    print(f"Deletando form {form_id}...")
    api_delete(f"/form/{form_id}")
    print("Form deletado.")


def cmd_stats(form_id, from_date="", to_date=""):
    """Estatisticas do form"""
    params = {}
    if from_date:
        params["from_date"] = from_date
    if to_date:
        params["to_date"] = to_date
    print(f"Estatisticas do form {form_id}:")
    print()
    result = api_get(f"/form/stats/{form_id}", params)
    pp(result)


def cmd_stats_per_day(form_id):
    """Stats por dia"""
    result = api_get(f"/form/stats-per-day/{form_id}")
    pp(result)


# ============================================================
# COMANDOS — RESPOSTAS
# ============================================================

def cmd_answers(form_id, page="1", limit="20"):
    """Lista respostas de um form"""
    print(f"Respostas do form {form_id} (pagina {page}):")
    print()
    result = api_get(f"/form/answers/{form_id}", {"page": page, "limit": limit})
    pp(result)


def cmd_export_csv(form_id):
    """Exporta respostas como CSV (retorna URL ou dados)"""
    print(f"Exportando CSV do form {form_id}...")
    result = api_get(f"/form/answers/csv/{form_id}")
    pp(result)


def cmd_delete_answer(answer_id):
    """Deleta uma resposta"""
    print(f"Deletando resposta {answer_id}...")
    api_delete(f"/answered-form/{answer_id}")
    print("Resposta deletada.")


def cmd_delete_answers(*ids):
    """Deleta multiplas respostas"""
    ids_str = ",".join(ids)
    print(f"Deletando {len(ids)} respostas...")
    api_delete(f"/answered-form?ids={ids_str}")
    print("Respostas deletadas.")


# ============================================================
# COMANDOS — QUESTOES
# ============================================================

def cmd_create_question(form_id, body_json):
    """Cria questao"""
    try:
        body = json.loads(body_json)
    except json.JSONDecodeError:
        print(f"Erro: JSON invalido: {body_json}")
        sys.exit(1)
    body["form_id"] = form_id
    print(f"Criando questao no form {form_id}...")
    result = api_post("/question", body)
    print(f"Questao criada! ID: {result.get('id', '?')}")
    pp(result)


def cmd_edit_question(question_id, body_json):
    """Edita questao"""
    try:
        body = json.loads(body_json)
    except json.JSONDecodeError:
        print(f"Erro: JSON invalido: {body_json}")
        sys.exit(1)
    print(f"Editando questao {question_id}...")
    result = api_put(f"/question/{question_id}", body)
    print("Questao atualizada!")
    pp(result)


def cmd_delete_question(question_id):
    """Deleta questao"""
    print(f"Deletando questao {question_id}...")
    api_delete(f"/question/{question_id}")
    print("Questao deletada.")


def cmd_create_choice(body_json):
    """Cria choice"""
    try:
        body = json.loads(body_json)
    except json.JSONDecodeError:
        print(f"Erro: JSON invalido: {body_json}")
        sys.exit(1)
    print("Criando choice...")
    result = api_post("/question/choice", body)
    print(f"Choice criada! ID: {result.get('id', '?')}")
    pp(result)


# ============================================================
# COMANDOS — WEBHOOK
# ============================================================

def cmd_webhooks(form_id=""):
    """Lista webhooks"""
    params = {}
    if form_id:
        params["form_id"] = form_id
    print("Webhooks:")
    print()
    result = api_get("/webhook", params)
    if isinstance(result, list):
        for wh in result:
            print(f"  {truncate(wh.get('url', '?'), 60)} | Form: {wh.get('form_id', '?')} | ID: {wh.get('id', '?')}")
    else:
        pp(result)


def cmd_create_webhook(body_json):
    """Cria webhook"""
    try:
        body = json.loads(body_json)
    except json.JSONDecodeError:
        print(f"Erro: JSON invalido: {body_json}")
        sys.exit(1)
    print("Criando webhook...")
    result = api_post("/webhook", body)
    print(f"Webhook criado! ID: {result.get('id', '?')}")
    pp(result)


def cmd_edit_webhook(webhook_id, body_json):
    """Edita webhook"""
    try:
        body = json.loads(body_json)
    except json.JSONDecodeError:
        print(f"Erro: JSON invalido: {body_json}")
        sys.exit(1)
    print(f"Editando webhook {webhook_id}...")
    result = api_put(f"/webhook/{webhook_id}", body)
    print("Webhook atualizado!")
    pp(result)


def cmd_delete_webhook(webhook_id):
    """Deleta webhook"""
    print(f"Deletando webhook {webhook_id}...")
    api_delete(f"/webhook/{webhook_id}")
    print("Webhook deletado.")


def cmd_webhook_logs(webhook_id):
    """Logs do webhook"""
    result = api_get(f"/webhook/logs/{webhook_id}")
    pp(result)


def cmd_resend_webhook(body_json):
    """Reenvia webhook"""
    try:
        body = json.loads(body_json)
    except json.JSONDecodeError:
        print(f"Erro: JSON invalido: {body_json}")
        sys.exit(1)
    print("Reenviando webhook...")
    result = api_post("/webhook/resend", body)
    pp(result)


# ============================================================
# COMANDOS — LOGICA
# ============================================================

def cmd_logics(form_id, logic_type=""):
    """Lista logicas do form"""
    params = {}
    if logic_type:
        params["type"] = logic_type
    print(f"Logicas do form {form_id}:")
    print()
    result = api_get(f"/logic/form/{form_id}", params)
    pp(result)


def cmd_create_logic(body_json):
    """Cria logica"""
    try:
        body = json.loads(body_json)
    except json.JSONDecodeError:
        print(f"Erro: JSON invalido: {body_json}")
        sys.exit(1)
    print("Criando logica...")
    result = api_post("/logic", body)
    print(f"Logica criada! ID: {result.get('id', '?')}")
    pp(result)


# ============================================================
# COMANDOS — INTEGRACOES
# ============================================================

def cmd_integrations():
    """Lista integracoes"""
    print("Integracoes:")
    print()
    result = api_get("/integration")
    if isinstance(result, list):
        for integ in result:
            print(f"  {integ.get('type', '?')} | ID: {integ.get('id', '?')}")
    else:
        pp(result)


def cmd_create_api_key():
    """Cria API Key"""
    print("Criando API Key...")
    result = api_post("/integration/api-key")
    print(f"API Key criada!")
    pp(result)


def cmd_delete_integration(integration_id):
    """Deleta integracao"""
    print(f"Deletando integracao {integration_id}...")
    api_delete(f"/integration/{integration_id}")
    print("Integracao deletada.")


# ============================================================
# COMANDOS — ENDING
# ============================================================

def cmd_create_ending(body_json):
    """Cria ending page"""
    try:
        body = json.loads(body_json)
    except json.JSONDecodeError:
        print(f"Erro: JSON invalido: {body_json}")
        sys.exit(1)
    print("Criando ending...")
    result = api_post("/ending", body)
    print(f"Ending criado! ID: {result.get('id', '?')}")
    pp(result)


def cmd_edit_ending(ending_id, body_json):
    """Edita ending"""
    try:
        body = json.loads(body_json)
    except json.JSONDecodeError:
        print(f"Erro: JSON invalido: {body_json}")
        sys.exit(1)
    result = api_put(f"/ending/{ending_id}", body)
    print("Ending atualizado!")
    pp(result)


# ============================================================
# COMANDOS — NOTIFICACOES
# ============================================================

def cmd_notifications():
    """Lista notificacoes"""
    result = api_get("/notification")
    pp(result)


# ============================================================
# COMANDOS — PLANOS
# ============================================================

def cmd_plans():
    """Lista planos"""
    print("Planos disponiveis:")
    print()
    result = api_get("/plan/all")
    if isinstance(result, list):
        for plan in result:
            print(f"  {plan.get('name', '?')} | R$ {plan.get('price', '?')} | ID: {plan.get('id', '?')}")
    else:
        pp(result)


# ============================================================
# COMANDOS — FAVORITOS
# ============================================================

def cmd_favorites():
    """Lista favoritos"""
    result = api_get("/favorite")
    pp(result)


def cmd_favorite_form(form_id):
    """Favorita form"""
    result = api_post("/favorite", {"form_id": form_id})
    print(f"Form favoritado!")
    pp(result)


# ============================================================
# COMANDOS — RAW
# ============================================================

def cmd_raw(method, endpoint, body_json=None):
    """Chamada raw a API"""
    method = method.upper()
    if method == "GET":
        result = api_get(endpoint)
    elif method == "POST":
        body = json.loads(body_json) if body_json else {}
        result = api_post(endpoint, body)
    elif method == "PUT":
        body = json.loads(body_json) if body_json else {}
        result = api_put(endpoint, body)
    elif method == "DELETE":
        result = api_delete(endpoint)
    else:
        print(f"Erro: Metodo HTTP invalido: {method}")
        sys.exit(1)
    pp(result)


# ============================================================
# HELP
# ============================================================

def cmd_help():
    """Mostra ajuda"""
    print("lightforms.py -- Helper para API do LightForms v2")
    print()
    print("AUTH:")
    print("  me                                        Usuario autenticado")
    print("  login <email> <password>                  Login (retorna token)")
    print()
    print("WORKSPACE:")
    print("  workspaces                                Lista workspaces")
    print("  folders                                   Lista folders")
    print("  create-folder <nome>                      Cria folder")
    print()
    print("FORMS:")
    print("  forms [page] [limit]                      Lista forms")
    print("  form <formId>                             Detalha form com questoes")
    print("  create-form <nome> [json_extra]           Cria form")
    print("  create-form-ai <prompt>                   Cria form via AI")
    print("  duplicate-form <formId>                   Duplica form")
    print("  edit-form <formId> <json>                 Edita form")
    print("  toggle-form <formId>                      Ativa/desativa form")
    print("  delete-form <formId>                      Deleta form")
    print("  stats <formId> [from] [to]                Estatisticas")
    print("  stats-per-day <formId>                    Stats por dia")
    print()
    print("RESPOSTAS:")
    print("  answers <formId> [page] [limit]           Lista respostas")
    print("  export-csv <formId>                       Exporta CSV")
    print("  delete-answer <answerId>                  Deleta resposta")
    print("  delete-answers <id1> <id2> ...            Deleta multiplas")
    print()
    print("QUESTOES:")
    print("  create-question <formId> <json>           Cria questao")
    print("  edit-question <questionId> <json>         Edita questao")
    print("  delete-question <questionId>              Deleta questao")
    print("  create-choice <json>                      Cria choice")
    print()
    print("WEBHOOKS:")
    print("  webhooks [formId]                         Lista webhooks")
    print("  create-webhook <json>                     Cria webhook")
    print("  edit-webhook <webhookId> <json>           Edita webhook")
    print("  delete-webhook <webhookId>                Deleta webhook")
    print("  webhook-logs <webhookId>                  Logs do webhook")
    print("  resend-webhook <json>                     Reenvia webhook")
    print()
    print("LOGICA:")
    print("  logics <formId> [type]                    Lista logicas")
    print("  create-logic <json>                       Cria logica")
    print()
    print("INTEGRACOES:")
    print("  integrations                              Lista integracoes")
    print("  create-api-key                            Cria API Key")
    print("  delete-integration <id>                   Deleta integracao")
    print()
    print("OUTROS:")
    print("  plans                                     Lista planos")
    print("  notifications                             Notificacoes")
    print("  favorites                                 Favoritos")
    print("  favorite-form <formId>                    Favorita form")
    print("  create-ending <json>                      Cria ending page")
    print("  edit-ending <endingId> <json>             Edita ending")
    print("  raw <METHOD> <endpoint> [json]            Chamada direta")
    print("  help                                      Mostra esta ajuda")
    print()
    print("Exemplos:")
    print("  python3 lightforms.py me")
    print("  python3 lightforms.py forms")
    print("  python3 lightforms.py create-form \"Pesquisa de Satisfacao\"")
    print('  python3 lightforms.py create-webhook \'{"url":"https://hook.com/x","form_id":"UUID"}\'')
    print("  python3 lightforms.py answers FORM_UUID")
    print("  python3 lightforms.py stats FORM_UUID")


# ============================================================
# ROUTER
# ============================================================

COMMANDS = {
    "me": (cmd_me, 0, 0),
    "login": (cmd_login, 2, 2),
    "workspaces": (cmd_workspaces, 0, 0),
    "folders": (cmd_folders, 0, 0),
    "create-folder": (cmd_create_folder, 1, 99),
    "forms": (cmd_forms, 0, 2),
    "form": (cmd_form, 1, 1),
    "create-form": (cmd_create_form, 1, 2),
    "create-form-ai": (cmd_create_form_ai, 1, 99),
    "duplicate-form": (cmd_duplicate_form, 1, 1),
    "edit-form": (cmd_edit_form, 2, 2),
    "toggle-form": (cmd_toggle_form, 1, 1),
    "delete-form": (cmd_delete_form, 1, 1),
    "stats": (cmd_stats, 1, 3),
    "stats-per-day": (cmd_stats_per_day, 1, 1),
    "answers": (cmd_answers, 1, 3),
    "export-csv": (cmd_export_csv, 1, 1),
    "delete-answer": (cmd_delete_answer, 1, 1),
    "delete-answers": (cmd_delete_answers, 1, 99),
    "create-question": (cmd_create_question, 2, 2),
    "edit-question": (cmd_edit_question, 2, 2),
    "delete-question": (cmd_delete_question, 1, 1),
    "create-choice": (cmd_create_choice, 1, 1),
    "webhooks": (cmd_webhooks, 0, 1),
    "create-webhook": (cmd_create_webhook, 1, 1),
    "edit-webhook": (cmd_edit_webhook, 2, 2),
    "delete-webhook": (cmd_delete_webhook, 1, 1),
    "webhook-logs": (cmd_webhook_logs, 1, 1),
    "resend-webhook": (cmd_resend_webhook, 1, 1),
    "logics": (cmd_logics, 1, 2),
    "create-logic": (cmd_create_logic, 1, 1),
    "integrations": (cmd_integrations, 0, 0),
    "create-api-key": (cmd_create_api_key, 0, 0),
    "delete-integration": (cmd_delete_integration, 1, 1),
    "plans": (cmd_plans, 0, 0),
    "notifications": (cmd_notifications, 0, 0),
    "favorites": (cmd_favorites, 0, 0),
    "favorite-form": (cmd_favorite_form, 1, 1),
    "create-ending": (cmd_create_ending, 1, 1),
    "edit-ending": (cmd_edit_ending, 2, 2),
    "raw": (cmd_raw, 2, 3),
    "help": (cmd_help, 0, 0),
    "--help": (cmd_help, 0, 0),
    "-h": (cmd_help, 0, 0),
}


def main():
    if len(sys.argv) < 2:
        cmd_help()
        return

    command = sys.argv[1]
    args = sys.argv[2:]

    if command not in COMMANDS:
        print(f"Erro: Comando desconhecido: {command}")
        print()
        cmd_help()
        sys.exit(1)

    func, min_args, max_args = COMMANDS[command]

    if len(args) < min_args:
        print(f"Erro: '{command}' precisa de pelo menos {min_args} argumento(s)")
        sys.exit(1)

    if max_args < 99 and len(args) > max_args:
        args = args[:max_args]

    func(*args)


if __name__ == "__main__":
    main()
