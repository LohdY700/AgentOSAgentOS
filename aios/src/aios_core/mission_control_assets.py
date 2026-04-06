MISSION_CONTROL_HTML = """<!doctype html>
<html>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>Mission Control</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 24px; max-width: 1100px; }
    .card { border: 1px solid #ddd; border-radius: 12px; padding: 12px; margin: 10px 0; }
    .cols { display:grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .ok { color: #0a7d2c; font-weight:700; }
    ul { margin: 6px 0 0 20px; }
    code { background:#f2f2f2; padding:2px 6px; border-radius:6px; }
    textarea { width:100%; min-height:70px; }
  </style>
</head>
<body>
  <h1>🎯 Mission Control</h1>
  <p><b>PRIVATE</b> — chỉ để sếp Cường xem nội bộ, không public.</p>
  <p><a href='/' style='font-weight:600'>⬅ Quay về AIOS Dashboard</a></p>
  <p id='meta'>Loading...</p>
  <div class='cols'>
    <div class='card'><h3>Team</h3><ul id='team'></ul></div>
    <div class='card'><h3>Recent Commits</h3><ul id='commits'></ul></div>
  </div>
  <div class='card'><h3>Sprint Lanes</h3><div id='lanes'></div></div>
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
<script src='/mission-control.js'></script>
</body>
</html>
"""

MISSION_CONTROL_JS = """
function esc(s){ return String(s || ''); }

async function addNote() {
  const noteEl = document.getElementById('note');
  const note = (noteEl.value || '').trim();
  if (!note) return;
  const res = await fetch('/api/mission/note', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({note})
  });
  const data = await res.json();
  document.getElementById('note-res').textContent = data.ok ? '✅ Saved' : ('⚠️ ' + (data.error || 'failed'));
  if (data.ok) noteEl.value = '';
  await refreshMission();
}

async function refreshMission() {
  const res = await fetch('/api/mission/status');
  const data = await res.json();
  const st = data.state || {};
  document.getElementById('meta').innerHTML = '<span class="ok">Mission status loaded</span> | Updated: ' + esc(st.updated_at || 'n/a');

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
    const ul = document.createElement('ul');
    for (const it of (lane.items || [])) {
      const li = document.createElement('li');
      li.textContent = `${it.task} [${it.status}]`;
      ul.appendChild(li);
    }
    card.appendChild(ul);
    lanes.appendChild(card);
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
