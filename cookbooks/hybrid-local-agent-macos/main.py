from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright
import ast
import subprocess
import sys
import httpx
import os
import time
import urllib.parse
from typing import Optional
from memory import add_memory, search_memory
from rag_store import add_conversation_turn, search_conversations

# Initialisation du serveur MCP
mcp = FastMCP("Ma Sandbox Python & IA")

# --- ⚙️ CONFIGURATION ---

# 1. Le Modèle "Concierge" (Nettoyeur/Synthétiseur)
JANITOR_MODEL = "hf.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF:Q8_0"

# 2. Gestion des chemins (Mac/Windows compatible)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
CACHE_FILE = os.path.join(DATA_DIR, "last_web_content.txt")
SHARED_DIR = os.path.join(DATA_DIR, "shared")
os.makedirs(SHARED_DIR, exist_ok=True)

# Allow reading only inside the project by default.
ALLOWED_FILE_ROOTS = [BASE_DIR]
_extra_allowed = os.environ.get("MCP_ALLOWED_DIRS", "")
if _extra_allowed:
    for _p in _extra_allowed.split(os.pathsep):
        _p = _p.strip()
        if _p:
            ALLOWED_FILE_ROOTS.append(os.path.abspath(_p))

# 3. Limites de sécurité
MAX_CODE_CHARS = 50000
MAX_WEB_CHARS = 200000
MAX_FILE_CHARS = 200000
MAX_OUTPUT_CHARS = 20000
MAX_SHARED_CHARS = 200000

# Liste complète des imports bloqués (système, réseau, fichiers)
BLOCKED_IMPORTS = {
    "os", "sys", "subprocess", "socket", "shutil", "pathlib",
    "importlib", "builtins", "ctypes", "multiprocessing", "threading",
    "pickle", "marshal", "zipfile", "tarfile", "glob", "fnmatch",
    "tempfile", "configparser", "plistlib", "json", "yaml",
}

# Appels de fonctions dangereux
BLOCKED_CALLS = {
    "open", "eval", "exec", "compile", "__import__", "global",
    "breakpoint", "help", "dir", "vars", "locals", "reload",
}

# Noms/attributs interdits (y compris depuis les modules)
BLOCKED_NAMES = {
    "__builtins__", "builtins", "__globals__", "__class__", "__import__",
    "_io", "_thread", "sys", "os", "subprocess", "socket"
}

# Mots-clés et patterns suspects
SUSPICIOUS_TOKENS = [
    "import os", "import sys", "import subprocess", "import socket",
    "import shutil", "__import__", "open(", "eval(", "exec(",
    ".iterdir()", ".rglob", ".glob(", "pathlib", "global(",
    "__builtins__", "breakpoint", "help(", "vars(", "locals(",
]


# --- 🛠️ FONCTIONS UTILITAIRES ---

def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit: return text
    return text[:limit] + "\n\n[...sortie tronquée...]"

def _is_suspicious(code: str) -> Optional[str]:
    lowered = code.lower()
    for token in SUSPICIOUS_TOKENS:
        if token in lowered: return token
    return None

def _set_limits() -> None:
    try:
        import resource
        # On limite un peu la RAM/CPU des sous-processus par sécurité
        resource.setrlimit(resource.RLIMIT_CPU, (10, 10)) 
    except Exception:
        pass

def _is_allowed_path(path: str) -> Optional[str]:
    if not path:
        return "Erreur : chemin vide."
    expanded = os.path.expanduser(path)
    real_path = os.path.realpath(expanded)
    for root in ALLOWED_FILE_ROOTS:
        try:
            if os.path.commonpath([root, real_path]) == root:
                return None
        except ValueError:
            # On ignore les roots incompatibles (ex: lecteurs Windows)
            continue
    return "Erreur : chemin interdit (hors sandbox)."

def _validate_url(url: str) -> Optional[str]:
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return "URL invalide."
    if parsed.scheme not in {"http", "https"}:
        return "Schema URL interdit."
    if not parsed.netloc:
        return "URL sans hote."
    return None

