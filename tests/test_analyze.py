import json
import pathlib

import yaml

from radar.analyze import analyze, classify_region, visa_signal, language_check, required_years

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROFILE = yaml.safe_load((ROOT / "config" / "profile.yml").read_text())
JOBS = {j["url"].rsplit("/", 1)[1]: j for j in json.loads((ROOT / "tests/fixtures/sample_jobs.json").read_text())}

KEEP = {"1": "egypt", "2": "gulf", "4": "europe", "6": "remote", "11": "gulf", "12": "egypt",
        "14": "remote", "16": "europe", "17": "egypt"}
DROP = {"3": "senior", "5": "visa", "7": "remote", "8": "nationals", "9": "English",
        "10": "German", "13": "years", "15": "title", "18": "title"}


def test_kept_jobs_land_in_the_right_region():
    for n, region in KEEP.items():
        job, why = analyze(JOBS[n], PROFILE)
        assert job, f"job {n} dropped: {why}"
        assert job["region"] == region


def test_dropped_jobs_have_the_right_reason():
    for n, word in DROP.items():
        job, why = analyze(JOBS[n], PROFILE)
        assert job is None, f"job {n} should be dropped"
        assert word.lower() in why.lower(), f"job {n}: {why}"


def test_visa_negation_wins():
    assert visa_signal("We offer relocation support. We cannot sponsor visas.") == "no"
    assert visa_signal("Visa sponsorship is available.") == "yes"
    assert visa_signal("Great team.") == "unknown"


def test_language_nice_to_have_is_kept():
    reason, nice = language_check("Our working language is English; German is a plus.")
    assert reason is None and nice == ["German"]


def test_years_and_regions():
    assert required_years("You have 3+ years of experience with Linux.") == 3
    assert classify_region("Home based - Worldwide", None)[0] == "remote"
    assert classify_region("Lahore, Pakistan", None)[0] is None
    assert classify_region("6th of October, Giza", None)[0] == "egypt"


def test_target_titles_and_non_targets():
    from radar.analyze import classify_role
    for t in ["Cloud Operations Engineer", "Systems Specialist", "Storage Engineer", "IT Infrastructure Specialist",
              "Linux Administrator", "SAP Basis Consultant", "Junior DevOps Engineer"]:
        assert classify_role(t), t
    for t in ["SOC Analyst L1", "Frontend Engineer", "Cloud Sales Executive", "Data Engineer"]:
        assert classify_role(t) is None, t
