import re
import urllib.request

ports = {
    5152: "lotofacil",
    5153: "diadesorte",
    5154: "lotomania",
    5155: "quina",
    5156: "megasena",
    5157: "maismilionaria",
    5158: "duplasena",
    5159: "timemania",
    5160: "supersete",
}

pat = re.compile(
    r'dd-ge-destaque-(\d)"[^>]*>.*?<span class="dd-ge-rank">(\d+)</span>([^<]+)',
    re.S,
)

for port, name in ports.items():
    url = f"http://127.0.0.1:{port}/"
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            html = r.read().decode("utf-8", "replace")
        rows = []
        seen = set()
        for m in pat.finditer(html):
            key = (m.group(1), m.group(3).strip())
            if key in seen:
                continue
            seen.add(key)
            rows.append(f"{m.group(1)} {m.group(3).strip()}")
        print(f"{port} {name}: " + (" | ".join(rows) if rows else "SEM DESTAQUE"))
    except Exception as e:
        print(f"{port} {name}: ERRO {type(e).__name__} {e}")
