MISSION_CONTROL_HTML = """<!doctype html>
<html>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>Mission Control</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 24px; max-width: 1200px; }
    .card { border: 1px solid #ddd; border-radius: 12px; padding: 12px; margin: 10px 0; }
    .cols { display:grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .kpis { display:grid; grid-template-columns: repeat(4, minmax(120px,1fr)); gap: 8px; }
    .kpi { border:1px solid #eee; border-radius:10px; padding:8px; background:#fafafa; }
    .ok { color: #0a7d2c; font-weight:700; }
    ul { margin: 6px 0 0 20px; }
    code { background:#f2f2f2; padding:2px 6px; border-radius:6px; }
    textarea, input { width:100%; }
    .task { margin: 6px 0; }
    .tag { display:inline-block; border-radius:999px; padding:2px 8px; font-size:12px; font-weight:600; background:#f1f3f5; }
    .todo { background:#fff3cd; }
    .in_progress { background:#dbeafe; }
    .blocked { background:#ffe4e6; }
    .done { background:#dcfce7; }
    .row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
    button { padding:6px 10px; }
  </style>
</head>
<body>
  <h1>🎯 Mission Control</h1>
  <p><b>PRIVATE</b> — chỉ để sếp Cường xem nội bộ, không public.</p>
  <p><a href='/' style='font-weight:600'>⬅ Quay về AIOS Dashboard</a></p>
  <p id='meta'>Loading...</p>

  <div class='card'>
    <h3>KPI</h3>
    <div id='kpis' class='kpis'></div>
    <div class='row' style='margin-top:8px'>
      <button onclick='generateDailyReport()'>Generate Daily Report</button>
      <span id='report-res' style='color:#444'></span>
    </div>
  </div>

  <div class='cols'>
    <div class='card'><h3>Team</h3><ul id='team'></ul></div>
    <div class='card'><h3>Recent Commits</h3><ul id='commits'></ul></div>
  </div>

  <div class='card'>
    <h3>Sprint Lanes (Kanban-lite)</h3>
    <div id='lanes'></div>
  </div>

  <div class='card'>
    <h3>Blockers</h3>
    <div class='row'>
      <input id='blocker-text' placeholder='Nêu blocker cần xử lý hoặc cần sếp duyệt...' />
      <button onclick='addBlocker()'>Add Blocker</button>
    </div>
    <ul id='blockers'></ul>
  </div>

  <div class='card'><h3>Artifacts (docs)</h3><ul id='artifacts'></ul></div>

  <div class='card'>
    <h3>Mission Notes</h3>
    <textarea id='note' placeholder='Ghi chú tiến độ để xem lại sau...'></textarea>
    <div style='margin-top:8px'>
      <button onclick='addNote()'>Add Note</button>
      <button onclick='refreshMission()'>Refresh</button>
      <span id='note-res' style='margin-left:8px;color:#444'></span>
    </div>
    <ul id='notes'></ul>
  </div>
<script src='/mission-control.js?v=__MC_VER__'></script>
</body>
</html>
"""

