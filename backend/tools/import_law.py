"""Импорт отдельных статей кодексов и законов в knowledge/ (рядом с Конституцией).

Зачем выборочно: весь кодекс — это сотни статей, которые разбавят поиск. Берите только нужные темы
(угрозы, шантаж, мошенничество, трудовые споры и т.д.) и обязательно сверяйте текст с официальным источником.

Запуск (текст кодекса скопируйте с adilet.zan.kz или prg.kz в файл):
  python tools/import_law.py uk.txt --code uk --short "УК РК" \
      --name "Уголовный кодекс Республики Казахстан от 3 июля 2014 года № 226-V" \
      --url https://adilet.zan.kz/rus/docs/K1400000226 \
      --articles 105,115 --keywords-file tools/law_keywords_example.json --verified

Результат: knowledge/uk_st115.md и т.д. Поле `article` получает вид «ст. 115 УК РК», поэтому не пересекается
с поиском по номеру статьи Конституции. Без --verified ставится verified: false (в интерфейсе — «не сверено»).
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
HEADER = re.compile(r"^(?:Статья|Бап|Article)\s+(\d+(?:[-.]\d+)?)\.?\s*(.*)$", re.I)
HEADER_KK = re.compile(r"^(\d+(?:[-.]\d+)?)\s*-\s*бап\.?\s*(.*)$", re.I)
# Служебные пометки об изменениях редакции (prg.kz / adilet) — это не текст нормы
NOISE = re.compile(
    r"(внесен\w*\s+изменени|изложен\w*\s+в\s+редакции|исключен\w*\s+в\s+соответствии|"
    r"в\s+соответствии\s+с\s+Законом\s+РК\s+от|ред\.\)|см\.\s+статью|вводится\s+в\s+действие|"
    r"^Источник|^Документ|^Статус|^Примечание\s+РЦПИ)", re.I)
MAXLEN = 1100


def clean(line):
    line = LINK.sub(r"\1", line)
    line = line.replace("**", "").replace("\xa0", " ")
    return re.sub(r"[ \t]+", " ", line).strip()


def parse_articles(text):
    """Возвращает {номер_строкой: {"title": str, "paras": [str]}}."""
    lines = [clean(l) for l in text.splitlines()]
    lines = [l for l in lines if l]
    arts, cur, i = {}, None, 0
    while i < len(lines):
        l = lines[i]
        m = HEADER.match(l) or HEADER_KK.match(l)
        if m and len(l) < 260 and "настоящ" not in l.lower():
            num, title = m.group(1), m.group(2).strip()
            if not title and i + 1 < len(lines) and not re.match(r"^\d", lines[i + 1]) and not NOISE.search(lines[i + 1]):
                title = lines[i + 1]
                i += 1
            cur = arts.setdefault(num, {"title": title, "paras": []})
            if title and not cur["title"]:
                cur["title"] = title
        elif cur is not None and not NOISE.search(l):
            cur["paras"].append(l)
        i += 1
    return arts


def split_parts(paras):
    parts, cur = [], ""
    for p in paras:
        if cur and len(cur) + len(p) > MAXLEN:
            parts.append(cur.strip())
            cur = ""
        cur += p + "\n\n"
    if cur.strip():
        parts.append(cur.strip())
    return parts


def render(num, art, *, short, name, source_url, lang, verified, keywords):
    parts = split_parts(art["paras"]) or [art["title"]]
    sections = []
    for k, part in enumerate(parts, 1):
        head = f"Статья {num}" + (f", часть {k} из {len(parts)}" if len(parts) > 1 else "")
        sections.append(f"## {head}\n{part}\n")
    title = f"{short}, статья {num}. {art['title']}".strip().rstrip(".")
    meta = (f"---\ntitle: {title}\narticle: ст. {num} {short}\nsource: {name}\nurl: {source_url}\n"
            f"kind: norm\nconstitution: false\nverified: {'true' if verified else 'false'}\nlang: {lang}\n"
            f"keywords: {art['title']}, {keywords}\n---\n")
    return meta + "\n".join(sections)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--code", required=True, help="префикс файлов, например uk, tk, gk")
    ap.add_argument("--short", required=True, help="краткое название, например «УК РК»")
    ap.add_argument("--name", required=True, help="полное название акта")
    ap.add_argument("--url", default="")
    ap.add_argument("--lang", default="ru", choices=["ru", "kk"])
    ap.add_argument("--articles", default="", help="номера через запятую; пусто — все статьи (не рекомендуется)")
    ap.add_argument("--keywords-file", default="", help='JSON {"115": "угроза, угрожают, ..."} — бытовые синонимы')
    ap.add_argument("--verified", action="store_true", help="текст сверен с официальным источником")
    ap.add_argument("--out", default=str(ROOT / "knowledge"))
    a = ap.parse_args()

    arts = parse_articles(Path(a.src).read_text(encoding="utf-8"))
    wanted = [x.strip() for x in a.articles.split(",") if x.strip()] or sorted(arts, key=lambda n: float(n.replace("-", ".")))
    kw = json.loads(Path(a.keywords_file).read_text(encoding="utf-8")) if a.keywords_file else {}

    out = Path(a.out)
    out.mkdir(exist_ok=True)
    written, missing = 0, []
    for num in wanted:
        art = arts.get(num)
        if not art or not art["paras"]:
            missing.append(num)
            continue
        body = render(num, art, short=a.short, name=a.name, source_url=a.url, lang=a.lang,
                      verified=a.verified, keywords=kw.get(num, ""))
        (out / f"{a.code}_st{num.replace('.', '_')}.md").write_text(body, encoding="utf-8")
        written += 1
    print(f"Записано статей: {written} из {len(wanted)}")
    if missing:
        print("НЕ НАЙДЕНЫ или пустые:", ", ".join(missing), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
