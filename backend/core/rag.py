"""Мини-RAG без внешних сервисов: BM25 по фрагментам из knowledge/*.md.

Подходит для русского и казахского: слова усекаются до 5 символов (грубый стемминг),
а в front matter можно добавлять keywords на обоих языках.
"""
import math
import re
from collections import Counter
from functools import lru_cache
from django.conf import settings

_WORD = re.compile(r"[\w]+", re.UNICODE)
_STOP = set("""и в во не на что я с со как а то все она так его но да ты к у же вы за бы по только ее мне было вот от меня еще нет о из ему
теперь когда даже ну вдруг ли если уже или ни быть был него до вас нибудь опять уж вам сказал ведь там потом себя ничего ей может они тут где есть надо
ней для мы тебя их чем была сам чтоб без будто чего раз тоже себе под будет ж тогда кто этот того потому этого какой совсем ним здесь этом один почти мой тем чтобы
нее сейчас были куда зачем всех никогда можно при два об другой хоть после над больше тот через эти нас про всего них какая много разве три эту моя впрочем хорошо свою
этой перед иногда лучше чуть том нельзя такой им более всегда конечно всю между мен сен ол біз сіз олар бір және бұл деп үшін мен ме ма маған маны оны оған сені мені әкелдім қойды қылды болды бар жоқ""".split())


def _stem(tok):
    return tok[:6]


def tokenize(text):
    toks = [t.lower() for t in _WORD.findall(text or "")]
    return [_stem(t) for t in toks if t not in _STOP and (len(t) > 2 or t.isdigit())]


def _parse(path):
    raw = path.read_text(encoding="utf-8")
    meta, body = {}, raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = parts[2]
    return meta, body


class Index:
    def __init__(self, directory):
        self.chunks = []
        for path in sorted(directory.glob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            meta, body = _parse(path)
            sections = re.split(r"^##\s+", body, flags=re.MULTILINE)
            for sec in sections:
                sec = sec.strip()
                if not sec:
                    continue
                head, _, text = sec.partition("\n")
                text = text.strip() or head
                cid = f"{path.stem}#{len(self.chunks)}"
                self.chunks.append({
                    "id": cid,
                    "title": meta.get("title", path.stem),
                    "article": meta.get("article", ""),
                    "source": meta.get("source", ""),
                    "url": meta.get("url", ""),
                    # norm — текст закона/Конституции; guide — практическая памятка проекта (не норма права)
                    # concept — программный документ/принцип внутренней политики (не норма права); к нему можно привязать статьи Конституции
                    "kind": meta.get("kind", "norm").lower() if meta.get("kind", "norm").lower() in ("guide", "concept") else "norm",
                    "constitution_articles": [x.strip() for x in meta.get("constitution_articles", "").split(",") if x.strip()],
                    "constitution": meta.get("constitution", "false").lower() == "true",
                    "verified": meta.get("verified", "false").lower() == "true",
                    "section": head.strip(),
                    "text": text,
                    "_tokens": tokenize(" ".join([meta.get("keywords", ""), meta.get("keywords", ""), head, text])),
                })
        n = len(self.chunks) or 1
        self.avg = sum(len(c["_tokens"]) for c in self.chunks) / n
        df = Counter()
        for c in self.chunks:
            df.update(set(c["_tokens"]))
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def search(self, query, k=4, min_coverage=0.3, min_score=0.5):
        q = list(dict.fromkeys(tokenize(query)))
        if not q or not self.chunks:
            return []
        k1, b = 1.5, 0.75
        results = []
        for c in self.chunks:
            tf = Counter(c["_tokens"])
            length = len(c["_tokens"]) or 1
            score, hit = 0.0, 0
            for t in q:
                if t in tf:
                    hit += 1
                    f = tf[t]
                    score += self.idf.get(t, 0) * f * (k1 + 1) / (f + k1 * (1 - b + b * length / self.avg))
            coverage = hit / len(q)
            if score >= min_score and coverage >= min_coverage:
                results.append((score, coverage, c))
        results.sort(key=lambda r: r[0], reverse=True)
        out = []
        for score, cov, c in results[:k]:
            item = {key: val for key, val in c.items() if not key.startswith("_")}
            item["score"] = round(score, 2)
            item["confidence"] = round(min(1.0, cov * 1.2), 2)
            out.append(item)
        return out


_ART_REF = re.compile(r"\b(?:стат\w*|ст\.?|бап)\s*(?:конституции\s*)?(?:рк\s*)?(?:№\s*)?(\d{1,3})(?!\d)(?:[.,]\d+)?", re.I)
_ART_REF2 = re.compile(r"(?<!\d)(\d{1,3})\s*-?\s*(?:я\s*)?стат\w*", re.I)


def by_article(query, k=4):
    """Прямой запрос номера статьи: «статья 33», «ст. 1», «Статья Конституции РК 1.1»."""
    m = _ART_REF.search(query or "") or _ART_REF2.search(query or "")
    if not m:
        return []
    want = f"ст. {int(m.group(1))}"
    out = []
    for c in get_index().chunks:
        if c["article"] == want:
            item = {key: val for key, val in c.items() if not key.startswith("_")}
            item.update(score=99.0, confidence=1.0)
            out.append(item)
    return out[:k]


@lru_cache(maxsize=1)
def get_index():
    return Index(settings.KNOWLEDGE_DIR)


def search(query, k=4):
    return get_index().search(query, k=k)


def article_chunks(refs):
    """Фрагменты Конституции по ссылкам вида «33» или «преамбула» (для карточек концепций)."""
    wanted = {("ст. " + r) if r.isdigit() else r.lower() for r in refs}
    return [{k: v for k, v in c.items() if not k.startswith("_")} | {"score": 0.0, "confidence": 1.0}
            for c in get_index().chunks if c["constitution"] and c["article"].lower() in wanted]
