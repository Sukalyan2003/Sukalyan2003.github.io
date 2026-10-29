/* Browser-local ways to explore the portfolio. No requests, analytics or audio. */
(function () {
  'use strict';

  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  // One tab stop enters the map. Arrow keys visit its other projects.
  var map = document.querySelector('.project-map');
  if (map) {
    var nodes = Array.from(map.querySelectorAll('[data-project]'));
    var edges = Array.from(map.querySelectorAll('[data-connection]'));
    var detail = document.querySelector('#map-detail');
    function selectProject(button, announce) {
      var slug = button.dataset.project;
      var relations = [];
      var related = new Set();
      edges.forEach(function (edge) {
        var active = edge.dataset.from === slug || edge.dataset.to === slug;
        edge.classList.toggle('is-connected', active);
        if (active) {
          related.add(edge.dataset.from === slug ? edge.dataset.to : edge.dataset.from);
          relations.push(edge.dataset.connection);
        }
      });
      nodes.forEach(function (node) {
        node.setAttribute('aria-pressed', String(node === button));
        node.tabIndex = node === button ? 0 : -1;
        node.classList.toggle('is-related', related.has(node.dataset.project));
      });
      var template = document.querySelector('[data-project-card="' + slug + '"]');
      detail.replaceChildren(template.content.cloneNode(true));
      if (!reducedMotion.matches) detail.animate([{ opacity: .25, transform: 'translateY(7px)' }, { opacity: 1, transform: 'translateY(0)' }], { duration: 180 });
      document.querySelector('[data-map-connections]').textContent = relations.length
        ? 'Connections: ' + Array.from(new Set(relations)).join(' · ')
        : 'Open the project to read more.';
      if (announce) document.querySelector('[data-map-status]').textContent = button.textContent.trim() + ' selected. ' + relations.join(', ') + '.';
    }
    nodes.forEach(function (node, index) {
      node.addEventListener('click', function () { selectProject(node, true); });
      node.addEventListener('pointerenter', function (event) { if (event.pointerType === 'mouse') selectProject(node, false); });
      node.addEventListener('focus', function () { selectProject(node, true); });
      node.addEventListener('keydown', function (event) {
        var offset = { ArrowRight: 1, ArrowLeft: -1, ArrowDown: 3, ArrowUp: -3 }[event.key];
        if (!offset) return;
        event.preventDefault();
        nodes[(index + offset + nodes.length) % nodes.length].focus();
      });
    });
    selectProject(nodes[0], false);
  }

  var find = document.querySelector('#find-dialog');
  if (find) {
    var search = find.querySelector('#site-query');
    var results = find.querySelector('#find-results');
    var entries = JSON.parse(document.querySelector('#find-index').textContent);
    var normalise = function (value) { return value.toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, ''); };
    entries.forEach(function (entry) { entry.search = normalise(entry.title + ' ' + entry.terms); });
    function searchSite() {
      var tokens = normalise(search.value).trim().split(/\s+/).filter(Boolean);
      var matches = entries.filter(function (entry) { return tokens.every(function (word) { return entry.search.indexOf(word) !== -1; }); });
      if (tokens.length) matches.sort(function (a, b) {
        var q = normalise(search.value).trim();
        return Number(normalise(b.title).indexOf(q) !== -1) - Number(normalise(a.title).indexOf(q) !== -1);
      });
      results.replaceChildren();
      matches.slice(0, 12).forEach(function (entry) {
        var item = document.createElement('li');
        var link = document.createElement('a');
        var kind = document.createElement('span');
        link.href = entry.url;
        kind.className = 'eyebrow';
        kind.textContent = entry.kind;
        link.append(kind, document.createTextNode(entry.title));
        item.append(link);
        results.append(item);
      });
      find.querySelector('[data-find-empty]').hidden = matches.length > 0;
      find.querySelector('#find-count').textContent = matches.length === 0 ? 'No results' : (matches.length > 12 ? 'First 12 of ' + matches.length + ' results' : matches.length + (matches.length === 1 ? ' result' : ' results'));
    }
    var findButton = document.querySelector('[data-open-find]');
    findButton.addEventListener('click', function () {
      if (!find.open) return;
      searchSite();
      search.focus();
      search.select();
    });
    search.addEventListener('input', searchSite);
    find.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        event.preventDefault();
        find.close();
        return;
      }
      var links = Array.from(results.querySelectorAll('a'));
      var index = links.indexOf(document.activeElement);
      if (event.key === 'ArrowDown' && links.length) {
        event.preventDefault();
        links[(index + 1) % links.length].focus();
      } else if (event.key === 'ArrowUp' && index !== -1) {
        event.preventDefault();
        if (index === 0) search.focus();
        else links[index - 1].focus();
      } else if (event.key === 'Enter' && document.activeElement === search && links.length) {
        event.preventDefault();
        links[0].click();
      }
    });
    document.addEventListener('keydown', function (event) {
      var editing = event.target.closest('input, textarea, select, [contenteditable="true"]');
      var shortcut = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k';
      if (shortcut || (!editing && event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey)) {
        event.preventDefault();
        if (!findButton.hidden) findButton.click();
      }
    });
  }

  var press = document.querySelector('#print-dialog');
  if (press) {
    var canvas = press.querySelector('canvas');
    var context = canvas.getContext('2d');
    var photograph = document.querySelector('.portrait__colour img');
    var spacing = press.querySelector('#print-spacing');
    var contrast = press.querySelector('#print-contrast');
    var photoButton = press.querySelector('[data-print-photo]');
    // Easter egg: typing "press" outside a form field opens the printing press.
    var pressOpener = document.querySelector('[data-open-print]');
    var typed = '';
    document.addEventListener('keydown', function (event) {
      if (!pressOpener || event.ctrlKey || event.metaKey || event.altKey || event.key.length !== 1) return;
      if (event.target.closest && event.target.closest('input, textarea, select, [contenteditable]')) return;
      typed = (typed + event.key.toLowerCase()).slice(-5);
      if (typed === 'press') { typed = ''; pressOpener.click(); }
    });
    var pixels = null;
    var photoMode = false;
    var ready = false;
    var sample = document.createElement('canvas');
    sample.width = sample.height = 440;
    var sampler = sample.getContext('2d', { willReadFrequently: true });

    function drawPrint() {
      if (!ready || !context) return;
      press.querySelector('#print-spacing-value').value = spacing.value + ' px';
      press.querySelector('#print-contrast-value').value = Number(contrast.value).toFixed(1) + '×';
      if (photoMode) {
        context.drawImage(photograph, 0, 0, 440, 440);
        canvas.setAttribute('aria-label', 'Colour photograph of Sukalyan Roy');
        return;
      }
      var palette = getComputedStyle(document.documentElement);
      context.fillStyle = palette.getPropertyValue('--paper').trim();
      context.fillRect(0, 0, 440, 440);
      var red = press.querySelector('input[value="red"]').checked;
      context.fillStyle = palette.getPropertyValue(red ? '--signal' : '--ink').trim();
      var step = Number(spacing.value);
      var gain = Number(contrast.value);
      for (var y = step / 2; y < 440; y += step) {
        for (var x = step / 2; x < 440; x += step) {
          var offset = (Math.floor(y) * 440 + Math.floor(x)) * 4;
          var light = (pixels[offset] * .2126 + pixels[offset + 1] * .7152 + pixels[offset + 2] * .0722) / 255;
          var darkness = Math.max(0, Math.min(1, (1 - light - .5) * gain + .5));
          var radius = Math.sqrt(darkness) * step * .5;
          context.beginPath();
          context.arc(x, y, radius, 0, Math.PI * 2);
          context.fill();
        }
      }
      canvas.setAttribute('aria-label', (red ? 'Red' : 'Black') + ' ink portrait of Sukalyan Roy, ' + step + ' pixel dot spacing, contrast ' + gain.toFixed(1));
    }
    function loadPhoto() {
      if (ready) { drawPrint(); return; }
      var controls = press.querySelectorAll('.print-settings input, .print-settings button');
      controls.forEach(function (control) { control.disabled = true; });
      photograph.decode().then(function () {
        sampler.drawImage(photograph, 0, 0, 440, 440);
        pixels = sampler.getImageData(0, 0, 440, 440).data;
        ready = true;
        canvas.hidden = false;
        press.querySelector('[data-print-loading]').hidden = true;
        controls.forEach(function (control) { control.disabled = false; });
        drawPrint();
      }).catch(function () {
        press.querySelector('[data-print-loading]').textContent = 'The photograph could not be loaded. You can still view the portrait on the page.';
      });
    }
    if (context && sampler) document.querySelector('[data-open-print]').addEventListener('click', function () {
      if (press.open) loadPhoto();
    });
    else document.querySelector('[data-open-print]').hidden = true;
    press.addEventListener('input', drawPrint);
    photoButton.addEventListener('click', function () {
      photoMode = !photoMode;
      photoButton.setAttribute('aria-pressed', String(photoMode));
      photoButton.textContent = photoMode ? 'Show halftone' : 'Show photograph';
      spacing.disabled = contrast.disabled = photoMode;
      press.querySelectorAll('[name="print-ink"]').forEach(function (input) { input.disabled = photoMode; });
      drawPrint();
    });
    press.querySelector('[data-print-reset]').addEventListener('click', function () {
      spacing.value = '8';
      contrast.value = '1';
      press.querySelector('input[value="black"]').checked = true;
      if (photoMode) photoButton.click();
      drawPrint();
    });
    press.querySelector('[data-print-save]').addEventListener('click', function () {
      if (!ready) return;
      canvas.toBlob(function (blob) {
        if (!blob) return;
        var url = URL.createObjectURL(blob);
        var link = document.createElement('a');
        link.download = 'sukalyan-roy-' + (photoMode ? 'portrait' : 'halftone') + '.png';
        link.href = url;
        link.click();
        setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
      }, 'image/png');
    });
    new MutationObserver(function () { if (press.open) drawPrint(); }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () { if (press.open) drawPrint(); });
  }

  // Remote covers and posters fall back to the text card if they fail to load.
  document.querySelectorAll('img[data-remote-img]').forEach(function (img) {
    function missing() { img.closest('[data-img-box]').classList.add('is-missing'); }
    if (img.complete && img.currentSrc && img.naturalWidth === 0) missing();
    else img.addEventListener('error', missing);
  });

  // Shelves show the first rows; "Show all" extends the grid downward.
  var SHELF_LIMIT = 15;
  document.querySelectorAll('[data-shelf]').forEach(function (shelf) {
    var allItems = Array.from(shelf.querySelectorAll('[data-shelf-item]'));
    var filter = shelf.querySelector('[data-film-filter]');
    var more = shelf.querySelector('[data-shelf-more]');
    var expanded = false;
    function matching() {
      return allItems.filter(function (item) { return !filter || filter.value === 'all' || item.dataset.filmType === filter.value; });
    }
    function render() {
      var items = matching();
      allItems.forEach(function (item) { item.hidden = true; });
      items.forEach(function (item, i) { item.hidden = !expanded && i >= SHELF_LIMIT; });
      more.hidden = items.length <= SHELF_LIMIT;
      more.setAttribute('aria-expanded', String(expanded));
      more.textContent = expanded ? 'Show fewer' : 'Show all ' + items.length;
    }
    more.addEventListener('click', function () {
      expanded = !expanded;
      render();
      if (!expanded) shelf.scrollIntoView({ block: 'start', behavior: reducedMotion.matches ? 'instant' : 'smooth' });
    });
    if (filter) filter.addEventListener('change', render);
    var surprise = shelf.querySelector('[data-shelf-surprise]');
    if (surprise) surprise.addEventListener('click', function () {
      var items = matching();
      if (!items.length) return;
      var selected = items[Math.floor(Math.random() * items.length)];
      if (selected.hidden) { expanded = true; render(); }
      allItems.forEach(function (item) { item.classList.remove('is-picked'); });
      selected.classList.add('is-picked');
      selected.scrollIntoView({ block: 'center', behavior: reducedMotion.matches ? 'instant' : 'smooth' });
      selected.querySelector('a').focus({ preventScroll: true });
    });
    render();
  });

  var fusion = document.querySelector('.fusion-lab');
  if (fusion) {
    var defaults = { dense: ['cancel', 'window', 'queue', 'header'], sparse: ['window', 'header', 'cancel', 'queue'] };
    var orders = { dense: defaults.dense.slice(), sparse: defaults.sparse.slice() };
    var labels = {};
    fusion.querySelectorAll('[data-ranking="dense"] li').forEach(function (row) { labels[row.dataset.doc] = row.children[1].textContent; });
    var rankedRows = Array.from(fusion.querySelectorAll('[data-result]'));
    var resultList = fusion.querySelector('.fusion-results');

    function updateFusion(announce) {
      var active = ['dense', 'sparse'].filter(function (key) { return fusion.querySelector('[data-retriever="' + key + '"]').checked; });
      var wasVisible = !resultList.hidden;
      var previous = new Map();
      rankedRows.forEach(function (row) { row.getAnimations().forEach(function (animation) { animation.cancel(); }); previous.set(row.dataset.result, row.getBoundingClientRect().top); });
      var ranked = rankedRows.map(function (row) {
        var id = row.dataset.result;
        var score = active.reduce(function (total, key) { return total + 1 / (61 + orders[key].indexOf(id)); }, 0);
        return { id: id, score: score, row: row };
      }).sort(function (a, b) { return b.score - a.score || a.id.localeCompare(b.id); });
      ranked.forEach(function (item) {
        item.row.querySelector('output').value = item.score.toFixed(6);
        item.row.querySelector('[data-result-ranks]').textContent = active.map(function (key) { return (key === 'dense' ? 'Semantic #' : 'Exact-term #') + (orders[key].indexOf(item.id) + 1); }).join(' · ');
        item.row.querySelector('rect').setAttribute('width', String(item.score / .04 * 200));
        resultList.append(item.row);
      });
      resultList.hidden = active.length === 0;
      fusion.querySelector('[data-fusion-empty]').hidden = active.length > 0;
      var winner = ranked[0];
      var formula = active.map(function (key) { return '1 / (60 + ' + (orders[key].indexOf(winner.id) + 1) + ')'; }).join(' + ');
      fusion.querySelector('[data-fusion-formula]').textContent = active.length ? 'Top result: ' + formula + ' = ' + winner.score.toFixed(6) : 'No retrievers enabled.';
      if (announce) fusion.querySelector('[data-fusion-status]').textContent = active.length ? labels[winner.id] + ' ranks first with score ' + winner.score.toFixed(6) + '.' : 'No retrievers enabled.';
      if (!reducedMotion.matches && active.length && wasVisible) ranked.forEach(function (item) {
        var change = previous.get(item.id) - item.row.getBoundingClientRect().top;
        if (change) item.row.animate([{ transform: 'translateY(' + change + 'px)' }, { transform: 'translateY(0)' }], { duration: 260, easing: 'ease-out' });
      });
    }
    function syncRanking(key, focusId) {
      var list = fusion.querySelector('[data-ranking="' + key + '"]');
      orders[key].forEach(function (id, index) {
        var row = list.querySelector('[data-doc="' + id + '"]');
        row.querySelector('.rank-position').textContent = String(index + 1).padStart(2, '0');
        row.querySelector('button').disabled = index === 0;
        list.append(row);
      });
      updateFusion(true);
      if (focusId) {
        var selected = list.querySelector('[data-doc="' + focusId + '"]');
        var button = selected.querySelector('button');
        (button.disabled ? selected : button).focus({ preventScroll: true });
      }
    }
    fusion.querySelectorAll('[data-ranking]').forEach(function (list) {
      var key = list.dataset.ranking;
      list.querySelectorAll('li').forEach(function (row) { row.draggable = true; });
      list.addEventListener('click', function (event) {
        var button = event.target.closest('[data-move-up]');
        if (!button || button.disabled) return;
        var id = button.dataset.moveUp;
        var index = orders[key].indexOf(id);
        orders[key].splice(index, 1);
        orders[key].splice(index - 1, 0, id);
        syncRanking(key, id);
      });
      list.addEventListener('dragstart', function (event) {
        var row = event.target.closest('[data-doc]');
        event.dataTransfer.setData('text/plain', key + '/' + row.dataset.doc);
        event.dataTransfer.effectAllowed = 'move';
        row.classList.add('is-dragging');
      });
      list.addEventListener('dragend', function () { list.querySelectorAll('li').forEach(function (row) { row.classList.remove('is-dragging', 'is-drop-target'); }); });
      list.addEventListener('dragover', function (event) { event.preventDefault(); event.dataTransfer.dropEffect = 'move'; });
      list.addEventListener('dragenter', function (event) { event.preventDefault(); var row = event.target.closest('[data-doc]'); if (row) row.classList.add('is-drop-target'); });
      list.addEventListener('dragleave', function (event) { var row = event.target.closest('[data-doc]'); if (row) row.classList.remove('is-drop-target'); });
      list.addEventListener('drop', function (event) {
        event.preventDefault();
        var source = event.dataTransfer.getData('text/plain').split('/');
        var target = event.target.closest('[data-doc]');
        if (source[0] !== key || !target || orders[key].indexOf(source[1]) === -1) return;
        var from = orders[key].indexOf(source[1]);
        var to = orders[key].indexOf(target.dataset.doc);
        orders[key].splice(from, 1);
        orders[key].splice(to, 0, source[1]);
        syncRanking(key, source[1]);
        list.querySelectorAll('li').forEach(function (row) { row.classList.remove('is-dragging', 'is-drop-target'); });
      });
    });
    fusion.querySelectorAll('[data-retriever]').forEach(function (input) { input.addEventListener('change', function () { updateFusion(true); }); });
    fusion.querySelector('[data-fusion-reset]').addEventListener('click', function () {
      orders.dense = defaults.dense.slice();
      orders.sparse = defaults.sparse.slice();
      fusion.querySelectorAll('[data-retriever]').forEach(function (input) { input.checked = true; });
      syncRanking('dense');
      syncRanking('sparse');
    });
    updateFusion(false);
  }
})();
