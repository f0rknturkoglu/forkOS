"""forkOS CLI — local API'ye konusan terminal araci.

Kullanici: `make cli ARGS="today"` ya da dogrudan:
    backend/.venv/bin/python -m app.cli add-todo "raporu bitir" --due 2026-09-05

API adresi: FORKOS_API ortam degiskeni (varsayilan http://127.0.0.1:8787).
Yalnizca okuma + tek satirlik yazmalar; karma yazma islemleri web arayuzune
birakilir. Veri terminalden cikmaz, her sey local kalir (AGENTS.md).
"""

from __future__ import annotations

from typing import Any

import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="forkOS — kişisel işletim sistemi komutları")
console = Console()

DEFAULT_BASE = "http://127.0.0.1:8787"
TIMEOUT = 10.0


def _client(prefix: str = "/api") -> httpx.Client:
    base = __import__("os").environ.get("FORKOS_API", DEFAULT_BASE).rstrip("/")
    return httpx.Client(base_url=f"{base}{prefix}", timeout=TIMEOUT)


def _call(method: str, path: str, prefix: str = "/api", **kwargs: Any) -> Any:
    """API cagrisi; hata govdesindeki detail'i rich ile basar."""
    with _client(prefix) as client:
        response = client.request(method, path, **kwargs)
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        console.print(f"[red]Hata ({response.status_code}): {detail}[/red]")
        raise typer.Exit(1)
    if response.status_code == 204:
        return None
    return response.json()


@app.command("status")
def status() -> None:
    """API ayakta mi, kac modul kayitli."""
    try:
        health = _call("GET", "/health", prefix="")
    except httpx.HTTPError as exc:
        console.print(f"[red]API'ye ulasilamadi: {exc}[/red]")
        raise typer.Exit(1) from exc
    modules = health.get("modules", [])
    console.print(f"[green]forkOS çalışıyor[/green] — {len(modules)} modül: {', '.join(modules)}")


@app.command("today")
def today() -> None:
    """Bugunun takvimi: zamanli maddeler + kontrol listesi."""
    agenda = _call("GET", "/today/agenda")

    timed = [row for row in agenda["timed"] if not row.get("completed")]
    if timed:
        table = Table(title=f"Zamanlı — {agenda['day']}", show_header=False, box=None)
        for row in timed:
            starts = row.get("starts_at", "")[11:16] if row.get("starts_at") else ""
            duration = f" ({row['duration_min']}dk)" if row.get("duration_min") else ""
            table.add_row(f"[dim]{starts}[/dim]", row["title"] + duration)
        console.print(table)

    checklist = [row for row in agenda["checklist"] if not row.get("completed")]
    if checklist:
        table = Table(title="Kontrol listesi", show_header=False, box=None)
        for row in checklist:
            table.add_row("☐", row["title"])
        console.print(table)

    if not timed and not checklist:
        console.print("Bugün planlanmış madde yok.")
    done = len(agenda["completed"])
    if done:
        console.print(f"[dim]{done} madde tamamlanmış.[/dim]")


@app.command("add-todo")
def add_todo(
    text: str = typer.Argument(..., help="Görev metni"),
    due: str = typer.Option(None, "--due", help="YYYY-MM-DD son tarih"),
    tag: list[str] = typer.Option(None, "--tag", help="Etiket (tekrarlanabilir)"),
) -> None:
    """Yeni gorev ekle."""
    payload: dict[str, Any] = {"title": text, "tags": tag or []}
    if due:
        payload["due_at"] = f"{due}T23:59:00+03:00"
    created = _call("POST", "/todos", json=payload)
    console.print(f"[green]Eklendi:[/green] {created['title']} ({created['id']})")


@app.command("done")
def done(todo_id: str = typer.Argument(..., help="Görev id'si")) -> None:
    """Gorevi tamamla."""
    completed = _call("POST", f"/todos/{todo_id}/complete")
    console.print(f"[green]Tamamlandı:[/green] {completed['title']}")


@app.command("capture")
def capture(
    url: str = typer.Argument(..., help="Kaydedilecek adres"),
    title: str = typer.Option("", "--title", help="Başlık (boşsa sayfadan alınır)"),
    note: str = typer.Option(None, "--note", help="Not"),
    collection: str = typer.Option("inbox", "--collection", help="inbox|read_later|learning|reference|projects|archive"),
    tag: list[str] = typer.Option(None, "--tag", help="Etiket (tekrarlanabilir)"),
) -> None:
    """Adresi kutuphaneye kaydet (capture)."""
    payload = {
        "url": url,
        "title": title,
        "note": note,
        "collection": collection,
        "source": "cli",
        "tags": tag or [],
    }
    saved = _call("POST", "/capture", json=payload)
    where = f" → {collection}" if collection != "inbox" else ""
    console.print(f"[green]Kaydedildi:[/green] {saved.get('title') or url}{where}")


@app.command("jobs")
def jobs(
    limit: int = typer.Option(5, "--limit", min=1, max=50),
    section: str = typer.Option("jobs", "--section", help="jobs|announcements|trash"),
) -> None:
    """Son firsatlar (is ilanlari)."""
    browse = _call("GET", "/opportunities/browse", params={"limit": limit, "section": section})
    items = browse["items"]
    if not items:
        console.print("Bu bölümde fırsat yok.")
        return
    table = Table(title=f"Fırsatlar — {section} ({browse['total']})", show_header=False, box=None)
    for item in items:
        org = f" · [dim]{item['organization']}[/dim]" if item.get("organization") else ""
        score = f" · skor {item['score']:.0f}" if item.get("score") is not None else ""
        status = f" · [dim]{item['status']}[/dim]" if item["status"] != "discovered" else ""
        table.add_row(item["title"] + org + score + status)
    console.print(table)


@app.command("scraper-health")
def scraper_health() -> None:
    """Scraper sağlık durumu: katalog, son koşumlar ve çalışma başarısı."""
    catalog = _call("GET", "/sources/catalog")
    runs = _call("GET", "/sources/runs")

    latest_run: dict[str, dict] = {}
    for r in runs:
        src = r.get("source") or r.get("source_id")
        if src and src not in latest_run:
            latest_run[src] = r

    table = Table(title="Scraper Sağlık Durumu", box=None)
    table.add_column("Kaynak ID", style="cyan")
    table.add_column("Tür", style="magenta")
    table.add_column("Kategori", style="yellow")
    table.add_column("Son Durum", style="bold")
    table.add_column("Yeni/Toplam", justify="right")
    table.add_column("Son Koşum", style="dim")

    for s in catalog:
        src_id = s.get("id", "")
        kind = s.get("kind", "job")
        cat = s.get("category") or "—"
        run = latest_run.get(src_id)
        if not run:
            table.add_row(src_id, kind, cat, "[dim]henüz çalışmadı[/dim]", "—", "—")
        else:
            status = run.get("status", "unknown")
            color = "green" if status == "ok" else "yellow" if status == "empty" else "red"
            counts = f"{run.get('items_new', 0)}/{run.get('items_found', run.get('items_total', 0))}"
            started = (run.get("started_at") or "")[:19].replace("T", " ")
            table.add_row(src_id, kind, cat, f"[{color}]{status}[/{color}]", counts, started)

    console.print(table)


if __name__ == "__main__":
    app()