MISSION_CONTROL_JS = """
function esc(s){ return String(s || ''); }

async function postJson(url, payload) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(payload || {})
  });
  return await res.json();
}

async function addNote() {
  const noteEl = document.getElementById('note');
  const note = (noteEl.value || '').trim();
  if (!note) return;
  const data = await postJson('/api/mission/note', {note});
  document.getElementById('note-res').textContent = data.ok ? '✅ Saved' : ('⚠️ ' + (data.error || 'failed'));
  if (data.ok) noteEl.value = '';
  await refreshMission();
}

async function setTaskStatus(lane, task, status) {
  const data = await postJson('/api/mission/task-status', {lane, task, status});
  if (!data.ok) alert('Update task failed: ' + (data.error || 'unknown'));
  await refreshMission();
}

async function addBlocker() {
  const el = document.getElementById('blocker-text');
  const text = (el.value || '').trim();
  if (!text) return;
  const data = await postJson('/api/mission/blocker', {action:'add', text});
  if (data.ok) el.value = '';
  await refreshMission();
}

async function resolveBlocker(id) {
  await postJson('/api/mission/blocker', {action:'resolve', id});
  await refreshMission();
}

async function generateDailyReport() {
  const data = await postJson('/api/mission/daily-report', {});
  document.getElementById('report-res').textContent = data.ok ? ('✅ ' + (data.path || 'generated')) : ('⚠️ ' + (data.error || 'failed'));
  await refreshMission();
}

function renderKPIs(kpi) {
  const root = document.getElementById('kpis');
  root.innerHTML = '';
  const cards = [
    ['Tasks Total', kpi.tasks_total],
    ['Done', kpi.done],
    ['In Progress', kpi.in_progress],
    ['Blocked', kpi.blocked],
    ['Todo', kpi.todo],
    ['Notes', kpi.notes],
    ['Blockers', kpi.blockers],
    ['Commits(hint)', kpi.commits_24h_hint],
  ];
  for (const [label, value] of cards) {
    const d = document.createElement('div');
    d.className = 'kpi';
    d.innerHTML = `<div style="font-size:12px;color:#666">${label}</div><div style="font-size:22px;font-weight:700">${value ?? 0}</div>`;
    root.appendChild(d);
  }
}

async function refreshMission() {
  const res = await fetch('/api/mission/status');
  const data = await res.json();
  const st = data.state || {};
  document.getElementById('meta').innerHTML = '<span class="ok">Mission status loaded</span> | Updated: ' + esc(st.updated_at || 'n/a');

  renderKPIs(data.kpi || {});

  const team = document.getElementById('team'); team.innerHTML='';
  for (const t of (st.team || [])) {
    const li = document.createElement('li');
    li.textContent = `${t.name} — ${t.role} [${t.status}]`;
    team.appendChild(li);
  }

  const commits = document.getElementById('commits'); commits.innerHTML='';
  for (const c of (data.commits || [])) {
    const li = document.createElement('li');
    li.innerHTML = '<code>' + esc(c.hash) + '</code> ' + esc(c.subject);
    commits.appendChild(li);
  }

  const lanes = document.getElementById('lanes'); lanes.innerHTML='';
  for (const lane of (st.lanes || [])) {
    const card = document.createElement('div');
    card.className = 'card';
    const h = document.createElement('h4');
    h.textContent = lane.name;
    card.appendChild(h);
    for (const it of (lane.items || [])) {
      const div = document.createElement('div');
      div.className = 'task';
      div.innerHTML = `<span>${esc(it.task)}</span> <span class="tag ${esc(it.status)}">${esc(it.status)}</span>`;

      const row = document.createElement('div');
      row.className = 'row';
      for (const s of ['todo','in_progress','blocked','done']) {
        const b = document.createElement('button');
        b.textContent = s;
        b.onclick = () => setTaskStatus(lane.name, it.task, s);
        row.appendChild(b);
      }
      div.appendChild(row);
      card.appendChild(div);
    }
    lanes.appendChild(card);
  }

  const blockers = document.getElementById('blockers'); blockers.innerHTML='';
  for (const b of (st.blockers || []).slice().reverse()) {
    const li = document.createElement('li');
    li.textContent = `[${esc(b.status)}] ${esc(b.text)}`;
    if (b.status === 'open') {
      const btn = document.createElement('button');
      btn.style.marginLeft = '8px';
      btn.textContent = 'Resolve';
      btn.onclick = () => resolveBlocker(String(b.id || ''));
      li.appendChild(btn);
    }
    blockers.appendChild(li);
  }

  const artifacts = document.getElementById('artifacts'); artifacts.innerHTML='';
  for (const a of (data.artifacts || [])) {
    const li = document.createElement('li');
    li.textContent = `${a.name} (${a.path})`;
    artifacts.appendChild(li);
  }

  const notes = document.getElementById('notes'); notes.innerHTML='';
  for (const n of (st.notes || []).slice().reverse()) {
    const li = document.createElement('li');
    li.textContent = `${n.created_at || ''} — ${n.text || ''}`;
    notes.appendChild(li);
  }
}

refreshMission();
setInterval(refreshMission, 15000);
"""
