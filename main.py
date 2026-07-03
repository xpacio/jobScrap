import sys
from typing import List

from rich.console import Console
from rich.table import Table

from config import AppConfig
from models.job import Job
from store import Store


console = Console()

PROVIDER_MAP = {}


def load_providers():
    from providers.remoteok import RemoteOKProvider
    PROVIDER_MAP["remoteok"] = RemoteOKProvider
    from providers.weworkremotely import WeWorkRemotelyProvider
    PROVIDER_MAP["weworkremotely"] = WeWorkRemotelyProvider


def display_jobs(jobs: List[Job]):
    if not jobs:
        console.print("\n[bold yellow]No se encontraron ofertas nuevas.[/bold yellow]")
        return

    console.print(f"\n[bold green]✓ {len(jobs)} ofertas nuevas encontradas[/bold green]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Fuente", style="dim", width=8)
    table.add_column("Título", width=40)
    table.add_column("Empresa", width=25)
    table.add_column("Ubicación", width=20)
    table.add_column("Fecha", width=12)

    for job in sorted(jobs, key=lambda j: j.date_posted or "", reverse=True):
        source_tag = {
            "indeed": "[bold cyan]Indeed[/]",
            "remoteok": "[bold green]RemoteOK[/]",
            "wwr": "[bold yellow]WWR[/]",
        }.get(job.source, job.source)
        table.add_row(
            source_tag,
            job.title[:60],
            job.company[:35] or "-",
            job.location[:30] or "-",
            (job.date_posted or "-")[:15],
        )

    console.print(table)


def main():
    load_providers()
    config = AppConfig()
    store = Store(config.db_path)

    total_new = 0
    jobs_all: List[Job] = []

    for provider_name in config.providers:
        provider_cls = PROVIDER_MAP.get(provider_name)
        if not provider_cls:
            console.print(f"[red]Provider '{provider_name}' no encontrado[/red]")
            continue

        provider = provider_cls()
        console.print(f"\n[bold]🔍 Buscando en {provider.name.upper()}...[/bold]")

        for keyword in config.search.keywords:
            console.print(f"  [dim]Buscando '{keyword}'...[/dim]", end="\r")

            try:
                jobs = provider.search(
                    keyword=keyword,
                    location=config.search.location,
                    max_results=config.search.max_results_per_keyword,
                )
                new = store.save_jobs(jobs)
                total_new += new
                jobs_all.extend(jobs)
                console.print(f"  [dim]'{keyword}' → {len(jobs)} encontrados, {new} nuevos[/dim]")
            except Exception as e:
                console.print(f"  [red]Error con '{keyword}': {e}[/red]")

    total_db = store.count()
    store.close()

    seen = set()
    unique_jobs = []
    for j in jobs_all:
        if j.url not in seen:
            seen.add(j.url)
            unique_jobs.append(j)

    console.print(f"\n[bold]📊 Total en DB: {total_db} ofertas | Esta sesión: {total_new} nuevas (mostrando {len(unique_jobs)} únicas)[/bold]")

    display_jobs(unique_jobs)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrumpido por el usuario[/yellow]")
        sys.exit(0)
