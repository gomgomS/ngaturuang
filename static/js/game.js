(() => {
  const cfg = window.__GAME_CONFIG__ || {};
  const name = cfg.name || "Player";
  const canvas = document.getElementById("gameCanvas");
  const ctx = canvas.getContext("2d");
  const playersListEl = document.getElementById("playersList");
  const chatLogEl = document.getElementById("chatLog");
  const chatFormEl = document.getElementById("chatForm");
  const chatInputEl = document.getElementById("chatInput");

  const pressed = new Set();
  let selfId = null;
  const players = new Map(); // id -> {id, name, x, y, color, spriteUrl}
  const spriteCache = new Map(); // url -> {img, ok}

  const socket = io({
    query: { name }
  });

  socket.on("connect", () => {
    addSystemMessage(`Connected as ${name}`);
  });

  socket.on("server_error", (payload) => {
    const msg = payload && payload.message ? payload.message : "Unknown error";
    alert(msg);
    window.location.href = "/";
  });

  socket.on("init_state", (state) => {
    selfId = state.selfId;
    players.clear();
    for (const p of state.players || []) {
      players.set(p.id, { ...p });
      ensureSpriteLoaded(p.spriteUrl);
    }
    renderSidebar();
  });

  socket.on("player_joined", (p) => {
    players.set(p.id, p);
    ensureSpriteLoaded(p.spriteUrl);
    addSystemMessage(`${p.name} joined`);
    renderSidebar();
  });

  socket.on("player_left", ({ id }) => {
    const p = players.get(id);
    if (p) addSystemMessage(`${p.name} left`);
    players.delete(id);
    renderSidebar();
  });

  socket.on("player_moved", ({ id, x, y }) => {
    const p = players.get(id);
    if (p) {
      p.x = x;
      p.y = y;
    }
  });

  socket.on("chat", ({ from, text }) => {
    addChatMessage(from, text);
  });

  function addSystemMessage(text) {
    const div = document.createElement("div");
    div.className = "msg system";
    div.textContent = text;
    chatLogEl.appendChild(div);
    chatLogEl.scrollTop = chatLogEl.scrollHeight;
  }

  function addChatMessage(from, text) {
    const div = document.createElement("div");
    div.className = "msg";
    const strong = document.createElement("strong");
    strong.textContent = from + ": ";
    div.appendChild(strong);
    div.appendChild(document.createTextNode(text));
    chatLogEl.appendChild(div);
    chatLogEl.scrollTop = chatLogEl.scrollHeight;
  }

  chatFormEl.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = chatInputEl.value.trim();
    if (!text) return;
    socket.emit("chat", { text });
    chatInputEl.value = "";
  });

  function renderSidebar() {
    playersListEl.innerHTML = "";
    const sorted = Array.from(players.values()).sort((a, b) => a.name.localeCompare(b.name));
    for (const p of sorted) {
      const li = document.createElement("li");
      li.textContent = p.name + (p.id === selfId ? " (you)" : "");
      li.style.setProperty("--dot-color", p.color);
      li.className = "player-item";
      playersListEl.appendChild(li);
    }
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    // Draw border
    ctx.strokeStyle = "#ddd";
    ctx.strokeRect(0.5, 0.5, canvas.width - 1, canvas.height - 1);

    // Draw players
    for (const p of players.values()) {
      drawPlayer(p);
    }
    requestAnimationFrame(draw);
  }

  function ensureSpriteLoaded(url) {
    if (!url || spriteCache.has(url)) return;
    const img = new Image();
    img.onload = () => spriteCache.set(url, { img, ok: true });
    img.onerror = () => spriteCache.set(url, { img: null, ok: false });
    img.src = url;
  }

  function drawPlayer(p) {
    const r = 14;
    const sprite = p.spriteUrl ? spriteCache.get(p.spriteUrl) : null;
    ctx.font = "12px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";

    if (sprite && sprite.ok && sprite.img) {
      const size = 36;
      ctx.drawImage(sprite.img, p.x - size/2, p.y - size/2, size, size);
      ctx.fillStyle = "#111";
      ctx.fillText(p.name, p.x, p.y - r - 4);
      return;
    }

    // Stick figure drawing (head, body, arms, legs, hands, feet)
    const outline = p.id === selfId ? "#222" : "#555";
    const bodyColor = p.color || "#6b7280";

    const headRadius = Math.round(r * 0.8); // ~11
    const neckY = p.y - Math.round(r * 0.3);
    const headCenterY = neckY - headRadius;
    const hipY = p.y + Math.round(r * 0.9);
    const shoulderY = neckY + Math.round(r * 0.15);

    const armLen = Math.round(r * 1.4);
    const legLen = Math.round(r * 1.8);
    const handRadius = Math.max(2, Math.round(r * 0.25));
    const footLen = Math.max(4, Math.round(r * 0.6));

    // Head (filled with player color, outlined)
    ctx.beginPath();
    ctx.arc(p.x, headCenterY, headRadius, 0, Math.PI * 2);
    ctx.fillStyle = bodyColor;
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = outline;
    ctx.stroke();

    // Torso
    ctx.beginPath();
    ctx.moveTo(p.x, neckY);
    ctx.lineTo(p.x, hipY);
    ctx.lineWidth = 3;
    ctx.strokeStyle = outline;
    ctx.stroke();

    // Arms
    const leftHandX = p.x - armLen;
    const rightHandX = p.x + armLen;
    ctx.beginPath();
    ctx.moveTo(p.x, shoulderY);
    ctx.lineTo(leftHandX, shoulderY);
    ctx.moveTo(p.x, shoulderY);
    ctx.lineTo(rightHandX, shoulderY);
    ctx.lineWidth = 3;
    ctx.strokeStyle = outline;
    ctx.stroke();

    // Hands (small circles)
    ctx.beginPath();
    ctx.arc(leftHandX, shoulderY, handRadius, 0, Math.PI * 2);
    ctx.arc(rightHandX, shoulderY, handRadius, 0, Math.PI * 2);
    ctx.fillStyle = bodyColor;
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = outline;
    ctx.stroke();

    // Legs
    const leftFootX = p.x - Math.round(r * 0.8);
    const rightFootX = p.x + Math.round(r * 0.8);
    const footY = hipY + legLen;
    ctx.beginPath();
    ctx.moveTo(p.x, hipY);
    ctx.lineTo(leftFootX, footY);
    ctx.moveTo(p.x, hipY);
    ctx.lineTo(rightFootX, footY);
    ctx.lineWidth = 3;
    ctx.strokeStyle = outline;
    ctx.stroke();

    // Feet (short horizontal lines)
    ctx.beginPath();
    ctx.moveTo(leftFootX - footLen / 2, footY);
    ctx.lineTo(leftFootX + footLen / 2, footY);
    ctx.moveTo(rightFootX - footLen / 2, footY);
    ctx.lineTo(rightFootX + footLen / 2, footY);
    ctx.lineWidth = 3;
    ctx.strokeStyle = outline;
    ctx.stroke();

    // Name above the head
    ctx.fillStyle = "#111";
    ctx.fillText(p.name, p.x, headCenterY - headRadius - 2);
  }

  // Input handling
  window.addEventListener("keydown", (e) => {
    if (e.target === chatInputEl) return; // typing
    if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " "].includes(e.key)) e.preventDefault();
    pressed.add(e.key);
  });
  window.addEventListener("keyup", (e) => {
    pressed.delete(e.key);
  });

  const SPEED = 6;
  setInterval(() => {
    let dx = 0, dy = 0;
    if (pressed.has("ArrowLeft") || pressed.has("a") || pressed.has("A")) dx -= SPEED;
    if (pressed.has("ArrowRight") || pressed.has("d") || pressed.has("D")) dx += SPEED;
    if (pressed.has("ArrowUp") || pressed.has("w") || pressed.has("W")) dy -= SPEED;
    if (pressed.has("ArrowDown") || pressed.has("s") || pressed.has("S")) dy += SPEED;
    if (dx !== 0 || dy !== 0) {
      socket.emit("move", { dx, dy });
    }
  }, 60);

  draw();
})();


