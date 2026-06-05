#!/usr/bin/env bash
# Wrapper para operações no Vaultwarden (keys.myworkhome.com.br)
# Uso: vault.sh <comando> [args...]
#   vault.sh list                          — lista todos os itens
#   vault.sh get <nome_ou_id>             — obtém item pelo nome ou ID
#   vault.sh save-password <nome> <user> <pass> [url]  — cria/atualiza login
#   vault.sh save-note <nome> <conteudo>  — cria nota segura
#   vault.sh save-ssh <nome> <chave_privada> [chave_publica]  — salva SSH key
#   vault.sh delete <id>                  — deleta item

set -euo pipefail

BW_SERVER="https://keys.myworkhome.com.br"
BW_EMAIL="oracle-evo@automacaosoftware.com.br"

_unlock() {
    if [[ -z "${BW_PASSWORD:-}" ]]; then
        # Tenta carregar do .env se não estiver no ambiente
        ENV_FILE="$(dirname "$(dirname "$(realpath "$0")")")/.env"
        if [[ -f "$ENV_FILE" ]]; then
            BW_PASSWORD=$(grep '^BW_PASSWORD=' "$ENV_FILE" | cut -d= -f2-)
        fi
        if [[ -z "${BW_PASSWORD:-}" ]]; then
            echo "ERRO: variável BW_PASSWORD não definida" >&2
            exit 1
        fi
    fi
    bw config server "$BW_SERVER" >/dev/null 2>&1
    # Garante login (ignora se já logado)
    echo "$BW_PASSWORD" | bw login "$BW_EMAIL" --raw >/dev/null 2>&1 || true
    # Desbloqueia via pipe e retorna a sessão
    echo "$BW_PASSWORD" | bw unlock --raw 2>/dev/null
}

_session() {
    SESSION=$(_unlock)
    bw sync --session "$SESSION" >/dev/null 2>&1
    echo "$SESSION"
}

cmd="${1:-list}"
shift || true

case "$cmd" in
    list)
        S=$(_session)
        bw list items --session "$S" 2>/dev/null \
            | python3 -c "
import sys, json
items = json.load(sys.stdin)
if not items:
    print('(vault vazio)')
else:
    types = {1:'Login', 2:'Nota', 3:'Cartão', 4:'Identidade', 5:'SSH Key'}
    for i in items:
        print(f\"{i['id']} | {types.get(i['type'],'?'):8} | {i['name']}\")
"
        ;;

    get)
        NAME="${1:-}"
        S=$(_session)
        bw get item "$NAME" --session "$S" 2>/dev/null | python3 -m json.tool
        ;;

    save-password)
        NAME="${1:-}"; USER="${2:-}"; PASS="${3:-}"; URL="${4:-}"
        S=$(_session)
        TEMPLATE=$(bw get template item --session "$S" 2>/dev/null \
            | python3 -c "
import sys, json
t = json.load(sys.stdin)
t['name'] = sys.argv[1]
t['type'] = 1
t['login'] = {'username': sys.argv[2], 'password': sys.argv[3], 'uris': [{'match': None, 'uri': sys.argv[4]}] if sys.argv[4] else []}
print(json.dumps(t))
" "$NAME" "$USER" "$PASS" "$URL")
        echo "$TEMPLATE" | bw encode | bw create item --session "$S" >/dev/null
        echo "OK: '$NAME' salvo no vault."
        ;;

    save-note)
        NAME="${1:-}"; CONTENT="${2:-}"
        S=$(_session)
        TEMPLATE=$(bw get template item --session "$S" 2>/dev/null \
            | python3 -c "
import sys, json
t = json.load(sys.stdin)
t['name'] = sys.argv[1]
t['type'] = 2
t['secureNote'] = {'type': 0}
t['notes'] = sys.argv[2]
print(json.dumps(t))
" "$NAME" "$CONTENT")
        echo "$TEMPLATE" | bw encode | bw create item --session "$S" >/dev/null
        echo "OK: nota '$NAME' salva no vault."
        ;;

    save-ssh)
        NAME="${1:-}"; PRIVKEY="${2:-}"; PUBKEY="${3:-}"
        S=$(_session)
        TEMPLATE=$(bw get template item --session "$S" 2>/dev/null \
            | python3 -c "
import sys, json
t = json.load(sys.stdin)
t['name'] = sys.argv[1]
t['type'] = 2
t['secureNote'] = {'type': 0}
content = 'PRIVATE KEY:\n' + sys.argv[2]
if sys.argv[3]:
    content += '\n\nPUBLIC KEY:\n' + sys.argv[3]
t['notes'] = content
print(json.dumps(t))
" "$NAME" "$PRIVKEY" "$PUBKEY")
        echo "$TEMPLATE" | bw encode | bw create item --session "$S" >/dev/null
        echo "OK: SSH key '$NAME' salvo no vault."
        ;;

    delete)
        ID="${1:-}"
        S=$(_session)
        bw delete item "$ID" --session "$S" --permanent
        echo "OK: item '$ID' deletado."
        ;;

    *)
        echo "Comando desconhecido: $cmd"
        exit 1
        ;;
esac
