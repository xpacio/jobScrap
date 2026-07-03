#!/usr/bin/env python3
import re
import sys
from pathlib import Path
from typing import List, Set, Tuple
from collections import Counter

from models.job import Job
from store import Store
from config import AppConfig

TECH_KEYWORDS = {
    'python', 'php', 'javascript', 'typescript', 'java', 'go', 'rust',
    'ruby', 'perl', 'bash', 'shell', 'zsh', 'powershell', 'plpgsql',
    'linux', 'unix', 'centos', 'debian', 'ubuntu', 'rhel', 'alpine',
    'docker', 'kubernetes', 'k8s', 'ansible', 'terraform', 'puppet', 'chef',
    'git', 'github', 'gitlab', 'svn',
    'postgresql', 'postgres', 'mysql', 'mariadb', 'mongodb', 'redis',
    'sqlite', 'mssql', 'oracle', 'couchdb',
    'nginx', 'apache', 'traefik', 'haproxy', 'caddy',
    'azure', 'aws', 'gcp', 'cloud', 'digitalocean', 'linode',
    'devops', 'sysadmin', 'sysop', 'sre', 'admin',
    'grafana', 'prometheus', 'nagios', 'zabbix', 'datadog', 'elk',
    'jenkins', 'gitlab', 'circleci', 'github', 'ci/cd',
    'network', 'firewall', 'vpn', 'dns', 'dhcp', 'ldap', 'proxy',
    'backup', 'restore', 'replication', 'failover', 'ha',
    'vmware', 'proxmox', 'kvm', 'xen', 'virtualbox', 'vagrant',
    'contpaq', 'respaldos', 'ftp', 'sftp', 'api', 'rest', 'soap',
    'ssl', 'tls', 'ssh', 'certbot', 'letsencrypt',
    'monitoring', 'logging', 'alerting', 'incident',
    'agile', 'scrum', 'jira', 'confluence',
    'windows', 'server', 'exchange', 'outlook', 'active',
    'cpanel', 'whm', 'plesk', 'directadmin',
    'cloudflare', 'varnish', 'memcached', 'rabbitmq',
    'nginx', 'apache', 'iis',
    'scripting', 'automation', 'orchestration',
    'soporte', 'infraestructura', 'tecnologia',
}


def extract_text_from_pdf(pdf_path: str) -> str:
    import fitz
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def extract_skills(text: str) -> Set[str]:
    text_lower = text.lower()
    skills = set()

    for kw in TECH_KEYWORDS:
        if kw in text_lower:
            skills.add(kw)

    for word in re.findall(r'\b[A-Z][a-zA-Z0-9+#.]{2,}\b', text):
        w = word.lower()
        if len(w) >= 3 and w not in skills:
            skills.add(w)

    return skills


def score_job(job: Job, skills: Set[str]) -> int:
    haystack = f"{job.title} {job.snippet} {job.company}".lower()
    score = 0
    for s in skills:
        if s in haystack:
            score += 1
    return score


def main():
    if len(sys.argv) < 2:
        print("Uso: cv_match.py <ruta_al_cv.pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not Path(pdf_path).exists():
        print(f"Error: no existe: {pdf_path}")
        sys.exit(1)

    print(f"Leyendo CV: {pdf_path}")
    text = extract_text_from_pdf(pdf_path)
    print(f"Texto extraido: {len(text)} caracteres\n")

    skills = extract_skills(text)
    print(f"Skills detectados ({len(skills)}):")
    for s in sorted(skills):
        print(f"  - {s}")
    print()

    config = AppConfig()
    store = Store(dsn=config.dsn, db_path=config.db_path)
    jobs = store.get_all_jobs()

    scored: List[Tuple[int, Job]] = [(score_job(j, skills), j) for j in jobs]
    scored.sort(key=lambda x: (-x[0], x[1].date_posted or ""))

    matched = [(s, j) for s, j in scored if s > 0]

    if not matched:
        print("No se encontraron coincidencias con tu perfil.")
        store.close()
        return

    print(f"{'Score':<7} {'Fuente':<10} {'Titulo':<50} {'Empresa':<20}")
    print("-" * 87)
    for score, job in matched:
        src = job.source.upper()[:10]
        print(f"{score:<7} {src:<10} {job.title[:50]:<50} {job.company[:20]:<20}")

    print(f"\n{len(matched)}/{len(jobs)} ofertas coinciden con tu perfil")
    store.close()


if __name__ == "__main__":
    main()
