import os
from typing import List

from models.job import Job
from store import Store


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JobScrap - Ofertas {days} días</title>
<style>
  *,*::before,*::after{{box-sizing:border-box}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f5f5;margin:0;padding:20px;color:#222}}
  h1{{font-size:1.4rem;margin:0 0 8px}}
  .subtitle{{color:#666;margin-bottom:20px;font-size:.9rem}}
  .last-run{{color:#888;font-size:.8rem;margin-bottom:12px;text-align:right}}
  .stats{{margin-bottom:16px;display:flex;gap:12px;flex-wrap:wrap}}
  .stat{{background:#fff;padding:8px 14px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.06);font-size:.85rem}}
  .stat strong{{font-size:1.1rem}}
  table{{width:100%;max-width:1400px;margin:0 auto;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
  th{{background:#f8f9fa;padding:10px 12px;text-align:left;font-size:.8rem;text-transform:uppercase;letter-spacing:.5px;color:#666;border-bottom:2px solid #eee}}
  td{{padding:10px 12px;border-bottom:1px solid #f0f0f0;font-size:.88rem;vertical-align:middle}}
  tr:hover{{background:#fafafa}}
  tr:last-child td{{border-bottom:none}}
  .title-cell{{font-weight:600}}
  .title-cell a{{color:#1a73e8;text-decoration:none}}
  .title-cell a:hover{{text-decoration:underline}}
  .salary-cell{{color:#0a7;font-weight:600;white-space:nowrap}}
  .remote-badge{{display:inline-block;font-size:.75rem;padding:2px 10px;border-radius:99px;font-weight:500}}
  .remote-yes{{background:#e3f5e7;color:#0a5}}
  .remote-no{{background:#fde8e8;color:#c33}}
  .date-cell{{color:#888;white-space:nowrap;font-size:.82rem}}
  .company-cell{{color:#555}}
  .tooltip{{position:relative;cursor:help}}
  .tooltip .tooltip-text{{visibility:hidden;width:180px;background:#333;color:#fff;text-align:center;border-radius:6px;padding:5px 10px;position:absolute;z-index:1;bottom:125%;left:50%;margin-left:-90px;opacity:0;transition:opacity .2s;font-size:.78rem;font-weight:400;pointer-events:none}}
  .tooltip .tooltip-text::after{{content:"";position:absolute;top:100%;left:50%;margin-left:-5px;border:5px solid transparent;border-top-color:#333}}
  .tooltip:hover .tooltip-text{{visibility:visible;opacity:1}}
  .footer{{text-align:center;margin-top:20px;font-size:.8rem;color:#999}}
  a{{color:#1a73e8}}
  @media(max-width:768px){{table{{font-size:.8rem}}th,td{{padding:8px 6px}}}}
</style>
</head>
<body>
<h1>🔍 JobScrap — Ofertas de empleo</h1>
<p class="subtitle">Últimos {days} días | {total} ofertas | {remote_count} remotas</p>
<div class="last-run">⏱ Última búsqueda: {last_run}</div>
<div class="stats">
  <div class="stat"><strong>{total}</strong> ofertas</div>
  <div class="stat"><strong>{remote_count}</strong> remotas 🏠</div>
  <div class="stat"><strong>{onsite_count}</strong> presenciales 🏢</div>
  <div class="stat"><strong>{with_salary}</strong> con sueldo visible 💰</div>
</div>
<table>
  <thead>
    <tr>
      <th>Título</th>
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
<p class="footer" style="margin-top:20px">
  Generado: {generated} | <a href="https://github.com/xpacio/jobScrap" style="color:#1a73e8;">jobScrap</a>
</p>
</body>
</html>"""

ROW_TEMPLATE = """    <tr>
      <td class="title-cell">
        <span class="tooltip">
          <a href="{url}" target="_blank" rel="noopener">{title}</a>
          <span class="tooltip-text">📍 {location}<br>🔹 {source}</span>
        </span>
      </td>
      <td class="company-cell">{company}</td>
      <td class="salary-cell">{salary}</td>
      <td>{remote_html}</td>
      <td class="date-cell">{date}</td>
    </tr>"""


def generate_html(days: int = 20, output: str = "public/jobs.html", dsn: str = ""):
    store = Store(dsn=dsn or os.environ.get("JOBSCRAP_DSN"))
    jobs = store.get_recent_jobs(days)
    store.close()

    total = len(jobs)
    remote_count = sum(1 for j in jobs if j.remote)
    onsite_count = total - remote_count
    with_salary = sum(1 for j in jobs if j.salary.strip())

    rows_html = "\n".join(_build_row(j) for j in jobs)

    import datetime
    generated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    last_run = generated

    html = HTML_TEMPLATE.format(
        days=days,
        total=total,
        remote_count=remote_count,
        onsite_count=onsite_count,
        with_salary=with_salary,
        rows=rows_html,
        generated=generated,
        last_run=last_run,
    )

    with open(output, "w") as f:
        f.write(html)

    last_run_path = os.path.join(os.path.dirname(output), "last_run.txt")
    with open(last_run_path, "w") as f:
        f.write(generated)

    return output


def _build_row(job: Job) -> str:
    salary = job.salary if job.salary else "—"
    remote_html = (
        '<span class="remote-badge remote-yes">🏠 Remoto</span>'
        if job.remote
        else '<span class="remote-badge remote-no">🏢 Presencial</span>'
    )
    source_map = {
        "remoteok": "RemoteOK",
        "wwr": "WWR",
        "computrabajo": "CompuTrabajo",
        "indeed": "Indeed",
    }
    return ROW_TEMPLATE.format(
        url=job.url,
        title=job.title,
        company=job.company or "—",
        location=job.location or "No especificada",
        salary=salary,
        source=source_map.get(job.source, job.source),
        remote_html=remote_html,
        date=job.date_posted or "—",
    )


if __name__ == "__main__":
    path = generate_html()
    print(f"HTML generado: {path}")