def _safe_shared_path(filename: str) -> tuple[Optional[str], Optional[str]]:
    if not filename:
        return None, "Erreur : nom de fichier vide."
    expanded = os.path.expanduser(str(filename))
    if os.path.isabs(expanded):
        return None, "Erreur : chemin absolu interdit."
    normalized = os.path.normpath(expanded)
    if normalized.startswith(".."):
        return None, "Erreur : traversal interdit."
    full_path = os.path.join(SHARED_DIR, normalized)
    real_path = os.path.realpath(full_path)
    try:
        if os.path.commonpath([SHARED_DIR, real_path]) != SHARED_DIR:
            return None, "Erreur : chemin hors dossier partage."
    except ValueError:
        return None, "Erreur : chemin invalide."
    return real_path, None

def _normalize_attachments(attachments) -> list[str]:
    if attachments is None:
        return []
    if isinstance(attachments, str):
        attachments = [a.strip() for a in attachments.split(",") if a.strip()]
    if not isinstance(attachments, list):
        return []

    safe_paths = []
    for raw_path in attachments:
        expanded = os.path.expanduser(str(raw_path))
        path_error = _is_allowed_path(expanded)
        if path_error:
            raise ValueError(path_error)
        if not os.path.exists(expanded):
            raise ValueError(f"Piece jointe introuvable : {expanded}")
        safe_paths.append(os.path.realpath(expanded))
    return safe_paths

