// Live rep/form readout driven by the /ws WebSocket. The annotated video is a
// plain MJPEG <img>, so this file only handles the data channel + controls.

const $ = (id) => document.getElementById(id);

function render(s) {
  $("reps").textContent = s.reps ?? 0;
  $("phase").textContent = s.phase ?? "—";
  $("knee").textContent = s.knee_angle != null ? `${s.knee_angle}°` : "—";
  $("lean").textContent = s.torso_lean != null ? `${s.torso_lean}°` : "—";
  $("lastrep").textContent = s.last_rep_feedback || "—";
  $("cue").textContent = s.cue || "—";
  document.body.classList.toggle("disconnected", !s.tracking);
}

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const sock = new WebSocket(`${proto}://${location.host}/ws`);
  sock.onmessage = (ev) => render(JSON.parse(ev.data));
  sock.onclose = () => {
    $("cue").textContent = "Disconnected — retrying…";
    document.body.classList.add("disconnected");
    setTimeout(connect, 1000);
  };
}

$("reset").addEventListener("click", () =>
  fetch("/reset", { method: "POST" })
);

$("exercise").addEventListener("change", (e) =>
  fetch(`/exercise/${e.target.value}`, { method: "POST" })
);

connect();
