"""
Interfaz web minima para probar el recomendador.

Ejecutar:
    python web_app.py
"""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from recommender import recommend_for_profile


HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8000"))


HTML = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Recomendador CEEI</title>
  <style>
    :root {
      color-scheme: light;
      font-family: Arial, Helvetica, sans-serif;
      --ink: #1f2933;
      --muted: #5f6b7a;
      --line: #d8dee8;
      --panel: #ffffff;
      --bg: #f4f7fb;
      --accent: #116466;
      --warn: #9a3412;
      --warn-bg: #fff4e6;
      --ok-bg: #edf7f4;
    }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
    }
    main {
      max-width: 1040px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }
    h1 {
      margin: 0 0 18px;
      font-size: 30px;
      letter-spacing: 0;
    }
    form {
      display: grid;
      gap: 12px;
      margin-bottom: 22px;
    }
    label {
      font-weight: 700;
    }
    textarea {
      min-height: 140px;
      resize: vertical;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 6px;
      font: inherit;
      line-height: 1.45;
      background: #fff;
    }
    button {
      justify-self: start;
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: #fff;
      padding: 11px 16px;
      font-weight: 700;
      cursor: pointer;
    }
    .notice {
      border: 1px solid var(--line);
      border-left: 6px solid var(--accent);
      background: var(--ok-bg);
      padding: 16px;
      margin: 18px 0;
      border-radius: 6px;
    }
    .notice.low {
      border-left-color: var(--warn);
      background: var(--warn-bg);
    }
    .notice h2 {
      margin: 0 0 8px;
      font-size: 20px;
    }
    .notice p {
      margin: 0 0 10px;
      color: var(--muted);
    }
    .notice ul {
      margin: 0;
      padding-left: 22px;
    }
    .list {
      display: grid;
      gap: 10px;
    }
    .item {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 14px;
    }
    .item h3 {
      margin: 0 0 8px;
      font-size: 18px;
      letter-spacing: 0;
    }
    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      color: var(--muted);
      font-size: 14px;
    }
    .tag {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 8px;
      background: #fff;
    }
    a {
      color: var(--accent);
      overflow-wrap: anywhere;
    }
    .vector {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 14px;
      margin: 14px 0 20px;
    }
    .vector h2 {
      margin: 0 0 10px;
      font-size: 18px;
    }
    .vector-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }
    .vector-table th,
    .vector-table td {
      border-top: 1px solid var(--line);
      padding: 8px;
      text-align: left;
    }
    .vector-table th:last-child,
    .vector-table td:last-child {
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
  </style>
</head>
<body>
  <main>
    <h1>Recomendador de contenidos para emprendedores</h1>
    <form id="form">
      <label for="profile">Perfil emprendedor</label>
      <textarea id="profile" name="profile" required>CEO de startup en fase de escalado internacional. Busca financiacion, softlanding, crecimiento comercial, KPIs e internacionalizacion.</textarea>
      <button type="submit">Recomendar</button>
    </form>
    <section id="result"></section>
  </main>
  <script>
    const form = document.querySelector("#form");
    const result = document.querySelector("#result");

    function esc(value) {
      return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
      }[char]));
    }

    function render(data) {
      const isLow = data.status === "low_match_profile";
      const title = isLow ? "Baja coincidencia con el corpus" : "Recomendaciones";
      const label = isLow ? "Recomendaciones exploratorias" : "Documentos recomendados";
      const suggestions = (data.suggestions || []).map(item => `<li>${esc(item)}</li>`).join("");
      const profileVectorRows = (data.profile_vector || []).map(item => `
        <tr>
          <td>${esc(item.term)}</td>
          <td>${esc(item.weight)}</td>
        </tr>`).join("");
      const profileVector = `
        <section class="vector">
          <h2>Vector TF-IDF del perfil emprendedor</h2>
          ${profileVectorRows ? `
            <table class="vector-table">
              <thead>
                <tr>
                  <th>Término</th>
                  <th>Peso</th>
                </tr>
              </thead>
              <tbody>${profileVectorRows}</tbody>
            </table>` : "<p>No hay vector para mostrar.</p>"}
        </section>`;
      const notice = `
        <div class="notice ${isLow ? "low" : ""}">
          <h2>${title}</h2>
          <p>${esc(data.message || `Mejor score: ${data.max_score}`)}</p>
          ${suggestions ? `<ul>${suggestions}</ul>` : ""}
        </div>`;
      const items = (data.recommendations || []).map(item => `
        <article class="item">
          <h3>${esc(item.title || item.document_id)}</h3>
          <div class="meta">
            <span class="tag">score ${esc(item.score)}</span>
            <span class="tag">${esc(item.confidence_level)}</span>
            ${item.recommendation_type ? `<span class="tag">${esc(label)}</span>` : ""}
          </div>
          ${item.url ? `<p><a href="${esc(item.url)}" target="_blank" rel="noreferrer">${esc(item.url)}</a></p>` : ""}
        </article>`).join("");
      result.innerHTML = `${notice}${profileVector}<h2>${label}</h2><div class="list">${items || "<p>No hay documentos para mostrar.</p>"}</div>`;
    }

    form.addEventListener("submit", async event => {
      event.preventDefault();
      result.innerHTML = "<p>Calculando recomendaciones...</p>";
      const body = new URLSearchParams(new FormData(form));
      const response = await fetch("/recommend", { method: "POST", body });
      render(await response.json());
    });
  </script>
</body>
</html>
"""


class RecommenderHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path != "/":
            self.send_error(404)
            return

        self._send_html(HTML)

    def do_POST(self) -> None:
        if self.path != "/recommend":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        profile_text = parse_qs(body).get("profile", [""])[0]
        response = recommend_for_profile(profile_text)
        self._send_json(response)

    def _send_html(self, html: str) -> None:
        encoded = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, payload: dict) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    server = ThreadingHTTPServer((HOST, args.port), RecommenderHandler)
    print(f"Interfaz web disponible en http://{HOST}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
