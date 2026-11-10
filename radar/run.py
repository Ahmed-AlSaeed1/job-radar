"""Daily run: python -m radar.run   (or --demo to build sample data offline)."""
import argparse
import collections
import concurrent.futures as cf
import datetime as dt
import json
import pathlib
import re
import sys
import traceback

import yaml

from . import fetchers
from .analyze import ROLE_LABELS, analyze
from .skills import SKILLS

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data" / "jobs.json"
STATE = ROOT / "state"


def load_yaml(name):
    return yaml.safe_load((ROOT / "config" / name).read_text(encoding="utf-8")) or {}


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def validate_profile(profile):
    unknown = [k for lvl in ("strong", "familiar") for k in profile.get("skills", {}).get(lvl, []) if k not in SKILLS]
    if unknown:
        sys.exit(f"config/profile.yml has unknown skill keys: {unknown}. See radar/skills.py for valid keys.")


def is_link_only(c):
    fetchable = c.get("ats") or c.get("slugs") or c.get("slug") or c.get("workday_url")
    return bool(c.get("link")) or (bool(c.get("career_url")) and not fetchable)


def collect(companies_cfg, detected):
    """Run every source in parallel. Returns (raw_jobs, source_status)."""
    tasks = {}
    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        for b in companies_cfg.get("job_boards", []):
            if b.get("enabled", True):
                tasks[pool.submit(fetchers.BOARDS[b["id"]])] = ("board", b["id"], None)
        for c in companies_cfg.get("companies", []):
            if is_link_only(c):
                continue  # link-only company, shown on the site, nothing to fetch
            tasks[pool.submit(fetchers.fetch_company, c, detected)] = ("company", c["name"], c)

        raw, status = [], []
        for fut in cf.as_completed(tasks):
            kind, name, c = tasks[fut]
            entry = {"name": name, "kind": kind, "ok": False, "fetched": 0, "kept": 0}
            try:
                result = fut.result()
                jobs, info = (result, None) if kind == "board" else result
                for j in jobs:
                    j.setdefault("source", name if kind == "company" else name)
                raw.extend(jobs)
                entry.update(ok=True, fetched=len(jobs))
                if info:
                    entry["ats"] = f"{info['ats']}:{info['slug']}"
            except fetchers.NotFound as e:
                entry["error"] = f"not found ({e})"
            except Exception as e:  # keep going: one broken source must not stop the run
                entry["error"] = f"{type(e).__name__}: {str(e)[:160]}"
                traceback.print_exc()
            status.append(entry)
    return raw, status


def dedupe_key(job):
    norm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
    return f"{norm(job['company'])}|{norm(job['title'])}|{job['region']}"


def career_links(companies_cfg, status):
    """Link-only companies, plus any company whose automatic fetch failed this run."""
    failed = {x["name"] for x in status if x["kind"] == "company" and not x["ok"]}
    return [
        {"name": c["name"], "url": c.get("career_url"), "regions": c.get("regions", []),
         "fallback": c["name"] in failed}
        for c in companies_cfg.get("companies", [])
        if is_link_only(c) or c["name"] in failed
    ]


def build(raw_jobs, status, profile, companies_cfg, seen, today, demo=False):
    kept, reasons, keys = [], collections.Counter(), set()
    per_source = collections.Counter()
    for raw in raw_jobs:
        job, why = analyze(raw, profile)
        if not job:
            reasons[why] += 1
            continue
        k = dedupe_key(job)
        if k in keys:
            reasons["duplicate"] += 1
            continue
        keys.add(k)
        per_source[raw.get("source")] += 1
        kept.append(job)

    first_run = not seen
    for job in kept:
        job["first_seen"] = seen.get(job["id"], today)
        job["is_new"] = (not first_run) and job["first_seen"] == today
        seen[job["id"]] = job["first_seen"]

    # forget ids not seen for 60 days
    cutoff = (dt.date.fromisoformat(today) - dt.timedelta(days=60)).isoformat()
    for jid in [j for j, d in seen.items() if d < cutoff]:
        del seen[jid]

    for s in status:
        s["kept"] = per_source.get(s["name"], 0)

    # what the market asks for that you don't have yet
    missing, partial = collections.Counter(), collections.Counter()
    for job in kept:
        missing.update(job["missing"])
        partial.update(job["partial"])

    kept.sort(key=lambda j: (j["is_new"], j["score"] or 0), reverse=True)
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
        "today": today,
        "demo": demo,
        "first_run": first_run,
        "profile": {"name": profile.get("name", ""), "headline": profile.get("headline", "")},
        "roles": ROLE_LABELS,
        "skill_names": {k: v[0] for k, v in SKILLS.items()},
        "jobs": kept,
        "gaps": {
            "missing": [[k, n] for k, n in missing.most_common(15)],
            "partial": [[k, n] for k, n in partial.most_common(10)],
        },
        "dropped": dict(reasons.most_common()),
        "sources": sorted(status, key=lambda s: (s["ok"], s["kept"]), reverse=True),
        "career_links": career_links(companies_cfg, status),
        "search": profile.get("search", {}),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="build sample data from tests/fixtures (no network)")
    args = ap.parse_args()

    profile = load_yaml("profile.yml")
    validate_profile(profile)
    companies_cfg = load_yaml("companies.yml")
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()

    if args.demo:
        raw = load_json(ROOT / "tests" / "fixtures" / "sample_jobs.json", [])
        status = [{"name": "Demo data", "kind": "board", "ok": True, "fetched": len(raw), "kept": 0}]
        for j in raw:
            j["source"] = "Demo data"
        data = build(raw, status, profile, companies_cfg, {}, today, demo=True)
        data["first_run"] = False
        for i, job in enumerate(data["jobs"]):
            job["is_new"] = i % 3 == 0
        save_json(OUT, data)
        print(f"demo: kept {len(data['jobs'])} of {len(raw)}; dropped {data['dropped']}")
        return

    detected = load_json(STATE / "detected_ats.json", {})
    seen = load_json(STATE / "seen.json", {})
    raw, status = collect(companies_cfg, detected)
    data = build(raw, status, profile, companies_cfg, seen, today)

    save_json(OUT, data)
    save_json(STATE / "seen.json", seen)
    save_json(STATE / "detected_ats.json", detected)

    ok = sum(s["ok"] for s in status)
    print(f"sources ok {ok}/{len(status)}; fetched {len(raw)}; kept {len(data['jobs'])}; "
          f"new today {sum(j['is_new'] for j in data['jobs'])}")
    print("dropped:", data["dropped"])
    for s in status:
        if not s["ok"]:
            print(f"  ! {s['name']}: {s.get('error')}")


if __name__ == "__main__":
    main()
