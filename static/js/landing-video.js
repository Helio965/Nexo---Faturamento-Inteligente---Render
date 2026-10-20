/*
 * NEXO — Player demonstrativo da landing (v3)
 * ============================================================
 * Regras (ver Docs/VALIDACAO_VIDEO_RENDER.md):
 *  - Reprodução contínua em loop, iniciada por script (play() MUDO) quando o vídeo
 *    se aproxima da área visível. O atributo `autoplay` NÃO é usado: no Chrome e no
 *    Safari ele faz o próprio navegador pausar o vídeo mudo fora da tela.
 *  - Este script nunca chama pause(). A rolagem controla somente o SOM.
 *  - Som apenas com 100% da área do vídeo visível: viewport visual (zoom/pinça),
 *    cabeçalho fixo, contêineres com recorte e aba visível. Em tela cheia vale a
 *    área da tela cheia.
 *  - Permissão de áudio decidida pelo NAVEGADOR: API de política de autoplay quando
 *    existir; senão, sonda silenciosa em elemento separado. Sem permissão, aparece o
 *    botão temporário "Ativar som da demonstração", que desmuta dentro do gesto.
 *  - Sem bibliotecas e sem chamadas ao backend.
 */
(function () {
  'use strict';

  var video = document.getElementById('nexo-demo-video');
  var frame = document.getElementById('nexo-demo-frame');
  if (!video || !frame || typeof video.play !== 'function') return;

  var actionButton = document.getElementById('nexo-demo-sound-enable');
  var actionLabel = actionButton ? actionButton.querySelector('[data-label]') : null;
  var fullscreenButton = document.getElementById('nexo-demo-fullscreen');
  var errorPanel = document.getElementById('nexo-demo-error');
  var retryButton = document.getElementById('nexo-demo-retry');
  var header = document.querySelector('.nexo-header');
  var sources = video.getElementsByTagName('source');

  var LABEL_SOUND = 'Ativar som da demonstração';
  var LABEL_PLAY = 'Reproduzir demonstração';
  var LABEL_EXPAND = 'Expandir vídeo';
  var LABEL_EXIT = 'Sair da tela cheia';
  var REFUSAL_WINDOW_MS = 1500;  // pausa logo após desmutar: confirmar com o navegador
  var MAX_AUTO_FAILURES = 3;     // tentativas automáticas antes de exigir um gesto

  /*
   * Máquina de estados — única fonte de verdade do player.
   *   playback: idle | starting | playing | interrupted | needs-gesture | error
   *   audio:    unknown | probing | needs-gesture | confirming | allowed
   * fullyVisible, fullscreen e pageVisible são entradas recalculadas a partir do DOM.
   * Saídas: video.muted (somente via setMuted), botões e atributos data-* do quadro.
   */
  var state = {
    playback: 'idle',
    audio: 'unknown',
    fullyVisible: false,
    fullscreen: false,
    pageVisible: document.visibilityState !== 'hidden'
  };

  var fullscreenMode = null;       // 'element' | 'native' | null
  var clipAncestors = [];          // ancestrais com overflow != visible
  var layoutDirty = true;
  var checkQueued = false;
  var nearViewport = true;         // dica do IntersectionObserver (economiza trabalho na rolagem)
  var pendingVolumeEvents = 0;     // volumechange provocados por este script
  var lastUnmuteAt = -Infinity;
  var verifiedUnmuteAt = null;     // desmute já verificado após uma pausa (evita laço)
  var autoFailures = 0;
  var probeActivation = null;      // navigator.userActivation.hasBeenActive na última sonda

  function noop() {}

  function now() {
    return window.performance && performance.now ? performance.now() : Date.now();
  }

  // ------------------------------------------------------------------
  // Saída de áudio: o ÚNICO ponto que escreve em video.muted.
  // ------------------------------------------------------------------
  function setMuted(value) {
    if (video.muted === value) return;
    pendingVolumeEvents++;
    video.muted = value;
    if (!value) lastUnmuteAt = now();
  }

  function applyAudio() {
    var granted = state.audio === 'allowed' || state.audio === 'confirming';
    var audible = granted && state.fullyVisible && state.pageVisible && state.playback === 'playing';
    setMuted(!audible);
  }

  // ------------------------------------------------------------------
  // Visibilidade integral (função central)
  // ------------------------------------------------------------------
  function fullscreenElement() {
    return document.fullscreenElement || document.webkitFullscreenElement || null;
  }

  function ownsFullscreen(el) {
    return !!el && (el === frame || el === video || (typeof el.contains === 'function' && el.contains(video)));
  }

  function nativeFullscreen() {
    return !!video.webkitDisplayingFullscreen;  // tela cheia nativa do iPhone
  }

  // Área efetivamente visível, nas coordenadas de getBoundingClientRect().
  function viewportBox() {
    var vv = window.visualViewport;
    if (vv && vv.width > 0 && vv.height > 0) {
      return { left: vv.offsetLeft, top: vv.offsetTop,
        right: vv.offsetLeft + vv.width, bottom: vv.offsetTop + vv.height };
    }
    var de = document.documentElement;
    return { left: 0, top: 0, right: de.clientWidth || window.innerWidth,
      bottom: de.clientHeight || window.innerHeight };
  }

  // Menos de meio pixel físico: absorve arredondamento de layout/zoom, mas 1 px CSS
  // fora da área já é suficiente para silenciar.
  function edgeTolerance() {
    var dpr = window.devicePixelRatio || 1;
    var scale = (window.visualViewport && window.visualViewport.scale) || 1;
    return Math.min(0.5, 0.5 / (dpr * scale));
  }

  function inside(r, box, tol) {
    return r.left >= box.left - tol && r.top >= box.top - tol &&
      r.right <= box.right + tol && r.bottom <= box.bottom + tol;
  }

  function overlaps(r, box, tol) {
    return box.right > r.left + tol && box.left < r.right - tol &&
      box.bottom > r.top + tol && box.top < r.bottom - tol;
  }

  function refreshLayoutCache() {
    layoutDirty = false;
    clipAncestors = [];
    for (var el = video.parentElement; el && el !== document.body && el !== document.documentElement;
      el = el.parentElement) {
      var cs = window.getComputedStyle(el);
      var x = cs.overflowX !== 'visible';
      var y = cs.overflowY !== 'visible';
      if (!x && !y) continue;
      // Bordas fracionárias (computed style): clientWidth/clientHeight são inteiros
      // arredondados e gerariam falso "parcial" com zoom ou telas de alta densidade.
      clipAncestors.push({
        el: el, x: x, y: y,
        bl: parseFloat(cs.borderLeftWidth) || 0, br: parseFloat(cs.borderRightWidth) || 0,
        bt: parseFloat(cs.borderTopWidth) || 0, bb: parseFloat(cs.borderBottomWidth) || 0,
        scrolls: /auto|scroll/.test(cs.overflowX + ' ' + cs.overflowY)
      });
    }
    // Reserva o espaço do cabeçalho fixo no dimensionamento do vídeo (CSS).
    if (header) {
      var h = Math.ceil(header.getBoundingClientRect().height);
      if (h > 0) frame.style.setProperty('--nexo-demo-header', h + 'px');
    }
  }

  // Caixa de recorte (padding box) de um ancestral, em pixels fracionários.
  function clipBox(item) {
    var el = item.el;
    var b = el.getBoundingClientRect();
    var sbV = 0;
    var sbH = 0;
    if (item.scrolls) {  // barras de rolagem só existem em contêineres roláveis
      sbV = Math.max(0, el.offsetWidth - el.clientWidth - Math.round(item.bl + item.br));
      sbH = Math.max(0, el.offsetHeight - el.clientHeight - Math.round(item.bt + item.bb));
    }
    return {
      left: item.x ? b.left + item.bl : -Infinity,
      right: item.x ? b.right - item.br - sbV : Infinity,
      top: item.y ? b.top + item.bt : -Infinity,
      bottom: item.y ? b.bottom - item.bb - sbH : Infinity
    };
  }

  function computeFullyVisible() {
    if (document.visibilityState === 'hidden') return false;
    if (nativeFullscreen()) return true;
    var fsEl = fullscreenElement();
    if (fsEl && !ownsFullscreen(fsEl)) return false;  // outro elemento cobre a página

    var r = video.getBoundingClientRect();
    if (!(r.width > 0 && r.height > 0)) return false;
    var tol = edgeTolerance();
    if (!inside(r, viewportBox(), tol)) return false;
    if (fsEl) return true;  // em tela cheia, cabeçalho e contêineres da página não se aplicam

    if (header && overlaps(r, header.getBoundingClientRect(), tol)) return false;
    for (var i = 0; i < clipAncestors.length; i++) {
      if (!inside(r, clipBox(clipAncestors[i]), tol)) return false;
    }
    return true;
  }

  function updateInputs() {
    if (layoutDirty) refreshLayoutCache();
    state.pageVisible = document.visibilityState !== 'hidden';
    state.fullscreen = ownsFullscreen(fullscreenElement()) || nativeFullscreen();
    state.fullyVisible = computeFullyVisible();
  }

  function runCheck() {
    checkQueued = false;
    updateInputs();
    commit();
  }

  function scheduleCheck() {
    if (checkQueued) return;
    checkQueued = true;
    (window.requestAnimationFrame || function (cb) { return window.setTimeout(cb, 16); })(runCheck);
  }

  function markLayoutDirty() {
    layoutDirty = true;
    scheduleCheck();
  }

  function onScroll() {
    // Longe da tela não há o que recalcular; o IntersectionObserver avisa na volta.
    if (nearViewport || state.fullyVisible) scheduleCheck();
  }

  // ------------------------------------------------------------------
  // Reprodução
  // ------------------------------------------------------------------
  function setPlayback(value) {
    state.playback = value;
    commit();
  }

  function startPlayback() {
    if (state.playback === 'error') return;
    // Nunca começa audível sem confirmação do navegador.
    if (!(state.audio === 'allowed' && state.fullyVisible)) setMuted(true);
    var promise;
    try {
      promise = video.play();
    } catch (err) {
      onPlayRejected(err);
      return;
    }
    if (state.playback !== 'playing') setPlayback('starting');
    if (promise && typeof promise.then === 'function') promise.then(onPlayResolved, onPlayRejected);
  }

  function onPlayResolved() {
    autoFailures = 0;
    if (!video.paused && state.playback !== 'playing') setPlayback('playing');
  }

  function onPlayRejected(err) {
    var name = err && err.name;
    if (name === 'AbortError') return;  // interrompido por load(): o próximo evento decide
    if (name === 'NotSupportedError') {
      setError();
      return;
    }
    autoFailures++;
    // NotAllowedError com o vídeo mudo: o navegador bloqueou até a reprodução muda
    // (ex.: modo de pouca energia do iOS). Só um gesto do usuário libera.
    if (name === 'NotAllowedError' || autoFailures >= MAX_AUTO_FAILURES) {
      setPlayback('needs-gesture');
    } else {
      setPlayback('interrupted');
    }
  }

  // Retomada após interrupção involuntária, somente em pontos de controle (nunca a cada
  // rolagem e nunca em resposta imediata ao evento pause, para não brigar com controles
  // do sistema operacional).
  function resumeIfInterrupted() {
    if (state.playback === 'interrupted' && document.visibilityState !== 'hidden') startPlayback();
  }

  function setError() {
    state.playback = 'error';
    setMuted(true);
    commit();
  }

  function onPlaying() {
    autoFailures = 0;
    if (state.playback !== 'error') setPlayback('playing');
  }

  function onPause() {
    if (state.playback === 'error' || video.ended) return;
    var justUnmuted = state.audio === 'allowed' && !video.muted &&
      now() - lastUnmuteAt < REFUSAL_WINDOW_MS && verifiedUnmuteAt !== lastUnmuteAt;
    if (justUnmuted) {
      verifyAudioAfterPause();
      return;
    }
    if (state.playback === 'playing' || state.playback === 'starting') setPlayback('interrupted');
  }

  // Pausa logo após desmutar fora de um gesto: só o navegador sabe se foi recusa de áudio
  // (Safari/Firefox pausam) ou uma pausa transitória. Pergunta a ele com UM play() com som:
  // NotAllowedError = recusa -> volta ao mudo e pede o gesto. Uma verificação por desmute.
  function verifyAudioAfterPause() {
    verifiedUnmuteAt = lastUnmuteAt;
    var refused = function () {
      state.audio = 'needs-gesture';
      setMuted(true);
      startPlayback();
    };
    var promise;
    try {
      promise = video.play();
    } catch (err) {
      refused();
      return;
    }
    if (promise && typeof promise.then === 'function') {
      promise.then(noop, function (err) {
        if (err && err.name === 'AbortError') return;
        refused();
      });
    }
  }

  function onEnded() {
    // Com loop o evento não ocorre; reforço para navegadores que ignorem o atributo.
    try { video.currentTime = 0; } catch (e) { /* sem efeito */ }
    startPlayback();
  }

  function onVolumeChange() {
    if (pendingVolumeEvents > 0) {
      pendingVolumeEvents--;
      return;
    }
    // Mudança externa (ex.: controles nativos da tela cheia do iPhone).
    if (nativeFullscreen()) state.audio = video.muted ? 'needs-gesture' : 'allowed';
    commit();
  }

  // ------------------------------------------------------------------
  // Permissão de áudio
  // ------------------------------------------------------------------
  function hasActivation() {
    var ua = navigator.userActivation;
    return ua ? !!ua.hasBeenActive : null;
  }

  function maybeProbe() {
    if (!state.fullyVisible || state.playback !== 'playing') return;
    if (state.audio === 'unknown') {
      probeAudio();
    } else if (state.audio === 'needs-gesture' && probeActivation === false && hasActivation() === true) {
      probeAudio();  // houve interação depois da última sonda: o navegador pode ter liberado
    }
  }

  // WAV de 50 ms de silêncio (PCM 8 bits, 8 kHz, mono) como data: URI — sem rede e sem
  // URL temporária para revogar.
  function silentWavUri() {
    var le = function (value, bytes) {
      var s = '';
      for (var i = 0; i < bytes; i++) s += String.fromCharCode((value >>> (8 * i)) & 255);
      return s;
    };
    var n = 400;
    var wav = 'RIFF' + le(36 + n, 4) + 'WAVEfmt ' + le(16, 4) + le(1, 2) + le(1, 2) +
      le(8000, 4) + le(8000, 4) + le(1, 2) + le(8, 2) + 'data' + le(n, 4);
    for (var j = 0; j < n; j++) wav += String.fromCharCode(128);
    return 'data:audio/wav;base64,' + window.btoa(wav);
  }

  function probeResult(allowed) {
    if (state.audio !== 'probing') return;  // um gesto do usuário já decidiu
    state.audio = allowed ? 'allowed' : 'needs-gesture';
    commit();
  }

  function probeAudio() {
    state.audio = 'probing';
    probeActivation = hasActivation();

    // 1) API de detecção de política de autoplay, quando o navegador oferece. Consulta
    //    por TIPO ('mediaelement'): a consulta pelo elemento mudo responderia 'allowed'.
    if (typeof navigator.getAutoplayPolicy === 'function') {
      var policy = null;
      try { policy = navigator.getAutoplayPolicy('mediaelement'); } catch (e) { policy = null; }
      if (policy === 'allowed') return probeResult(true);
      if (policy === 'allowed-muted' || policy === 'disallowed') return probeResult(false);
    }

    // 2) Sonda silenciosa (50 ms) em elemento SEPARADO: não toca no vídeo principal.
    var settled = false;
    var finish = function (allowed) {
      if (settled) return;
      settled = true;
      probeResult(allowed);
    };
    try {
      var probe = document.createElement('audio');
      probe.preload = 'auto';
      probe.src = silentWavUri();
      var promise = probe.play();
      if (!promise || typeof promise.then !== 'function') {
        finish(false);
        return;
      }
      promise.then(function () {
        // Permitido. Espera a sonda terminar sozinha antes de desmutar o vídeo, para não
        // sobrepor as duas transições na sessão de mídia do navegador.
        probe.addEventListener('ended', function () { window.setTimeout(function () { finish(true); }, 100); });
        window.setTimeout(function () { finish(true); }, 800);
      }, function () { finish(false); });
    } catch (e) {
      finish(false);
    }
  }

  // Gesto do usuário no botão temporário: reproduzir (bloqueio) ou ativar som.
  function onActionClick() {
    if (state.playback === 'needs-gesture' || state.playback === 'interrupted' || state.playback === 'idle') {
      autoFailures = 0;
      startPlayback();  // dentro do gesto o navegador libera a reprodução muda
      return;
    }
    updateInputs();
    if (!state.fullyVisible || state.audio === 'allowed') {
      commit();
      return;
    }
    state.audio = 'confirming';
    setMuted(false);  // DENTRO do gesto real do usuário
    var promise;
    try {
      promise = video.play();
    } catch (err) {
      onConfirmFailed();
      return;
    }
    if (promise && typeof promise.then === 'function') {
      promise.then(onConfirmed, onConfirmFailed);
    } else {
      window.setTimeout(function () {
        if (video.paused) onConfirmFailed(); else onConfirmed();
      }, 0);
    }
    commit();
  }

  function onConfirmed() {
    if (state.audio !== 'confirming') return;
    state.audio = 'allowed';  // o botão some definitivamente
    commit();
  }

  function onConfirmFailed() {
    if (state.audio !== 'confirming') return;
    state.audio = 'needs-gesture';
    setMuted(true);
    if (video.paused) startPlayback();
    commit();
  }

  // ------------------------------------------------------------------
  // Tela cheia
  // ------------------------------------------------------------------
  function detectFullscreenMode() {
    var enabled = document.fullscreenEnabled || document.webkitFullscreenEnabled;
    if (enabled && (frame.requestFullscreen || frame.webkitRequestFullscreen)) return 'element';
    if (typeof video.webkitEnterFullscreen === 'function') return 'native';  // iPhone
    return null;
  }

  function onFullscreenClick() {
    if (state.playback === 'needs-gesture' || state.playback === 'interrupted') startPlayback();
    try {
      var result;
      if (ownsFullscreen(fullscreenElement())) {
        result = document.exitFullscreen ? document.exitFullscreen()
          : document.webkitExitFullscreen && document.webkitExitFullscreen();
      } else if (fullscreenMode === 'element') {
        result = frame.requestFullscreen ? frame.requestFullscreen({ navigationUI: 'hide' })
          : frame.webkitRequestFullscreen();
      } else if (fullscreenMode === 'native') {
        video.webkitEnterFullscreen();  // iPhone: player nativo (ver documentação)
      }
      if (result && typeof result.catch === 'function') result.catch(noop);
    } catch (e) { /* recusado pelo navegador (ex.: iframe sem allowfullscreen) */ }
  }

  function onFullscreenChange() {
    markLayoutDirty();
    updateInputs();  // nova área (tela cheia) ou retorno à página: recalcula na hora
    commit();
    resumeIfInterrupted();
    window.setTimeout(scheduleCheck, 250);  // transições animadas (macOS/iPadOS)
  }

  // ------------------------------------------------------------------
  // Renderização (somente escreve quando algo muda)
  // ------------------------------------------------------------------
  function setAttr(el, name, value) {
    if (el && el.getAttribute(name) !== value) el.setAttribute(name, value);
  }

  function setHidden(el, hidden) {
    if (el && el.hidden !== hidden) el.hidden = hidden;
  }

  function render() {
    setAttr(frame, 'data-playback', state.playback);
    setAttr(frame, 'data-audio', state.audio);
    setAttr(frame, 'data-visibility', state.fullyVisible ? 'full' : 'partial');
    setAttr(frame, 'data-fullscreen', state.fullscreen ? 'true' : 'false');

    var showPlay = state.playback === 'needs-gesture';
    var showSound = !showPlay && state.playback === 'playing' && state.audio === 'needs-gesture' &&
      state.fullyVisible;
    if (actionButton) {
      var label = showPlay ? LABEL_PLAY : LABEL_SOUND;
      setAttr(actionButton, 'data-action', showPlay ? 'play' : 'sound');
      if (actionLabel && actionLabel.textContent !== label) actionLabel.textContent = label;
      var hide = !(showPlay || showSound);
      if (hide && document.activeElement === actionButton && fullscreenButton && !fullscreenButton.hidden) {
        try { fullscreenButton.focus({ preventScroll: true }); } catch (e) { /* sem efeito */ }
      }
      setHidden(actionButton, hide);
    }
    setHidden(errorPanel, state.playback !== 'error');
    if (fullscreenButton) {
      setHidden(fullscreenButton, !fullscreenMode || state.playback === 'error');
      var fsLabel = state.fullscreen ? LABEL_EXIT : LABEL_EXPAND;
      setAttr(fullscreenButton, 'aria-label', fsLabel);
      setAttr(fullscreenButton, 'title', fsLabel);
    }
  }

  function commit() {
    applyAudio();
    maybeProbe();
    render();
  }

  // ------------------------------------------------------------------
  // Inicialização
  // ------------------------------------------------------------------
  video.controls = false;
  video.loop = true;
  video.defaultMuted = true;
  setMuted(true);
  fullscreenMode = detectFullscreenMode();

  video.addEventListener('playing', onPlaying);
  video.addEventListener('pause', onPause);
  video.addEventListener('ended', onEnded);
  video.addEventListener('volumechange', onVolumeChange);
  video.addEventListener('error', function () { if (video.error) setError(); });
  if (sources.length) sources[sources.length - 1].addEventListener('error', setError);
  video.addEventListener('webkitbeginfullscreen', onFullscreenChange);
  video.addEventListener('webkitendfullscreen', onFullscreenChange);

  if (actionButton) actionButton.addEventListener('click', onActionClick);
  if (fullscreenButton) fullscreenButton.addEventListener('click', onFullscreenClick);
  if (retryButton) {
    retryButton.addEventListener('click', function () {
      autoFailures = 0;
      state.playback = 'idle';
      try { video.load(); } catch (e) { /* sem efeito */ }
      startPlayback();
    });
  }

  document.addEventListener('scroll', onScroll, { capture: true, passive: true });
  window.addEventListener('resize', markLayoutDirty);
  window.addEventListener('orientationchange', markLayoutDirty);
  window.addEventListener('load', markLayoutDirty);
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', scheduleCheck);
    window.visualViewport.addEventListener('scroll', scheduleCheck);
  }
  if (typeof window.ResizeObserver === 'function') {
    var ro = new ResizeObserver(markLayoutDirty);
    ro.observe(frame);
    if (header) ro.observe(header);
  }
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(markLayoutDirty, noop);

  document.addEventListener('visibilitychange', function () {
    updateInputs();  // aba oculta: silencia imediatamente, sem esperar o próximo quadro
    commit();
    resumeIfInterrupted();
  });
  window.addEventListener('pageshow', function () { markLayoutDirty(); resumeIfInterrupted(); });
  document.addEventListener('resume', resumeIfInterrupted);
  window.addEventListener('online', resumeIfInterrupted);
  document.addEventListener('fullscreenchange', onFullscreenChange);
  document.addEventListener('webkitfullscreenchange', onFullscreenChange);

  // Fonte inexistente/não suportada também é detectada pelo play() (NotSupportedError).
  if (video.error) setError();

  if (typeof window.IntersectionObserver === 'function') {
    // Dica barata para a rolagem: o vídeo cruza a borda da viewport.
    new IntersectionObserver(function (entries) {
      nearViewport = entries[entries.length - 1].isIntersecting;
      scheduleCheck();
    }, { threshold: [0, 1] }).observe(video);

    // Início sob demanda: quando o vídeo está a até uma altura de tela de distância.
    var starter = new IntersectionObserver(function (entries) {
      if (!entries[entries.length - 1].isIntersecting) return;
      starter.disconnect();
      if (state.playback === 'idle') startPlayback();
    }, { rootMargin: '100% 0px 100% 0px' });
    starter.observe(video);
  } else {
    startPlayback();
  }

  updateInputs();
  commit();
})();
