<?php
$raw = getenv('JOBSCRAP_DSN') ?: 'pgsql:dbname=jobscrap user=jobscrap password=jobscrap_local host=localhost';
$dsn = str_starts_with($raw, 'pgsql:') ? $raw : "pgsql:$raw";

try {
    $pdo = new PDO($dsn);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (PDOException $e) {
    // Fallback to read static HTML
    if (file_exists(__DIR__ . '/jobs.html')) {
        readfile(__DIR__ . '/jobs.html');
        exit;
    }
    die('Sin conexión a BD y sin reporte HTML disponible.');
}

$days = isset($_GET['d']) ? min(365, max(1, (int)$_GET['d'])) : 14;
$source = $_GET['source'] ?? '';
$remote = $_GET['remote'] ?? '';
$search = $_GET['q'] ?? '';

$where = ["created_at >= NOW() - make_interval(days => $days)"];
$params = [];

if ($source) {
    $where[] = 'source = ?';
    $params[] = $source;
}
if ($remote === '1') {
    $where[] = 'remote = TRUE';
} elseif ($remote === '0') {
    $where[] = 'remote = FALSE';
}
if ($search) {
    $where[] = '(LOWER(title) LIKE ? OR LOWER(company) LIKE ?)';
    $params[] = '%' . mb_strtolower($search) . '%';
    $params[] = '%' . mb_strtolower($search) . '%';
}

$sql = 'SELECT * FROM jobs WHERE ' . implode(' AND ', $where) . ' ORDER BY created_at DESC';

$stmt = $pdo->prepare($sql);
$stmt->execute($params);
$jobs = $stmt->fetchAll(PDO::FETCH_ASSOC);

$total = count($jobs);
$remote_count = 0;
$with_salary = 0;
foreach ($jobs as $j) {
    if ($j['remote']) $remote_count++;
    if (trim($j['salary'] ?? '')) $with_salary++;
}

// Get sources for filter
$sources = $pdo->query("SELECT DISTINCT source FROM jobs ORDER BY source")->fetchAll(PDO::FETCH_COLUMN);
?>
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>JobScrap — Ofertas TI</title>
<style>
*,*::before,*::after{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f5f5;margin:0;padding:20px;color:#222}
h1{font-size:1.4rem;margin:0 0 4px}
.subtitle{color:#666;margin-bottom:16px;font-size:.9rem}
.toolbar{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;align-items:center}
.toolbar form{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
select,input,button{padding:6px 10px;border:1px solid #ccc;border-radius:6px;font-size:.85rem;background:#fff}
button{background:#1a73e8;color:#fff;border-color:#1a73e8;cursor:pointer}
button:hover{background:#1557b0}
.stats{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap}
.stat{background:#fff;padding:6px 12px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.06);font-size:.85rem}
.stat strong{font-size:1.05rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:10px;max-width:1400px;margin:0 auto}
.card{background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 4px rgba(0,0,0,.08);transition:box-shadow .15s;display:flex;flex-direction:column}
.card:hover{box-shadow:0 3px 12px rgba(0,0,0,.12)}
.card-title{font-size:1rem;font-weight:600;margin:0 0 5px;line-height:1.3}
.card-title a{color:#1a73e8;text-decoration:none}
.card-title a:hover{text-decoration:underline}
.meta{font-size:.82rem;color:#555;display:flex;flex-wrap:wrap;gap:3px 10px;margin-bottom:6px}
.meta span{white-space:nowrap}
.company{font-weight:500;color:#333}
.salary{color:#0a7;font-weight:600}
.remote-badge{display:inline-block;font-size:.75rem;padding:1px 8px;border-radius:99px}
.remote-yes{background:#e3f5e7;color:#0a5}
.remote-no{background:#fde8e8;color:#c33}
.source{font-size:.75rem;color:#999}
.date{color:#888}
.footer{text-align:center;margin-top:20px;font-size:.8rem;color:#999}
a{color:#1a73e8}
@media(max-width:480px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<h1>🔍 JobScrap — Ofertas de empleo TI</h1>
<p class="subtitle"><?= $total ?> ofertas · <?= $remote_count ?> remotas · <?= $with_salary ?> con sueldo</p>

<div class="stats">
  <div class="stat"><strong><?= $total ?></strong> ofertas</div>
  <div class="stat"><strong><?= $remote_count ?></strong> 🏠 remotas</div>
  <div class="stat"><strong><?= $total - $remote_count ?></strong> 🏢 presenciales</div>
  <div class="stat"><strong><?= $with_salary ?></strong> 💰 con sueldo</div>
</div>

<div class="toolbar">
  <form method="get" action="">
    <select name="d">
      <option value="7" <?= $days===7?'selected':'' ?>>7 días</option>
      <option value="14" <?= $days===14?'selected':'' ?>>14 días</option>
      <option value="30" <?= $days===30?'selected':'' ?>>30 días</option>
      <option value="90" <?= $days===90?'selected':'' ?>>90 días</option>
    </select>
    <select name="source">
      <option value="">Todas las fuentes</option>
      <?php foreach ($sources as $s): ?>
        <option value="<?= htmlspecialchars($s) ?>" <?= $source===$s?'selected':'' ?>><?= htmlspecialchars($s) ?></option>
      <?php endforeach; ?>
    </select>
    <select name="remote">
      <option value="">Todos</option>
      <option value="1" <?= $remote==='1'?'selected':'' ?>>🏠 Remoto</option>
      <option value="0" <?= $remote==='0'?'selected':'' ?>>🏢 Presencial</option>
    </select>
    <input type="text" name="q" placeholder="Buscar título/empresa…" value="<?= htmlspecialchars($search) ?>">
    <button type="submit">Filtrar</button>
  </form>
</div>

<div class="grid">
<?php if ($total === 0): ?>
  <p>No se encontraron ofertas.</p>
<?php else: ?>
  <?php foreach ($jobs as $j):
    $source_map = ['remoteok'=>'RemoteOK','wwr'=>'WWR','computrabajo'=>'CompuTrabajo','trabajoorg'=>'TrabajoOrg'];
    $src_label = $source_map[$j['source']] ?? $j['source'];
  ?>
  <div class="card">
    <div class="card-title"><a href="<?= htmlspecialchars($j['url']) ?>" target="_blank" rel="noopener"><?= htmlspecialchars($j['title']) ?></a></div>
    <div class="meta">
      <span class="company">🏢 <?= htmlspecialchars($j['company'] ?: '—') ?></span>
      <span>📍 <?= htmlspecialchars($j['location'] ?: '—') ?></span>
      <?php if (trim($j['salary'] ?? '')): ?><span class="salary">💰 <?= htmlspecialchars($j['salary']) ?></span><?php endif; ?>
      <span class="date">📅 <?= htmlspecialchars($j['date_posted'] ?: '—') ?></span>
      <span class="source">🔹 <?= $src_label ?></span>
    </div>
    <div>
      <span class="remote-badge <?= $j['remote'] ? 'remote-yes' : 'remote-no' ?>"><?= $j['remote'] ? '🏠 Remoto' : '🏢 Presencial' ?></span>
    </div>
  </div>
  <?php endforeach; ?>
<?php endif; ?>
</div>

<p class="footer">Generado: <?= date('Y-m-d H:i') ?> · <a href="https://github.com/xpacio/jobScrap">jobScrap</a></p>
</body>
</html>
<?php $pdo = null; ?>