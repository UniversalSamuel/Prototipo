"""
Painel de Gestao a Vista - P&D Univel

Servidor web local (Flask) que mostra o quadro de acompanhamento das atividades,
com botao de gravacao de audio e caixa de anotacao por texto direto na tela.

Uso:
    pythonw.exe dashboard.py

Se ja houver um servidor rodando nesta porta, so abre o navegador nele (nao
inicia um segundo servidor). Isso permite usar o mesmo comando tanto no
agendamento de logon do Windows quanto no atalho da area de trabalho.

Nao depende do Claude Code estar aberto para capturar audio/anotacoes - so o
processamento (transcricao, classificacao, registro, envio) acontece depois,
quando uma sessao do Claude Code processar as pastas 'pendentes' e
'pendentes_texto' (ver CLAUDE.md, secao "Etapa 0").
"""

import os
import socket
import sqlite3
import sys
import threading
import webbrowser
from datetime import datetime

from flask import Flask, jsonify, redirect, render_template_string, request

import gravar_atividade as gravador

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_DIR, "atividades_pd.db")
PENDENTES_TEXTO_DIR = os.path.join(PROJECT_DIR, "pendentes_texto")
PENDENTES_AUDIO_DIR = os.path.join(PROJECT_DIR, "pendentes")
PORT = 8765

app = Flask(__name__)

STATUS_ORDER = ["Aguardando prazo", "Em andamento", "Cobrança enviada", "Concluído"]
STATUS_CLASS = {
    "Aguardando prazo": "waiting",
    "Em andamento": "progress",
    "Cobrança enviada": "overdue",
    "Concluído": "done",
}


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def pendentes_count():
    audio = len([f for f in os.listdir(PENDENTES_AUDIO_DIR) if f.lower().endswith(".wav")]) \
        if os.path.isdir(PENDENTES_AUDIO_DIR) else 0
    texto = len([f for f in os.listdir(PENDENTES_TEXTO_DIR) if f.lower().endswith(".txt")]) \
        if os.path.isdir(PENDENTES_TEXTO_DIR) else 0
    return audio, texto


