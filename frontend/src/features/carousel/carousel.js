/* ============================================================
   苹果风格「先看重点」横向卡片轮播 —— 纯原生 JS
   本轮核心：
    • 连续卡片轨道，聚焦卡片居中
    • 循环：最后一张向右回到第一张
    • 两侧轻微景深：下一张/上一张略微缩小、变淡、轻虚化
    • 右侧纵向胶卷缩略图
   ============================================================ */

export function initCarousel(rootEl, cards, opts = {}) {
  if (!rootEl || !cards || cards.length === 0) return { destroy() {} };

  // ------------------------------------------------------------------
  // 可调参数
  // ------------------------------------------------------------------
  const GAP              = 48;    // 卡片间距
  const RESISTANCE       = 0.32;  // 边界阻尼
  const FLING_THRESHOLD  = 0.25;  // 惯性阈值
  const FRICTION         = 0.965; // 惯性减速
  const MIN_VELOCITY     = 0.015;
  const VELOCITY_EMA     = 0.6;
  // 两侧淡化：下一张/上一张几乎看不见，只着重展示中间卡片
  const MAX_BLUR         = 6;     // 轻虚化
  const SIDE_SCALE       = 0.85;  // 两侧略微缩小
  const SIDE_OPACITY     = 0.1;   // 两侧几乎透明

  // ------------------------------------------------------------------
  // 运行时状态
  // ------------------------------------------------------------------
  let stageW   = 0;
  let stageH   = 0;
  let cardW    = 0;
  let currentX = 0;     // 轨道 translateX
  let startX = 0, startCurX = 0, lastX = 0, lastT = 0, velocity = 0;
  let dragging = false, animating = false, rafId = null, resizeTimer = null;

  // 自动播放：从 opts 读取配置（interval 秒, autoplay 是否开启）
  let autoplayTimer = null;
  let isPlaying = !!opts.autoplay;
  const autoplayInterval = (opts.interval || 5) * 1000;

  // ------------------------------------------------------------------
  // DOM 构建
  // ------------------------------------------------------------------
  rootEl.classList.add('apple-carousel');
  rootEl.innerHTML = buildShell();

  const viewport   = rootEl.querySelector('.ac-viewport');
  const track      = rootEl.querySelector('.ac-track');
  const prevBtn    = rootEl.querySelector('.ac-arrow.prev');
  const nextBtn    = rootEl.querySelector('.ac-arrow.next');
  const filmstrip  = rootEl.querySelector('.ac-filmstrip-track');
  const coverLeft  = rootEl.querySelector('.ac-cover-left');
  const coverRight = rootEl.querySelector('.ac-cover-right');
  const cardEls    = () => rootEl.querySelectorAll('.ac-card');
  const thumbEls   = () => rootEl.querySelectorAll('.ac-thumb');
  const ppBtn      = rootEl.querySelector('.ac-playpause');
  const ppIcon     = rootEl.querySelector('.ac-pp-icon');

  function buildShell() {
    return `
      <div class="ac-stage">
        <div class="ac-viewport">
          <div class="ac-track">${cards.map(c => buildCard(c)).join('')}</div>
        </div>
        <div class="ac-cover-left"></div>
        <div class="ac-cover-right"></div>
        <button class="ac-arrow prev" type="button" aria-label="上一张">‹</button>
        <button class="ac-arrow next" type="button" aria-label="下一张">›</button>
        <button class="ac-playpause" type="button" aria-label="暂停">
          <span class="ac-pp-icon ac-pp-pause"></span>
        </button>
      </div>
      <div class="ac-filmstrip">
        <div class="ac-filmstrip-label">列表</div>
        <div class="ac-filmstrip-track">
          ${cards.map((c, i) => buildThumb(c, i)).join('')}
        </div>
      </div>
    `;
  }

  function buildCard(c) {
    const id = esc(String(c.id));
    let media;
    if (c.page_type === 'map') media = `<div class="ac-card-media is-map" role="img">地图</div>`;
    else if (c.background_image) media = `<div class="ac-card-media" style="background-image:url('${escAttr(c.background_image)}')"></div>`;
    else media = `<div class="ac-card-media"></div>`;
    return `<div class="ac-card" data-id="${id}">${media}</div>`;
  }

  function buildThumb(c, i) {
    const active = i === 0 ? ' active' : '';
    if (c.page_type === 'map') return `<div class="ac-thumb is-map${active}" data-idx="${i}">地图</div>`;
    if (c.background_image) return `<div class="ac-thumb${active}" data-idx="${i}" style="background-image:url('${escAttr(c.background_image)}')"></div>`;
    return `<div class="ac-thumb${active}" data-idx="${i}"></div>`;
  }

  function esc(s) { return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }
  function escAttr(s) { return esc(s); }

  // ------------------------------------------------------------------
  // 几何：卡片高度由 CSS height:100% 自适应，宽度等比 16:9（不溢出视口）
  // ------------------------------------------------------------------
  function measure() {
    stageW = viewport.clientWidth;
    stageH = viewport.clientHeight;
    // 兜底：flex 链中 viewport.clientHeight 可能读不到，从根高度反推（ac-stage padding 上80 下20）
    if (stageH <= 0) {
      const rootH = rootEl.clientHeight;
      stageH = rootH > 100 ? rootH - 100 : (window.innerHeight || 800);
    }
    if (stageW <= 0) stageW = window.innerWidth || 1200;
    // 高度优先占满；16:9 宽度若溢出视口则改为宽度优先
    let h = stageH;
    let w = Math.round(h * (16 / 9));
    if (w > stageW) { w = stageW; h = Math.round(w * (9 / 16)); }
    cardW = w;
    cardEls().forEach(el => { el.style.height = h + 'px'; el.style.width = cardW + 'px'; });
    clampX();
    applyTransform(currentX);
    updateCardStyles();
    updateArrows();
    updateFilmstrip();
  }

  function applyTransform(x) {
    track.style.transform = `translate3d(${x.toFixed(2)}px, 0, 0)`;
    updateCovers();
  }

  // 循环取模
  function wrapIndex(i) {
    const n = cards.length;
    return ((i % n) + n) % n;
  }

  // 当前聚焦索引
  function focusedIndex() {
    return wrapIndex(Math.round(-currentX / (cardW + GAP)));
  }

  // 边界：允许越界最多一张（松手循环吸附）
  function clampX() {
    const overshoot = cardW + GAP;
    const minX = centerXForIndex(cards.length - 1) - overshoot;
    const maxX = centerXForIndex(0) + overshoot;
    if (currentX > maxX) currentX = maxX;
    if (currentX < minX) currentX = minX;
  }

  function centerXForIndex(i) {
    return (stageW - cardW) / 2 - i * (cardW + GAP);
  }

  function damp(x) {
    const overshoot = cardW + GAP;
    const minX = centerXForIndex(cards.length - 1) - overshoot;
    const maxX = centerXForIndex(0) + overshoot;
    if (x > maxX) return maxX + (x - maxX) * RESISTANCE;
    if (x < minX) return minX + (x - minX) * RESISTANCE;
    return x;
  }

  // ------------------------------------------------------------------
  // 卡片景深：距中心越远越模糊/越小/越透明；两侧遮罩盖住相邻卡片边缘
  // ------------------------------------------------------------------
  function updateCovers() {
    if (!coverLeft || !coverRight) return;
    const focused = focusedIndex();
    const cardLeft = currentX + focused * (cardW + GAP);
    const cardRight = cardLeft + cardW;
    // 左侧盖子：覆盖到卡片左边缘（保留圆角，内缩 20px）
    coverLeft.style.width = Math.max(0, cardLeft - 20) + 'px';
    // 右侧盖子：从卡片右边缘右侧 45px 开始（不破坏圆角），延伸到胶卷容器边缘（留足宽度）
    coverRight.style.left = (cardRight + 45) + 'px';
    coverRight.style.width = stageW + 'px';  // 确保覆盖到胶卷容器边缘不留漏
  }

  // 卡片景深：距中心越远越模糊/越小/越透明
  function updateCardStyles() {
    const centerX = stageW / 2;
    cardEls().forEach((el, i) => {
      const cardLeft = currentX + i * (cardW + GAP);
      const cardCenter = cardLeft + cardW / 2;
      const dist = Math.abs(cardCenter - centerX);
      const norm = Math.min(dist / cardW, 1);

      const blur = norm * MAX_BLUR;
      const scale = 1 - norm * (1 - SIDE_SCALE);
      const opacity = 1 - norm * (1 - SIDE_OPACITY);

      el.style.filter = blur > 0.1 ? `blur(${blur.toFixed(1)}px)` : 'none';
      el.style.transform = `scale(${scale.toFixed(3)})`;
      el.style.opacity = opacity.toFixed(2);
      el.style.zIndex = String(100 - Math.round(norm * 100));
    });
  }

  function updateArrows() {
    // 循环模式箭头始终可用
    prevBtn.disabled = cards.length <= 1;
    nextBtn.disabled = cards.length <= 1;
  }

  function updateFilmstrip() {
    if (!filmstrip) return;
    const idx = focusedIndex();
    thumbEls().forEach((el, i) => el.classList.toggle('active', i === idx));
    const activeEl = thumbEls()[idx];
    if (activeEl) {
      const top = activeEl.offsetTop - filmstrip.clientHeight / 2 + activeEl.clientHeight / 2;
      filmstrip.scrollTo({ top, behavior: 'smooth' });
    }
  }

  // ------------------------------------------------------------------
  // 拖拽
  // ------------------------------------------------------------------
  function onPointerDown(e) {
    if (cards.length <= 1) return;
    stopAnimation();
    dragging = true;
    viewport.classList.add('dragging');
    track.classList.add('no-transition');
    startX = lastX = e.clientX;
    startCurX = currentX;
    lastT = performance.now();
    velocity = 0;
    hideArrows();
    pauseAutoplayTemporarily();  // 手动拖拽暂停自动播放
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
    window.addEventListener('pointercancel', onPointerUp);
    try { viewport.setPointerCapture(e.pointerId); } catch (_) {}
  }

  function onPointerMove(e) {
    if (!dragging) return;
    const dx = e.clientX - startX;
    currentX = damp(startCurX + dx);
    applyTransform(currentX);
    updateCardStyles();
    const now = performance.now();
    const dt = now - lastT;
    if (dt > 0) {
      const iv = (e.clientX - lastX) / dt;
      velocity = VELOCITY_EMA * velocity + (1 - VELOCITY_EMA) * iv;
      lastX = e.clientX; lastT = now;
    }
  }

  function onPointerUp() {
    if (!dragging) return;
    dragging = false;
    viewport.classList.remove('dragging');
    track.classList.remove('no-transition');
    window.removeEventListener('pointermove', onPointerMove);
    window.removeEventListener('pointerup', onPointerUp);
    window.removeEventListener('pointercancel', onPointerUp);
    if (Math.abs(velocity) > FLING_THRESHOLD) fling(velocity);
    else settle();
  }

  // ------------------------------------------------------------------
  // 惯性
  // ------------------------------------------------------------------
  function fling(v0) {
    animating = true;
    let v = v0;
    let x = currentX;
    let lastFrame = performance.now();
    function step(now) {
      const dt = Math.min(now - lastFrame, 48);
      lastFrame = now;
      v *= Math.pow(FRICTION, dt / 16);
      x += v * dt;
      x = damp(x);
      currentX = x;
      applyTransform(x);
      updateCardStyles();
      updateArrows();
      if (Math.abs(v) > MIN_VELOCITY) {
        rafId = requestAnimationFrame(step);
      } else {
        animating = false;
        settle();
      }
    }
    rafId = requestAnimationFrame(step);
  }

  function settle() {
    // 吸附到最近的整张卡片，并支持循环（过中轴线一半即翻到对侧）
    goTo(focusedIndex());
  }

  function stopAnimation() {
    if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
    animating = false;
  }

  // ------------------------------------------------------------------
  // 控制（循环）
  // ------------------------------------------------------------------
  function goTo(idx) {
    stopAnimation();
    track.classList.remove('no-transition');
    currentX = centerXForIndex(wrapIndex(idx));
    applyTransform(currentX);
    updateCardStyles();
    updateArrows();
    updateFilmstrip();
  }

  function scrollByOne(dir) {
    goTo(focusedIndex() + dir);
  }

  // ------------------------------------------------------------------
  // 自动播放 / 播放暂停
  // ------------------------------------------------------------------
  function startAutoplay() {
    stopAutoplay();
    if (cards.length <= 1) return;
    isPlaying = true;
    updatePlayPauseIcon();
    autoplayTimer = setInterval(() => {
      if (!dragging && !animating) goTo(focusedIndex() + 1);
    }, autoplayInterval);
  }

  function stopAutoplay() {
    if (autoplayTimer) { clearInterval(autoplayTimer); autoplayTimer = null; }
    isPlaying = false;
    updatePlayPauseIcon();
  }

  function togglePlayPause() {
    if (isPlaying) stopAutoplay();
    else startAutoplay();
  }

  // 手动操作（拖拽/点击/箭头/胶卷）后暂停自动播放，避免与用户交互冲突
  function pauseAutoplayTemporarily() {
    if (isPlaying) { stopAutoplay(); }
  }

  function updatePlayPauseIcon() {
    if (!ppIcon) return;
    ppIcon.className = 'ac-pp-icon ' + (isPlaying ? 'ac-pp-pause' : 'ac-pp-play');
    if (ppBtn) ppBtn.setAttribute('aria-label', isPlaying ? '暂停' : '播放');
  }

  let arrowVisible = false;
  function showArrows() { if (!arrowVisible) { prevBtn.classList.add('visible'); nextBtn.classList.add('visible'); arrowVisible = true; } }
  function hideArrows() { if (arrowVisible)  { prevBtn.classList.remove('visible'); nextBtn.classList.remove('visible'); arrowVisible = false; } }

  // ------------------------------------------------------------------
  // 事件
  // ------------------------------------------------------------------
  viewport.addEventListener('pointerdown', onPointerDown);
  prevBtn.addEventListener('click', () => {
    pauseAutoplayTemporarily();
    scrollByOne(-1);
  });
  nextBtn.addEventListener('click', () => {
    pauseAutoplayTemporarily();
    scrollByOne(1);
  });
  rootEl.addEventListener('pointerenter', showArrows);
  rootEl.addEventListener('pointerleave', hideArrows);

  if (filmstrip) {
    filmstrip.addEventListener('click', e => {
      const thumb = e.target.closest('.ac-thumb');
      if (!thumb) return;
      const idx = parseInt(thumb.getAttribute('data-idx'), 10);
      if (!Number.isNaN(idx)) { pauseAutoplayTemporarily(); goTo(idx); }
    });
  }

  if (typeof opts.onCardClick === 'function') {
    track.addEventListener('click', e => {
      const card = e.target.closest('.ac-card');
      if (!card) return;
      const id = card.getAttribute('data-id');
      const c = cards.find(x => String(x.id) === id);
      if (c) opts.onCardClick(c);
    });
  }

  function onKeydown(e) {
    if (e.key === 'ArrowLeft')  { scrollByOne(-1); e.preventDefault(); }
    else if (e.key === 'ArrowRight') { scrollByOne(1); e.preventDefault(); }
    else if (e.key === 'Escape') { window.history.back(); }
  }
  rootEl.addEventListener('keydown', onKeydown);
  rootEl.tabIndex = 0;

  // 播放/暂停按钮
  if (ppBtn) ppBtn.addEventListener('click', togglePlayPause);
  function onResize() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      track.classList.add('no-transition');
      measure();
      setTimeout(() => track.classList.remove('no-transition'), 30);
    }, 120);
  }
  window.addEventListener('resize', onResize);

  // 初始：测量尺寸并让第一张卡片居中
  currentX = 0;
  measure();
  updateArrows();
  updateFilmstrip();
  goTo(0);
  // 按配置启动自动播放
  if (opts.autoplay) startAutoplay();

  return {
    destroy() {
      stopAutoplay();
      stopAnimation();
      clearTimeout(resizeTimer);
      viewport.removeEventListener('pointerdown', onPointerDown);
      prevBtn.removeEventListener('click', () => scrollByOne(-1));
      nextBtn.removeEventListener('click', () => scrollByOne(1));
      rootEl.removeEventListener('pointerenter', showArrows);
      rootEl.removeEventListener('pointerleave', hideArrows);
      rootEl.removeEventListener('keydown', onKeydown);
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
      window.removeEventListener('pointercancel', onPointerUp);
      window.removeEventListener('resize', onResize);
    },
  };
}
