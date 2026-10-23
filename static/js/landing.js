/* Landing de Kiba X: tema, filtro del odontograma y apariciones.
   Sin dependencias y sin frameworks, igual que el resto de la app. */
(function () {
  'use strict';

  /* ---------- Modo oscuro ---------- */
  var themeToggle = document.getElementById('themeToggle');

  function syncThemeLabel() {
    if (!themeToggle) return;
    var dark = document.body.classList.contains('dark');
    themeToggle.setAttribute('aria-label', dark ? 'Cambiar a modo claro' : 'Cambiar modo oscuro');
    themeToggle.setAttribute('title', dark ? 'Modo claro' : 'Modo oscuro');
  }

  if (themeToggle) {
    syncThemeLabel();
    themeToggle.addEventListener('click', function () {
      document.body.classList.toggle('dark');
      var dark = document.body.classList.contains('dark');
      localStorage.setItem('theme', dark ? 'dark' : 'light');
      syncThemeLabel();
    });
  }

  /* ---------- Navegación: borde al scrollear ---------- */
  var nav = document.querySelector('.landing-nav');
  if (nav) {
    var onScroll = function () {
      nav.classList.toggle('is-scrolled', window.scrollY > 10);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  /* ---------- Odontograma de demostración ---------- */
  var odontograph = document.querySelector('[data-demo-odontogram]');
  var readout = document.getElementById('demoReadout');

  if (odontograph && readout) {
    var chips = Array.prototype.slice.call(odontograph.querySelectorAll('.state-chip'));
    var faceStates = ['caries', 'obturado'];
    var copy = {
      caries: {
        kind: 'face',
        note: 'Caries activa en caras oclusal, mesial, vestibular y distal.'
      },
      obturado: {
        kind: 'face',
        note: 'Restauraciones previas registradas por cara.'
      },
      corona: {
        kind: 'tooth',
        note: 'Coronas con historial y estudios adjuntos.'
      },
      endodoncia: {
        kind: 'tooth',
        note: 'Tratamientos de conducto documentados.'
      },
      implante: {
        kind: 'tooth',
        note: 'Implantes con seguimiento fotográfico.'
      },
      ausente: {
        kind: 'tooth',
        note: 'Ausencias registradas, incluidas las de la dentición temporaria.'
      }
    };

    var resetReadout = function () {
      readout.textContent = 'Elegí un estado para ver los hallazgos de esta ficha de ejemplo.';
    };

    var clearMarks = function () {
      var marks = odontograph.querySelectorAll('.face, .tooth-overlay');
      Array.prototype.forEach.call(marks, function (mark) {
        mark.classList.remove('is-dim', 'is-match');
      });
    };

    var plural = function (n, one, many) {
      return n === 1 ? one : many;
    };

    var filterBy = function (state) {
      var info = copy[state];
      if (!info) return;
      var teeth = odontograph.querySelectorAll('.demo-tooth');
      var matches = [];
      var faces = 0;

      Array.prototype.forEach.call(teeth, function (tooth) {
        var toothMatch = false;
        var toothFaces = tooth.querySelectorAll('.face');
        var overlays = tooth.querySelectorAll('.tooth-overlay');

        if (info.kind === 'face') {
          Array.prototype.forEach.call(toothFaces, function (face) {
            var match = face.classList.contains('status-' + state);
            face.classList.toggle('is-match', match);
            face.classList.toggle('is-dim', !match);
            if (match) {
              faces += 1;
              toothMatch = true;
            }
          });
          Array.prototype.forEach.call(overlays, function (overlay) {
            overlay.classList.remove('is-match');
            overlay.classList.add('is-dim');
          });
        } else {
          toothMatch = tooth.getAttribute('data-general') === state;
          Array.prototype.forEach.call(toothFaces, function (face) {
            face.classList.toggle('is-match', toothMatch);
            face.classList.toggle('is-dim', !toothMatch);
          });
          Array.prototype.forEach.call(overlays, function (overlay) {
            overlay.classList.toggle('is-match', toothMatch);
            overlay.classList.toggle('is-dim', !toothMatch);
          });
        }

        if (toothMatch) matches.push(tooth.getAttribute('data-tooth'));
      });

      var label = state.charAt(0).toUpperCase() + state.slice(1);
      var amount = info.kind === 'face'
        ? faces + ' ' + plural(faces, 'cara', 'caras') + ' en ' +
          matches.length + ' ' + plural(matches.length, 'diente', 'dientes')
        : matches.length + ' ' + plural(matches.length, 'diente', 'dientes');

      readout.innerHTML = '<strong>' + label + '</strong> · ' + amount + '. ' + info.note;
    };

    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        var state = chip.getAttribute('data-state');
        var wasActive = chip.getAttribute('aria-pressed') === 'true';

        chips.forEach(function (other) {
          other.setAttribute('aria-pressed', 'false');
        });
        clearMarks();

        if (wasActive) {
          resetReadout();
          return;
        }

        chip.setAttribute('aria-pressed', 'true');
        filterBy(state);
      });
    });
  }

  /* ---------- Apariciones al scrollear ---------- */
  var revealItems = Array.prototype.slice.call(document.querySelectorAll('.reveal'));
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (!revealItems.length) return;
  if (reduced || !('IntersectionObserver' in window)) {
    revealItems.forEach(function (item) { item.classList.add('is-in'); });
    return;
  }

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-in');
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

  revealItems.forEach(function (item) { observer.observe(item); });
})();
