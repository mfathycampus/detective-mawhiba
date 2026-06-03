from flask import Flask, render_template, request, jsonify, session
import random, time, json, os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mawhiba-detective-2026")

# ══════════════════════════════════════════
#  Game Logic
# ══════════════════════════════════════════

SUSPECTS_DATA = [
    {"name": "Mehtar",  "location": "المكتبة",        "motive": "الانتقام",  "alibi": "لا يوجد",       "suspicion": 0, "evidence": []},
    {"name": "Lena",    "location": "المختبر",         "motive": "المصلحة",   "alibi": "شهادة زميل",    "suspicion": 0, "evidence": []},
    {"name": "Omar",    "location": "الممر الخلفي",    "motive": "الطمع",     "alibi": "كاميرا الأمن",  "suspicion": 0, "evidence": []},
    {"name": "Sara",    "location": "المنزل",          "motive": "لا يوجد",   "alibi": "اتصال هاتفي",   "suspicion": 0, "evidence": []},
]

CLUES = [
    {"desc": "بصمة أصابع في المكتبة",     "suspect": "Mehtar", "weight": 35},
    {"desc": "شهادة شاهد عيان",            "suspect": "Lena",   "weight": 20},
    {"desc": "رسالة مشفرة على الطاولة",    "suspect": "Mehtar", "weight": 45},
    {"desc": "كاميرا أمنية عند الباب",     "suspect": "Omar",   "weight": 15},
    {"desc": "كتاب عن التشفير بجيبه",      "suspect": "Mehtar", "weight": 25},
]

SECRET_MSG   = "PHKWDU LV DW WKH OLEUDUB"
REAL_SHIFT   = 3
REAL_DECODED = "MEHTAR IS AT THE LIBRARY"
CRIMINAL     = "Mehtar"

def caesar_decrypt(text, shift):
    result = ""
    for ch in text:
        if ch.isalpha():
            base = 65 if ch.isupper() else 97
            result += chr((ord(ch) - base - shift) % 26 + base)
        else:
            result += ch
    return result