BASE_CSS = """
:root {
  --bg: #f4f1ea; --bg-soft: #ece7dc; --surface: #ffffff;
  --ink: #26221b; --ink-dim: #6b6255; --line: #ddd5c4;
  --accent: #a8552a; --accent-ink: #ffffff;
  --waiting: #b8862a; --waiting-bg: #f7ecd6;
  --progress: #3c6e9e; --progress-bg: #e3edf5;
  --overdue: #b23f34; --overdue-bg: #f6e2df;
  --done: #4b7d5c; --done-bg: #e4efe6;
  --shadow: 0 1px 2px rgba(38,34,27,.06), 0 6px 16px -8px rgba(38,34,27,.18);
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1a1712; --bg-soft: #211d17; --surface: #24201a;
    --ink: #ece6d9; --ink-dim: #a89d8a; --line: #3a3428;
    --accent: #d98552; --accent-ink: #241206;
    --waiting: #e0b054; --waiting-bg: #332a17;
    --progress: #7db0e8; --progress-bg: #1c2c3a;
    --overdue: #e2796c; --overdue-bg: #3a211d;
    --done: #7fbf97; --done-bg: #1e2f22;
    --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 20px -10px rgba(0,0,0,.5);
  }
}
:root[data-theme="dark"] {
  --bg: #1a1712; --bg-soft: #211d17; --surface: #24201a;
  --ink: #ece6d9; --ink-dim: #a89d8a; --line: #3a3428;
  --accent: #d98552; --accent-ink: #241206;
  --waiting: #e0b054; --waiting-bg: #332a17;
  --progress: #7db0e8; --progress-bg: #1c2c3a;
  --overdue: #e2796c; --overdue-bg: #3a211d;
  --done: #7fbf97; --done-bg: #1e2f22;
  --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 20px -10px rgba(0,0,0,.5);
}
:root[data-theme="light"] {
  --bg: #f4f1ea; --bg-soft: #ece7dc; --surface: #ffffff;
  --ink: #26221b; --ink-dim: #6b6255; --line: #ddd5c4;
  --accent: #a8552a; --accent-ink: #ffffff;
  --waiting: #b8862a; --waiting-bg: #f7ecd6;
  --progress: #3c6e9e; --progress-bg: #e3edf5;
  --overdue: #b23f34; --overdue-bg: #f6e2df;
  --done: #4b7d5c; --done-bg: #e4efe6;
  --shadow: 0 1px 2px rgba(38,34,27,.06), 0 6px 16px -8px rgba(38,34,27,.18);
}
* { box-sizing: border-box; }
html, body { height: 100%; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font-family: "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif;
  font-size: 15px; line-height: 1.45;
}
.wrap { max-width: 1180px; margin: 0 auto; padding: 32px 28px 64px; }
a { color: var(--accent); }
header.board-head {
  display: flex; align-items: flex-end; justify-content: space-between;
  gap: 24px; flex-wrap: wrap; padding-bottom: 18px;
  border-bottom: 2px solid var(--line); margin-bottom: 24px;
}
.eyebrow {
  text-transform: uppercase; letter-spacing: .14em; font-size: 11.5px;
  font-weight: 600; color: var(--accent); margin: 0 0 6px;
}
h1 {
  font-family: "Bahnschrift", "Arial Narrow", "Segoe UI Semibold", sans-serif;
  font-weight: 700; font-stretch: condensed; letter-spacing: .01em;
  font-size: clamp(26px, 4vw, 38px); margin: 0; text-wrap: balance;
}
.meta { text-align: right; color: var(--ink-dim); font-size: 13px; }
.meta strong {
  display: block; color: var(--ink); font-family: "Cascadia Code","Consolas",ui-monospace,monospace;
  font-size: 14px; font-variant-numeric: tabular-nums;
}
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px,1fr)); gap: 12px; margin-bottom: 22px; }
.stat { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; box-shadow: var(--shadow); }
.stat .n { font-family: "Cascadia Code","Consolas",ui-monospace,monospace; font-variant-numeric: tabular-nums; font-size: 26px; font-weight: 600; line-height: 1; }
.stat .l { margin-top: 6px; font-size: 12px; color: var(--ink-dim); text-transform: uppercase; letter-spacing: .06em; }
.stat.acc-waiting .n { color: var(--waiting); }
.stat.acc-progress .n { color: var(--progress); }
.stat.acc-overdue .n { color: var(--overdue); }
.stat.acc-done .n { color: var(--done); }

.panel {
  background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
  padding: 16px 18px; margin-bottom: 22px; box-shadow: var(--shadow);
}
.panel h2 {
  font-family: "Bahnschrift", "Arial Narrow", sans-serif; font-stretch: condensed;
  font-size: 15px; text-transform: uppercase; letter-spacing: .05em; margin: 0 0 12px; color: var(--ink);
}
.capture-row { display: flex; gap: 18px; flex-wrap: wrap; }
.capture-col { flex: 1 1 260px; min-width: 240px; }

.rec-btn {
  display: flex; align-items: center; gap: 10px; width: 100%;
  border: 1px solid var(--line); background: var(--bg-soft); color: var(--ink);
  border-radius: 10px; padding: 14px 16px; font-size: 14px; font-weight: 600;
  cursor: pointer; transition: background .15s ease, border-color .15s ease;
}
.rec-btn:hover { border-color: var(--accent); }
.rec-btn .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--ink-dim); flex: none; }
.rec-btn.recording { background: var(--overdue-bg); border-color: var(--overdue); color: var(--overdue); }
.rec-btn.recording .dot { background: var(--overdue); animation: pulse 1.2s ease-in-out infinite; }
@media (prefers-reduced-motion: reduce) { .rec-btn.recording .dot { animation: none; } }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .3; } }
.rec-hint { margin-top: 8px; font-size: 12px; color: var(--ink-dim); }

textarea.note {
  width: 100%; min-height: 84px; resize: vertical; border: 1px solid var(--line);
  border-radius: 10px; padding: 10px 12px; font-family: inherit; font-size: 13.5px;
  background: var(--bg-soft); color: var(--ink);
}
textarea.note:focus { outline: 2px solid var(--accent); outline-offset: 1px; }
.note-btn {
  margin-top: 8px; border: none; background: var(--accent); color: var(--accent-ink);
  border-radius: 8px; padding: 9px 16px; font-size: 13px; font-weight: 600; cursor: pointer;
}
.note-btn:hover { filter: brightness(1.06); }
.note-status { margin-top: 8px; font-size: 12.5px; color: var(--ink-dim); min-height: 1.2em; }
.note-status.ok { color: var(--done); }

.notice {
  display: flex; align-items: center; gap: 12px; background: var(--bg-soft);
  border: 1px dashed var(--line); border-radius: 10px; padding: 12px 16px;
  margin-bottom: 22px; font-size: 13.5px; color: var(--ink-dim);
}
.notice .idot { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); flex: none; animation: pulse 2.4s ease-in-out infinite; }
.notice strong { color: var(--ink); font-weight: 600; }

.filters { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 22px; }
.pill {
  display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; font-weight: 600;
  padding: 6px 12px; border-radius: 20px; background: var(--surface); border: 1px solid var(--line);
  color: var(--ink); text-decoration: none;
}
.pill:hover { border-color: var(--accent); }
.pill.active { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); }

.board { display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; align-items: start; }
@media (max-width: 900px) { .board { grid-template-columns: repeat(2,1fr); } }
@media (max-width: 560px) { .board { grid-template-columns: 1fr; } }
.col { background: var(--bg-soft); border: 1px solid var(--line); border-radius: 12px; padding: 14px; min-height: 160px; display: flex; flex-direction: column; gap: 12px; }
.col-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.col-title { font-size: 12.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; }
.col-count { font-family: "Cascadia Code","Consolas",ui-monospace,monospace; font-size: 12px; font-variant-numeric: tabular-nums; background: var(--surface); border: 1px solid var(--line); border-radius: 20px; min-width: 22px; text-align: center; padding: 1px 7px; }
.col-waiting { border-top: 3px solid var(--waiting); } .col-waiting .col-title { color: var(--waiting); }
.col-progress { border-top: 3px solid var(--progress); } .col-progress .col-title { color: var(--progress); }
.col-overdue { border-top: 3px solid var(--overdue); } .col-overdue .col-title { color: var(--overdue); }
.col-done { border-top: 3px solid var(--done); } .col-done .col-title { color: var(--done); }

.card { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 13px 14px; box-shadow: var(--shadow); }
.card-title { font-size: 14px; font-weight: 600; margin: 0 0 10px; line-height: 1.35; }
.card-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-size: 12.5px; color: var(--ink-dim); }
.card-row + .card-row { margin-top: 7px; }
.who { display: flex; align-items: center; gap: 7px; color: var(--ink); font-weight: 600; }
.avatar { width: 20px; height: 20px; border-radius: 50%; background: var(--accent); color: var(--accent-ink); font-size: 10px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none; }
.badge { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 20px; white-space: nowrap; }
.badge-outlook { background: var(--progress-bg); color: var(--progress); }
.badge-teams { background: var(--waiting-bg); color: var(--waiting); }
.due { font-family: "Cascadia Code","Consolas",ui-monospace,monospace; font-variant-numeric: tabular-nums; }
.due.today, .due.late { color: var(--overdue); font-weight: 700; }
.flag-urgent { display: inline-flex; align-items: center; gap: 4px; font-size: 10.5px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; color: var(--overdue); background: var(--overdue-bg); padding: 2px 7px; border-radius: 20px; margin-top: 9px; }
.flag-urgent::before { content: "\\25CF"; font-size: 8px; }
.done-btn {
  display: block; width: 100%; margin-top: 10px; border: 1px solid var(--line);
  background: var(--bg-soft); color: var(--ink-dim); border-radius: 8px;
  padding: 7px 10px; font-size: 11.5px; font-weight: 600; cursor: pointer;
}
.done-btn:hover { border-color: var(--done); color: var(--done); background: var(--done-bg); }
.done-btn:disabled { opacity: .5; cursor: default; }
.empty { color: var(--ink-dim); font-size: 12.5px; text-align: center; padding: 22px 8px; border: 1px dashed var(--line); border-radius: 10px; }

table.hist { width: 100%; border-collapse: collapse; font-size: 13px; }
table.hist th { text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--ink-dim); padding: 6px 10px; border-bottom: 1px solid var(--line); }
table.hist td { padding: 9px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
table.hist tr:last-child td { border-bottom: none; }
.status-pill { display: inline-block; font-size: 11px; font-weight: 700; padding: 2px 9px; border-radius: 20px; white-space: nowrap; }
.status-pill.waiting { background: var(--waiting-bg); color: var(--waiting); }
.status-pill.progress { background: var(--progress-bg); color: var(--progress); }
.status-pill.overdue { background: var(--overdue-bg); color: var(--overdue); }
.status-pill.done { background: var(--done-bg); color: var(--done); }
.overflow { overflow-x: auto; }

footer { margin-top: 28px; padding-top: 16px; border-top: 1px solid var(--line); font-size: 12px; color: var(--ink-dim); display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
footer code { font-family: "Cascadia Code","Consolas",ui-monospace,monospace; background: var(--bg-soft); padding: 1px 6px; border-radius: 4px; }
"""

