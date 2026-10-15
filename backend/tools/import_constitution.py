"""Разбор Конституции РК (текст из .docx / .md / .txt) на файлы knowledge/konst2026_*.md.

Запуск:
  extract-text Конституция.docx > const.txt          # или: pandoc Конституция.docx -t plain -o const.txt
  python tools/import_constitution.py const.txt --lang ru --url https://... [--unverified]

Каждая статья — отдельный файл; длинные статьи делятся на части по пунктам (для точного поиска).
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
ART = re.compile(r"^(?:Статья|Бап|Article)\s+(\d+)\s*$", re.I)
SEC = re.compile(r"^(?:Раздел|Бөлім|Section)\s+([IVXLC]+)\s*$", re.I)
MAXLEN = 1100


def clean(line):
    line = LINK.sub(r"\1", line)               # убираем ссылки
    line = line.replace("**", "").replace("\xa0", " ")
    return re.sub(r"[ \t]+", " ", line).strip()


def split_parts(paras):
    """Группирует абзацы в части до MAXLEN знаков, не разрывая пункты."""
    parts, cur = [], ""
    for p in paras:
        if cur and len(cur) + len(p) > MAXLEN:
            parts.append(cur.strip())
            cur = ""
        cur += p + "\n\n"
    if cur.strip():
        parts.append(cur.strip())
    return parts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--lang", default="ru", choices=["ru", "kk"])
    ap.add_argument("--url", default="https://prg.kz/document/?doc_id=35502996")
    ap.add_argument("--source", default="Конституция Республики Казахстан (принята на референдуме 15 марта 2026 г.)")
    ap.add_argument("--unverified", action="store_true", help="не ставить verified: true")
    ap.add_argument("--out", default=str(ROOT / "knowledge"))
    a = ap.parse_args()

    extra = json.loads((ROOT / "tools" / "keywords_ru.json").read_text(encoding="utf-8")) if a.lang == "ru" else {}
    lines = [clean(l) for l in Path(a.src).read_text(encoding="utf-8").splitlines()]
    lines = [l for l in lines if l]
    sec_no, sec_title, arts, cur, i = "", "", {}, None, 0
    preamble = []
    while i < len(lines):
        l = lines[i]
        if SEC.match(l):
            sec_no = SEC.match(l).group(1)
            sec_title = lines[i + 1] if i + 1 < len(lines) and not ART.match(lines[i + 1]) else ""
            i += 2 if sec_title else 1
            cur = None
            continue
        m = ART.match(l)
        if m:
            n = int(m.group(1))
            cur = arts.setdefault(n, {"n": n, "sec_no": sec_no, "sec": sec_title, "paras": []})
        elif cur is not None:
            cur["paras"].append(l)
        elif not sec_no and l.upper().startswith(("МЫ, ", "МЫ,")) or (not sec_no and preamble):
            preamble.append(l)
        i += 1

    out = Path(a.out)
    out.mkdir(exist_ok=True)
    tag = "" if a.lang == "ru" else "_kk"
    verified = "false" if a.unverified else "true"
    n_files = 0
    for n, art in sorted(arts.items()):
        body = [p for p in art["paras"] if not re.match(r"^(Источник|Документ|Статус)", p)]
        parts = split_parts(body)
        text = []
        for k, part in enumerate(parts, 1):
            head = f"Статья {n}" + (f", часть {k} из {len(parts)}" if len(parts) > 1 else "")
            text.append(f"## {head}\n{part}\n")
        meta = (f"---\ntitle: Конституция РК 2026, статья {n}. Раздел {art['sec_no']}. {art['sec']}\n"
                f"article: ст. {n}\nsource: {a.source}\nurl: {a.url}\nconstitution: true\nverified: {verified}\n"
                f"lang: {a.lang}\nkeywords: {art['sec']}, {extra.get(str(n), '')}\n---\n")
        (out / f"konst2026{tag}_st{n:02d}.md").write_text(meta + "\n".join(text), encoding="utf-8")
        n_files += 1
    if preamble:
        (out / f"konst2026{tag}_preambula.md").write_text(
            f"---\ntitle: Конституция РК 2026, преамбула\narticle: преамбула\nsource: {a.source}\nurl: {a.url}\n"
            f"constitution: true\nverified: {verified}\nlang: {a.lang}\nkeywords: ценности, Справедливый Казахстан, Закон и Порядок\n---\n"
            f"## Преамбула\n" + "\n".join(preamble) + "\n", encoding="utf-8")
    nums = sorted(arts)
    print(f"Статей: {len(arts)} (номера {nums[0]}–{nums[-1]}), файлов: {n_files}, преамбула: {'да' if preamble else 'нет'}")
    missing = [x for x in range(nums[0], nums[-1] + 1) if x not in arts]
    if missing:
        print("ПРОПУЩЕНЫ статьи:", missing, file=sys.stderr)


if __name__ == "__main__":
    main()