def binary_search(lst, target):
    lo, hi, steps, path = 0, len(lst)-1, 0, []
    while lo <= hi:
        mid = (lo + hi) // 2
        steps += 1
        path.append(lst[mid])
        if lst[mid] == target:
            return mid, steps, path
        elif lst[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1, steps, path

def pascal_triangle(n):
    t = [[1]]
    for i in range(1, n):
        row = [1]
        for j in range(1, i):
            row.append(t[i-1][j-1] + t[i-1][j])
        row.append(1)
        t.append(row)
    return t

def init_game(name):
    return {
        "name": name,
        "score": 100,
        "hints": 0,
        "clues_found": [],
        "solved": False,
        "start": time.time(),
        "suspects": [dict(s) for s in SUSPECTS_DATA],
        "actions": [],
    }

def get_game():
    return session.get("game")

def save_game(g):
    session["game"] = g
    session.modified = True

# ══════════════════════════════════════════
#  Routes
# ══════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/start", methods=["POST"])
def start():
    data = request.json or {}
    name = (data.get("name") or "محقق مجهول").strip()[:30]
    g = init_game(name)
    save_game(g)
    return jsonify({"ok": True, "name": name})

@app.route("/api/state")
def state():
    g = get_game()
    if not g:
        return jsonify({"error": "no_game"}), 400
    elapsed = int(time.time() - g["start"])
    return jsonify({
        "name": g["name"],
        "score": g["score"],
        "hints": g["hints"],
        "clues": g["clues_found"],
        "solved": g["solved"],
        "elapsed": f"{elapsed//60}:{elapsed%60:02d}",
        "suspects": g["suspects"],
        "actions": g["actions"][-6:],
    })

@app.route("/api/cipher", methods=["POST"])
def cipher():
    g = get_game()
    if not g: return jsonify({"error": "no_game"}), 400
    data = request.json or {}
    mode = data.get("mode", "auto")

    results = []
    if mode == "auto":
        kws = ["THE", "IS", "AT", "LIBRARY", "FOUND"]
        for shift in range(1, 26):
            decoded = caesar_decrypt(SECRET_MSG, shift)
            hits = sum(1 for w in kws if w in decoded)
            results.append({"shift": shift, "decoded": decoded, "hits": hits, "match": hits >= 2})
        correct = next((r for r in results if r["shift"] == REAL_SHIFT), None)
        if correct:
            for s in g["suspects"]:
                if s["name"] == CRIMINAL:
                    s["suspicion"] = min(100, s["suspicion"] + 45)
                    s["evidence"].append("الرسالة تشير لموقعه")
            if "رسالة مشفرة" not in " ".join(g["clues_found"]):
                g["clues_found"].append("الرسالة المفككة تشير إلى Mehtar في المكتبة")
            g["actions"].append("🔐 تم فك تشفير الرسالة السرية!")
        save_game(g)
        return jsonify({"results": results, "correct": REAL_SHIFT, "decoded": REAL_DECODED})

    elif mode == "manual":
        shift = int(data.get("shift", 0)) % 26
        decoded = caesar_decrypt(SECRET_MSG, shift)
        correct = (shift == REAL_SHIFT)
        if correct:
            for s in g["suspects"]:
                if s["name"] == CRIMINAL:
                    s["suspicion"] = min(100, s["suspicion"] + 45)
                    s["evidence"].append("الرسالة تشير لموقعه")
            if "رسالة مشفرة" not in " ".join(g["clues_found"]):
                g["clues_found"].append(f"الإزاحة {shift} صحيحة: {decoded}")
            g["actions"].append(f"🔐 جربت إزاحة {shift} — {'صحيح!' if correct else 'خطأ'}")
        else:
            g["score"] = max(0, g["score"] - 5)
            g["actions"].append(f"✗ إزاحة {shift} خاطئة (-5 نقاط)")
        save_game(g)
        return jsonify({"shift": shift, "decoded": decoded, "correct": correct})

    elif mode == "hint":
        if g["hints"] >= 3:
            return jsonify({"error": "no_hints"})
        g["hints"] += 1
        g["score"] = max(0, g["score"] - 10)
        g["actions"].append(f"💡 استخدمت تلميحاً {g['hints']}/3 (-10 نقاط)")
        save_game(g)
        return jsonify({"hint": "الإزاحة هي أول عدد أولي بعد 2", "hints_left": 3 - g["hints"]})

@app.route("/api/search", methods=["POST"])
def search():
    g = get_game()
    if not g: return jsonify({"error": "no_game"}), 400
    data   = request.json or {}
    target = (data.get("target") or "").strip().capitalize()
    mode   = data.get("mode", "binary")

    names = sorted([s["name"] for s in g["suspects"]])

    if mode == "binary":
        idx, steps, path = binary_search(names, target)
        g["actions"].append(f"🔍 بحث ثنائي عن '{target}': {steps} خطوة")
        save_game(g)
        return jsonify({"found": idx != -1, "index": idx, "steps": steps, "path": path, "names": names})

    elif mode == "linear":
        for i, n in enumerate(names):
            if n == target:
                g["actions"].append(f"🐢 بحث خطي عن '{target}': {i+1} خطوة")
                save_game(g)
                return jsonify({"found": True, "index": i, "steps": i+1, "names": names})
        save_game(g)
        return jsonify({"found": False, "index": -1, "steps": len(names), "names": names})

@app.route("/api/clue", methods=["POST"])
def add_clue():
    g = get_game()
    if not g: return jsonify({"error": "no_game"}), 400
    data = request.json or {}
    idx  = int(data.get("index", -1))
    if not (0 <= idx < len(CLUES)):
        return jsonify({"error": "invalid"})
    clue = CLUES[idx]
    for s in g["suspects"]:
        if s["name"] == clue["suspect"]:
            s["suspicion"] = min(100, s["suspicion"] + clue["weight"])
            if clue["desc"] not in s["evidence"]:
                s["evidence"].append(clue["desc"])
    if clue["desc"] not in g["clues_found"]:
        g["clues_found"].append(clue["desc"])
    g["actions"].append(f"🔬 دليل جديد: {clue['desc']}")
    save_game(g)
    return jsonify({"ok": True, "suspect": clue["suspect"], "weight": clue["weight"],
                    "suspects": g["suspects"]})

@app.route("/api/pascal", methods=["POST"])
def pascal():
    g = get_game()
    if not g: return jsonify({"error": "no_game"}), 400
    data = request.json or {}
    rows = min(max(int(data.get("rows", 5)), 3), 8)
    t    = pascal_triangle(rows)
    key  = sum(t[-1]) % 26
    decoded = caesar_decrypt(SECRET_MSG, key)
    g["actions"].append(f"🔺 مثلث باسكال {rows} صفوف — مفتاح {key}")
    save_game(g)
    return jsonify({"triangle": t, "key": key, "decoded": decoded,
                    "last_row_sum": sum(t[-1])})

@app.route("/api/verdict", methods=["POST"])
def verdict():
    g = get_game()
    if not g: return jsonify({"error": "no_game"}), 400
    data   = request.json or {}
    choice = (data.get("choice") or "").strip()
    correct = (choice == CRIMINAL)

    if correct:
        bonus = 50 if g["hints"] == 0 else (30 if g["hints"] <= 1 else 10)
        g["score"] += bonus
        g["solved"] = True
        elapsed = int(time.time() - g["start"])
        g["actions"].append(f"⚖ حكم صحيح! +{bonus} نقطة مكافأة")
        msg = f"🎉 أحسنت! {CRIMINAL} هو المجرم فعلاً. نقاط المكافأة: +{bonus}"
    else:
        g["score"] = max(0, g["score"] - 20)
        g["actions"].append(f"✗ حكم خاطئ على {choice} (-20 نقطة)")
        msg = f"✗ {choice} بريء! خسرت 20 نقطة. جمّع المزيد من الأدلة."
        elapsed = 0

    save_game(g)
    return jsonify({
        "correct": correct, "criminal": CRIMINAL, "msg": msg,
        "score": g["score"],
        "elapsed": f"{elapsed//60}:{elapsed%60:02d}" if correct else None,
        "hints_used": g["hints"],
    })

@app.route("/api/report")
def report():
    g = get_game()
    if not g: return jsonify({"error": "no_game"}), 400
    elapsed = int(time.time() - g["start"])
    lines = [
        "═" * 50,
        f"  تقرير التحقيق — المحقق: {g['name']}",
        "═" * 50,
        f"  الوقت: {elapsed//60}:{elapsed%60:02d}",
        f"  النقاط: {g['score']}",
        f"  التلميحات: {g['hints']}/3",
        f"  الأدلة: {len(g['clues_found'])}",
        "",
        "  الأدلة المكتشفة:",
    ]
    for i, c in enumerate(g["clues_found"], 1):
        lines.append(f"  {i}. {c}")
    lines.append("")
    lines.append("  ملفات المشتبهين:")
    lines.append("-" * 40)
    for s in sorted(g["suspects"], key=lambda x: x["suspicion"], reverse=True):
        bar = "█" * (s["suspicion"]//10) + "░" * (10 - s["suspicion"]//10)
        lines.append(f"  {s['name']:10} [{bar}] {s['suspicion']}%")
    if g["solved"]:
        lines += ["", f"  ✅ الجريمة حُلّت! المجرم: {CRIMINAL}"]
    return jsonify({"report": "\n".join(lines), "solved": g["solved"]})

if __name__ == "__main__":
    app.run(debug=True)