PAGE_HEAD_JS = """
async function toggleRec() {
  const btn = document.getElementById('recBtn');
  const label = document.getElementById('recLabel');
  const hint = document.getElementById('recHint');
  const recording = btn.classList.contains('recording');
  const url = recording ? '/api/gravar/parar' : '/api/gravar/iniciar';
  btn.disabled = true;
  try {
    const res = await fetch(url, { method: 'POST' });
    const data = await res.json();
    btn.classList.toggle('recording', data.gravando);
    label.textContent = data.gravando ? 'Gravando... clique para parar' : 'Gravar atividade';
    hint.textContent = data.gravando
      ? 'Fale a atividade e para quem e. Clique de novo para salvar.'
      : (data.salvo ? 'Gravacao salva em pendentes/.' : 'Primeiro clique inicia a gravacao.');
  } catch (e) {
    hint.textContent = 'Erro ao falar com o painel: ' + e;
  } finally {
    btn.disabled = false;
  }
}
async function enviarAnotacao() {
  const ta = document.getElementById('noteText');
  const status = document.getElementById('noteStatus');
  const texto = ta.value.trim();
  if (!texto) { status.textContent = 'Escreva a anotacao antes de registrar.'; status.className = 'note-status'; return; }
  try {
    const res = await fetch('/api/anotacao', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({texto: texto})
    });
    const data = await res.json();
    if (data.ok) {
      ta.value = '';
      status.textContent = 'Anotacao registrada - sera confirmada com voce na proxima checagem.';
      status.className = 'note-status ok';
    } else {
      status.textContent = 'Erro ao registrar: ' + (data.erro || 'desconhecido');
      status.className = 'note-status';
    }
  } catch (e) {
    status.textContent = 'Erro ao falar com o painel: ' + e;
    status.className = 'note-status';
  }
}
async function marcarConcluido(id, btn) {
  if (!confirm('Marcar esta atividade como concluída?')) return;
  btn.disabled = true;
  btn.textContent = 'Salvando...';
  try {
    const res = await fetch('/api/concluir/' + id, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      window.location.reload();
    } else {
      btn.textContent = 'Erro - tentar de novo';
      btn.disabled = false;
    }
  } catch (e) {
    btn.textContent = 'Erro - tentar de novo';
    btn.disabled = false;
  }
}
async function pollRec() {
  try {
    const res = await fetch('/api/gravar/status');
    const data = await res.json();
    const btn = document.getElementById('recBtn');
    const label = document.getElementById('recLabel');
    if (btn && !btn.disabled) {
      btn.classList.toggle('recording', data.gravando);
      label.textContent = data.gravando ? 'Gravando... clique para parar' : 'Gravar atividade';
    }
  } catch (e) { /* silencioso */ }
}
setInterval(pollRec, 4000);
setInterval(() => {
  const ta = document.getElementById('noteText');
  const btn = document.getElementById('recBtn');
  const editing = ta && document.activeElement === ta;
  const recording = btn && btn.classList.contains('recording');
  if (!editing && !recording) { window.location.reload(); }
}, 90000);
"""

