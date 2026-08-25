/* Polit Bureau — comportament comu de totes les pagines.
 *
 * Tres coses: el consentiment de galetes, la carrega dels anuncis (que NOMES
 * passa despres del consentiment) i el cercador de territoris.
 */

(function () {
  "use strict";
  var PB = window.PB || {};
  var KEY = "pb-consent";

  /* --------------------------------------------------------- consentiment */

  function consent() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }

  function setConsent(value) {
    try { localStorage.setItem(KEY, value); } catch (e) { /* mode privat */ }
    document.getElementById("pbcookie").hidden = true;
    if (value === "yes") loadThirdParty();
  }

  window.pbResetConsent = function () {
    try { localStorage.removeItem(KEY); } catch (e) { /* res */ }
    location.reload();
  };

  /* Els scripts de tercers NOMES es carreguen aqui. Mentre l'usuari no accepti,
     el navegador no fa ni una peticio a Google: no n'hi ha prou de no ensenyar
     anuncis, el que exigeix el RGPD es no carregar-los. */
  var loaded = false;
  function loadThirdParty() {
    if (loaded) return;
    loaded = true;

    if (PB.adsense) {
      var ads = document.createElement("script");
      ads.async = true;
      ads.crossOrigin = "anonymous";
      ads.src = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client="
        + encodeURIComponent(PB.adsense);
      document.head.appendChild(ads);
      ads.onload = function () {
        document.querySelectorAll("ins.adsbygoogle").forEach(function () {
          (window.adsbygoogle = window.adsbygoogle || []).push({});
        });
      };
    }

    if (PB.ga) {
      var ga = document.createElement("script");
      ga.async = true;
      ga.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(PB.ga);
      document.head.appendChild(ga);
      window.dataLayer = window.dataLayer || [];
      window.gtag = function () { window.dataLayer.push(arguments); };
      window.gtag("js", new Date());
      window.gtag("config", PB.ga, { anonymize_ip: true });
    }
  }

  function initConsent() {
    var box = document.getElementById("pbcookie");
    if (!box) return;
    // Sense anuncis ni analitica configurats no hi ha res a consentir, i
    // ensenyar un banner de galetes que no fa res es enganyar l'usuari.
    if (!PB.adsense && !PB.ga) { box.remove(); return; }

    var choice = consent();
    if (choice === "yes") { loadThirdParty(); return; }
    if (choice === "no") return;
    box.hidden = false;
    document.getElementById("pbaccept").onclick = function () { setConsent("yes"); };
    document.getElementById("pbreject").onclick = function () { setConsent("no"); };
  }

  /* ------------------------------------------------------------ cercador */

  var index = null, hits = [], sel = -1, timer = null;

  function slug(text) {
    return text.normalize("NFKD").replace(/[̀-ͯ]/g, "")
      .replace(/[^\w\s'-]/g, " ").replace(/\s+/g, " ").trim().toLowerCase();
  }

  function loadIndex() {
    if (index) return Promise.resolve(index);
    return fetch(PB.root + "assets/search.json")
      .then(function (r) { return r.json(); })
      .then(function (rows) { index = rows; return rows; });
  }

  var LEVEL = {
    es: { municipality: "Municipio", province: "Provincia", region: "Comunidad" },
    ca: { municipality: "Municipi", province: "Província", region: "Comunitat" }
  };

  function render() {
    var box = document.getElementById("pbhits");
    if (!hits.length) {
      box.innerHTML = '<div class="none">—</div>';
      box.hidden = false;
      return;
    }
    var lang = PB.lang;
    box.innerHTML = hits.map(function (h, i) {
      var url = lang === "ca" ? h[5] : h[4];
      return '<a href="' + PB.root.replace(/\/$/, "") + url + '" class="' +
        (i === sel ? "sel" : "") + '"><span>' + h[0] + '</span>' +
        '<span class="lv">' + (LEVEL[lang] || LEVEL.es)[h[2]] + "</span></a>";
    }).join("");
    box.hidden = false;
  }

  function search(query) {
    var q = slug(query);
    if (q.length < 2) { hits = []; document.getElementById("pbhits").hidden = true; return; }
    // Primer els que comencen igual i, dins de cada grup, el territori mes gran:
    // qui escriu "Soria" gairebe sempre busca la provincia, no un carrer.
    var starts = [], contains = [];
    for (var i = 0; i < index.length && starts.length + contains.length < 60; i++) {
      var key = index[i][1];
      if (key.indexOf(q) === 0) starts.push(index[i]);
      else if (key.indexOf(q) > 0) contains.push(index[i]);
    }
    hits = starts.concat(contains).slice(0, 12);
    sel = hits.length ? 0 : -1;
    render();
  }

  window.pbSearch = function (ev) {
    ev.preventDefault();
    if (hits[sel]) location.href = PB.root.replace(/\/$/, "") +
      (PB.lang === "ca" ? hits[sel][5] : hits[sel][4]);
    return false;
  };

  function initSearch() {
    var input = document.getElementById("pbq");
    if (!input) return;
    input.addEventListener("input", function () {
      clearTimeout(timer);
      var value = input.value;
      timer = setTimeout(function () {
        loadIndex().then(function () { search(value); });
      }, 120);
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        if (!hits.length) return;
        sel = (sel + (e.key === "ArrowDown" ? 1 : hits.length - 1)) % hits.length;
        render();
      } else if (e.key === "Escape") {
        document.getElementById("pbhits").hidden = true;
      }
    });
    input.addEventListener("blur", function () {
      setTimeout(function () { document.getElementById("pbhits").hidden = true; }, 150);
    });
    input.addEventListener("focus", function () { if (hits.length) render(); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { initConsent(); initSearch(); });
  } else { initConsent(); initSearch(); }
})();
