"""
Genera la portada del perfil de GitHub de Jerson Molina (estilo terminal / neofetch).

- Retrato ASCII a partir de la foto de perfil de GitHub.
- Estadísticas reales (repos, contribuciones, estrellas, commits, seguidores, líneas de código).
- Dos versiones: dark_mode.svg y light_mode.svg, con efecto de escritura de terminal.

Lo ejecuta a diario la acción .github/workflows/update.yml. Solo necesita Pillow.
"""
import io
import json
import os
import sys
import time
import urllib.request
from html import escape

from PIL import Image, ImageEnhance, ImageOps

USER = os.environ.get("PROFILE_USER", "JersonMolinaT")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(OUT_DIR, "stats.json")

# ----------------------------------------------------------------------------
# Datos fijos (edítalos aquí)
# ----------------------------------------------------------------------------
PROFILE = [
    ("head", "jerson@molina"),
    ("kv", "OS", "Windows 11, iOS, iPadOS, Linux"),
    ("kv", "Uptime", "15+ años en tecnología y negocio"),
    ("kv", "Host", "DIGITAL POS (DGP) · Colombia"),
    ("kv", "Kernel", "Economista + Ing. de Software"),
    ("kv", "Rol", "Líder Desarrollo, Innovación y TI"),
    ("kv", "IDE", "VS Code, Claude Code, n8n"),
    ("gap",),
    ("kv", "Languages.Programming", "Python, JavaScript, SQL"),
    ("kv", "Languages.Real", "Español, English"),
    ("gap",),
    ("kv", "Stack.Automatización", "n8n, APIs, Webhooks"),
    ("kv", "Stack.IA", "Claude, Ollama, Agentes"),
    ("kv", "Stack.Sistemas", "CRM, ERP, Integraciones"),
    ("kv", "Certificaciones", "Auditor ISO 9001"),
    ("gap",),
    ("head", "Contacto"),
    ("kv", "Email.Personal", "jersonmol@gmail.com"),
    ("kv", "LinkedIn", "in/strategic-sales"),
    ("kv", "Web", "digitalpos.com.co"),
    ("gap",),
    ("head", "GitHub Stats"),
    ("stats1",),
    ("stats2",),
    ("stats3",),
]

WIDTH = 55            # ancho de cada línea de datos, en caracteres
COLS, ROWS = 37, 25   # tamaño del retrato ASCII


# ----------------------------------------------------------------------------
# GitHub API
# ----------------------------------------------------------------------------
def _req(url, data=None, tries=6):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    for i in range(tries):
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                if r.status == 202:          # GitHub está calculando estadísticas
                    time.sleep(3 + i * 2)
                    continue
                body = r.read()
                return json.loads(body) if body else None
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                print(f"  ! {url}: {e}", file=sys.stderr)
            time.sleep(2)
    return None


def graphql(query, variables):
    return _req("https://api.github.com/graphql",
                json.dumps({"query": query, "variables": variables}).encode())