DASHBOARD_TEMPLATE = """
<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painel P&D Univel</title>
<style>{{ css|safe }}</style>
</head>
<body>
<div class="wrap">
  <header class="board-head">
    <div>
      <p class="eyebrow">P&amp;D &middot; Univel</p>
      <h1>Painel de Gestão à Vista</h1>
    </div>
    <div class="meta">atualizado em<strong>{{ agora }}</strong></div>
  </header>

  <div class="stats">
    <div class="stat acc-waiting"><div class="n">{{ counts['Aguardando prazo'] }}</div><div class="l">Aguardando prazo</div></div>
    <div class="stat acc-progress"><div class="n">{{ counts['Em andamento'] }}</div><div class="l">Em andamento</div></div>
    <div class="stat acc-overdue"><div class="n">{{ counts['Cobrança enviada'] }}</div><div class="l">Cobrança enviada</div></div>
    <div class="stat acc-done"><div class="n">{{ counts['Concluído'] }}</div><div class="l">Concluído</div></div>
  </div>

  {% if pend_audio or pend_texto %}
  <div class="notice">
    <span class="idot"></span>
    <span>
      {% if pend_audio %}<strong>{{ pend_audio }}</strong> gravação(ões) de áudio{% endif %}
      {% if pend_audio and pend_texto %} e {% endif %}
      {% if pend_texto %}<strong>{{ pend_texto }}</strong> anotação(ões) por texto{% endif %}
      aguardando a próxima checagem para virar atividade registrada.
    </span>
  </div>
  {% endif %}

  <div class="panel">
    <h2>Nova anotação</h2>
    <div class="capture-row">
      <div class="capture-col">
        <button id="recBtn" class="rec-btn" onclick="toggleRec()">
          <span class="dot"></span>
          <span id="recLabel">Gravar atividade</span>
        </button>
        <div id="recHint" class="rec-hint">Clique para começar a falar; clique de novo para salvar.</div>
      </div>
      <div class="capture-col" style="flex: 2 1 380px;">
        <textarea id="noteText" class="note" placeholder="Ex: Bruno. Fazer o resumo do eixo, definir prazo."></textarea>
        <button class="note-btn" onclick="enviarAnotacao()">Registrar anotação</button>
        <div id="noteStatus" class="note-status"></div>
      </div>
    </div>
  </div>

  <div class="filters">
    <a class="pill {{ 'active' if not colaborador else '' }}" href="/">Todos</a>
    {% for nome in colaboradores %}
    <a class="pill {{ 'active' if colaborador == nome else '' }}" href="/colaborador/{{ nome }}">{{ nome }}</a>
    {% endfor %}
  </div>

  <div class="board">
    {% for status in status_order %}
    <section class="col col-{{ status_class[status] }}">
      <div class="col-head">
        <span class="col-title">{{ status }}</span>
        <span class="col-count">{{ grouped[status]|length }}</span>
      </div>
      {% if grouped[status] %}
        {% for a in grouped[status] %}
        <article class="card">
          <p class="card-title">{{ a['titulo'] }}</p>
          <div class="card-row">
            <span class="who"><span class="avatar">{{ a['colaborador'][0]|upper }}</span>{{ a['colaborador'] }}</span>
            <span class="badge badge-{{ 'outlook' if a['canal_usado'] == 'Outlook' else 'teams' }}">{{ a['canal_usado'] or '—' }}</span>
          </div>
          <div class="card-row">
            <span>anotado {{ a['data_anotacao'] }}</span>
            {% if a['prazo_combinado'] %}
              <span class="due {{ 'late' if a['atrasado'] else ('today' if a['vence_hoje'] else '') }}">
                {{ 'venceu' if a['atrasado'] else ('vence hoje' if a['vence_hoje'] else 'prazo') }} · {{ a['prazo_combinado'] }}
              </span>
            {% else %}
              <span class="due">sem prazo ainda</span>
            {% endif %}
          </div>
          {% if a['urgencia_detectada'] == 'Sim' %}<span class="flag-urgent">Urgente</span>{% endif %}
          {% if status != 'Concluído' %}
          <button class="done-btn" onclick="marcarConcluido({{ a['id'] }}, this)">Marcar concluído</button>
          {% endif %}
        </article>
        {% endfor %}
      {% else %}
        <div class="empty">Nada aqui</div>
      {% endif %}
    </section>
    {% endfor %}
  </div>

  <footer>
    <span>Fonte: <code>atividades_pd.db</code></span>
    <span>{{ total }} registro(s) no total</span>
  </footer>
</div>
<script>{{ js|safe }}</script>
</body>
</html>
"""

