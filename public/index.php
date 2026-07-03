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
    die('Sin conexion a BD y sin reporte HTML disponible.');
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

function time_ago($timestamp) {
    $now = new DateTime();
    $then = DateTime::createFromFormat('Y-m-d H:i:s', $timestamp);
    if (!$then) return $timestamp;
    $diff = $now->getTimestamp() - $then->getTimestamp();
    if ($diff < 60) return 'hace menos de 1 minuto';
    if ($diff < 3600) return 'hace ' . floor($diff / 60) . ' minutos';
    if ($diff < 86400) return 'hace ' . floor($diff / 3600) . ' horas';
    return 'hace ' . floor($diff / 86400) . ' dias';
}

$last_run_relative = '';
$last_run_file = __DIR__ . '/last_run.txt';
if (file_exists($last_run_file)) {
    $ts = trim(file_get_contents($last_run_file));
    $last_run_relative = time_ago($ts);
}

$source_map = ['remoteok'=>'RemoteOK','wwr'=>'WWR','computrabajo'=>'CompuTrabajo','trabajoorg'=>'TrabajoOrg'];
?>
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>JobScrap</title>
</head>
<body>

<h1>JobScrap - Ofertas de empleo TI</h1>
<p><?= $total ?> ofertas | <?= $remote_count ?> remotas | <?= $with_salary ?> con sueldo</p>
<?php if ($last_run_relative): ?>
<p><i>Ultima busqueda: <?= htmlspecialchars($last_run_relative) ?></i></p>
<?php endif; ?>

<hr>

<form method="get" action="">
<select name="d">
  <option value="7" <?= $days===7?'selected':'' ?>>7 dias</option>
  <option value="20" <?= $days===20?'selected':'' ?>>20 dias</option>
  <option value="30" <?= $days===30?'selected':'' ?>>30 dias</option>
  <option value="90" <?= $days===90?'selected':'' ?>>90 dias</option>
</select>
<select name="source">
  <option value="">Todas las fuentes</option>
  <?php foreach ($sources as $s): ?>
    <option value="<?= htmlspecialchars($s) ?>" <?= $source===$s?'selected':'' ?>><?= htmlspecialchars($s) ?></option>
  <?php endforeach; ?>
</select>
<select name="remote">
  <option value="">Todos</option>
  <option value="1" <?= $remote==='1'?'selected':'' ?>>Remoto</option>
  <option value="0" <?= $remote==='0'?'selected':'' ?>>Presencial</option>
</select>
<input type="text" name="q" placeholder="Buscar..." value="<?= htmlspecialchars($search) ?>">
<button type="submit">Filtrar</button>
</form>

<hr>

<?php if ($total === 0): ?>
  <p>No se encontraron ofertas.</p>
<?php else: ?>
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
    <?php foreach ($jobs as $j):
      $src_label = $source_map[$j['source']] ?? $j['source'];
      $loc = $j['location'] ?: 'No especificada';
      $tooltip = 'Ubicacion: ' . $loc . ' | Fuente: ' . $src_label;
      $tipo = $j['remote'] ? 'Remoto' : 'Presencial';
    ?>
    <tr>
      <td><a href="<?= htmlspecialchars($j['url']) ?>" target="_blank" rel="noopener" title="<?= htmlspecialchars($tooltip) ?>"><?= htmlspecialchars($j['title']) ?></a></td>
      <td><?= htmlspecialchars($j['company'] ?: '-') ?></td>
      <td><?= $j['salary'] ? htmlspecialchars($j['salary']) : '-' ?></td>
      <td><?= $tipo ?></td>
      <td><?= htmlspecialchars($j['date_posted'] ?: '-') ?></td>
    </tr>
    <?php endforeach; ?>
  </tbody>
</table>
<?php endif; ?>

<hr>
<p>Generado: <?= date('Y-m-d H:i') ?> | <a href="https://github.com/xpacio/jobScrap">jobScrap</a></p>
</body>
</html>
<?php $pdo = null; ?>