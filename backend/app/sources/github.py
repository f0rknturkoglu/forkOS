from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx

from app.sources.base import RawItem


class GithubSource:
    id = "github"
    interval_minutes = 180

    def __init__(self, token: str, login: str):
        self.token = token
        self.login = login

    async def fetch(self) -> list[RawItem]:
        now = datetime.now(UTC)
        variables = {
            "login": self.login,
            "from": (now - timedelta(days=365)).isoformat(),
            "to": now.isoformat(),
            "since": (now - timedelta(days=1)).isoformat(),
        }
        query = """
        query($login:String!,$from:DateTime!,$to:DateTime!,$since:GitTimestamp!) {
          user(login:$login) {
            contributionsCollection(from:$from,to:$to) {
              contributionCalendar { weeks { contributionDays { date contributionCount } } }
            }
            repositoriesContributedTo(
              first:30, contributionTypes:[COMMIT], includeUserRepositories:true
            ) {
              nodes { nameWithOwner defaultBranchRef { target { ... on Commit {
                history(first:100,since:$since) { nodes { oid messageHeadline committedDate url
                  author { user { login } } } }
              } } } }
            }
          }
        }"""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.github.com/graphql",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"query": query, "variables": variables},
            )
            response.raise_for_status()
            payload = response.json()
        if payload.get("errors"):
            first = payload["errors"][0]
            message = first.get("message") if isinstance(first, dict) else str(first)
            raise RuntimeError(message or "GitHub GraphQL error")
        return parse_github_payload(payload, self.login)


def parse_github_payload(payload: dict, login: str) -> list[RawItem]:
    """GitHub GraphQL cevabını null repository düğümlerine dayanıklı çevir."""
    user = payload.get("data", {}).get("user")
    if not user:
        raise RuntimeError("GitHub kullanıcısı bulunamadı")
    items: list[RawItem] = []
    weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    for week in weeks:
        for day in week["contributionDays"]:
            items.append(
                RawItem(
                    external_id=f"day:{day['date']}",
                    title=day["date"],
                    extra={"kind": "contribution", "count": day["contributionCount"]},
                )
            )
    for repo in user["repositoriesContributedTo"]["nodes"]:
        if not isinstance(repo, dict):
            continue
        history = ((repo.get("defaultBranchRef") or {}).get("target") or {}).get(
            "history"
        ) or {}
        for commit in history.get("nodes", []):
            author = ((commit.get("author") or {}).get("user") or {}).get("login")
            if author and author.casefold() != login.casefold():
                continue
            items.append(
                RawItem(
                    external_id=f"commit:{commit['oid']}",
                    title=commit["messageHeadline"],
                    url=commit.get("url"),
                    published_at=datetime.fromisoformat(
                        commit["committedDate"].replace("Z", "+00:00")
                    ),
                    extra={
                        "kind": "commit",
                        "repo": repo["nameWithOwner"],
                        "oid": commit["oid"],
                    },
                )
            )
    return items