COLABORADOR_TEMPLATE = """
<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ nome }} — Painel P&D Univel</title>
<style>{{ css|safe }}</style>
</head>
<body>
<div class="wrap">
  <header class="board-head">
    <div>
      <p class="eyebrow">P&amp;D &middot; Univel</p>
      <h1>{{ nome }}</h1>
    </div>
    <div class="meta"><a href="/">&larr; voltar ao painel</a></div>
  </header>

  <div class="stats">
    <div class="stat"><div class="n">{{ itens|length }}</div><div class="l">Total</div></div>
    <div class="stat acc-done"><div class="n">{{ concluidos }}</div><div class="l">Concluídos</div></div>
    <div class="stat acc-overdue"><div class="n">{{ atrasados }}</div><div class="l">Em atraso</div></div>
    <div class="stat acc-progress"><div class="n">{{ abertos }}</div><div class="l">Em aberto</div></div>
  </div>

  <div class="panel">
    <h2>Histórico completo</h2>
    <div class="overflow">
    <table class="hist">
      <thead>
        <tr><th>Atividade</th><th>Status</th><th>Anotado em</th><th>Prazo</th><th>Concluído em</th><th>Tempo de execução</th><th></th></tr>
      </thead>
      <tbody>
        {% for a in itens %}
        <tr>
          <td>{{ a['titulo'] }}</td>
          <td><span class="status-pill {{ status_class[a['status']] }}">{{ a['status'] }}</span></td>
          <td>{{ a['data_anotacao'] }}</td>
          <td>{% if a['prazo_combinado'] %}<span class="{{ 'due late' if a['atrasado'] else 'due' }}">{{ a['prazo_combinado'] }}</span>{% else %}—{% endif %}</td>
          <td>{{ a['concluido_em'] or '—' }}</td>
          <td>{{ a['tempo_execucao'] }}</td>
          <td>{% if a['status'] != 'Concluído' %}<button class="done-btn" style="margin-top:0;" onclick="marcarConcluido({{ a['id'] }}, this)">Marcar concluído</button>{% endif %}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    </div>
  </div>

  <script>{{ js|safe }}</script>
  <footer>
    <span>Fonte: <code>atividades_pd.db</code></span>
    <span>{{ itens|length }} registro(s) de {{ nome }}</span>
  </footer>
</div>
</body>
</html>
"""


