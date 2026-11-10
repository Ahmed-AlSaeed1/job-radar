"""Fetch jobs from public job-board APIs and company career systems (ATS).

Every fetcher returns a list of normalized raw jobs:
    {title, company, location, remote, url, description, posted_at, source}
Only public, documented feeds are used. No logins, no scraping of LinkedIn/Wuzzuf.
"""
import datetime as dt
import re
import time
from urllib.parse import urlparse

import requests

from .analyze import classify_region, classify_role

UA = {"User-Agent": "job-radar/1.0 (personal job search; github.com)", "Accept": "application/json"}
TIMEOUT = 25


class NotFound(Exception):
    pass


def _get(url, params=None, method="GET", json_body=None, retries=2):
    for attempt in range(retries + 1):
        try:
            r = requests.request(method, url, params=params, json=json_body, headers=UA, timeout=TIMEOUT)
        except requests.RequestException:
            if attempt == retries:
                raise
            time.sleep(3 * (attempt + 1))
            continue
        if r.status_code in (404, 410):
            raise NotFound(url)
        if r.status_code in (429, 500, 502, 503, 504) and attempt < retries:
            time.sleep(5 * (attempt + 1))
            continue
        r.raise_for_status()
        return r
    raise RuntimeError("unreachable")


def _iso(value):
    """Accept unix seconds/ms or ISO strings; return YYYY-MM-DD or None."""
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)) or str(value).isdigit():
            v = float(value)
            if v > 1e12:
                v /= 1000
            return dt.datetime.fromtimestamp(v, dt.timezone.utc).date().isoformat()
        return str(value)[:10]
    except (ValueError, OSError):
        return None


def _title_ok(title):
    return classify_role(title or "") is not None


# ============================================================== company ATS fetchers


def greenhouse(slug, company):
    last = None
    for host in ("boards-api.greenhouse.io", "boards-api.eu.greenhouse.io"):
        try:
            data = _get(f"https://{host}/v1/boards/{slug}/jobs", params={"content": "true"}).json()
        except NotFound as e:
            last = e
            continue
        return [{
            "title": j.get("title"),
            "company": company,
            "location": (j.get("location") or {}).get("name", ""),
            "remote": None,
            "url": j.get("absolute_url"),
            "description": j.get("content", ""),
            "posted_at": _iso(j.get("first_published") or j.get("updated_at")),
        } for j in data.get("jobs", [])]
    raise last or NotFound(slug)


def lever(slug, company):
    last = None
    for host in ("api.lever.co", "api.eu.lever.co"):
        try:
            data = _get(f"https://{host}/v0/postings/{slug}", params={"mode": "json"}).json()
        except NotFound as e:
            last = e
            continue
        if not isinstance(data, list):
            raise NotFound(slug)
        out = []
        for j in data:
            cats = j.get("categories") or {}
            locs = cats.get("allLocations") or [cats.get("location") or ""]
            lists = "\n".join(f"{x.get('text', '')}\n{x.get('content', '')}" for x in j.get("lists") or [])
            out.append({
                "title": j.get("text"),
                "company": company,
                "location": " / ".join(l for l in locs if l),
                "remote": (j.get("workplaceType") == "remote") or None,
                "url": j.get("hostedUrl"),
                "description": f"{j.get('descriptionPlain', '')}\n{lists}\n{j.get('additionalPlain', '')}",
                "posted_at": _iso(j.get("createdAt")),
            })
        return out
    raise last or NotFound(slug)


def ashby(slug, company):
    data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}").json()
    out = []
    for j in data.get("jobs", []):
        locs = [j.get("location") or ""] + [
            (s.get("location") if isinstance(s, dict) else str(s)) for s in j.get("secondaryLocations") or []]
        out.append({
            "title": j.get("title"),
            "company": company,
            "location": " / ".join(l for l in locs if l),
            "remote": j.get("isRemote") or j.get("workplaceType") == "Remote" or None,
            "url": j.get("jobUrl") or j.get("applyUrl"),
            "description": j.get("descriptionPlain") or j.get("descriptionHtml", ""),
            "posted_at": _iso(j.get("publishedAt")),
        })
    return out


def smartrecruiters(slug, company):
    out, offset = [], 0
    while offset < 500:
        data = _get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
                    params={"limit": 100, "offset": offset}).json()
        content = data.get("content", [])
        if not content and offset == 0 and data.get("totalFound", 0) == 0:
            raise NotFound(slug)
        for p in content:
            if not _title_ok(p.get("name")):
                continue  # only fetch details for relevant titles
            loc = p.get("location") or {}
            try:
                d = _get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings/{p['id']}").json()
                secs = (d.get("jobAd") or {}).get("sections") or {}
                desc = "\n".join((secs.get(k) or {}).get("text", "") for k in
                                 ("companyDescription", "jobDescription", "qualifications", "additionalInformation"))
                url = d.get("postingUrl") or d.get("applyUrl")
            except Exception:
                desc, url = "", None
            out.append({
                "title": p.get("name"),
                "company": company,
                "location": ", ".join(x for x in (loc.get("city"), loc.get("country")) if x),
                "remote": loc.get("remote") or None,
                "url": url or f"https://jobs.smartrecruiters.com/{slug}/{p['id']}",
                "description": desc,
                "posted_at": _iso(p.get("releasedDate")),
            })
        offset += 100
        if offset >= data.get("totalFound", 0):
            break
    return out


