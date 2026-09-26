/* Engineering Tales - blog enhancements.
 *
 * Every job here is progressive enhancement; each page is complete without
 * this file:
 *   1. "More" menu closes on Escape and outside click (it opens natively).
 *   2. Copy buttons on code blocks.
 *   3. Share: native share sheet and copy-link (static share links always work).
 *   4. Contents: open beside the text on wide screens, mark the heading being read.
 *   5. Search and filters over /blog/search.json (static section and tag
 *      pages cover the same ground without JavaScript).
 *   6. Load giscus comments, and keep their theme in step with Paper/Press.
 */
(function () {
  'use strict';

  var root = document.documentElement;

  /* ------------------------------------------------------------ more menu */
  var more = document.querySelector('.more-menu details');
  if (more) {
    document.addEventListener('click', function (event) {
      if (more.open && !more.contains(event.target)) more.open = false;
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && more.open) {
        more.open = false;
        more.querySelector('summary').focus();
      }
    });
  }

  function announce(output, message) {
    if (!output) return;
    output.textContent = message;
    window.setTimeout(function () { output.textContent = ''; }, 2500);
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      var area = document.createElement('textarea');
      area.value = text;
      area.setAttribute('readonly', '');
      area.className = 'visually-hidden';
      document.body.appendChild(area);
      area.select();
      try {
        document.execCommand('copy') ? resolve() : reject(new Error('copy failed'));
      } catch (err) {
        reject(err);
      } finally {
        document.body.removeChild(area);
      }
    });
  }

  /* ----------------------------------------------------------------- code */
  [].forEach.call(document.querySelectorAll('.code-block'), function (block) {
    var bar = block.querySelector('.code-block__bar');
    var code = block.querySelector('pre code');
    if (!bar || !code) return;
    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'code-copy';
    button.textContent = 'Copy';
    button.setAttribute('aria-label', 'Copy code to clipboard');
    button.addEventListener('click', function () {
      copyText(code.textContent).then(function () {
        button.textContent = 'Copied';
      }, function () {
        button.textContent = 'Press Ctrl+C';
      });
      window.setTimeout(function () { button.textContent = 'Copy'; }, 2000);
    });
    bar.appendChild(button);
  });

  /* ---------------------------------------------------------------- share */
  var status = document.querySelector('[data-share-status]');
  var native = document.querySelector('[data-share]');
  if (native && navigator.share) {
    native.hidden = false;
    native.addEventListener('click', function () {
      navigator.share({ title: document.title, url: location.href.split('#')[0] })
        .catch(function () { /* dismissed */ });
    });
  }
  var copyLink = document.querySelector('[data-copy-link]');
  if (copyLink) {
    copyLink.hidden = false;
    copyLink.addEventListener('click', function () {
      copyText(copyLink.getAttribute('data-copy-link')).then(function () {
        announce(status, 'Link copied');
      }, function () {
        announce(status, 'Could not copy - use the address bar');
      });
    });
  }

  /* -------------------------------------------------------------- contents */
  var toc = document.querySelector('[data-toc]');
  if (toc) {
    // Rendered closed so nothing shifts on narrow screens, where it sits above
    // the text; on wide screens it lives in the side rail, so opening it moves
    // no content.
    if (window.matchMedia && window.matchMedia('(min-width: 1101px)').matches) {
      toc.open = true;
    }
    var links = [].slice.call(toc.querySelectorAll('a[href^="#"]'));
    var headings = links.map(function (link) {
      return document.getElementById(decodeURIComponent(link.getAttribute('href').slice(1)));
    });
    if ('IntersectionObserver' in window) {
      var visible = {};
      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) { visible[entry.target.id] = entry.isIntersecting; });
        var current = -1;
        headings.forEach(function (h, i) { if (h && visible[h.id] && current === -1) current = i; });
        if (current === -1) return;
        links.forEach(function (link, i) { link.classList.toggle('is-active', i === current); });
      }, { rootMargin: '-64px 0px -60% 0px' });
      headings.forEach(function (h) { if (h) observer.observe(h); });
    }
  }

  /* --------------------------------------------------------------- search */
  var finder = document.querySelector('[data-finder]');
  if (finder && window.fetch) {
    var input = finder.querySelector('#finder-q');
    var sectionSelect = finder.querySelector('#finder-section');
    var tagSelect = finder.querySelector('#finder-tag');
    var results = document.querySelector('[data-finder-results]');
    var archive = document.querySelector('[data-archive]');
    var finderStatus = document.querySelector('[data-finder-status]');
    var records = null;
    finder.hidden = false;

    var params = new URLSearchParams(location.search);
    if (params.get('q')) input.value = params.get('q');
    if (params.get('section')) sectionSelect.value = params.get('section');
    if (params.get('tag')) tagSelect.value = params.get('tag');

    // The finder lives on /blog/ only; records carry root-absolute URLs
    // ("/blog/slug/"), made relative to this page so any server root works.
    var local = function (url) { return url.replace(/^\/blog\//, ''); };

    var el = function (tag, cls, text) {
      var node = document.createElement(tag);
      if (cls) node.className = cls;
      if (text != null) node.textContent = text;
      return node;
    };

    var renderRow = function (post) {
      var li = el('li', 'dispatch');
      var date = el('div', 'dispatch__date');
      var time = el('time', null, post.dateLabel);
      time.setAttribute('datetime', post.date);
      date.appendChild(time);
      date.appendChild(el('span', 'dispatch__read', post.minutes + ' min read'));
      var body = el('div', 'dispatch__body');
      var kicker = el('p', 'dispatch__kicker');
      var sectionLink = el('a', null, post.sectionLabel);
      sectionLink.href = post.section + '/';
      kicker.appendChild(sectionLink);
      var h3 = el('h3');
      var link = el('a', null, post.title);
      link.href = local(post.url);
      h3.appendChild(link);
      body.appendChild(kicker);
      body.appendChild(h3);
      if (post.summary) body.appendChild(el('p', null, post.summary));
      if (post.tags.length) {
        var tags = el('div', 'tags');
        post.tags.slice(0, 4).forEach(function (t) {
          var a = el('a', 'tag', t.label);
          a.href = 'tags/' + t.slug + '/';
          tags.appendChild(a);
        });
        var meta = el('div', 'dispatch__meta');
        meta.appendChild(tags);
        body.appendChild(meta);
      }
      li.appendChild(date);
      li.appendChild(body);
      return li;
    };

    var normalise = function (s) {
      return (s || '').toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '');
    };

    var apply = function () {
      var q = normalise(input.value.trim());
      var section = sectionSelect.value;
      var tag = tagSelect.value;
      var query = new URLSearchParams();
      if (q) query.set('q', input.value.trim());
      if (section) query.set('section', section);
      if (tag) query.set('tag', tag);
      var qs = query.toString();
      history.replaceState(null, '', location.pathname + (qs ? '?' + qs : '') + location.hash);

      if (!q && !section && !tag) {
        results.hidden = true;
        archive.hidden = false;
        finderStatus.textContent = '';
        return;
      }
      if (!records) return;
      var terms = q.split(/\s+/).filter(Boolean);
      var matches = records.filter(function (post) {
        if (section && post.section !== section) return false;
        if (tag && !post.tags.some(function (t) { return t.slug === tag; })) return false;
        // Word-prefix match: "rag" finds "RAG" and "ragged", not "storage".
        var words = normalise([post.title, post.summary, post.sectionLabel]
          .concat(post.tags.map(function (t) { return t.label; })).join(' ')).split(/[^a-z0-9]+/);
        return terms.every(function (term) {
          return words.some(function (word) { return word.indexOf(term) === 0; });
        });
      });
      results.textContent = '';
      matches.forEach(function (post) { results.appendChild(renderRow(post)); });
      results.hidden = matches.length === 0;
      archive.hidden = true;
      finderStatus.textContent = matches.length
        ? matches.length + (matches.length === 1 ? ' post matches' : ' posts match')
        : 'No posts match. Try fewer words, or clear the filters.';
    };

    var load = function () {
      if (records) return Promise.resolve();
      return fetch('search.json', { credentials: 'same-origin' })
        .then(function (response) {
          if (!response.ok) throw new Error(response.status);
          return response.json();
        })
        .then(function (data) { records = data; })
        .catch(function () {
          finderStatus.textContent = 'Search is unavailable right now; browse by section or tag below.';
        });
    };

    var timer = null;
    input.addEventListener('input', function () {
      window.clearTimeout(timer);
      timer = window.setTimeout(function () { load().then(apply); }, 120);
    });
    sectionSelect.addEventListener('change', function () { load().then(apply); });
    tagSelect.addEventListener('change', function () { load().then(apply); });
    finder.addEventListener('submit', function (event) { event.preventDefault(); });

    if (input.value || sectionSelect.value || tagSelect.value) load().then(apply);
    if (location.hash === '#search') input.focus();
    window.addEventListener('hashchange', function () {
      if (location.hash === '#search') input.focus();
    });
  }

  /* ------------------------------------------------------------- comments */
  var mount = document.querySelector('[data-giscus]');
  if (mount) {
    var isDark = function () {
      var theme = root.dataset.theme;
      if (theme) return theme === 'dark';
      return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    };
    var themeUrl = function () {
      return mount.getAttribute(isDark() ? 'data-theme-press' : 'data-theme-paper');
    };
    var script = document.createElement('script');
    script.src = 'https://giscus.app/client.js';
    script.async = true;
    script.crossOrigin = 'anonymous';
    var attrs = {
      'data-repo': mount.getAttribute('data-repo'),
      'data-repo-id': mount.getAttribute('data-repo-id'),
      'data-category': mount.getAttribute('data-category'),
      'data-category-id': mount.getAttribute('data-category-id'),
      'data-mapping': 'specific',
      'data-term': mount.getAttribute('data-term'),
      'data-strict': '1',
      'data-reactions-enabled': '1',
      'data-emit-metadata': '0',
      'data-input-position': 'top',
      'data-theme': themeUrl(),
      'data-lang': 'en',
      'data-loading': 'lazy'
    };
    Object.keys(attrs).forEach(function (key) { script.setAttribute(key, attrs[key]); });
    var fallback = mount.querySelector('.comments__fallback');
    if (fallback) fallback.hidden = true;
    mount.appendChild(script);

    var syncTheme = function () {
      var frame = document.querySelector('iframe.giscus-frame');
      if (!frame || !frame.contentWindow) return;
      frame.contentWindow.postMessage({ giscus: { setConfig: { theme: themeUrl() } } }, 'https://giscus.app');
    };
    new MutationObserver(syncTheme).observe(root, { attributes: true, attributeFilter: ['data-theme'] });
    if (window.matchMedia) {
      var query = window.matchMedia('(prefers-color-scheme: dark)');
      if (query.addEventListener) query.addEventListener('change', syncTheme);
    }
  }
})();
