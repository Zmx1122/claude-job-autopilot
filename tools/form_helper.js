/* Job Autopilot form helper — paste this whole file into javascript_tool once per page load; it defines window.__jf.
   One call does what used to take many: read every field, fill them all, check what is still empty.
   __jf.fields()                 one line per field: "i|kind[*]|label|value"  (* = required; radios and checkbox groups are one line)
   __jf.fill({Vorname: 'Jane', 'E-Mail': 'jane@example.com', Anrede: 'Frau', Datenschutz: true, '#7': 'text'})
                                 keys = label text (case-insensitive; exact > starts with > contains) or #i from fields();
                                 values: text, an option's text (select / radio), true/false (checkbox), [texts] (checkbox group)
                                 → {filled, missing, skipped, requiredEmpty}
   __jf.click('Weiter')          visible button / link with that text (exact first) → {clicked, disabled} or {clicked: null, buttons}
   await __jf.waitFor('Lebenslauf', 40)   until the text (or 'css:<selector>') shows up → {ok, s} (or {ok: false, state})
   __jf.state()                  url, title, heading, error messages, required-but-empty fields, visible buttons
   __jf.files()                  file inputs with their chosen files, and file names the page shows (upload check)
   Never fills password fields (the user types them) and never touches file inputs (tools/upload_file.sh does).
   Reaches open shadow roots and same-origin iframes. Custom widgets (react-select, div dropdowns, canvas) come back in
   `missing`: use real clicks for those. Portals that hide the form from scripts (SuccessFactors) need screenshots instead.
*/
(() => {
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  const norm = s => clean(s).toLowerCase().replace(/[*✱:]/g, '').trim();
  const txt = r => (r.body ? r.body.innerText : r.textContent) || '';
  function roots() {
    const out = [];
    const add = r => {
      out.push(r);
      r.querySelectorAll('*').forEach(e => {
        if (e.shadowRoot) add(e.shadowRoot);
        if (e.tagName === 'IFRAME') { try { if (e.contentDocument && e.contentDocument.body) add(e.contentDocument); } catch (_) { /* cross-origin */ } }
      });
    };
    add(document);
    return out;
  }
  const q = sel => roots().flatMap(r => [...r.querySelectorAll(sel)]);
  function shown(e) {   // rendered at all; sizes are not used because a hidden browser pane lays blocks out 0 px wide
    if (e.checkVisibility) return e.checkVisibility({ visibilityProperty: true });
    return e.getClientRects().length > 0 && e.ownerDocument.defaultView.getComputedStyle(e).visibility !== 'hidden';
  }
  function label(e) {
    const r = e.getRootNode(), d = e.ownerDocument;
    let t = e.labels && e.labels.length ? [...e.labels].map(l => l.innerText).join(' ') : '';
    const by = e.getAttribute('aria-labelledby');
    if (!t && by) t = by.split(/\s+/).map(id => ((r.getElementById && r.getElementById(id)) || d.getElementById(id) || {}).innerText || '').join(' ');
    t = t || e.getAttribute('aria-label') || e.getAttribute('placeholder') || e.title || '';
    if (!t) {
      const b = e.closest('[class*=question],[class*=Question],[class*=field],[class*=Field],.form-group,li');
      if (b) t = b.innerText.split('\n')[0];
    }
    return clean(t || e.name || e.id).slice(0, 90);
  }
  function question(e) {   // the question of a radio / checkbox group
    const g = e.closest('fieldset,[role=radiogroup],[role=group]');
    if (g) { const lg = g.querySelector('legend'); return clean(lg ? lg.innerText : (g.getAttribute('aria-label') || g.innerText.split('\n')[0])).slice(0, 90); }
    const b = e.closest('[class*=question],[class*=Question],[class*=field],[class*=Field],.form-group,li');
    return b ? clean(b.innerText.split('\n')[0]).slice(0, 90) : (e.name || '');
  }
  const optText = e => clean(e.labels && e.labels[0] ? e.labels[0].innerText : e.value);
  const required = (e, l) => e.required || e.getAttribute('aria-required') === 'true' || /[*✱]/.test(l);
  function scan() {
    const els = q('input,select,textarea').filter(e => !['hidden', 'submit', 'button', 'reset', 'image'].includes(e.type) && !e.disabled &&
      (e.type === 'file' || shown(e) || (e.labels && [...e.labels].some(shown))));
    const items = [], groups = {};
    for (const e of els) {
      const multi = e.type === 'checkbox' && e.name && els.filter(x => x.type === 'checkbox' && x.name === e.name).length > 1;
      if (e.type === 'radio' || multi) {
        const k = e.type + ':' + (e.name || question(e));
        if (!groups[k]) { groups[k] = { kind: e.type === 'radio' ? 'radio' : 'checks', els: [], label: question(e), req: false }; items.push(groups[k]); }
        groups[k].els.push(e); groups[k].req = groups[k].req || required(e, groups[k].label);
      } else {
        const l = label(e);
        items.push({ kind: e.tagName === 'SELECT' ? 'select' : e.tagName === 'TEXTAREA' ? 'textarea' : e.type, els: [e], label: l, req: required(e, l) });
      }
    }
    return items;
  }
  function value(it) {
    const e = it.els[0];
    if (it.kind === 'radio') { const c = it.els.find(x => x.checked); return (c ? '=' + optText(c) + ' ' : '') + '| ' + it.els.map(optText).join(' / '); }
    if (it.kind === 'checks') return '=' + it.els.filter(x => x.checked).map(optText).join(' + ') + ' | ' + it.els.map(optText).join(' / ');
    if (it.kind === 'checkbox') return e.checked ? '☑' : '☐';
    if (it.kind === 'select') return '=' + clean(e.selectedOptions[0] && e.selectedOptions[0].text) + ' | ' + [...e.options].map(o => clean(o.text)).filter(Boolean).slice(0, 25).join(' / ');
    if (it.kind === 'file') return [...(e.files || [])].map(f => f.name).join(', ') + (e.accept ? ' (accept ' + e.accept + ')' : '');
    if (it.kind === 'password') return '(password: the user types it)';
    return e.value ? '=' + clean(e.value).slice(0, 60) : '';
  }
  function best(list, key, text) {
    const k = norm(key); let hit = null, top = 0;
    for (const o of list) {
      const t = norm(text(o)), v = norm(o.value || '');
      const s = t === k || v === k ? 3 : t.startsWith(k) ? 2 : t.includes(k) ? 1 : 0;
      if (s > top) { hit = o; top = s; }
    }
    return hit;
  }
  function setNative(e, v) {   // React / Vue / Angular see the change only through the native setter plus events
    const w = e.ownerDocument.defaultView;
    const P = { INPUT: w.HTMLInputElement, TEXTAREA: w.HTMLTextAreaElement, SELECT: w.HTMLSelectElement }[e.tagName].prototype;
    e.focus();
    Object.getOwnPropertyDescriptor(P, 'value').set.call(e, v);
    for (const t of ['input', 'change']) e.dispatchEvent(new w.Event(t, { bubbles: true, composed: true }));
    e.blur();
  }
  function empty(it) {
    const e = it.els[0];
    if (it.kind === 'radio' || it.kind === 'checks') return !it.els.some(x => x.checked);
    if (it.kind === 'checkbox') return !e.checked;
    if (it.kind === 'file') return !(e.files && e.files.length);
    return !e.value;
  }
  const requiredEmpty = () => scan().filter(it => it.req && empty(it)).map(it => it.label);
  function fields() { return scan().map((it, i) => `${i}|${it.kind}${it.req ? '*' : ''}|${it.label}|${value(it)}`); }
  function fill(map) {
    const items = scan(), res = { filled: [], missing: [], skipped: [] };
    for (const [key, v] of Object.entries(map)) {
      const it = /^#\d+$/.test(key) ? items[+key.slice(1)] : best(items, key, x => x.label);
      if (!it) { res.missing.push(key); continue; }
      const e = it.els[0];
      if (it.kind === 'password') { res.skipped.push(`${key}: password field — the user types it`); continue; }
      if (it.kind === 'file') { res.skipped.push(`${key}: file input — use tools/upload_file.sh`); continue; }
      let ok = true;
      if (it.kind === 'radio' || it.kind === 'checks') {
        for (const want of [].concat(v)) {
          const o = best(it.els, String(want), optText);
          if (!o) ok = false; else if (!o.checked) o.click();
        }
      } else if (it.kind === 'checkbox') {
        const want = v === true || /^(true|yes|ja|1|x)$/i.test(String(v));
        if (e.checked !== want) e.click();
      } else if (it.kind === 'select') {
        const o = best([...e.options], String(v), x => x.text);
        if (o) setNative(e, o.value); else ok = false;
      } else setNative(e, String(v));
      if (ok) res.filled.push(`${key} → ${it.label}`);
      else res.missing.push(`${key}: no option "${v}" (${value(it).slice(0, 150)})`);
    }
    res.requiredEmpty = requiredEmpty();
    return res;
  }
  const btnText = e => clean(e.innerText || e.value || e.getAttribute('aria-label') || '');
  const buttons = () => q('button,a,[role=button],input[type=submit],input[type=button],[role=tab],[role=option],[role=menuitem]').filter(shown);
  function click(text) {
    const k = norm(text), c = buttons(), t = e => norm(btnText(e));
    const hit = c.find(e => t(e) === k) || c.find(e => t(e).startsWith(k)) || c.find(e => t(e).includes(k));
    if (!hit) return { clicked: null, buttons: [...new Set(c.map(btnText).filter(Boolean))].slice(0, 25) };
    const disabled = !!hit.disabled || hit.getAttribute('aria-disabled') === 'true';
    hit.scrollIntoView({ block: 'center' });
    if (!disabled) hit.click();
    return { clicked: btnText(hit).slice(0, 80), disabled };
  }
  async function waitFor(what, sec = 30) {
    const t0 = Date.now(), css = what.startsWith('css:') ? what.slice(4) : null, k = norm(what);
    while (Date.now() - t0 < sec * 1000) {
      if (css ? q(css).some(shown) : roots().some(r => norm(txt(r)).includes(k))) return { ok: true, s: Math.round((Date.now() - t0) / 100) / 10 };
      await new Promise(r => setTimeout(r, 500));
    }
    return { ok: false, s: sec, state: state() };
  }
  function state() {
    const errs = q('[role=alert],[aria-invalid=true],[class*=error],[class*=Error],[class*=invalid]').filter(e => shown(e) || e.matches('input,select,textarea'))
      .map(e => e.matches('input,select,textarea') ? 'invalid: ' + label(e) : clean(e.innerText)).filter(s => s && s.length < 200);
    const h = q('h1,h2,h3').filter(shown).map(e => clean(e.innerText)).filter(Boolean)[0] || '';
    return { url: location.href.slice(0, 150), title: document.title.slice(0, 100), heading: h.slice(0, 100), errors: [...new Set(errs)].slice(0, 10),
             requiredEmpty: requiredEmpty(), buttons: [...new Set(q('button,input[type=submit],[role=button]').filter(shown).map(btnText).filter(Boolean))].slice(0, 15) };
  }
  function files() {
    const inputs = q('input[type=file]').map(e => ({ label: label(e), accept: e.accept, multiple: e.multiple, chosen: [...(e.files || [])].map(f => f.name) }));
    const names = roots().flatMap(r => txt(r).match(/[^\s/\\"'<>|]{1,80}\.(?:pdf|docx?|png|jpe?g)\b/gi) || []);
    return { inputs, shownNames: [...new Set(names)].slice(0, 20) };
  }
  window.__jf = { fields, fill, click, waitFor, state, files, version: 1 };
  return 'form helper ready: __jf.fields() · fill({...}) · click(text) · await waitFor(text, s) · state() · files()';
})();