def workable(slug, company):
    data = _get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}", params={"details": "true"}).json()
    out = []
    for j in data.get("jobs", []):
        loc = ", ".join(x for x in (j.get("city"), j.get("state"), j.get("country")) if x)
        out.append({
            "title": j.get("title"),
            "company": company,
            "location": loc,
            "remote": j.get("telecommuting") or None,
            "url": j.get("url") or j.get("shortlink"),
            "description": j.get("description", ""),
            "posted_at": _iso(j.get("published_on") or j.get("created_at")),
        })
    return out


def recruitee(slug, company):
    data = _get(f"https://{slug}.recruitee.com/api/offers/").json()
    return [{
        "title": j.get("title"),
        "company": company,
        "location": j.get("location") or ", ".join(x for x in (j.get("city"), j.get("country")) if x),
        "remote": j.get("remote") or None,
        "url": j.get("careers_url"),
        "description": f"{j.get('description', '')}\n{j.get('requirements', '')}",
        "posted_at": _iso(j.get("published_at") or j.get("created_at")),
    } for j in data.get("offers", [])]


WORKDAY_TERMS = ["devops", "cloud", "infrastructure", "system administrator", "systems engineer",
                 "linux", "site reliability", "platform engineer"]


def workday(url, company):
    """url like https://dell.wd1.myworkdayjobs.com/External (the public careers site)."""
    u = urlparse(url)
    tenant = u.netloc.split(".")[0]
    site = [p for p in u.path.split("/") if p and not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", p)][0]
    base = f"{u.scheme}://{u.netloc}/wday/cxs/{tenant}/{site}"
    paths = {}
    for term in WORKDAY_TERMS:
        data = _get(f"{base}/jobs", method="POST",
                    json_body={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": term}).json()
        for p in data.get("jobPostings", []):
            if _title_ok(p.get("title")):
                paths[p["externalPath"]] = p
    out = []
    for path, p in list(paths.items())[:40]:
        try:
            info = _get(f"{base}{path}").json().get("jobPostingInfo", {})
        except Exception:
            info = {}
        out.append({
            "title": p.get("title"),
            "company": company,
            "location": info.get("location") or p.get("locationsText", ""),
            "remote": None,
            "url": info.get("externalUrl") or f"{u.scheme}://{u.netloc}/{site}{path}",
            "description": info.get("jobDescription", ""),
            "posted_at": _iso(info.get("startDate")),
        })
    return out


ATS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "smartrecruiters": smartrecruiters,
    "workable": workable,
    "recruitee": recruitee,
}
AUTO_ORDER = ["greenhouse", "lever", "ashby", "workable", "smartrecruiters", "recruitee"]


def _looks_like_company(jobs, regions):
    """Guard against a different company with the same slug on another ATS:
    accept only if at least one job is located in the regions we expect for it."""
    if not regions:
        return True
    for j in jobs:
        region, _ = classify_region(j.get("location", ""), j.get("remote"), j.get("title", ""))
        if region in regions:
            return True
    return False


def fetch_company(c, detected_cache):
    """Return (jobs, info) for one company entry from companies.yml."""
    name = c["name"]
    if c.get("workday_url"):
        return workday(c["workday_url"], name), {"ats": "workday", "slug": c["workday_url"]}

    slugs = c.get("slugs") or [c.get("slug") or re.sub(r"[^a-z0-9]", "", name.lower())]
    regions = c.get("regions") or []

    if c.get("ats"):
        jobs = ATS[c["ats"]](slugs[0], name)
        return jobs, {"ats": c["ats"], "slug": slugs[0]}

    cached = detected_cache.get(name)
    if cached:
        try:
            return ATS[cached["ats"]](cached["slug"], name), cached
        except NotFound:
            detected_cache.pop(name, None)  # company moved ATS: detect again

    for slug in slugs:
        for ats in AUTO_ORDER:
            try:
                jobs = ATS[ats](slug, name)
            except NotFound:
                continue
            except requests.RequestException:
                continue
            if jobs and _looks_like_company(jobs, regions):
                info = {"ats": ats, "slug": slug}
                detected_cache[name] = info
                return jobs, info
    raise NotFound(f"no public job board found for slugs {slugs}")


# ============================================================== job boards


def arbeitnow(max_pages=8, domain="www.arbeitnow.com", label="Arbeitnow"):
    out = []
    for page in range(1, max_pages + 1):
        data = _get(f"https://{domain}/api/job-board-api", params={"page": page}).json()
        rows = data.get("data", [])
        for j in rows:
            out.append({
                "title": j.get("title"),
                "company": j.get("company_name"),
                "location": j.get("location", ""),
                "remote": j.get("remote") or None,
                "url": j.get("url"),
                "description": j.get("description", ""),
                "posted_at": _iso(j.get("created_at")),
                "source": label,
            })
        if not rows or not (data.get("links") or {}).get("next"):
            break
    return out


def arbeitnow_uk():
    return arbeitnow(max_pages=5, domain="www.arbeitnow.co.uk", label="Arbeitnow UK")


def remotive():
    out = []
    for cat in ("devops", "software-dev"):
        data = _get("https://remotive.com/api/remote-jobs", params={"category": cat}).json()
        for j in data.get("jobs", []):
            out.append({
                "title": j.get("title"),
                "company": j.get("company_name"),
                "location": f"Remote {j.get('candidate_required_location', '')}".strip(),
                "remote": True,
                "url": j.get("url"),
                "description": j.get("description", ""),
                "posted_at": _iso(j.get("publication_date")),
                "source": "Remotive",
            })
    return out


def remoteok():
    data = _get("https://remoteok.com/api").json()
    out = []
    for j in data[1:]:  # first element is the API legal notice
        if not isinstance(j, dict):
            continue
        out.append({
            "title": j.get("position"),
            "company": j.get("company"),
            "location": f"Remote {j.get('location', '')}".strip(),
            "remote": True,
            "url": j.get("url"),
            "description": j.get("description", ""),
            "posted_at": _iso(j.get("date") or j.get("epoch")),
            "source": "Remote OK",
        })
    return out


HIMALAYAS_TERMS = ["devops", "cloud engineer", "infrastructure engineer", "system administrator",
                   "site reliability", "platform engineer", "linux"]


def himalayas():
    out, seen = [], set()
    for term in HIMALAYAS_TERMS:
        data = _get("https://himalayas.app/jobs/api/search",
                    params={"q": term, "keyword": term, "country": "Egypt", "limit": 20}).json()
        for j in data.get("jobs", []):
            key = j.get("guid") or j.get("applicationLink")
            if key in seen:
                continue
            seen.add(key)
            restr = j.get("locationRestrictions") or []
            restr = [r.get("name", "") if isinstance(r, dict) else str(r) for r in restr]
            # empty restrictions = worldwide; restrictions that include Egypt are fine too
            loc = "Remote Worldwide" if not restr or "Egypt" in restr else "Remote " + ", ".join(restr)
            out.append({
                "title": j.get("title"),
                "company": j.get("companyName"),
                "location": loc,
                "remote": True,
                "url": j.get("applicationLink"),
                "description": j.get("description") or j.get("excerpt", ""),
                "posted_at": _iso(j.get("pubDate")),
                "source": "Himalayas",
            })
        time.sleep(1.5)
    return out

WORKABLE_TERMS = ["devops", "cloud engineer", "infrastructure engineer", "system administrator",
                  "systems engineer", "site reliability", "linux", "sap basis"]
WORKABLE_PLACES = ["Egypt", "United Arab Emirates", "Saudi Arabia", "Qatar", "Kuwait", "Bahrain", "Oman"]


def workable_search():
    """jobs.workable.com: the public job search across every company that hires with Workable.
    Many Egyptian and Gulf companies use Workable, so this is the main Egypt/Gulf feed."""
    out, seen = [], set()
    for place in WORKABLE_PLACES:
        for term in WORKABLE_TERMS:
            token = None
            for _ in range(3):  # up to 60 results per term and place
                params = {"query": term, "location": place}
                if token:
                    params["pageToken"] = token
                try:
                    data = _get("https://jobs.workable.com/api/v1/jobs", params=params).json()
                except NotFound:
                    break
                for j in data.get("jobs", []):
                    if j.get("id") in seen or not _title_ok(j.get("title")):
                        continue
                    seen.add(j.get("id"))
                    loc = j.get("location") or {}
                    locs = j.get("locations") or []
                    location = ", ".join(x for x in (loc.get("city"), loc.get("countryName")) if x) or " / ".join(
                        x for x in locs if x != "TELECOMMUTE")
                    out.append({
                        "title": j.get("title"),
                        "company": (j.get("company") or {}).get("title") or "",
                        "location": location,
                        "remote": ("TELECOMMUTE" in locs) or j.get("workplace") == "remote" or None,
                        "url": j.get("url"),
                        "description": f"{j.get('description', '')}\n{j.get('requirementsSection', '')}",
                        "posted_at": _iso(j.get("created")),
                        "source": "Workable",
                    })
                token = data.get("nextPageToken")
                if not token or not data.get("jobs"):
                    break
                time.sleep(0.5)
    return out


BOARDS = {
    "workable": workable_search,
    "arbeitnow": arbeitnow,
    "arbeitnow_uk": arbeitnow_uk,
    "remotive": remotive,
    "remoteok": remoteok,
    "himalayas": himalayas,
}
