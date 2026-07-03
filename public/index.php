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

// --- Keywords CRUD ---
$pdo->exec("CREATE TABLE IF NOT EXISTS keywords (
    id SERIAL PRIMARY KEY,
    word TEXT NOT NULL UNIQUE,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
)");

$msg = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';
    if ($action === 'add' && !empty($_POST['word'])) {
        $word = trim($_POST['word']);
        if ($word) {
            $stmt = $pdo->prepare("INSERT INTO keywords (word) VALUES (?) ON CONFLICT (word) DO UPDATE SET active = TRUE");
            $stmt->execute([$word]);
            $msg = "Keyword agregada: " . htmlspecialchars($word);
        }
    } elseif ($action === 'delete' && !empty($_POST['id'])) {
        $stmt = $pdo->prepare("DELETE FROM keywords WHERE id = ?");
        $stmt->execute([(int)$_POST['id']]);
        $msg = "Keyword eliminada";
    } elseif ($action === 'toggle' && !empty($_POST['id'])) {
        $stmt = $pdo->prepare("UPDATE keywords SET active = NOT active WHERE id = ?");
        $stmt->execute([(int)$_POST['id']]);
        $msg = "Keyword actualizada";
    }
}

$keywords_all = $pdo->query("SELECT id, word, active FROM keywords ORDER BY id")->fetchAll(PDO::FETCH_ASSOC);
$active_keywords = array_filter($keywords_all, fn($k) => $k['active']);
$active_keyword_words = array_map(fn($k) => $k['word'], $active_keywords);

// --- Filters ---
$days = isset($_GET['d']) ? min(365, max(1, (int)$_GET['d'])) : 20;
$source = $_GET['source'] ?? '';
$remote = $_GET['remote'] ?? '';
$search = $_GET['q'] ?? '';
$kw_filter = $_GET['kw'] ?? '';

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
if ($kw_filter) {
    $like = '%' . mb_strtolower($kw_filter) . '%';
    $where[] = '(LOWER(title) LIKE ? OR LOWER(company) LIKE ?)';
    $params[] = $like;
    $params[] = $like;
}

$sql = 'SELECT * FROM jobs WHERE ' . implode(' AND ', $where) . " ORDER BY created_at DESC, (CASE WHEN COALESCE(salary, '') != '' THEN 0 ELSE 1 END), remote DESC NULLS LAST";

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
    if ($diff < 60) return 'menos de 1 minuto';
    if ($diff < 3600) return floor($diff / 60) . ' minutos';
    if ($diff < 86400) return floor($diff / 3600) . ' horas';
    return floor($diff / 86400) . ' dias';
}

$last_run_ts = '';
$last_run_relative = '';
$last_run_file = __DIR__ . '/last_run.txt';
if (file_exists($last_run_file)) {
    $last_run_ts = trim(file_get_contents($last_run_file));
    $last_run_relative = time_ago($last_run_ts);
}

$source_map = ['remoteok'=>'RemoteOK','wwr'=>'WWR','computrabajo'=>'CompuTrabajo','trabajoorg'=>'TrabajoOrg','occ'=>'OCC','hireline'=>'Hireline'];

function is_new($created_at, $last_run_ts) {
    if (!$last_run_ts || !$created_at) return false;
    $c = DateTime::createFromFormat('Y-m-d H:i:s', substr($created_at, 0, 19));
    $l = DateTime::createFromFormat('Y-m-d H:i:s', substr($last_run_ts, 0, 19));
    return $c && $l && $c >= $l;
}
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

<details>
<summary><strong>Keywords para busqueda (<?= count($active_keywords) ?> activas)</strong></summary>
<div style="margin:10px 0">

<?php if ($msg): ?>
<p><strong><?= $msg ?></strong></p>
<?php endif; ?>

<table border="1" cellpadding="4" cellspacing="0">
  <thead>
    <tr>
      <th>Keyword</th>
      <th>Activa</th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <?php foreach ($keywords_all as $kw): ?>
    <tr>
      <td><?= htmlspecialchars($kw['word']) ?></td>
      <td><?= $kw['active'] ? 'Si' : 'No' ?></td>
      <td>
        <form method="post" action="" style="display:inline">
          <input type="hidden" name="action" value="toggle">
          <input type="hidden" name="id" value="<?= $kw['id'] ?>">
          <button type="submit"><?= $kw['active'] ? 'Desactivar' : 'Activar' ?></button>
        </form>
      </td>
      <td>
        <form method="post" action="" style="display:inline" onsubmit="return confirm('Eliminar keyword?')">
          <input type="hidden" name="action" value="delete">
          <input type="hidden" name="id" value="<?= $kw['id'] ?>">
          <button type="submit">Eliminar</button>
        </form>
      </td>
    </tr>
    <?php endforeach; ?>
  </tbody>
  <tfoot>
    <tr>
      <td colspan="4">
        <form method="post" action="">
          <input type="hidden" name="action" value="add">
          <input type="text" name="word" placeholder="Nueva keyword..." required>
          <button type="submit">Agregar</button>
        </form>
      </td>
    </tr>
  </tfoot>
</table>

<p>Keywords activas:
<?php foreach ($active_keyword_words as $w): ?>
  <a href="?kw=<?= urlencode($w) ?>&d=<?= $days ?>"><?= htmlspecialchars($w) ?></a>&nbsp;
<?php endforeach; ?>
<?php if ($kw_filter): ?>
  | <a href="?d=<?= $days ?>">Limpiar filtro</a>
<?php endif; ?>
</p>
</div>
</details>

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
      <th>Fuente</th>
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
      $src_short = mb_substr($src_label, 0, 5);
      $loc = $j['location'] ?: 'No especificada';
      $tooltip = 'Ubicacion: ' . $loc . ' | Fuente: ' . $src_label;
      $tipo = $j['remote'] ? 'R' : 'P';
      $titulo = $j['title'];
      if (is_new($j['created_at'], $last_run_ts)) $titulo .= ' (N)';
    ?>
    <tr>
      <td><?= htmlspecialchars($src_short) ?></td>
      <td><a href="<?= htmlspecialchars($j['url']) ?>" target="_blank" rel="noopener" title="<?= htmlspecialchars($tooltip) ?>"><?= htmlspecialchars($titulo) ?></a></td>
      <td><?= htmlspecialchars(mb_substr($j['company'] ?: '-', 0, 12)) ?></td>
      <td><?= $j['salary'] ? htmlspecialchars($j['salary']) : '-' ?></td>
      <td><?= $tipo ?></td>
      <td><?= htmlspecialchars(preg_replace('/^hace\s+/i', '', $j['date_posted'] ?: '-')) ?></td>
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