def fetch_stats():
    stats = {}
    user = _req(f"https://api.github.com/users/{USER}") or {}
    stats["followers"] = user.get("followers")

    repos, page = [], 1
    while True:
        batch = _req(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&page={page}")
        if not batch:
            break
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    own = [r for r in repos if not r.get("fork")]
    stats["repos"] = len(repos) if repos else None
    stats["stars"] = sum(r.get("stargazers_count", 0) for r in repos) if repos else None

    q = """query($login:String!){ user(login:$login){
        repositoriesContributedTo(first:1, contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY,PULL_REQUEST_REVIEW]){ totalCount }
        contributionsCollection{ contributionYears } } }"""
    g = graphql(q, {"login": USER})
    try:
        u = g["data"]["user"]
        stats["contributed"] = u["repositoriesContributedTo"]["totalCount"]
        years = u["contributionsCollection"]["contributionYears"]
        total = 0
        for y in years:
            qy = """query($login:String!,$from:DateTime!,$to:DateTime!){ user(login:$login){
                contributionsCollection(from:$from,to:$to){ totalCommitContributions restrictedContributionsCount } } }"""
            gy = graphql(qy, {"login": USER, "from": f"{y}-01-01T00:00:00Z", "to": f"{y}-12-31T23:59:59Z"})
            c = gy["data"]["user"]["contributionsCollection"]
            total += c["totalCommitContributions"] + c["restrictedContributionsCount"]
        stats["commits"] = total
    except Exception as e:  # noqa: BLE001
        print(f"  ! GraphQL: {e}", file=sys.stderr)

    add = dele = 0
    ok = False
    for r in own:
        contrib = _req(f"https://api.github.com/repos/{r['full_name']}/stats/contributors")
        if not isinstance(contrib, list):
            continue
        ok = True
        for c in contrib:
            if (c.get("author") or {}).get("login", "").lower() == USER.lower():
                for w in c.get("weeks", []):
                    add += w.get("a", 0)
                    dele += w.get("d", 0)
    if ok:
        stats["add"], stats["del"] = add, dele
    return stats


def load_stats():
    old = {}
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8") as f:
            old = json.load(f)
    new = fetch_stats()
    for k, v in new.items():        # si un dato falla, conserva el último bueno
        if v is not None:
            old[k] = v
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(old, f, indent=2)
    return old


# ----------------------------------------------------------------------------
# Retrato ASCII
# ----------------------------------------------------------------------------
RAMP = " .'`,:;!|ijlt1fJ?7*%kHSMW8@"


def portrait():
    raw = None
    for url in (f"https://github.com/{USER}.png?size=460",):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER}), timeout=60) as r:
                raw = r.read()
        except Exception as e:  # noqa: BLE001
            print(f"  ! avatar: {e}", file=sys.stderr)
    local = os.path.join(OUT_DIR, "avatar.png")
    if raw:
        Image.open(io.BytesIO(raw)).convert("RGB").save(local)
    if not os.path.exists(local):
        return [" " * COLS] * ROWS, [" " * COLS] * ROWS
    img = Image.open(local).convert("L")

    # recorte vertical centrado (cada carácter es ~2 veces más alto que ancho)
    w, h = img.size
    target = (COLS * 9.6) / (ROWS * 19)
    cw = min(w, int(h * target))
    ch = int(cw / target)
    left = (w - cw) // 2
    img = img.crop((left, 0, left + cw, min(h, ch)))
    img = ImageOps.autocontrast(img, cutoff=2)
    img = ImageEnhance.Contrast(img).enhance(1.25)
    small = img.resize((COLS, ROWS), Image.LANCZOS)

    def render(invert):
        rows = []
        for y in range(ROWS):
            row = ""
            for x in range(COLS):
                v = small.getpixel((x, y))
                if invert:
                    v = 255 - v
                row += RAMP[min(len(RAMP) - 1, v * len(RAMP) // 256)]
            rows.append(row)
        return rows

    return render(False), render(True)   # (modo oscuro, modo claro)


# ----------------------------------------------------------------------------
# SVG
# ----------------------------------------------------------------------------
def theme(dark):
    return dict(
        bg="#161b22" if dark else "#f6f8fa",
        fg="#c9d1d9" if dark else "#24292f",
        key="#ffa657" if dark else "#953800",
        val="#a5d6ff" if dark else "#0a3069",
        dots="#616e7f" if dark else "#c2cfde",
        add="#3fb950" if dark else "#1a7f37",
        dele="#f85149" if dark else "#cf222e",
    )


def fmt(n):
    return "—" if n is None else f"{n:,}"


def build(dark, art, s):
    t = theme(dark)
    D = lambda x: f'<tspan fill="{t["dots"]}">{x}</tspan>'   # noqa: E731
    K = lambda x: f'<tspan fill="{t["key"]}">{escape(x)}</tspan>'   # noqa: E731
    V = lambda x: f'<tspan fill="{t["val"]}">{escape(x)}</tspan>'   # noqa: E731

    def dots(used):
        return " " + "." * max(2, WIDTH - used) + " "

    out, ys = [], []
    lh, x_txt, y = 20, 410, 30
    for line in PROFILE:
        k = line[0]
        if k == "gap":
            y += lh * 0.55
            continue
        if k == "head":
            name = line[1]
            frag = f'{escape(name)} {D("-" * (WIDTH - len(name)))}'
        elif k == "kv":
            key, val = line[1], line[2]
            frag = f'{D(". ")}{K(key)}:{D(dots(len(key) + len(val) + 4))}{V(val)}'
        elif k == "stats1":
            a = f'{fmt(s.get("repos"))}'
            b = f'{fmt(s.get("contributed"))}'
            c = f'{fmt(s.get("stars"))}'
            left = f"Repos: {a} {{Contribuidos: {b}}}"
            frag = (f'{D(". ")}{K("Repos")}:{D(" ")}{V(a)} {{{K("Contribuidos")}: {V(b)}}}'
                    f'{D(dots(len(left) + len("Stars: ") + len(c) + 5))}| {K("Stars")}: {V(c)}')
        elif k == "stats2":
            a, b = fmt(s.get("commits")), fmt(s.get("followers"))
            left = f"Commits: {a}"
            frag = (f'{D(". ")}{K("Commits")}:{D(" ")}{V(a)}'
                    f'{D(dots(len(left) + len("Followers: ") + len(b) + 5))}| {K("Followers")}: {V(b)}')
        elif k == "stats3":
            a, d = s.get("add"), s.get("del")
            loc = None if a is None else a - d
            frag = (f'{D(". ")}{K("Lines of Code")}:{D(" ")}{V(fmt(loc))} ( '
                    f'<tspan fill="{t["add"]}">{fmt(a)}++</tspan>, '
                    f'<tspan fill="{t["dele"]}">{fmt(d)}--</tspan> )')
        out.append(frag)
        ys.append(y)
        y += lh
    height = int(y + 15)

    # efecto terminal: cada línea se "escribe" en orden
    defs, texts = [], []
    step, t0 = 0.28, 0.4
    for i, (yy, frag) in enumerate(zip(ys, out)):
        b = t0 + i * step
        defs.append(f'<clipPath id="c{i}"><rect x="{x_txt - 5}" y="{yy - 17}" height="22" width="0">'
                    f'<animate attributeName="width" from="0" to="580" begin="{b:.2f}s" dur="{step:.2f}s" fill="freeze"/>'
                    f'</rect></clipPath>')
        texts.append(f'<text x="{x_txt}" y="{yy}" fill="{t["fg"]}" clip-path="url(#c{i})">{frag}</text>')
    end = t0 + len(ys) * step
    cursor = (f'<rect x="{x_txt}" y="{ys[-1] + 9}" width="10" height="3" fill="{t["val"]}">'
              f'<animate attributeName="opacity" values="1;0;1" dur="1s" begin="{end:.2f}s" repeatCount="indefinite"/></rect>')

    ay0 = 30 + (height - 30 - len(art) * 19) / 2 + 12
    art_svg = "".join(f'<tspan x="15" y="{ay0 + i * 19:.0f}">{escape(r)}</tspan>' for i, r in enumerate(art))

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" font-family="ConsolasFallback,Consolas,'DejaVu Sans Mono',monospace" width="985" height="{height}" font-size="16px">
<style>
@font-face {{ src: local('Consolas'), local('Consolas Bold'); font-family: 'ConsolasFallback'; font-display: swap; -webkit-size-adjust: 109%; size-adjust: 109%; }}
text, tspan {{ white-space: pre; }}
</style>
<rect width="985" height="{height}" fill="{t["bg"]}" rx="15"/>
<text x="15" y="30" fill="{t["fg"]}">{art_svg}</text>
<defs>{"".join(defs)}</defs>
{"".join(texts)}
{cursor}
</svg>
'''


def main():
    print("Retrato...")
    art_dark, art_light = portrait()
    print("Estadísticas...")
    s = load_stats()
    print(json.dumps(s))
    for name, dark, art in (("dark_mode", True, art_dark), ("light_mode", False, art_light)):
        with open(os.path.join(OUT_DIR, f"{name}.svg"), "w", encoding="utf-8") as f:
            f.write(build(dark, art, s))
    print("OK")


if __name__ == "__main__":
    main()
