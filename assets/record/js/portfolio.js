/* Progressive enhancements. The reading path and evidence are static HTML. */
(function () {
  'use strict';

  document.querySelectorAll('[data-enhance]').forEach(function (element) {
    element.hidden = false;
  });

  var nav = document.querySelector('.site-nav');
  if (nav) {
    var measureNav = function () {
      document.documentElement.style.setProperty('--site-nav-h', nav.offsetHeight + 'px');
    };
    measureNav();
    if ('ResizeObserver' in window) new ResizeObserver(measureNav).observe(nav);
    else window.addEventListener('resize', measureNav);
  }

  var portrait = document.querySelector('.portrait[role="button"]');
  if (portrait) {
    var revealPortrait = function () {
      var revealed = portrait.classList.toggle('is-revealed');
      portrait.setAttribute('aria-pressed', String(revealed));
    };
    // Pointer and keyboard use the same state; hover remains a CSS enhancement.
    portrait.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        revealPortrait();
      }
    });
    portrait.addEventListener('click', revealPortrait);
  }

  var filters = document.querySelector('.work-filters');
  if (filters) {
    var entries = Array.from(document.querySelectorAll('.work-list .work-entry'));
    var counter = document.querySelector('[data-filter-count]');
    filters.addEventListener('click', function (event) {
      var button = event.target.closest('[data-filter]');
      if (!button) return;
      var selected = button.dataset.filter;
      filters.querySelectorAll('button').forEach(function (item) {
        item.setAttribute('aria-pressed', String(item === button));
      });
      var count = 0;
      entries.forEach(function (entry) {
        entry.hidden = selected !== 'all' && entry.dataset.category !== selected;
        if (!entry.hidden) count += 1;
      });
      counter.textContent = count + (count === 1 ? ' project' : ' projects');
      document.querySelector('[data-work-empty]').hidden = count > 0;
    });
  }

  var windowDemo = document.querySelector('[data-demo="window"]');
  if (windowDemo) {
    var start = windowDemo.querySelector('input');
    var windowOutput = windowDemo.querySelector('output');
    var region = windowDemo.querySelector('[data-window-region]');
    var description = windowDemo.querySelector('desc');
    var updateWindow = function () {
      var value = Number(start.value);
      windowOutput.value = value + '–' + (value + 16) + ' s';
      region.setAttribute('x', String(value * 10));
      description.textContent = 'Synthetic trace: selected read window from ' + value + ' to ' + (value + 16) + ' seconds in a sixty-second strip.';
    };
    start.addEventListener('input', updateWindow);
    windowDemo.querySelector('[data-reset]').addEventListener('click', function () {
      start.value = '8';
      updateWindow();
    });
    updateWindow();
  }

  var ablation = document.querySelector('[data-demo="leakage"]');
  if (ablation) {
    ablation.addEventListener('change', function () {
      var leaked = ablation.querySelector('input[value="leaked"]').checked;
      ablation.querySelector('output').value = leaked ? '0.925' : '~0.15';
      ablation.querySelector('[data-ablation-bar]').setAttribute('width', leaked ? '555' : '90');
      ablation.querySelector('svg').setAttribute('aria-label', 'Recorded R squared comparison, ' + (leaked ? '0.925 with the unavailable feature' : 'approximately 0.15 using quote-time inputs'));
      ablation.querySelector('.ablation-readout > span').textContent = leaked ? 'Reported comparison with the unavailable feature · R²' : 'Quote-time comparison · R²';
      ablation.querySelector('[data-ablation-explanation]').textContent = leaked
        ? 'The reported R² of 0.925 used realised annual medical cost: a field that does not exist when a new applicant receives a quote. The stronger score does not make that input usable.'
        : 'Realised annual cost is not available for a new applicant at quote time. The fixed-model ablation put the quote-time result near R² 0.15.';
    });
  }

  var dialog = document.querySelector('.figure-dialog');
  if (dialog && typeof dialog.showModal === 'function') {
    document.querySelectorAll('[data-expand-figure]').forEach(function (button) {
      button.addEventListener('click', function () {
        var figure = button.previousElementSibling;
        if (!figure || !figure.matches('figure')) return;
        var copy = figure.cloneNode(true);
        // A cloned diagram must not duplicate IDs or accessible-name references.
        copy.querySelectorAll('[id]').forEach(function (element) {
          var oldId = element.id;
          var newId = 'expanded-' + oldId;
          copy.querySelectorAll('[aria-labelledby]').forEach(function (labelled) {
            labelled.setAttribute('aria-labelledby', labelled.getAttribute('aria-labelledby').split(' ').map(function (id) { return id === oldId ? newId : id; }).join(' '));
          });
          element.id = newId;
        });
        dialog.querySelector('[data-figure-content]').replaceChildren(copy);
      });
    });
  }

  // All three dialogs share the same opening, dismissal and focus behaviour.
  document.querySelectorAll('dialog').forEach(function (modal) {
    var openers = document.querySelectorAll('[data-open-dialog="' + modal.id + '"]');
    if (typeof modal.showModal !== 'function') {
      openers.forEach(function (button) { button.hidden = true; });
      return;
    }
    var returnTo;
    openers.forEach(function (button) {
      button.addEventListener('click', function () {
        if (document.querySelector('dialog[open]')) return;
        returnTo = document.activeElement;
        modal.showModal();
        document.body.classList.add('has-modal');
      });
    });
    modal.querySelectorAll('[data-dialog-close]').forEach(function (button) {
      button.addEventListener('click', function () { modal.close(); });
    });
    modal.addEventListener('click', function (event) {
      if (event.target !== modal) return;
      var rect = modal.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right ||
          event.clientY < rect.top || event.clientY > rect.bottom) modal.close();
    });
    modal.addEventListener('close', function () {
      if (document.querySelector('dialog[open]')) return;
      document.body.classList.remove('has-modal');
      if (returnTo && returnTo.isConnected) returnTo.focus();
    });
  });

  var contents = document.querySelector('.case-contents');
  if (contents && 'IntersectionObserver' in window) {
    var contentsLinks = Array.from(contents.querySelectorAll('a[href^="#"]'));
    var observed = {};
    var observer = new IntersectionObserver(function (changes) {
      changes.forEach(function (change) { observed[change.target.id] = change.isIntersecting; });
      var current = contentsLinks.find(function (link) { return observed[link.hash.slice(1)]; });
      if (!current) return;
      contentsLinks.forEach(function (link) {
        if (link === current) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
      });
    }, { rootMargin: '-90px 0px -45% 0px' });
    contentsLinks.forEach(function (link) {
      var target = document.getElementById(link.hash.slice(1));
      if (target) observer.observe(target);
    });
  }
})();
