"""Автопроверка бота на наборе вопросов: python tools/eval_questions.py [--offline] [--verbose]  (из папки backend).

Для каждого вопроса в eval_set.json проверяется:
  expect       — среди источников есть одна из указанных статей;
  expect_kind  — среди источников есть источник этого вида (concept | guide | norm);
  refuse       — бот честно отказал (п. 4.9 положения);
  safety       — в ответе есть срочная заметка.
С ключом Gemini вопросы идут через модель (как у пользователя); --offline считает только поиск по базе и пропускает
вопросы с "needs_gemini". Пополняйте eval_set.json реальными вопросами: это ваша цифра качества для защиты.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.conf import settings
from core import services


def main():
    offline = "--offline" in sys.argv
    verbose = "--verbose" in sys.argv
    if offline:
        settings.GEMINI_API_KEY = ""
    mode = "офлайн (только поиск)" if (offline or not settings.GEMINI_API_KEY) else "с Gemini"
    cases = json.loads((Path(__file__).parent / "eval_set.json").read_text(encoding="utf-8"))
    passed = failed = skipped = 0
    print(f"Режим: {mode}. Вопросов в наборе: {len(cases)}\n")
    for case in cases:
        if case.get("needs_gemini") and mode != "с Gemini":
            skipped += 1
            continue
        r = services.answer_chat(case["q"], case.get("lang", "ru"))
        arts = [s["article"] for s in r["sources"]]
        kinds = {s.get("kind", "norm") for s in r["sources"]}
        problems = []
        if case.get("refuse"):
            if not r["refused"]:
                problems.append("ожидался отказ, а бот ответил")
        else:
            if r["refused"]:
                problems.append("бот отказал, а ответ в базе есть")
            if case.get("expect") and not set(case["expect"]) & set(arts):
                problems.append(f"нет ожидаемой статьи {case['expect']}, источники: {arts}")
            if case.get("expect_kind") and case["expect_kind"] not in kinds:
                problems.append(f"нет источника вида {case['expect_kind']}, виды: {sorted(kinds)}")
        if case.get("safety") and "safety" not in r:
            problems.append("нет срочной заметки")
        if problems:
            failed += 1
            print("НЕ ПРОШЁЛ:", case["q"], "\n   -", "\n   - ".join(problems))
        else:
            passed += 1
            if verbose:
                print("ок:", case["q"], arts)
    total = passed + failed
    print(f"\nИтог: {passed} из {total} ({round(100 * passed / total) if total else 0}%), пропущено без Gemini: {skipped}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
