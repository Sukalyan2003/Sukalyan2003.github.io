/* The Record - all of the site's JavaScript.
 *
 * Three jobs, all progressive enhancement:
 *   1. Theme toggle between Paper (light) and Press (dark).
 *   2. Tap-to-reveal on the portrait, because touch devices have no hover.
 *   3. Marking the current section in the contents strip while scrolling.
 *
 * The page is fully readable with this file blocked. Nothing here renders
 * content; the FOUC guard that applies a stored theme before first paint is
 * inline in <head>, not in this deferred file.
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'the-record-theme';
  var root = document.documentElement;

  /* ---------------------------------------------------------------- theme */
  var toggle = document.getElementById('theme-toggle');

  function systemPrefersDark() {
    return window.matchMedia &&
      window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  function currentTheme() {
    return root.dataset.theme || (systemPrefersDark() ? 'dark' : 'light');
  }

  function paint(theme) {
    var label = toggle.querySelector('[data-theme-label]');
    var isDark = theme === 'dark';
    if (label) label.textContent = isDark ? 'Press' : 'Paper';
    toggle.setAttribute('aria-pressed', String(isDark));
    toggle.setAttribute(
      'aria-label',
      'Theme: ' + (isDark ? 'Press (dark)' : 'Paper (light)') +
      '. Switch to ' + (isDark ? 'Paper' : 'Press') + '.'
    );
  }

  if (toggle) {
    paint(currentTheme());

    toggle.addEventListener('click', function () {
      var next = currentTheme() === 'dark' ? 'light' : 'dark';
      root.dataset.theme = next;
      paint(next);
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch (err) {
        /* Private mode or blocked storage: the choice just won't persist. */
      }
    });

    // If the visitor has never chosen explicitly, follow the OS if it changes.
    if (window.matchMedia) {
      var query = window.matchMedia('(prefers-color-scheme: dark)');
      var onChange = function () {
        var stored = null;
        try {
          stored = localStorage.getItem(STORAGE_KEY);
        } catch (err) { /* ignore */ }
        if (!stored) {
          delete root.dataset.theme;
          paint(currentTheme());
        }
      };
      if (query.addEventListener) query.addEventListener('change', onChange);
      else if (query.addListener) query.addListener(onChange);
    }
  }

  /* -------------------------------------------------------------- contents */
  /* Marks which section the reader is in. Without this the strip is still a
     working set of anchors, which is why nothing here renders content. */
  var marks = [].slice.call(document.querySelectorAll('.contents__list a[href^="#"]'));
  if (marks.length && 'IntersectionObserver' in window) {
    var byId = {};
    var targets = [];
    marks.forEach(function (link) {
      var section = document.getElementById(link.getAttribute('href').slice(1));
      if (section) {
        byId[section.id] = link;
        targets.push(section);
      }
    });

    var visible = {};
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        visible[entry.target.id] = entry.isIntersecting;
      });
      var current = null;
      targets.forEach(function (section) {
        if (visible[section.id]) current = current || section.id;
      });
      marks.forEach(function (link) {
        link.classList.remove('is-current');
      });
      if (current && byId[current]) byId[current].classList.add('is-current');
    }, { rootMargin: '-60px 0px -55% 0px' });

    targets.forEach(function (section) {
      observer.observe(section);
    });
  }

  /* -------------------------------------------------------------- portrait */
  var portrait = document.querySelector('.portrait');
  if (portrait && window.matchMedia && !window.matchMedia('(hover: hover)').matches) {
    portrait.addEventListener('click', function () {
      portrait.classList.toggle('is-revealed');
    });
  }
})();
