"""
OSINT Pipeline — moved from tools/osint/main.py.
Multi-source OSINT pipeline for researching a person.
"""

import re
import time
import urllib.parse
from urllib.parse import urlparse

import requests


class PersonOSINTPipeline:
    """
    Multi-source OSINT pipeline for researching a person.
    Free tier: Jina AI (search + reader), Wikipedia
    Premium add-ons: LinkdAPI (100 free credits), Hunter.io (25 free/mo)
    """

    def __init__(
        self,
        jina_api_key: str = "",
        apify_token: str = "",
        hunter_key: str = "",
        linkdapi_key: str = "",
    ):
        self.jina_api_key = jina_api_key
        self.apify_token = apify_token
        self.hunter_key = hunter_key
        self.linkdapi_key = linkdapi_key

    # ------------------------------------------------------------------
    # Internal: Jina Search & Reader helpers
    # ------------------------------------------------------------------
    def _search(self, query: str, timeout: int = 20) -> list:
        """s.jina.ai search -> list of {title, url, content}"""
        try:
            r = requests.get(
                f"https://s.jina.ai/{urllib.parse.quote(query)}",
                headers={
                    "Authorization": f"Bearer {self.jina_api_key}",
                    "Accept": "application/json",
                    "X-Respond-With": "no-content",
                },
                timeout=timeout,
            )
            if r.status_code == 200:
                return r.json().get("data", [])
        except Exception:
            pass
        return []

    def _read(self, url: str, timeout: int = 25) -> str | None:
        """r.jina.ai URL reader -> clean markdown or None"""
        try:
            r = requests.get(
                f"https://r.jina.ai/{url}",
                headers={
                    "Authorization": f"Bearer {self.jina_api_key}",
                    "Accept": "text/plain",
                },
                timeout=timeout,
            )
            if r.status_code == 200 and "Sign Up" not in r.text[:400]:
                return r.text
        except Exception:
            pass
        return None

    @staticmethod
    def _clean_markdown_links(text: str) -> str:
        """Convert [text](url) to just text."""
        return re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)

    # ------------------------------------------------------------------
    # STEP 1: Find LinkedIn URL
    # ------------------------------------------------------------------
    def find_linkedin_url(self, name: str, company: str, email: str = "") -> str | None:
        queries = [f'site:linkedin.com/in/ "{name}" "{company}"']
        if email:
            queries.insert(0, f"site:linkedin.com/in/ {email}")

        seen: set = set()
        for q in queries:
            for item in self._search(q):
                url = item.get("url", "")
                if "/authwall" in url:
                    continue
                m = re.search(r"linkedin\.com/in/([^/?]+)", url)
                if m and m.group(1) not in seen:
                    seen.add(m.group(1))
                    return f"https://www.linkedin.com/in/{m.group(1)}"
        return None

    # ------------------------------------------------------------------
    # STEP 2: LinkedIn Profile (Jina Reader)
    # ------------------------------------------------------------------
    def extract_linkedin(self, linkedin_url: str) -> dict:
        text = self._read(linkedin_url, timeout=30)
        if not text:
            return {"status": "auth_wall"}

        data: dict = {"status": "public_profile"}
        lines = text.split("\n")

        # Name
        for l in lines:
            m = re.match(r"^#\s+(.+)", l)
            if m:
                data["name"] = m.group(1).strip()
                break

        # Location
        for i, l in enumerate(lines):
            if "Location" in l:
                for j in range(i, min(i + 3, len(lines))):
                    m = re.search(
                        r"(?:Location|location)[:\s]*[\n\s]*(.{5,100})", lines[j]
                    )
                    if m:
                        loc = m.group(1).strip().rstrip("\u200b")
                        if len(loc) > 3:
                            data["location"] = loc
                            break

        # About
        in_about = False
        about: list = []
        for l in lines:
            if re.match(r"^##?\s*About", l):
                in_about = True
                continue
            if in_about:
                if re.match(r"^##", l):
                    break
                cleaned = self._clean_markdown_links(l).strip()
                if cleaned and "Agree" not in cleaned and "see more" not in cleaned:
                    about.append(cleaned)
        if about:
            data["about"] = " ".join(about)[:1000]

        # Followers
        for l in lines:
            m = re.search(r"###\s*([\d,]+)\s*followers?", l)
            if m:
                data["followers"] = m.group(1)

        # Companies
        in_exp = False
        companies: list = []
        for l in lines:
            if "Experience & Education" in l:
                in_exp = True
                continue
            if in_exp:
                if re.match(r"^##", l) and "Experience" not in l:
                    break
                m = re.search(r"###\s*(.+)", l)
                if m:
                    c = self._clean_markdown_links(m.group(1)).strip()
                    skip_words = [
                        "udit", "sudhanshu", "indu", "rashma", "the iconic",
                        "view mutual", "sign in", "welcome back",
                    ]
                    if c and len(c) > 2 and not any(w in c.lower() for w in skip_words):
                        companies.append(c)
        if companies:
            data["companies"] = companies

        # Certifications
        in_cert = False
        certs: list = []
        for l in lines:
            if re.match(r"^##\s*Licenses & Certifications", l):
                in_cert = True
                continue
            if in_cert:
                if re.match(r"^##", l):
                    break
                m = re.search(r"####\s*\[?([^\]]+)\]?", l)
                if m:
                    c = m.group(1).strip()
                    if c and c != "-":
                        certs.append(c)
        if certs:
            data["certifications"] = certs

        return data

    # ------------------------------------------------------------------
    # STEP 2b: LinkdAPI (full LinkedIn data)
    # ------------------------------------------------------------------
    def extract_linkdapi(self, linkedin_url: str) -> dict | None:
        if not self.linkdapi_key or self.linkdapi_key == "YOUR_LINKDAPI_KEY":
            return None
        m = re.search(r"linkedin\.com/in/([^/?]+)", linkedin_url)
        if not m:
            return None
        username = m.group(1)
        try:
            r = requests.get(
                "https://linkdapi.com/api/v1/profile/full",
                params={"username": username},
                headers={"X-linkdapi-apikey": self.linkdapi_key},
                timeout=30,
            )
            if r.status_code == 200:
                resp = r.json()
                profile_data = (
                    resp.get("data")
                    if isinstance(resp, dict) and "data" in resp
                    else resp
                )
                if isinstance(resp, dict) and resp.get("success") is False:
                    return None

                # Also fetch recent posts if we have a URN
                urn = profile_data.get("urn") or (
                    profile_data.get("result") or {}
                ).get("urn")
                if urn:
                    posts = self._linkdapi_get_posts(urn)
                    if posts:
                        profile_data["posts"] = posts
                return profile_data
        except Exception:
            pass
        return None

    def _linkdapi_get_posts(self, urn: str, max_posts: int = 10) -> list | None:
        """Fetch recent posts for a profile URN via LinkdAPI."""
        try:
            r = requests.get(
                "https://linkdapi.com/api/v1/posts/all",
                params={"urn": urn, "start": 0},
                headers={"X-linkdapi-apikey": self.linkdapi_key},
                timeout=20,
            )
            if r.status_code == 200:
                resp = r.json()
                raw = resp.get("data") if isinstance(resp, dict) else resp
                if isinstance(raw, dict):
                    raw = (
                        raw.get("items")
                        or raw.get("posts")
                        or raw.get("feed")
                        or [raw]
                    )
                if not raw or not isinstance(raw, list):
                    return None
                results = []
                for p in raw[:max_posts]:
                    text = p.get("text", "") or p.get("commentary", "") or ""
                    results.append(
                        {
                            "title": p.get("title") or text[:80] or "(no title)",
                            "text_preview": text[:300],
                            "url": p.get("url")
                            or p.get("shareUrl")
                            or f"https://www.linkedin.com/feed/update/{p.get('urn', '')}",
                            "published": p.get("publishedDate")
                            or p.get("timestamp")
                            or p.get("date"),
                            "likes": p.get("likes")
                            or p.get("reactions")
                            or p.get("numLikes"),
                            "comments": p.get("comments") or p.get("numComments"),
                        }
                    )
                return results
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # STEP 3: Web Presence
    # ------------------------------------------------------------------
    def search_web(self, name: str, company: str, email: str = "") -> dict:
        result: dict = {"articles": [], "profiles": [], "mentions": []}

        queries = [f'"{name}" "{company}"']
        if email:
            queries.append(f'"{email}" -linkedin')

        seen: set = set()
        for q in queries:
            for item in self._search(q):
                url = item.get("url", "")
                title = item.get("title", "")
                if (
                    not url
                    or url in seen
                    or "/authwall" in url
                    or "linkedin.com" in url
                ):
                    continue
                if "just a moment" in title.lower():
                    continue
                seen.add(url)

                domain = urlparse(url).netloc.lower()
                entry = {"title": title, "url": url}

                if "medium.com" in domain:
                    content = self._read(url)
                    if content:
                        entry["snippet"] = content[:600]
                    result["articles"].append(entry)
                elif any(d in domain for d in ["github", "gitlab"]):
                    result["profiles"].append({**entry, "type": "code"})
                elif any(d in domain for d in ["jointaro"]):
                    result["profiles"].append({**entry, "type": "bio"})
                else:
                    result["mentions"].append(entry)

        return result

    # ------------------------------------------------------------------
    # STEP 4: Company Info (Wikipedia)
    # ------------------------------------------------------------------
    def get_company_info(self, name: str) -> dict:
        info: dict = {"name": name}

        wiki = self._read(
            f"https://en.wikipedia.org/wiki/{urllib.parse.quote(name)}"
        )
        if wiki:
            clean = self._clean_markdown_links(wiki)
            clean = re.sub(r"\[\d+\]", "", clean)

            for p in re.split(r"\n\s*\n", clean):
                p = p.strip()
                if len(p) > 150 and p[0].isalpha():
                    lower = p[:80].lower()
                    if not any(
                        w in lower
                        for w in [
                            "controvers", "criticism", "allegation",
                            "lawsuit", "wikipedia", "privacy",
                        ]
                    ):
                        info["description"] = p[:600]
                        break

            for line in clean.split("\n"):
                ll = line.lower().strip()
                if ll.startswith("industry "):
                    info["industry"] = line.split(" ", 1)[-1].strip()[:80]
                elif ll.startswith("founded "):
                    info["founded"] = line.split(" ", 1)[-1].strip()[:80]
                elif "headquarter" in ll:
                    info["headquarters"] = line.split(" ", 1)[-1].strip()[:100]
                elif ll.startswith("revenue "):
                    info["revenue"] = line.split(" ", 1)[-1].strip()[:60]
                elif "employees" in ll:
                    m = re.search(r"([\d,]+)\s*(?:\(|$)", line)
                    if m and int(m.group(1).replace(",", "")) > 100:
                        info["employees"] = m.group(1)

        return info

    # ------------------------------------------------------------------
    # STEP 5: Email Verification
    # ------------------------------------------------------------------
    def verify_email(self, email: str) -> dict:
        r: dict = {"email": email}
        if not email or "@" not in email:
            return r
        r["valid_format"] = bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", email))
        r["domain"] = email.split("@")[1]

        if self.hunter_key and self.hunter_key != "YOUR_HUNTER_KEY":
            try:
                resp = requests.get(
                    "https://api.hunter.io/v2/email-verifier",
                    params={"email": email, "api_key": self.hunter_key},
                    timeout=10,
                )
                if resp.status_code == 200:
                    d = resp.json().get("data", {})
                    r["hunter_status"] = d.get("status", "?")
                    r["hunter_score"] = d.get("score", 0)
            except Exception:
                pass
        return r

    # ------------------------------------------------------------------
    # STEP 6: Recent News
    # ------------------------------------------------------------------
    def recent_news(self, name: str, company: str) -> list:
        items: list = []
        seen: set = set()
        for item in self._search(f'"{name}" "{company}"'):
            url = item.get("url", "")
            title = item.get("title", "")
            if not url or url in seen:
                continue
            if any(d in url for d in ["linkedin", "rocketreach", "whitepages"]):
                continue
            if "just a moment" in title.lower():
                continue
            seen.add(url)
            items.append({"title": title, "url": url})
        return items[:6]

    # ------------------------------------------------------------------
    # RUN
    # ------------------------------------------------------------------
    def run(self, name: str, email: str, company: str) -> dict:
        t0 = time.time()

        out: dict = {
            "query": {"name": name, "email": email, "company": company},
            "linkedin": {"url": None, "data": None, "source": None, "posts": []},
            "web": {},
            "company": {},
            "email": {},
            "news": [],
        }

        li_url = self.find_linkedin_url(name, company, email)
        out["linkedin"]["url"] = li_url

        if li_url:
            ld = self.extract_linkdapi(li_url)
            if ld:
                out["linkedin"]["data"] = ld
                out["linkedin"]["source"] = "linkdapi"
                posts = ld.pop("posts", None)
                if posts:
                    out["linkedin"]["posts"] = posts
            else:
                li_data = self.extract_linkedin(li_url)
                out["linkedin"]["data"] = li_data
                out["linkedin"]["source"] = li_data.get("status", "reader")

        out["web"] = self.search_web(name, company, email)
        out["company"] = self.get_company_info(company)
        out["email"] = self.verify_email(email)
        out["news"] = self.recent_news(name, company)
        out["_duration_seconds"] = round(time.time() - t0, 1)

        return out
