<?php
$raw = getenv('JOBSCRAP_DSN') ?: 'pgsql:dbname=jobscrap user=jobscrap password=jobscrap_local host=localhost';
$dsn = str_starts_with($raw, 'pgsql:') ? $raw : "pgsql:$raw";

try {
    $pdo = new PDO($dsn);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (PDOException $e) {
    if (file_exists(__DIR__ . '/jobs.html')) {
        readfile(__DIR__ . '/jobs.html');
        exit;
    }
    die('Sin conexión a BD y sin reporte HTML disponible.');
}

$days = isset($_GET['d']) ? min(365, max(1, (int)$_GET['d'])) : 20;
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

$sources = $pdo->query("SELECT DISTINCT source FROM jobs ORDER BY source")->fetchAll(PDO::FETCH_COLUMN);

$last_run_timestamp = '';
$last_run_file = __DIR__ . '/last_run.txt';
if (file_exists($last_run_file)) {
    $last_run_timestamp = file_get_contents($last_run_file);
}

$source_map = ['remoteok'=>'RemoteOK','wwr'=>'WWR','computrabajo'=>'CompuTrabajo','trabajoorg'=>'TrabajoOrg'];
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
.last-run{color:#888;font-size:.8rem;margin-bottom:12px;text-align:right}
table{width:100%;max-width:1400px;margin:0 auto;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)}
th{background:#f8f9fa;padding:10px 12px;text-align:left;font-size:.8rem;text-transform:uppercase;letter-spacing:.5px;color:#666;border-bottom:2px solid #eee}
td{padding:10px 12px;border-bottom:1px solid #f0f0f0;font-size:.88rem;vertical-align:middle}
tr:hover{background:#fafafa}
tr:last-child td{border-bottom:none}
.title-cell{font-weight:600}
.title-cell a{color:#1a73e8;text-decoration:none}
.title-cell a:hover{text-decoration:underline}
.salary-cell{color:#0a7;font-weight:600;white-space:nowrap}
.remote-badge{display:inline-block;font-size:.75rem;padding:2px 10px;border-radius:99px;font-weight:500}
.remote-yes{background:#e3f5e7;color:#0a5}
.remote-no{background:#fde8e8;color:#c33}
.date-cell{color:#888;white-space:nowrap;font-size:.82rem}
.company-cell{color:#555}
.tooltip{position:relative;cursor:help}
.tooltip .tooltip-text{visibility:hidden;width:180px;background:#333;color:#fff;text-align:center;border-radius:6px;padding:5px 10px;position:absolute;z-index:1;bottom:125%;left:50%;margin-left:-90px;opacity:0;transition:opacity .2s;font-size:.78rem;font-weight:400;pointer-events:none}
.tooltip .tooltip-text::after{content:"";position:absolute;top:100%;left:50%;margin-left:-5px;border:5px solid transparent;border-top-color:#333}
.tooltip:hover .tooltip-text{visibility:visible;opacity:1}
.footer{text-align:center;margin-top:20px;font-size:.8rem;color:#999}
a{color:#1a73e8}
@media(max-width:768px){table{font-size:.8rem}th,td{padding:8px 6px}}
</style>
</head>
<body>
<h1>🔍 JobScrap — Ofertas de empleo TI</h1>
<p class="subtitle"><?= $total ?> ofertas · <?= $remote_count ?> remotas · <?= $with_salary ?> con sueldo</p>

<?php if ($last_run_timestamp): ?>
<div class="last-run">⏱ Última búsqueda: <?= htmlspecialchars($last_run_timestamp) ?></div>
<?php endif; ?>

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
      <option value="20" <?= $days===20?'selected':'' ?>>20 días</option>
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

<?php if ($total === 0): ?>
  <p>No se encontraron ofertas.</p>
<?php else: ?>
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
    <?php foreach ($jobs as $j):
      $src_label = $source_map[$j['source']] ?? $j['source'];
      $location_tooltip = $j['location'] ?: 'No especificada';
    ?>
    <tr>
      <td class="title-cell">
        <span class="tooltip">
          <a href="<?= htmlspecialchars($j['url']) ?>" target="_blank" rel="noopener"><?= htmlspecialchars($j['title']) ?></a>
          <span class="tooltip-text">📍 <?= htmlspecialchars($location_tooltip) ?><br>🔹 <?= htmlspecialchars($src_label) ?></span>
        </span>
      </td>
      <td class="company-cell"><?= htmlspecialchars($j['company'] ?: '—') ?></td>
      <td class="salary-cell"><?= $j['salary'] ? htmlspecialchars($j['salary']) : '—' ?></td>
      <td><span class="remote-badge <?= $j['remote'] ? 'remote-yes' : 'remote-no' ?>"><?= $j['remote'] ? '🏠 Remoto' : '🏢 Presencial' ?></span></td>
      <td class="date-cell"><?= htmlspecialchars($j['date_posted'] ?: '—') ?></td>
    </tr>
    <?php endforeach; ?>
  </tbody>
</table>
<?php endif; ?>

<p class="footer">Generado: <?= date('Y-m-d H:i') ?> · <a href="https://github.com/xpacio/jobScrap">jobScrap</a></p>
</body>
</html>
<?php $pdo = null; ?>