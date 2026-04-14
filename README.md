# Agentes Claude — Hoppe & LightForms

Agentes especializados para operar o Hoppe e o LightForms via Claude Code.

## Instalação

### 1. Criar as pastas necessárias

```bash
mkdir -p ~/.claude/agents
mkdir -p ~/.claude/skills/lightforms/scripts
```

### 2. Baixar os arquivos

```bash
# Agentes
curl -o ~/.claude/agents/hoppe.md https://raw.githubusercontent.com/tiago1002bravy/sbroggio/main/hoppe.md
curl -o ~/.claude/agents/lightforms.md https://raw.githubusercontent.com/tiago1002bravy/sbroggio/main/lightforms.md

# Script helper do LightForms
curl -o ~/.claude/skills/lightforms/scripts/lightforms.py https://raw.githubusercontent.com/tiago1002bravy/sbroggio/main/scripts/lightforms.py
chmod +x ~/.claude/skills/lightforms/scripts/lightforms.py
```

### 3. Configurar credenciais do LightForms

```bash
cat > ~/.claude/skills/lightforms/config.env << 'EOF'
LIGHTFORMS_BASE_URL=https://app.lightforms.io
LIGHTFORMS_TOKEN=SEU_JWT_TOKEN_AQUI
LIGHTFORMS_WORKSPACE_ID=SEU_WORKSPACE_UUID_AQUI
EOF
```

Para obter o token:

```bash
python3 ~/.claude/skills/lightforms/scripts/lightforms.py login SEU_EMAIL SENHA
```

### 4. Verificar instalação

```bash
# Testar LightForms
python3 ~/.claude/skills/lightforms/scripts/lightforms.py me
```

Para o Hoppe, o agente usa o MCP — basta ter o servidor MCP do Hoppe configurado no Claude Code.

---

## Agentes disponíveis

| Agente | Descrição |
|--------|-----------|
| `hoppe` | Gerencia tasks, projetos, CRM e financeiro via MCP |
| `lightforms` | Gerencia formulários, respostas, webhooks e integrações via API |
