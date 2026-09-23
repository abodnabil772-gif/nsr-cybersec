import os
import subprocess
from datetime import datetime, timezone
from supabase import create_client

# ==== الاتصال بـ Supabase ====
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

tool = os.getenv("TOOL", "").lower().strip()
target = os.getenv("TARGET", "").strip()
op_id = os.getenv("OP_ID", "").strip()

# ==== خريطة الأدوات 1-6 ====
TOOLS = {
    "msf": (
        "Metasploit Framework",
        f"docker exec kali msfconsole -q -x "
        f"'use auxiliary/scanner/portscan/tcp; "
        f"set RHOSTS {target}; set THREADS 10; run; exit'"
    ),
    "sliver": (
        "Sliver C2 (Cobalt Strike alternative)",
        "docker exec kali bash -c 'curl -sSL https://sliver.sh/install | bash 2>&1 | tail -15; sliver-server --version 2>&1 | head -3'"
    ),
    "asyncrat": (
        "AsyncRAT Builder",
        "docker exec kali bash -c 'cd /tmp && git clone --depth 1 https://github.com/NYAN-x-CAT/AsyncRAT-C-Sharp.git 2>&1 | tail -3 && ls -la AsyncRAT-C-Sharp | head -20'"
    ),
    "spynote": (
        "SpyNote Android RAT",
        "docker exec kali bash -c 'cd /tmp && (git clone --depth 1 https://github.com/SpyNote/SpyNote.git 2>&1 | tail -3 || true) && echo \"SpyNote module checked\" && ls /tmp | head -20'"
    ),
    "set": (
        "Social-Engineer Toolkit",
        "docker exec kali bash -c 'setoolkit --version 2>&1 | head -10 || echo \"SET ready\"'"
    ),
    "aircrack": (
        "Aircrack-ng",
        "docker exec kali bash -c 'aircrack-ng --help 2>&1 | head -15'"
    ),
}

# ==== حماية: منع Command Injection ====
FORBIDDEN = [";", "|", "&", "`", "$", ">", "<", "\n", "\r", " "]
if any(c in target for c in FORBIDDEN):
    sb.table("operations_log").update({
        "status": "blocked",
        "output": "هدف غير آمن: يحتوي رموزاً ممنوعة",
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", op_id).execute()
    raise SystemExit(1)

# ==== التحقق من الأداة ====
if tool not in TOOLS:
    sb.table("operations_log").update({
        "status": "blocked",
        "output": f"الأداة '{tool}' غير مصرح بها. المتاح: {list(TOOLS.keys())}",
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", op_id).execute()
    raise SystemExit(1)

# ==== تحديث الحالة: running ====
name, cmd = TOOLS[tool]

sb.table("operations_log").update({
    "status": "running",
    "command": f"[{name}] target={target}",
}).eq("id", op_id).execute()

# ==== التنفيذ ====
try:
    r = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=1200
    )
    output = (r.stdout or "") + (r.stderr or "")
    if not output.strip():
        output = "تم التنفيذ بدون مخرجات."

    sb.table("operations_log").update({
        "status": "completed" if r.returncode == 0 else "failed",
        "output": output[:100000],
        "exit_code": r.returncode,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", op_id).execute()

except subprocess.TimeoutExpired:
    sb.table("operations_log").update({
        "status": "timeout",
        "output": "تجاوز الوقت 20 دقيقة.",
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", op_id).execute()

except Exception as e:
    sb.table("operations_log").update({
        "status": "failed",
        "output": f"خطأ غير متوقع: {str(e)}",
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", op_id).execute()
