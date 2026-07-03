import os
import sys
from typing import List

from rich.console import Console
from rich.table import Table

from config import AppConfig
from models.job import Job
from store import Store
from reporter import generate_html


console = Console()

PROVIDER_MAP = {}


def load_providers():
    from providers.remoteok import RemoteOKProvider
    PROVIDER_MAP["remoteok"] = RemoteOKProvider
    from providers.weworkremotely import WeWorkRemotelyProvider
    PROVIDER_MAP["weworkremotely"] = WeWorkRemotelyProvider
    from providers.computrabajo import ComputrabajoProvider
    PROVIDER_MAP["computrabajo"] = ComputrabajoProvider
    from providers.trabajoorg import TrabajoOrgProvider
    PROVIDER_MAP["trabajoorg"] = TrabajoOrgProvider
    from providers.occ import OCCProvider
    PROVIDER_MAP["occ"] = OCCProvider
    from providers.hireline import HirelineProvider
    PROVIDER_MAP["hireline"] = HirelineProvider


def display_jobs(jobs: List[Job]):
    if not jobs:
        console.print("\n[bold yellow]No se encontraron ofertas nuevas.[/bold yellow]")
        return

    console.print(f"\n[bold green]✓ {len(jobs)} ofertas nuevas encontradas[/bold green]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Fuente", style="dim", width=8)
    table.add_column("Título", width=35)
    table.add_column("Empresa", width=20)
    table.add_column("Ubicación", width=16)
    table.add_column("Sueldo", width=14)
    table.add_column("Tipo", width=8)
    table.add_column("Fecha", width=10)

    for job in sorted(jobs, key=lambda j: j.date_posted or "", reverse=True):
        source_tag = {
            "indeed": "[bold cyan]Indeed[/]",
            "remoteok": "[bold green]ROK[/]",
            "wwr": "[bold yellow]WWR[/]",
            "computrabajo": "[bold magenta]CT[/]",
            "trabajoorg": "[bold cyan]TO[/]",
        }.get(job.source, job.source)
        tipo = "🏠" if job.remote else "🏢"
        table.add_row(
            source_tag,
            job.title[:55],
            job.company[:30] or "-",
            job.location[:25] or "-",
            job.salary[:18] or "-",
            tipo,
            (job.date_posted or "-")[:12],
        )

    console.print(table)


def main():
    load_providers()
    config = AppConfig()
    store = Store(
        dsn=config.dsn or os.environ.get("JOBSCRAP_DSN"),
        db_path=config.db_path,
    )

    keywords = store.get_keywords()
    if not keywords:
        keywords = config.search.keywords
    if not keywords:
        console.print("[red]No hay keywords configuradas[/red]")
        return

    total_new = 0
    jobs_all: List[Job] = []

    for provider_name in config.providers:
        provider_cls = PROVIDER_MAP.get(provider_name)
        if not provider_cls:
            console.print(f"[red]Provider '{provider_name}' no encontrado[/red]")
            continue

        provider = provider_cls()
        console.print(f"\n[bold]🔍 Buscando en {provider.name.upper()}...[/bold]")

        for keyword in keywords:
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

    html_path = generate_html(days=config.search.days_back, dsn=config.dsn)
    console.print(f"\n[bold green]🌐 Reporte HTML generado: {html_path}[/bold green]")

    import datetime
    last_run_dir = os.path.dirname(html_path) if html_path else "."
    with open(os.path.join(last_run_dir, "last_run.txt"), "w") as f:
        f.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    console.print("[bold green]⏱ Última corrida registrada[/bold green]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrumpido por el usuario[/yellow]")
        sys.exit(0)
