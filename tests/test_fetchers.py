from radar import fetchers


class FakeResp:
    def __init__(self, data):
        self._d = data

    def json(self):
        return self._d


def test_auto_detect_picks_matching_board_and_rejects_wrong_company(monkeypatch):
    def fake_get(url, params=None, **kw):
        if "greenhouse.io/v1/boards/acme" in url:     # same slug, different company in the US
            return FakeResp({"jobs": [{"title": "DevOps Engineer", "location": {"name": "Austin, TX"},
                                       "absolute_url": "u", "content": "", "updated_at": "2026-11-01"}]})
        if "api.lever.co/v0/postings/acme" in url:    # the real one, in Cairo
            return FakeResp([{"text": "Cloud Engineer", "categories": {"location": "Cairo, Egypt"},
                              "hostedUrl": "https://jobs.lever.co/acme/1", "descriptionPlain": "AWS",
                              "createdAt": 1762732800000}])
        raise fetchers.NotFound(url)

    monkeypatch.setattr(fetchers, "_get", fake_get)
    cache = {}
    jobs, info = fetchers.fetch_company({"name": "Acme", "slugs": ["acme"], "regions": ["egypt"]}, cache)
    assert info == {"ats": "lever", "slug": "acme"}
    assert jobs[0]["location"] == "Cairo, Egypt" and jobs[0]["posted_at"] == "2025-11-10"
    assert cache["Acme"]["ats"] == "lever"


def test_greenhouse_falls_back_to_eu_host(monkeypatch):
    def fake_get(url, params=None, **kw):
        if url.startswith("https://boards-api.eu.greenhouse.io"):
            return FakeResp({"jobs": [{"title": "SRE", "location": {"name": "Riyadh"}, "absolute_url": "u",
                                       "content": "&lt;p&gt;Kubernetes&lt;/p&gt;"}]})
        raise fetchers.NotFound(url)

    monkeypatch.setattr(fetchers, "_get", fake_get)
    jobs = fetchers.greenhouse("tamara", "Tamara")
    assert jobs[0]["location"] == "Riyadh"
