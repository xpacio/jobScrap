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
  *, *::before, *::after {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f5f5f5; margin: 0; padding: 20px; color: #222;
  }}
  h1 {{ font-size: 1.4rem; margin: 0 0 8px; }}
  .subtitle {{ color: #666; margin-bottom: 20px; font-size: 0.9rem; }}
  .grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
    gap: 12px; max-width: 1400px; margin: 0 auto;
  }}
  .card {{
    background: #fff; border-radius: 10px; padding: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,.08); transition: box-shadow .15s;
    display: flex; flex-direction: column;
  }}
  .card:hover {{ box-shadow: 0 3px 12px rgba(0,0,0,.12); }}
  .card-title {{ font-size: 1rem; font-weight: 600; margin: 0 0 6px; line-height: 1.3; }}
  .card-title a {{ color: #1a73e8; text-decoration: none; }}
  .card-title a:hover {{ text-decoration: underline; }}
  .meta {{ font-size: .82rem; color: #555; display: flex; flex-wrap: wrap; gap: 4px 12px; margin-bottom: 8px; }}
  .meta span {{ white-space: nowrap; }}
  .company {{ font-weight: 500; color: #333; }}
  .salary {{ color: #0a7; font-weight: 600; }}
  .remote-badge {{ display: inline-block; font-size: .75rem; padding: 1px 8px; border-radius: 99px; }}
  .remote-yes {{ background: #e3f5e7; color: #0a5; }}
  .remote-no {{ background: #fde8e8; color: #c33; }}
  .snippet {{ font-size: .8rem; color: #777; margin-top: auto; padding-top: 8px; border-top: 1px solid #eee; }}
  .source {{ font-size: .75rem; color: #999; }}
  .date {{ color: #888; }}
  .stats {{ margin-bottom: 16px; display: flex; gap: 12px; flex-wrap: wrap; }}
  .stat {{ background: #fff; padding: 8px 14px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.06); font-size: .85rem; }}
  .stat strong {{ font-size: 1.1rem; }}
  @media (max-width: 480px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<h1>🔍 JobScrap — Ofertas de empleo</h1>
<p class="subtitle">Últimos {days} días | {total} ofertas | {remote_count} remotas</p>
<div class="stats">
  <div class="stat"><strong>{total}</strong> ofertas</div>
  <div class="stat"><strong>{remote_count}</strong> remotas 🏠</div>
  <div class="stat"><strong>{onsite_count}</strong> presenciales 🏢</div>
  <div class="stat"><strong>{with_salary}</strong> con sueldo visible 💰</div>
</div>
<div class="grid">
{cards}
</div>
<p class="subtitle" style="margin-top:20px;text-align:center;">
  Generado: {generated} | <a href="https://github.com/xpacio/jobScrap" style="color:#1a73e8;">jobScrap</a>
</p>
</body>
</html>"""

CARD_TEMPLATE = """<div class="card">
  <div class="card-title"><a href="{url}" target="_blank" rel="noopener">{title}</a></div>
  <div class="meta">
    <span class="company">🏢 {company}</span>
    <span>📍 {location}</span>
    {salary_html}
    <span class="date">📅 {date}</span>
    <span class="source">🔹 {source}</span>
  </div>
  <div>
    {remote_html}
  </div>
  {snippet_html}
</div>"""


def generate_html(days: int = 15, output: str = "public/jobs.html", dsn: str = ""):
    store = Store(dsn=dsn or os.environ.get("JOBSCRAP_DSN"))
    jobs = store.get_recent_jobs(days)
    store.close()

    total = len(jobs)
    remote_count = sum(1 for j in jobs if j.remote)
    onsite_count = total - remote_count
    with_salary = sum(1 for j in jobs if j.salary.strip())

    cards_html = "\n".join(_build_card(j) for j in jobs)

    import datetime
    generated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    html = HTML_TEMPLATE.format(
        days=days,
        total=total,
        remote_count=remote_count,
        onsite_count=onsite_count,
        with_salary=with_salary,
        cards=cards_html,
        generated=generated,
    )

    with open(output, "w") as f:
        f.write(html)

    return output


def _build_card(job: Job) -> str:
    salary_html = (
        f'<span class="salary">💰 {job.salary}</span>' if job.salary else ""
    )
    remote_html = (
        '<span class="remote-badge remote-yes">🏠 Remoto</span>'
        if job.remote
        else '<span class="remote-badge remote-no">🏢 Presencial</span>'
    )
    snippet_html = (
        f'<div class="snippet">{job.snippet}</div>' if job.snippet else ""
    )
    source_map = {
        "remoteok": "RemoteOK",
        "wwr": "WWR",
        "computrabajo": "CompuTrabajo",
        "indeed": "Indeed",
    }
    return CARD_TEMPLATE.format(
        url=job.url,
        title=job.title,
        company=job.company or "—",
        location=job.location or "—",
        salary_html=salary_html,
        date=job.date_posted or "—",
        source=source_map.get(job.source, job.source),
        remote_html=remote_html,
        snippet_html=snippet_html,
    )


if __name__ == "__main__":
    path = generate_html()
    print(f"HTML generado: {path}")
