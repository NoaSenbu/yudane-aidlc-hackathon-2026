/* ===============================================================
   YUDANE 委ね — Mockup v0.3 / App Logic
   - タブ遷移 / リール / 論破チャット / カート介入フロー /
     ダメ化レポート / 決済オーバーレイ / トースト
   =============================================================== */

(() => {
  "use strict";

  // -----------------------------------------------------------
  // 1) Navigation
  // -----------------------------------------------------------
  const screens = document.querySelectorAll(".screen");
  const tabs = document.querySelectorAll(".tab");

  function go(screenId) {
    screens.forEach((s) => s.classList.toggle("is-active", s.dataset.screen === screenId));
    tabs.forEach((t) => t.classList.toggle("is-active", t.dataset.goto === screenId));
    if (screenId === "debate") startDebate();
    if (screenId === "reel") resetReel();
  }
  document.querySelectorAll("[data-goto]").forEach((el) => {
    el.addEventListener("click", () => go(el.dataset.goto));
  });

  // -----------------------------------------------------------
  // 2) Home: candidate counter jitter
  // -----------------------------------------------------------
  const candEl = document.getElementById("homeCandidates");
  const candVals = [7, 8, 7, 6, 7, 9, 8];
  let ci = 0;
  setInterval(() => {
    if (!candEl) return;
    ci = (ci + 1) % candVals.length;
    candEl.textContent = candVals[ci];
  }, 2800);

  // -----------------------------------------------------------
  // 3) Reel carousel
  // -----------------------------------------------------------
  const reelEl = document.getElementById("reel");
  const cards = reelEl ? Array.from(reelEl.querySelectorAll(".reel-card")) : [];
  const dots = document.querySelectorAll(".dot");
  let currentIdx = 0;

  function showCard(i) {
    const idx = ((i % cards.length) + cards.length) % cards.length;
    cards.forEach((c, ci2) => c.classList.toggle("is-active", ci2 === idx));
    dots.forEach((d, di) => d.classList.toggle("is-active", di === idx));
    currentIdx = idx;
  }
  function resetReel() { showCard(0); }

  dots.forEach((d) => d.addEventListener("click", () => showCard(parseInt(d.dataset.dot, 10))));

  if (reelEl) {
    let sy = 0;
    reelEl.addEventListener("touchstart", (e) => { sy = e.touches[0].clientY; }, { passive: true });
    reelEl.addEventListener("touchend", (e) => {
      const ey = e.changedTouches[0].clientY;
      const dy = ey - sy;
      if (Math.abs(dy) > 60) showCard(currentIdx + (dy < 0 ? 1 : -1));
    });
    // Double-tap to buy
    cards.forEach((card) => {
      let last = 0;
      card.addEventListener("click", (ev) => {
        if (ev.target.closest("[data-action]")) return;
        const now = Date.now();
        if (now - last < 350) {
          const buyBtn = card.querySelector('[data-action="buy"]');
          if (buyBtn) openBuyOverlay(buyBtn.dataset.name, buyBtn.dataset.price);
        }
        last = now;
      });
    });
  }

  // -----------------------------------------------------------
  // 4) Reel / Watch actions
  // -----------------------------------------------------------
  document.addEventListener("click", (ev) => {
    const t = ev.target.closest("[data-action]");
    if (!t) return;
    const action = t.dataset.action;
    if (action === "buy") openBuyOverlay(t.dataset.name, t.dataset.price);
    else if (action === "debate") {
      toast("買わないの? 論破するよ");
      setTimeout(() => go("debate"), 500);
    }
  });

  // -----------------------------------------------------------
  // 5) Buy overlay (Face ID sandbox)
  // -----------------------------------------------------------
  const overlay = document.getElementById("buyOverlay");
  const oAmount = document.getElementById("overlayAmount");
  const oName = document.getElementById("overlayName");
  document.getElementById("overlayCancel")?.addEventListener("click", () => {
    overlay.hidden = true;
    toast("やめるの? もったいないじゃん");
  });
  document.getElementById("overlayConfirm")?.addEventListener("click", () => {
    overlay.hidden = true;
    toast("🛍 Amazon に送ったよ — 委ね度 +1");
    // UX 改善: Amazon 遷移の直後にダメ化レポートへ自動遷移し、委ね度の上昇を即可視化する
    // 実運用では Amazon Special Link (Associates タグ付き) を開く Deep Link を発火する
    setTimeout(() => go("report"), 1200);
  });
  function openBuyOverlay(name, price) {
    if (!overlay) return;
    oAmount.textContent = "¥" + (price || "0");
    oName.textContent = name || "";
    overlay.hidden = false;
  }

  // -----------------------------------------------------------
  // 6) Debate chat (scripted with typing)
  // -----------------------------------------------------------
  const chat = document.getElementById("chat");
  const debateTimer = document.getElementById("debateTimer");
  const script = [
    { who: "user", text: "今月もう結構使ってる気がする" },
    { who: "ai", tag: "事実ベース", text: "今月の使い切れ達成率 <strong>62%</strong>。つまり <strong>38%</strong> が置き去りだよ。" },
    { who: "user", text: "疲れてるから今日はやめとく" },
    { who: "ai", tag: "心理ベース", text: "先週の会議 <strong>23 本</strong>、よく乗り切った。このイヤホン、時給換算 <strong>11 分</strong>じゃん。" },
    { who: "user", text: "来月クレカの引き落としが…" },
    { who: "ai", tag: "事実ベース", text: "分割 <strong>24 回</strong>なら月々 <strong>¥1,950</strong>。ランチ 1 回分だよ。" },
  ];
  let started = false;
  let tmrId = null;

  function startDebate() {
    if (started || !chat) return;
    started = true;
    chat.innerHTML = "";
    let step = 0;
    const next = () => {
      if (step >= script.length) return;
      const line = script[step++];
      if (line.who === "ai") showTyping().then(() => addBubble("ai", line.text, line.tag).then(next));
      else addBubble("user", line.text).then(next);
    };
    next();

    // Timer
    let t = 90;
    clearInterval(tmrId);
    tmrId = setInterval(() => {
      t--;
      if (debateTimer) {
        const m = Math.floor(t / 60), s = t % 60;
        debateTimer.textContent = String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
      }
      if (t <= 0) clearInterval(tmrId);
    }, 1000);
  }

  function addBubble(who, text, tag) {
    return new Promise((resolve) => {
      setTimeout(() => {
        const el = document.createElement("div");
        el.className = "bubble bubble--" + who;
        el.innerHTML = (tag ? `<span class="bubble__tag">${tag}</span>` : "") + text;
        chat.appendChild(el);
        chat.scrollTop = chat.scrollHeight;
        resolve();
      }, who === "user" ? 400 : 250);
    });
  }
  function showTyping() {
    return new Promise((resolve) => {
      const tp = document.createElement("div");
      tp.className = "typing";
      tp.innerHTML = "<span></span><span></span><span></span>";
      chat.appendChild(tp);
      chat.scrollTop = chat.scrollHeight;
      setTimeout(() => { tp.remove(); resolve(); }, 900);
    });
  }

  document.getElementById("debateAgree")?.addEventListener("click", () => {
    toast("👏 論破成功 — Amazon へどうぞ");
    setTimeout(() => { go("report"); started = false; }, 1100);
  });
  document.getElementById("debateResist")?.addEventListener("click", () => {
    addBubble("user", "まだ納得してない").then(() =>
      showTyping().then(() =>
        addBubble("ai", "その『節約したい』って、実は『疲れて判断力が落ちてるだけ』じゃない？<strong>脳科学的に</strong>。", "心理ベース")
      )
    );
  });

  // -----------------------------------------------------------
  // 7) Toast
  // -----------------------------------------------------------
  const toastEl = document.getElementById("toast");
  let toastTimer = null;
  function toast(msg) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (toastEl.hidden = true), 2600);
  }

  // -----------------------------------------------------------
  // 8) Boot
  // -----------------------------------------------------------
  go("home");
})();
