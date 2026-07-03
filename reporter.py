import os
import re
from datetime import datetime
from typing import List

from models.job import Job
from store import Store


def _sort_key(job: Job):
    return (job.remote, job.salary != "", job.date_posted or "")


def _strip_hace(s: str) -> str:
    return re.sub(r'^hace\s+', '', s, flags=re.IGNORECASE)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>JobScrap - Ofertas {days} dias</title>
</head>
<body>

<h1>JobScrap - Ofertas de empleo</h1>
<p>Ultimos {days} dias | {total} ofertas | {remote_count} remotas</p>
<p><i>Ultima busqueda: {last_run}</i></p>

<hr>

<table border="1" cellpadding="6" cellspacing="0" width="100%">
  <thead>
    <tr>
      <th>Titulo</th>
      <th>Empresa</th>
      <th>Sueldo</th>
      <th>Tipo</th>
      <th>Fecha</th>
    </tr>
  </thead>
  <tbody>
{rows}
  </tbody>
</table>

<hr>
<p>Generado: {generated} | <a href="https://github.com/xpacio/jobScrap">jobScrap</a></p>
</body>
</html>"""

ROW_TEMPLATE = """    <tr>
      <td><a href="{url}" target="_blank" rel="noopener" title="{tooltip}">{title}</a></td>
      <td>{company}</td>
      <td>{salary}</td>
      <td>{tipo}</td>
      <td>{date}</td>
    </tr>"""


def _time_ago(timestamp: str) -> str:
    try:
        then = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return timestamp
    diff = (datetime.now() - then).total_seconds()
    if diff < 60:
        return "hace menos de 1 minuto"
    if diff < 3600:
        return f"hace {int(diff // 60)} minutos"
    if diff < 86400:
        return f"hace {int(diff // 3600)} horas"
    return f"hace {int(diff // 86400)} dias"


def generate_html(days: int = 20, output: str = "public/jobs.html", dsn: str = ""):
    store = Store(dsn=dsn or os.environ.get("JOBSCRAP_DSN"))
    jobs = store.get_recent_jobs(days)
    store.close()

    last_run_old = ""
    last_run_path = os.path.join(os.path.dirname(output) or ".", "last_run.txt")
    if os.path.exists(last_run_path):
        with open(last_run_path) as f:
            last_run_old = f.read().strip()

    total = len(jobs)
    remote_count = sum(1 for j in jobs if j.remote)
    onsite_count = total - remote_count
    with_salary = sum(1 for j in jobs if j.salary.strip())

    jobs.sort(key=_sort_key, reverse=True)
    rows_html = "\n".join(_build_row(j, last_run_old) for j in jobs)

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    last_run = generated

    html = HTML_TEMPLATE.format(
        days=days,
        total=total,
        remote_count=remote_count,
        rows=rows_html,
        generated=generated,
        last_run=last_run,
    )

    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w") as f:
        f.write(html)

    with open(last_run_path, "w") as f:
        f.write(generated)

    return output


def _is_new(created_at: str, last_run_ts: str) -> bool:
    if not last_run_ts or not created_at:
        return False
    try:
        last_dt = datetime.strptime(last_run_ts, "%Y-%m-%d %H:%M:%S")
        created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return created_dt >= last_dt
    except (ValueError, TypeError):
        return False


def _build_row(job: Job, last_run_ts: str = "") -> str:
    salary = job.salary if job.salary else "-"
    tipo = "R" if job.remote else "P"
    source_map = {
        "remoteok": "RemoteOK",
        "wwr": "WWR",
        "computrabajo": "CompuTrabajo",
        "indeed": "Indeed",
    }
    src = source_map.get(job.source, job.source)
    loc = job.location or "No especificada"
    tooltip = f"Ubicacion: {loc} | Fuente: {src}"
    title = job.title
    if _is_new(job.created_at, last_run_ts):
        title += " (N)"
    return ROW_TEMPLATE.format(
        url=job.url,
        title=title,
        company=(job.company or "-")[:12],
        salary=salary,
        tipo=tipo,
        date=_strip_hace(job.date_posted or "-"),
        tooltip=tooltip,
    )


if __name__ == "__main__":
    path = generate_html()
    print(f"HTML generado: {path}")
