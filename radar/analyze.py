"""Decide whether a job fits, and how well.

Input: a normalized raw job dict
    {title, company, location, remote, url, description, posted_at, source}
Output: (analysis dict, None) when kept, or (None, reason) when dropped.
"""
import datetime
import hashlib
import html
import re

from .skills import SKILLS

# ---------------------------------------------------------------- text utils

_BLOCK_TAGS = re.compile(r"<\s*(?:br|/p|/li|/div|/h\d|/tr|li)\b[^>]*>", re.I)
_TAGS = re.compile(r"<[^>]+>")


def html_to_text(raw):
    if not raw:
        return ""
    text = html.unescape(raw)          # Greenhouse double-escapes its HTML
    text = html.unescape(text)
    text = _BLOCK_TAGS.sub("\n", text)
    text = _TAGS.sub(" ", text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n|•|·|;", text) if s.strip()]


def job_id(source, url, title):
    return hashlib.sha1(f"{source}|{url}|{title}".encode()).hexdigest()[:12]


# ---------------------------------------------------------------- compiled skill regexes

_SKILL_RX = {
    key: (name, [re.compile(p, re.I) for p in pats], weight)
    for key, (name, pats, weight) in SKILLS.items()
}


def detect_skills(text):
    return [key for key, (_, rxs, _) in _SKILL_RX.items() if any(r.search(text) for r in rxs)]


# ---------------------------------------------------------------- role buckets (from title)

ROLES = [
    ("devops", "DevOps / SRE / Platform",
     r"dev ?ops|devsecops|site reliability|\bsre\b|platform engineer|reliability engineer|build (?:and|&) release|release engineer"),
    ("sap", "SAP Basis / HANA", r"sap basis|\bbasis\b|\bhana\b"),
    ("cloud", "Cloud", r"\bcloud\b"),
    ("infra", "Infrastructure / Virtualization",
     r"infrastructure|\binfra\b|virtuali[sz]ation|vmware|data ?cent(?:er|re)|\bhosting\b|storage engineer|backup engineer|"
     r"cloud operations|it operations"),
    ("sysadmin", "System Admin / System Engineer",
     r"system(?:s)? admin|sysadmin|system(?:s)? engineer|system(?:s)? specialist|systems? support engineer|\blinux\b|\bunix\b|server (?:admin|engineer)|"
     r"windows (?:admin|engineer)|it (?:operations|engineer|administrator)|technical operations"),
]
_ROLE_RX = [(k, label, re.compile(rx, re.I)) for k, label, rx in ROLES]
ROLE_LABELS = {k: label for k, label, _ in ROLES}

TITLE_EXCLUDE = re.compile(
    r"\b(?:sales|account (?:executive|manager)|recruit\w*|talent|marketing|customer success|"
    r"front-?end|back-?end developer|full-?stack|data scientist|data engineer|data analyst|machine learning|"
    r"\bml\b|mechanical|electrical|civil|embedded|firmware|hardware|avionics|rf engineer|teacher|instructor|"
    r"trainer|pre-?sales|solutions? consultant|cloud kitchen|intern|internship|working student|werkstudent|"
    r"praktikum|trainee|student|security|cyber\w*|cybersecurity|soc|siem|penetration|pentest\w*|grc|robotics)\b", re.I)


def classify_role(title):
    if TITLE_EXCLUDE.search(title):
        return None
    for key, _, rx in _ROLE_RX:
        if rx.search(title):
            return key
    return None


# ---------------------------------------------------------------- locations

EGYPT = ["egypt", "cairo", "giza", "alexandria", "6th of october", "smart village", "maadi",
         "nasr city", "sheikh zayed", "new capital", "heliopolis", "mansoura", "el gouna"]
GULF = ["united arab emirates", "uae", "dubai", "abu dhabi", "sharjah", "ajman", "saudi", "ksa", "riyadh",
        "jeddah", "dammam", "khobar", "neom", "qatar", "doha", "kuwait", "bahrain", "manama", "oman", "muscat"]
EUROPE = ["europe", "european union", "germany", "deutschland", "berlin", "munich", "münchen", "hamburg",
          "frankfurt", "cologne", "köln", "stuttgart", "düsseldorf", "dusseldorf", "leipzig", "dresden",
          "nuremberg", "nürnberg", "karlsruhe", "netherlands", "amsterdam", "rotterdam", "the hague", "eindhoven",
          "utrecht", "ireland", "dublin", "spain", "madrid", "barcelona", "valencia", "malaga", "portugal",
          "lisbon", "porto", "france", "paris", "lyon", "toulouse", "italy", "milan", "rome", "turin", "belgium",
          "brussels", "antwerp", "ghent", "luxembourg", "austria", "vienna", "graz", "switzerland", "zurich",
          "zürich", "geneva", "basel", "lausanne", "sweden", "stockholm", "gothenburg", "malmö", "malmo",
          "denmark", "copenhagen", "aarhus", "norway", "oslo", "finland", "helsinki", "estonia", "tallinn",
          "latvia", "riga", "lithuania", "vilnius", "poland", "warsaw", "krakow", "kraków", "wroclaw",
          "wrocław", "gdansk", "gdańsk", "czech", "prague", "brno", "slovakia", "bratislava", "hungary",
          "budapest", "romania", "bucharest", "cluj", "bulgaria", "sofia", "greece", "athens", "croatia",
          "zagreb", "serbia", "belgrade", "slovenia", "ljubljana", "cyprus", "limassol", "nicosia", "malta",
          "united kingdom", "uk", "england", "london", "manchester", "edinburgh", "scotland", "bristol",
          "leeds", "birmingham, uk"]
WORLDWIDE = ["worldwide", "anywhere", "global", "emea", "mena", "middle east", "africa", "international"]
REMOTE_RX = re.compile(r"\bremote\b|home[- ]based|work from home|\bwfh\b|anywhere|fully distributed", re.I)


def _has_any(text, words):
    low = text.lower()
    return any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", low) for w in words)


def classify_region(location, remote_flag, title=""):
    """Return (region, is_remote) or (None, reason)."""
    loc = location or ""
    is_remote = bool(remote_flag) or bool(REMOTE_RX.search(loc)) or bool(REMOTE_RX.search(title))
    if _has_any(loc, EGYPT):
        return "egypt", is_remote
    if _has_any(loc, GULF):
        return "gulf", is_remote
    if _has_any(loc, EUROPE):
        return "europe", is_remote
    if is_remote:
        stripped = REMOTE_RX.sub("", loc).strip(" ,-–/()|")
        if not stripped or _has_any(loc, WORLDWIDE):
            return "remote", True
        return None, "remote but limited to another country"
    return None, "location outside Egypt / Gulf / Europe"


REMOTE_RESTRICTED = re.compile(
    r"(?:must|need to|required to) (?:be |reside |live )?(?:based |located |residing )?in (?:the )?"
    r"(?:us|u\.s\.|united states|usa|canada|latam|latin america|india|apac|australia)\b"
    r"|\b(?:us|usa|u\.s\.)[- ]only\b"
    r"|only (?:open to|accepting|considering) (?:candidates|applicants)[^.]{0,30}\b(?:us|united states|usa|canada|india)\b",
    re.I)

GULF_NATIONALS = re.compile(
    r"\b(?:emirati|saudi|qatari|kuwaiti|omani|bahraini|uae) nationals?\b|\bsaudi(?:z|s)ation\b|\bemiratisation\b|"
    r"nationals only", re.I)


# ---------------------------------------------------------------- languages

FOREIGN_LANGS = (r"german|deutsch|french|dutch|flemish|swedish|danish|norwegian|finnish|polish|italian|spanish|"
                 r"portuguese|czech|hungarian|romanian|greek|turkish|hebrew|japanese|mandarin|chinese|cantonese|"
                 r"russian|ukrainian|estonian|latvian|lithuanian|bulgarian|croatian|serbian|slovak|slovenian|"
                 r"korean|hindi|urdu")
LANG_RX = re.compile(r"\b(" + FOREIGN_LANGS + r")\b", re.I)
LANG_NICE = re.compile(r"nice to have|is a plus|\bplus\b|bonus|advantage|preferred|desirable|beneficial|ideally", re.I)
LANG_REQ = re.compile(r"fluent|fluency|native|proficien|\b[bc][12]\b|business[- ]level|required|must|mandatory|"
                      r"excellent|very good|strong|working knowledge|speak|written and spoken|verbal and written", re.I)
EN_STOP = {"the", "and", "to", "of", "a", "in", "for", "with", "you", "we", "our", "is", "are", "on", "will",
           "as", "be", "your", "this", "that", "or", "an", "have", "who", "from"}


def language_check(text):
    """Return (excluded_reason or None, nice_to_have_languages list)."""
    tokens = re.findall(r"[a-zà-ÿß]+", text.lower())
    if len(tokens) > 80:
        ratio = sum(t in EN_STOP for t in tokens) / len(tokens)
        if ratio < 0.08:
            return "ad is not written in English", []
    nice = set()
    for s in sentences(text):
        found = LANG_RX.findall(s)
        if not found:
            continue
        if LANG_NICE.search(s):
            nice.update(f.capitalize() for f in found)
        elif LANG_REQ.search(s):
            return f"requires {found[0].capitalize()}", []
    return None, sorted(nice)


# ---------------------------------------------------------------- visa sponsorship

VISA_POS = re.compile(
    r"visa sponsorship|sponsor(?:ship)? (?:your |a |the )?(?:work )?(?:visa|permit)|we (?:will |can |do )?sponsor|"
    r"relocation (?:support|package|assistance|bonus|budget|allowance)|help (?:you )?(?:with )?relocat|"
    r"blue card|we support relocation|relocation (?:is )?(?:offered|provided|covered)", re.I)
VISA_NEG = re.compile(
    r"\bno (?:visa )?sponsorship|(?:not|unable to|cannot|can't|won't|do not|don't|does not|doesn't|are not able to)"
    r"[^.]{0,40}sponsor|sponsorship (?:is )?not (?:available|offered|provided|possible)|"
    r"(?:must|should) (?:already )?(?:have|hold|possess)[^.]{0,40}(?:right|permit|authori[sz]ation|eligib)[^.]{0,20}work|"
    r"(?:eu|uk|swiss) (?:work )?(?:permit|citizenship|passport) (?:is )?(?:required|mandatory)|"
    r"right to work in the (?:uk|eu|netherlands|germany)[^.]{0,30}(?:required|essential|must)|"
    r"without (?:the need for |requiring )(?:visa )?sponsorship|must be (?:an )?eu citizen|"
    r"only (?:consider|accept)[^.]{0,40}(?:eligible|authori[sz]ed) to work", re.I)


def visa_signal(text):
    pos = False
    for s in sentences(text):
        if VISA_NEG.search(s):
            return "no"
        if VISA_POS.search(s):
            pos = True
    return "yes" if pos else "unknown"


# ---------------------------------------------------------------- seniority and experience

SENIOR_RX = re.compile(r"\b(?:senior|sr\.?|lead|principal|staff|head|manager|director|vp|chief|expert)\b", re.I)
YEARS_RX = re.compile(
    r"(?:at least|minimum(?: of)?|min\.?)?\s*(\d{1,2})\s*(?:\+|plus)?\s*(?:-|–|to)?\s*(?:\d{1,2})?\s*\+?\s*years?",
    re.I)


def required_years(text):
    lows = []
    for s in sentences(text):
        if not re.search(r"experience|exp\b|background|track record|working", s, re.I):
            continue
        for m in YEARS_RX.finditer(s):
            n = int(m.group(1))
            if 0 < n <= 15:
                lows.append(n)
    return max(lows) if lows else None


# ---------------------------------------------------------------- fit scoring


def score_fit(skill_keys, profile):
    strong = set(profile.get("skills", {}).get("strong", []))
    familiar = set(profile.get("skills", {}).get("familiar", []))
    matched, partial, missing = [], [], []
    total_w = got = 0.0
    for key in skill_keys:
        name, _, weight = _SKILL_RX[key]
        total_w += weight
        if key in strong:
            matched.append(key)
            got += weight
        elif key in familiar:
            partial.append(key)
            got += weight * 0.6
        else:
            missing.append(key)
    score = round(100 * got / total_w) if len(skill_keys) >= 2 else None
    return score, matched, partial, missing


def skill_name(key):
    return SKILLS[key][0]


# ---------------------------------------------------------------- main entry point


def analyze(raw, profile):
    """Return (job_dict, None) if kept, else (None, reason)."""
    filters = profile.get("filters", {})
    title = (raw.get("title") or "").strip()
    text = html_to_text(raw.get("description") or "")
    full = f"{title}\n{text}"

    role = classify_role(title)
    if not role:
        return None, "title not a target role"
    if not filters.get("include_senior", False) and SENIOR_RX.search(title):
        return None, "senior/lead title"

    max_age = filters.get("max_age_days", 30)
    posted = raw.get("posted_at")
    if max_age and posted:
        try:
            age = (datetime.date.today() - datetime.date.fromisoformat(str(posted)[:10])).days
        except ValueError:
            age = 0
        if age > max_age:
            return None, f"posted more than {max_age} days ago"

    region, extra = classify_region(raw.get("location", ""), raw.get("remote"), title)
    if region is None:
        return None, extra
    is_remote = extra
    allowed = filters.get("regions", ["egypt", "remote", "gulf", "europe"])
    if region not in allowed:
        return None, f"region {region} disabled"

    if region == "remote" and REMOTE_RESTRICTED.search(text):
        return None, "remote limited to another country"
    if region == "gulf" and GULF_NATIONALS.search(full):
        return None, "nationals only"

    lang_reason, nice_langs = language_check(text)
    if lang_reason:
        return None, lang_reason

    visa = visa_signal(text) if region in ("europe", "gulf") else None
    if region == "europe" and visa == "no" and filters.get("europe_requires_sponsorship", True):
        return None, "no visa sponsorship"

    years = required_years(text)
    max_years = filters.get("max_years_required", 4)
    if years is not None and years > max_years:
        return None, f"asks for {years}+ years"

    skill_keys = detect_skills(full)
    score, matched, partial, missing = score_fit(skill_keys, profile)
    if score is None and role in ("sysadmin", "infra") and text:
        return None, "not enough infra keywords"

    return {
        "id": job_id(raw.get("source", ""), raw.get("url", ""), title),
        "title": title,
        "company": raw.get("company", ""),
        "location": raw.get("location", "") or ("Remote" if is_remote else ""),
        "region": region,
        "remote": is_remote,
        "role": role,
        "url": raw.get("url", ""),
        "source": raw.get("source", ""),
        "posted_at": raw.get("posted_at"),
        "score": score,
        "matched": matched,
        "partial": partial,
        "missing": missing,
        "years": years,
        "visa": visa,
        "langs_nice": nice_langs,
    }, None
