/* NEXO: vídeo demonstrativo em loop. Sem bibliotecas ou chamadas ao backend. */
(function () {
  'use strict';

  var video = document.getElementById('nexo-demo-video');
  var frame = document.getElementById('nexo-demo-frame');
  var soundButton = document.getElementById('nexo-demo-sound-enable');
  var fullscreenButton = document.getElementById('nexo-demo-fullscreen');
  if (!video || !frame || !soundButton || !fullscreenButton) return;

  var soundAuthorized = false;
  var resumePending = false;

  function fullyVisible() {
    if (document.visibilityState !== 'visible') return false;

    var rect = video.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return false;

    var topLimit = 0;
    if (!document.fullscreenElement && !document.webkitFullscreenElement) {
      var header = document.querySelector('.nexo-header');
      if (header) {
        var headerRect = header.getBoundingClientRect();
        topLimit = Math.max(0, headerRect.bottom);
      }
    }

    // A tolerância ZERO é intencional: o áudio depende de 100% da área visível.
    return rect.top >= topLimit &&
      rect.left >= 0 &&
      rect.bottom <= window.innerHeight &&
      rect.right <= document.documentElement.clientWidth;
  }

  function syncSound() {
    var visible = fullyVisible();
    if (!visible) {
      video.muted = true;
      soundButton.hidden = true;
      return;
    }

    if (!soundAuthorized) {
      video.muted = true;
      soundButton.hidden = false;
      return;
    }

    soundButton.hidden = true;
    video.muted = false;

    // O Safari pode pausar o player quando o áudio muda fora de um gesto.
    if (video.paused && !resumePending) {
      resumePending = true;
      var resume = video.play();
      if (resume && typeof resume.then === 'function') {
        resume.then(function () { resumePending = false; }).catch(function () {
          resumePending = false;
          soundAuthorized = false;
          video.muted = true;
          soundButton.hidden = !fullyVisible();
        });
      } else {
        resumePending = false;
      }
    }
  }

  function activateSound() {
    if (!fullyVisible()) return;
    video.muted = false;
    video.volume = 1;

    // play() ocorre DENTRO do clique para satisfazer o gesto exigido pelo navegador.
    var started;
    try {
      started = video.play();
    } catch (error) {
      video.muted = true;
      return;
    }
    if (started && typeof started.then === 'function') {
      started.then(function () {
        soundAuthorized = true;
        syncSound();
      }).catch(function () {
        soundAuthorized = false;
        video.muted = true;
        syncSound();
      });
    } else {
      soundAuthorized = true;
      syncSound();
    }
  }

  function syncFullscreenLabel() {
    var isFullscreen = document.fullscreenElement === frame ||
      document.webkitFullscreenElement === frame;
    var label = isFullscreen ? 'Sair da tela cheia' : 'Expandir vídeo para tela cheia';
    fullscreenButton.setAttribute('aria-label', label);
    fullscreenButton.title = label;
    syncSound();
  }

  soundButton.addEventListener('click', activateSound);
  fullscreenButton.addEventListener('click', function () {
    if (document.fullscreenElement === frame || document.webkitFullscreenElement === frame) {
      var exit = document.exitFullscreen || document.webkitExitFullscreen;
      if (exit) {
        var exiting = exit.call(document);
        if (exiting && typeof exiting.catch === 'function') exiting.catch(function () {});
      }
      return;
    }

    if (frame.requestFullscreen || frame.webkitRequestFullscreen) {
      try {
        var request = (frame.requestFullscreen || frame.webkitRequestFullscreen).call(frame);
        if (request && typeof request.catch === 'function') request.catch(function () {});
      } catch (error) {
        fullscreenButton.hidden = true;
      }
    } else if (typeof video.webkitEnterFullscreen === 'function') {
      // Fallback iOS: a interface nativa pode mostrar controles extras.
      video.webkitEnterFullscreen();
    } else {
      fullscreenButton.hidden = true;
    }
  });

  if (typeof IntersectionObserver === 'function') {
    var observer = new IntersectionObserver(function () {
      syncSound();
    }, { threshold: [0, 1] });
    observer.observe(video);
  }

  window.addEventListener('scroll', syncSound, { passive: true });
  window.addEventListener('resize', syncSound);
  window.addEventListener('orientationchange', syncSound);
  window.addEventListener('pageshow', syncSound);
  document.addEventListener('visibilitychange', syncSound);
  document.addEventListener('fullscreenchange', syncFullscreenLabel);
  document.addEventListener('webkitfullscreenchange', syncFullscreenLabel);
  video.addEventListener('webkitendfullscreen', syncSound);
  video.addEventListener('playing', syncSound);
  syncSound();
})();