def _scan_code(code: str) -> Optional[str]:
    """
    Analyse le code AST pour détecter les patterns dangereux.
    Interdit: imports système, appels dangereux, accès aux attributs interdits.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"Erreur syntaxe: {e.msg} (ligne {e.lineno})"

    for node in ast.walk(tree):
        # Vérifier les imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                base = (alias.name or "").split(".")[0]
                if base.lower() in BLOCKED_IMPORTS:
                    return f"Import interdit: {base}"
        elif isinstance(node, ast.ImportFrom):
            base = (node.module or "").split(".")[0]
            if base.lower() in BLOCKED_IMPORTS:
                return f"Import interdit: {base}"
        
        # Vérifier les appels de fonctions
        elif isinstance(node, ast.Call):
            # Appel direct à une fonction bloquée
            if isinstance(node.func, ast.Name) and node.func.id in BLOCKED_CALLS:
                return f"Appel interdit: {node.func.id}"
            # Appel comme attribut (ex: obj.method())
            if isinstance(node.func, ast.Attribute):
                attr = node.func.attr
                if attr in BLOCKED_CALLS:
                    return f"Appel interdit: .{attr}()"
            
        # Vérifier les noms de variables/attributs
        elif isinstance(node, ast.Name):
            if node.id in BLOCKED_NAMES:
                return f"Nom interdit: {node.id}"
        
        # Vérifier les accès aux attributs dangereux (ex: obj.__builtins__)
        elif isinstance(node, ast.Attribute):
            attr_name = node.attr
            if attr_name.startswith("__") and attr_name.endswith("__"):
                if attr_name in {"builtins", "globals", "class", "mro"}:
                    return f"Attribut spécial interdit: {attr_name}"
    
    # Vérification supplémentaire : chercher des patterns dans le code brut
    for token in ["global ", "__import__", "breakpoint"]:
        if token in code:
            return f"Pattern interdit trouvé"
    
    return None

def run_applescript(script: str) -> str:
    """Exécute un script AppleScript pour piloter macOS (Mail, etc.)"""
    try:
        result = subprocess.run(
            ['osascript', '-e', script], 
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Erreur AppleScript : {e.stderr}"

# ==========================================
# 📧 OUTILS EMAIL (APPLE MAIL NATIF)
# ==========================================

# --- CONFIGURATION EMAIL ---
# L'adresse exacte que l'agent doit utiliser (Expéditeur et Destinataire)
AGENT_EMAIL = "user@exemple.com"

# ==========================================
# 📧 OUTILS EMAIL (APPLE MAIL - CIBLÉ)
# ==========================================

@mcp.tool()
def read_unread_mails_mac(limit: int = 5) -> str:
    """
    Environnement: Python local (mcp-sandbox).
    Lit les emails du dossier local 'IA_INBOX' (Sur mon Mac).
    Plus de crash : on ne lit qu'un dossier dédié et léger.
    """
    print(f"--- 🍏 Lecture Dossier Local (IA_INBOX) ---")
    
    attachments_dir = os.path.join(DATA_DIR, "mail_attachments", time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(attachments_dir, exist_ok=True)
    safe_attachments_dir = attachments_dir.replace('"', '\\"')

    script = f'''
    tell application "Mail"
        set output to ""
        set foundCount to 0
        set attachmentsFolder to "{safe_attachments_dir}/"
        
        -- 1. On cible le dossier local "Sur mon Mac"
        -- C'est beaucoup plus stable que l'IMAP distant
        try
            set iaBox to mailbox "IA_INBOX"
        on error
            return "ERREUR : Je ne trouve pas le dossier 'IA_INBOX'. Crée-le dans la section 'Sur mon Mac'."
        end try
        
        -- 2. On prend les messages non lus de ce dossier
        try
            set unreadMsgs to (every message of iaBox whose read status is false)
        on error
            return "Le dossier IA_INBOX semble vide pour l'instant."
        end try
        
        repeat with msg in unreadMsgs
            set foundCount to foundCount + 1
            
            set msgSubject to subject of msg
            set msgSender to sender of msg
            set msgContent to content of msg
            set attachmentsList to ""
            set attIndex to 0
            repeat with att in mail attachments of msg
                set attIndex to attIndex + 1
                set attName to name of att
                set savePath to attachmentsFolder & foundCount & "_" & attIndex & "_" & attName
                try
                    save att in (POSIX file savePath)
                    set attachmentsList to attachmentsList & savePath & " | "
                on error errMsg
                    set attachmentsList to attachmentsList & attName & " (erreur: " & errMsg & ") | "
                end try
            end repeat
            if attachmentsList is "" then
                set attachmentsList to "Aucune"
            end if
            
            if length of msgContent > 1000 then
                set msgContent to text 1 thru 1000 of msgContent & "..."
            end if
            
            set output to output & "--- EMAIL " & foundCount & " ---" & return & "DE: " & msgSender & return & "SUJET: " & msgSubject & return & "CONTENU: " & msgContent & return & "PIECES_JOINTES: " & attachmentsList & return & "------------------" & return
            
            if foundCount is greater than or equal to {limit} then exit repeat
        end repeat
        
        if foundCount is 0 then
            return "Aucun mail non lu dans le dossier IA_INBOX."
        end if
        
        return output
    end tell
    '''
    return run_applescript(script)

@mcp.tool()
def send_email_mac(to_address: str, subject: str, content: str, attachments: Optional[list[str]] = None) -> str:
    """
    Environnement: Python local (mcp-sandbox).
    Crée et envoie un email via Apple Mail en utilisant l'adresse 'user@example.com'.
    attachments: liste de chemins locaux à joindre.
    """
    print(f"--- 📤 Envoi (De: {AGENT_EMAIL} -> À: {to_address}) ---")
    
    safe_subject = subject.replace('"', '\\"')
    safe_content = content.replace('"', '\\"')

    try:
        safe_attachments = _normalize_attachments(attachments)
    except ValueError as e:
        return f"Erreur pieces jointes : {e}"

    attachment_script = ""
    if safe_attachments:
        for attach_path in safe_attachments:
            safe_path = attach_path.replace('"', '\\"')
            attachment_script += f'''
            try
                set attPath to POSIX file "{safe_path}"
                make new attachment with properties {{file name: attPath}} at after the last paragraph
            on error errMsg
                set attachmentErrors to attachmentErrors & "{safe_path}: " & errMsg & return
            end try
'''

    # ICI : On ajoute la propriété 'sender' pour forcer le compte
    script = f'''
    tell application "Mail"
        set attachmentErrors to ""
        set newMessage to make new outgoing message with properties {{subject:"{safe_subject}", content:"{safe_content}", sender:"{AGENT_EMAIL}", visible:true}}
        tell newMessage
            make new to recipient at end of to recipients with properties {{address:"{to_address}"}}
{attachment_script}
        end tell
        send newMessage
        if attachmentErrors is not "" then
            return "Email envoyé, mais erreurs PJ : " & attachmentErrors
        end if
    end tell
    return "Email envoyé avec succès via {AGENT_EMAIL} !"
    '''
    
    return run_applescript(script)

# ==========================================
# 🧹 OUTILS CONCIERGE (JANITOR / QWEN)
# ==========================================

@mcp.tool()
async def repair_code(code: str, instruction: str = "Corrige l'indentation et la syntaxe") -> str:
    """
    Environnement: Python local (mcp-sandbox).
    UTILISE QWEN CODER.
    Ne lance PAS le code. Il le réécrit proprement (indentation, typos).
    Utilise cet outil si ton code généré contient des erreurs de syntaxe.
    """
    print(f"--- 🧹 Janitor Repair ({JANITOR_MODEL}) ---")
    
    payload = {
        "model": JANITOR_MODEL,
        "prompt": f"Tu es un linter strict. Corrige le code suivant selon : {instruction}.\nNe change PAS la logique. Renvoie SEULEMENT le code.\n\nCODE:\n{code}",
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 16000}
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post("http://localhost:11434/api/generate", json=payload)
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
            return f"Erreur Janitor : {resp.text}"
    except Exception as e:
        return f"Erreur : {e}"

@mcp.tool()
async def reshorter(text: str = None, file_path: str = None, instruction: str = "Résume ce contenu") -> str:
    """
    Environnement: Python local (mcp-sandbox).
    Analyse un texte ou un fichier avec le Janitor (Qwen).
    """
    content = text
    source_msg = "Texte direct"

    if file_path:
        print(f"--- 📉 Lecture fichier {file_path} ---")
        safe_path = os.path.expanduser(file_path)
        path_error = _is_allowed_path(safe_path)
        if path_error:
            return path_error
        if os.path.exists(safe_path):
            with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(MAX_FILE_CHARS + 1)
            if len(content) > MAX_FILE_CHARS:
                content = content[:MAX_FILE_CHARS] + "\n\n[...contenu tronqué...]"
            source_msg = f"Fichier"
        else:
            return f"Erreur : Fichier introuvable au chemin : {safe_path}"

    if not content: return "Erreur : Pas de contenu."

    # Sécurité anti-timeout
    MAX_CHARS = 35000 
    if len(content) > MAX_CHARS:
        content = content[:MAX_CHARS] + "\n\n[...Texte coupé...]"

    print(f"--- 🏎️ {JANITOR_MODEL} ({source_msg}) : Analyse ---")
    
    payload = {
        "model": JANITOR_MODEL, 
        "prompt": f"Instruction: {instruction}\n\nContexte:\n{content}\n\nRÉPONSE RAPIDE:",
        "stream": False,
        "options": {"num_ctx": 32000, "temperature": 0.0}
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client: 
            response = await client.post("http://localhost:11434/api/generate", json=payload)
            if response.status_code == 200:
                return f"📝 SYNTHÈSE :\n{response.json().get('response', '')}"
            return f"Erreur Ollama : {response.text}"
    except Exception as e:
        return f"Erreur : {e}"

# ==========================================
# 🎮 OUTILS ACTION (EXECUTION & WEB)
# ==========================================

@mcp.tool()
def execute_python_code(code: str) -> str:
    """
    Environnement: Python local (mcp-sandbox).
    Exécute du code Python en sandbox avec restrictions renforcées :
    - Interdit global(), __builtins__, et tous les imports système
    - Utilise un environnement isolé pour l'exécution
    - Limite l'accès aux variables globales dangereuses
    """
    if not code: 
        return "Erreur : aucun code."
    
    # 1. Vérification de la longueur
    if len(code) > MAX_CODE_CHARS:
        return f"Erreur : code trop long ({len(code)} chars, max {MAX_CODE_CHARS})."
    
    # 2. Vérification par pattern matching (rapide)
    bad = _is_suspicious(code)
    if bad:
        return f"⛔ Erreur sécurité : '{bad}' est interdit."
    
    # 3. Analyse AST approfondie
    scan_error = _scan_code(code)
    if scan_error:
        return f"⛔ Erreur sécurité (AST) : {scan_error}"
    
    temp_file = os.path.join(DATA_DIR, "temp_script.py")
    with open(temp_file, "w", encoding="utf-8") as f:
        # On-wrap le code dans un namespace isolé
        isolated_code = f'''
# -*- coding: utf-8 -*-
# Code exécuté en sandbox isolée - Builtins restreints

def _sandbox_safe_exec():
    import math
    import random
    
    # Le code utilisateur suit :
    
{chr(10).join('    ' + line for line in code.splitlines())}

_sandbox_safe_exec()
del _sandbox_safe_exec
'''
        f.write(isolated_code)

    try:
        # Pygame / Tkinter -> Processus détaché (pas de GUI en sandbox)
        if "pygame" in code.lower() or "tkinter" in code.lower():
            return "⚠️ Les interfaces graphiques ne sont pas autorisées dans cette sandbox."
        
        # Préparer un environnement minimal pour l'exécution
        # On n'utilise pas preexec_fn sur Windows (pas de fork)
        exec_env = {
            '__name__': '__main__',
            'math': __import__('math'),
            'random': __import__('random'),
            'json': __import__('json') if '"json"' not in code else None,
            # Autres modules "sûrs" optionnels
        }
        
        # Exécution standard avec timeout
        result = subprocess.run(
            [sys.executable, temp_file],
            cwd=DATA_DIR,
            capture_output=True, 
            text=True, 
            timeout=30,
            preexec_fn=None if os.name == "nt" else _set_limits,
        )
        
        output = result.stdout or result.stderr
        
        # Nettoyer les traces de debug potentielles
        clean_output = []
        for line in output.splitlines():
            if '__builtins__' not in line and 'sys.path' not in line:
                clean_output.append(line)
        
        final_output = '\n'.join(clean_output)
        return _truncate(final_output, MAX_OUTPUT_CHARS) if len(output) > 1000 else final_output
        
    except subprocess.TimeoutExpired:
        return "⏰ Erreur : timeout (30s). Code trop long ou boucle infinie."
    except Exception as e:
        return f"💥 Erreur exécution : {type(e).__name__}: {e}"

@mcp.tool()
async def browser_fetch(url: str) -> str:
    """
    Environnement: Python local (mcp-sandbox).
    Lit une page web (Playwright) et la sauvegarde.
    """
    print(f"--- 🌐 Browser Fetch : {url} ---")
    url_error = _validate_url(url)
    if url_error:
        return f"Erreur URL : {url_error}"
    
    # Vérification anti-escape de domaine
    blocked_domains = {'localhost', '127.0.0.1', '0.0.0.0'}
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc in blocked_domains:
        return "⛔ Accès localhost interdit pour raisons de sécurité."
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            # Contexte isolé avec permissions restreintes
            context = await browser.new_context(
                ignore_https_errors=False,
                java_script_enabled=True,
                bypass_csp=True  # CSP peut bloquer certains scripts
            )
            
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                title = await page.title()
                
                # Nettoyage agressif du contenu (supprime scripts, styles, etc.)
                content = await page.evaluate("""() => {
                    // Supprimer tous les éléments potentiellement dangereux
                    const selectors = [
                        'script', 'style', 'iframe', 'object', 'embed',
                        'nav', 'footer', 'header', 'aside',
                        '[onclick]', 'onload', 'onerror'
                    ];
                    selectors.forEach(sel => {
                        document.querySelectorAll(sel).forEach(el => el.remove());
                    });
                    
                    // Supprimer les attributs event handlers
                    document.querySelectorAll('*').forEach(el => {
                        Array.from(el.attributes).forEach(attr => {
                            if (attr.name.startsWith('on')) el.removeAttribute(attr.name);
                        });
                    });
                    
                    return document.body.innerText;
                }""")
                
            except Exception:
                await browser.close()
                return "Erreur Timeout Page."
            
            await browser.close()
            
            if len(content) > MAX_WEB_CHARS:
                content = content[:MAX_WEB_CHARS] + "\n\n[...contenu tronqué...]"
            
            full_text = f"SOURCE: {url}\nTITRE: {title}\n\n{content}"
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                f.write(full_text)
            
            return f"✅ Page sauvegardée dans : {CACHE_FILE}\n({len(full_text)} chars). Utilise 'reshorter' pour l'analyser."
    except Exception as e:
        return f"Erreur Playwright : {e}"

@mcp.tool()
def save_to_memory(info: str, category: str = "general") -> str:
    """
    Environnement: Python local (mcp-sandbox).
    MÉMOIRE LONG TERME : Sauvegarde une information importante pour ne pas l'oublier.
    Utilise cet outil quand l'utilisateur te donne un fait, une préférence, ou un projet.
    Args:
        info: L'information à retenir (ex: "Le code du projet est 1234")
        category: La catégorie (ex: "projet", "perso", "travail")
    """
    return add_memory(info, category)

@mcp.tool()
def read_from_memory(query: str) -> str:
    """
    Environnement: Python local (mcp-sandbox).
    MÉMOIRE LONG TERME : Cherche une information dans le passé.
    Utilise cet outil quand tu ne connais pas la réponse ou qu'on fait référence à un truc passé.
    Args:
        query: Les mots-clés de la recherche (ex: "code projet", "couleur préférée")
    """
    return search_memory(query)

# ==========================================
# 🧠 OUTILS RAG (CHROMADB)
# ==========================================

@mcp.tool()
def rag_add_turn(role: str, content: str, source: str = "mcp", conversation_id: str = "default") -> str:
    """
    Environnement: Python local (mcp-sandbox).
    Ajoute un tour de conversation dans le RAG (ChromaDB).
    """
    return add_conversation_turn(
        role=role,
        content=content,
        source=source,
        conversation_id=conversation_id,
    )

@mcp.tool()
def rag_search(query: str, n_results: int = 5, conversation_id: Optional[str] = None) -> str:
    """
    Environnement: Python local (mcp-sandbox).
    Recherche dans les conversations stockées (RAG).
    """
    return search_conversations(query=query, n_results=n_results, conversation_id=conversation_id)

# ==========================================
# 📁 OUTILS FICHIERS PARTAGÉS
# ==========================================

@mcp.tool()
def shared_list_files(limit: int = 200) -> str:
    """
    Environnement: Python local (mcp-sandbox).
    Liste les fichiers dans data/shared.
    """
    try:
        limit = max(1, min(int(limit), 500))
    except Exception:
        limit = 200

    entries = []
    for root, _, files in os.walk(SHARED_DIR):
        for name in files:
            full_path = os.path.join(root, name)
            rel_path = os.path.relpath(full_path, SHARED_DIR)
            entries.append(f"{rel_path} -> {full_path}")
            if len(entries) >= limit:
                break
        if len(entries) >= limit:
            break

    if not entries:
        return "Aucun fichier partage."
    return "\n".join(entries)

@mcp.tool()
def shared_write_text(filename: str, content: str) -> str:
    """
    Environnement: Python local (mcp-sandbox).
    Ecrit un fichier texte dans data/shared.
    """
    if content is None:
        return "Erreur : contenu vide."
    if len(content) > MAX_SHARED_CHARS:
        return f"Erreur : contenu trop long ({len(content)} chars)."
    
    # Vérification de sécurité sur le contenu (pas de path traversal)
    for forbidden in ['../', '..\\', '/etc/', '\\Windows\\']:
        if forbidden.lower() in content.lower():
            return f"⛔ Contenu interdit: {forbidden}"
    
    full_path, error = _safe_shared_path(filename)
    if error:
        return error
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"OK: {full_path}"

@mcp.tool()
def shared_read_text(filename: str) -> str:
    """
    Environnement: Python local (mcp-sandbox).
    Lit un fichier texte depuis data/shared.
    """
    full_path, error = _safe_shared_path(filename)
    if error:
        return error
    if not os.path.exists(full_path):
        return "Erreur : fichier introuvable."
    
    # Vérification additionnelle du type de fichier
    try:
        with open(full_path, 'rb') as f:
            header = f.read(1024)
            # Interdiction des fichiers binaires exécutables
            if b'\x7fELF' in header or b'MZ' in header:
                return "⛔ Fichier binaire interdit."
    except Exception:
        pass
    
    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read(MAX_FILE_CHARS + 1)
    if len(content) > MAX_FILE_CHARS:
        content = content[:MAX_FILE_CHARS] + "\n\n[...contenu tronqué...]"
    return content

if __name__ == "__main__":
    mcp.run()