def _parse_date(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _annotate(rows):
    hoje = datetime.now().date()
    out = []
    for r in rows:
        a = dict(r)
        prazo = _parse_date(a.get("prazo_combinado"))
        a["atrasado"] = bool(prazo and prazo.date() < hoje and a["status"] not in ("Concluído",))
        a["vence_hoje"] = bool(prazo and prazo.date() == hoje and not a["atrasado"])
        out.append(a)
    return out


@app.route("/")
def index():
    conn = db()
    rows = _annotate(conn.execute("SELECT * FROM atividades_pd ORDER BY data_anotacao DESC").fetchall())
    conn.close()

    grouped = {s: [] for s in STATUS_ORDER}
    for a in rows:
        grouped.setdefault(a["status"], []).append(a)
    counts = {s: len(grouped.get(s, [])) for s in STATUS_ORDER}
    colaboradores = sorted({a["colaborador"] for a in rows})
    pend_audio, pend_texto = pendentes_count()

    return render_template_string(
        DASHBOARD_TEMPLATE, css=BASE_CSS, js=PAGE_HEAD_JS,
        agora=datetime.now().strftime("%d/%m/%Y · %H:%M"),
        counts=counts, grouped=grouped, status_order=STATUS_ORDER,
        status_class=STATUS_CLASS, colaboradores=colaboradores,
        colaborador=None, total=len(rows),
        pend_audio=pend_audio, pend_texto=pend_texto,
    )


@app.route("/colaborador/<nome>")
def colaborador(nome):
    conn = db()
    rows = _annotate(conn.execute(
        "SELECT * FROM atividades_pd WHERE colaborador = ? ORDER BY data_anotacao DESC", (nome,)
    ).fetchall())
    conn.close()

    for a in rows:
        inicio = _parse_date(a.get("data_anotacao"))
        if a["status"] == "Concluído" and a.get("concluido_em") and inicio:
            fim = _parse_date(a["concluido_em"])
            dias = (fim - inicio).days if fim else None
            a["tempo_execucao"] = f"{dias} dia(s)" if dias is not None else "—"
        elif inicio:
            dias = (datetime.now() - inicio).days
            a["tempo_execucao"] = f"{dias} dia(s) em aberto"
        else:
            a["tempo_execucao"] = "—"

    concluidos = sum(1 for a in rows if a["status"] == "Concluído")
    atrasados = sum(1 for a in rows if a["atrasado"])
    abertos = sum(1 for a in rows if a["status"] != "Concluído")

    return render_template_string(
        COLABORADOR_TEMPLATE, css=BASE_CSS, js=PAGE_HEAD_JS, nome=nome, itens=rows,
        status_class=STATUS_CLASS, concluidos=concluidos, atrasados=atrasados, abertos=abertos,
    )


@app.route("/api/concluir/<int:atividade_id>", methods=["POST"])
def api_concluir(atividade_id):
    conn = db()
    row = conn.execute("SELECT id FROM atividades_pd WHERE id = ?", (atividade_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify(ok=False, erro="atividade não encontrada"), 404
    conn.execute(
        "UPDATE atividades_pd SET status = 'Concluído', concluido_em = ? WHERE id = ?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), atividade_id),
    )
    conn.commit()
    conn.close()
    return jsonify(ok=True)


@app.route("/api/gravar/iniciar", methods=["POST"])
def api_gravar_iniciar():
    if gravador.is_recording():
        return jsonify(gravando=True)
    t = threading.Thread(target=gravador.start_recording, daemon=True)
    t.start()
    return jsonify(gravando=True)


@app.route("/api/gravar/parar", methods=["POST"])
def api_gravar_parar():
    if gravador.is_recording():
        gravador.signal_stop()
        return jsonify(gravando=False, salvo=True)
    return jsonify(gravando=False, salvo=False)


@app.route("/api/gravar/status")
def api_gravar_status():
    return jsonify(gravando=gravador.is_recording())


@app.route("/api/anotacao", methods=["POST"])
def api_anotacao():
    data = request.get_json(silent=True) or {}
    texto = (data.get("texto") or "").strip()
    if not texto:
        return jsonify(ok=False, erro="texto vazio"), 400
    os.makedirs(PENDENTES_TEXTO_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    path = os.path.join(PENDENTES_TEXTO_DIR, f"{timestamp}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(texto)
    return jsonify(ok=True)


def _server_running():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


if __name__ == "__main__":
    url = f"http://127.0.0.1:{PORT}/"
    if _server_running():
        webbrowser.open(url)
        sys.exit(0)

    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=PORT, debug=False)
