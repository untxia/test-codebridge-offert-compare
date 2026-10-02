'use strict';
/* Offer Compare — interface. Tout le texte provenant des PDF est inséré via textContent (jamais innerHTML). */

const I18N = {
  fr: {
    title: 'Offer Compare',
    hero: 'Ce qui a vraiment changé entre deux offres, avec la preuve dans chaque document.',
    intro: "Déposez l'offre d'origine et sa révision (PDF, Word, Excel, CSV, HTML, JSON ou texte). L'outil liste les changements de fond — périmètre, quantités, prix unitaires, totaux, dates de livraison — chacun avec son emplacement dans les deux documents. Rien à ressaisir.",
    inputs: 'Documents', orig: 'Offre originale', rev: 'Offre révisée', choose: 'Cliquer ou déposer un fichier',
    compare: 'Comparer', comparing: 'Analyse en cours…', samples: 'Essayer avec un exemple :',
    s_normal: 'cas normal', s_format: 'mise en forme seule', s_ambiguous: 'cas ambigu', s_scanned: 'document scanné', s_mixed: 'Excel vs Word',
    limits: "Périmètre : 2 documents texte — PDF, Word, Excel, OpenDocument, CSV, HTML, JSON, texte ou Markdown, formats mélangeables (ni scan, ni image, ni manuscrit) —, 3 pages et 10 lignes max, une seule devise, 2 Mo par fichier. Les fichiers ne sont pas conservés.",
    needBoth: 'Choisissez les deux fichiers.',
    err: 'Erreur', errNet: 'Le serveur est injoignable.',
    d_conclude: 'Changements détectés', d_conclude_sub: '{n} changement(s) de fond à examiner.',
    d_conclude_arith: ' Le total affiché d\'un document ne correspond pas à ses lignes : voir « Contrôles arithmétiques ».',
    d_no_changes: 'Aucun changement de fond',
    d_no_changes_sub: "Même contenu commercial dans les deux offres. Les différences éventuelles ne portent que sur la mise en forme, l'ordre ou les libellés.",
    d_ask: 'Lecture partielle : {n} point(s) à confirmer',
    d_ask_sub: "Je n'ai pas conclu sur les lignes douteuses. Confirmez-les plus bas : le résultat est recalculé.",
    d_decline: 'Impossible de conclure',
    d_decline_sub: "Je préfère ne rien affirmer plutôt que de risquer un chiffre faux.",
    r_no_text_layer_original: "L'offre originale n'a pas de texte exploitable (scan ou image). Fournissez un fichier texte (PDF texte, Word, Excel...).",
    r_no_text_layer_revised: "L'offre révisée n'a pas de texte exploitable (scan ou image). Fournissez un fichier texte (PDF texte, Word, Excel...) ou confirmez les valeurs à la main.",
    r_no_line_items_original: "Aucun tableau de lignes reconnu dans l'offre originale.",
    r_no_line_items_revised: "Aucun tableau de lignes reconnu dans l'offre révisée.",
    r_currency_mismatch: 'Les deux offres ne sont pas dans la même devise.',
    r_multiple_currencies_original: "Plusieurs devises dans l'offre originale.",
    r_multiple_currencies_revised: "Plusieurs devises dans l'offre révisée.",
    sec_net: 'Effet net', stated: 'Total HT affiché', recomputed: 'Total HT recalculé (somme des lignes)',
    unattributed: 'Dont montant non attribué (lignes à confirmer)',
    sec_changes: 'Changements confirmés', th_item: 'Ligne', th_type: 'Type', th_change: 'Avant → Après', th_impact: 'Impact', th_src: 'Sources',
    ty_unit_price: 'Prix unitaire', ty_quantity: 'Quantité', ty_delivery_date: 'Livraison', ty_scope_removed: 'Ligne supprimée',
    ty_scope_added: 'Ligne ajoutée', ty_stated_total: 'Total affiché',
    f_ht: 'HT', f_vat: 'TVA', f_ttc: 'TTC', was: 'avant : ',
    src_orig: 'Original', src_rev: 'Révisée', src_totals: 'totaux', page: 'p.', line: 'l.',
    sec_ask: 'À confirmer', ask_intro: "Ces lignes ne sont pas rattachées avec certitude. Votre réponse recalcule la comparaison.",
    u_rename_or_replacement: "Libellés différents, conditions voisines : simple renommage ou remplacement par une autre ligne ?",
    u_split_or_merge: "Une ligne d'un côté correspond à plusieurs lignes de l'autre : scission, fusion ou remplacement ?",
    u_ambiguous_group: 'Plusieurs lignes se ressemblent des deux côtés : correspondance non établie.',
    u_stake: 'Montant en jeu : {a} → {b} ({d})',
    u_if_same: 'Si c\'est la même ligne : ', u_if_same_none: 'aucun changement de prix, de quantité ni de date (renommage seul).',
    u_orig_lines: 'Original', u_rev_lines: 'Révisée',
    a_same: "C'est la même ligne (renommage)", a_diff: 'Lignes différentes (suppression + ajout)',
    a_pick: 'Ligne {o} = ligne {r}, les autres sont des ajouts', a_all_new: 'Remplacement : tout est nouveau',
    a_reset: 'Annuler mes réponses',
    sec_arith: 'Contrôles arithmétiques',
    arith_note: "Les valeurs sont celles écrites dans les documents. Rien n'a été corrigé.",
    doc_original: "l'original", doc_revised: 'la révision',
    x_line_arithmetic: 'Ligne {n} ({doc}) : quantité × prix unitaire = {recomputed}, mais le document indique {stated}.',
    x_total_ht_sum_mismatch: 'Total HT ({doc}) : le document indique {stated} ; la somme des lignes donne {recomputed} (écart {diff}).',
    x_vat_mismatch: 'TVA ({doc}) : le document indique {stated} ; le taux appliqué au total HT affiché donne {recomputed}.',
    x_ttc_mismatch: 'Total TTC ({doc}) : le document indique {stated} ; HT + TVA affichés donnent {recomputed}.',
    sec_nc: 'Non signalé comme changement', nc_renamed: 'Ligne renommée', nc_reordered: "L'ordre des lignes a changé.", nc_none: 'Rien.',
    tech: 'Détails techniques', tech_line: 'Lecture {a} ms + {b} ms · comparaison {c} ms · total serveur {d} ms · méthode : {m}',
    warnings: 'Avertissements',
    v_title: 'Sources du changement', v_close: 'Fermer', v_orig: 'Offre originale — page {p}', v_rev: 'Offre révisée — page {p}', v_orig_g: 'Offre originale — {p}', v_rev_g: 'Offre révisée — {p}',
    loc_line: 'ligne {r}', loc_table: '{g}, ligne {r}', loc_item: 'élément {r}', loc_field: 'champ « {k} »', loc_cell: 'cellule {k}',
    gname: { Tableau: 'Tableau', Texte: 'Texte', Fichier: 'Fichier', 'Éléments': 'Éléments', Champs: 'Champs' },
    v_absent: 'Cette ligne n\'existe pas dans cette version.', v_fail: "Affichage du document impossible dans ce navigateur.",
  },
  en: {
    title: 'Offer Compare',
    hero: 'What really changed between two offers, with the proof in each document.',
    intro: 'Drop the original offer and its revision (PDF, Word, Excel, CSV, HTML, JSON or text). The tool lists the substantive changes — scope, quantities, unit prices, totals, delivery dates — each with its location in both documents. Nothing to retype.',
    inputs: 'Documents', orig: 'Original offer', rev: 'Revised offer', choose: 'Click or drop a file',
    compare: 'Compare', comparing: 'Analysing…', samples: 'Try an example:',
    s_normal: 'normal case', s_format: 'formatting only', s_ambiguous: 'ambiguous case', s_scanned: 'scanned document', s_mixed: 'Excel vs Word',
    limits: 'Scope: 2 text documents — PDF, Word, Excel, OpenDocument, CSV, HTML, JSON, text or Markdown, formats can be mixed (no scans, images or handwriting) —, up to 3 pages and 10 line items, a single currency, 2 MB per file. Files are not stored.',
    needBoth: 'Please choose both files.',
    err: 'Error', errNet: 'The server could not be reached.',
    d_conclude: 'Changes found', d_conclude_sub: '{n} substantive change(s) to review.',
    d_conclude_arith: ' A stated total does not match its own lines: see “Arithmetic checks”.',
    d_no_changes: 'No substantive change',
    d_no_changes_sub: 'The two offers have the same commercial content. Any differences are only formatting, row order or wording.',
    d_ask: 'Partial reading: {n} item(s) to confirm',
    d_ask_sub: 'I did not conclude on the doubtful lines. Confirm them below: the result is recomputed.',
    d_decline: 'Cannot conclude',
    d_decline_sub: 'I would rather say nothing than risk a wrong figure.',
    r_no_text_layer_original: 'The original offer has no usable text (scan or image). Please provide a text file (text PDF, Word, Excel...).',
    r_no_text_layer_revised: 'The revised offer has no usable text (scan or image). Please provide a text file (text PDF, Word, Excel...) or confirm the values by hand.',
    r_no_line_items_original: 'No line-item table recognised in the original offer.',
    r_no_line_items_revised: 'No line-item table recognised in the revised offer.',
    r_currency_mismatch: 'The two offers are not in the same currency.',
    r_multiple_currencies_original: 'Several currencies in the original offer.',
    r_multiple_currencies_revised: 'Several currencies in the revised offer.',
    sec_net: 'Net effect', stated: 'Stated total excl. VAT', recomputed: 'Recomputed total excl. VAT (sum of lines)',
    unattributed: 'Of which unattributed (lines to confirm)',
    sec_changes: 'Confirmed changes', th_item: 'Item', th_type: 'Type', th_change: 'Before → After', th_impact: 'Impact', th_src: 'Sources',
    ty_unit_price: 'Unit price', ty_quantity: 'Quantity', ty_delivery_date: 'Delivery', ty_scope_removed: 'Line removed',
    ty_scope_added: 'Line added', ty_stated_total: 'Stated total',
    f_ht: 'Excl. VAT', f_vat: 'VAT', f_ttc: 'Incl. VAT', was: 'was: ',
    src_orig: 'Original', src_rev: 'Revised', src_totals: 'totals', page: 'p.', line: 'row ',
    sec_ask: 'To confirm', ask_intro: 'These lines cannot be matched with certainty. Your answer recomputes the comparison.',
    u_rename_or_replacement: 'Different wording, similar terms: a simple rename or a replacement by another line?',
    u_split_or_merge: 'One line on one side matches several lines on the other: split, merge or replacement?',
    u_ambiguous_group: 'Several lines look alike on both sides: no match established.',
    u_stake: 'Amount at stake: {a} → {b} ({d})',
    u_if_same: 'If it is the same line: ', u_if_same_none: 'no change in price, quantity or date (rename only).',
    u_orig_lines: 'Original', u_rev_lines: 'Revised',
    a_same: 'Same line (renamed)', a_diff: 'Different lines (removal + addition)',
    a_pick: 'Row {o} = row {r}, the others are additions', a_all_new: 'Replacement: everything is new',
    a_reset: 'Undo my answers',
    sec_arith: 'Arithmetic checks',
    arith_note: 'Values are as written in the documents. Nothing was corrected.',
    doc_original: 'the original', doc_revised: 'the revision',
    x_line_arithmetic: 'Row {n} ({doc}): quantity × unit price = {recomputed}, but the document states {stated}.',
    x_total_ht_sum_mismatch: 'Total excl. VAT ({doc}): the document states {stated}; the sum of its lines is {recomputed} (difference {diff}).',
    x_vat_mismatch: 'VAT ({doc}): the document states {stated}; the rate applied to the stated total gives {recomputed}.',
    x_ttc_mismatch: 'Total incl. VAT ({doc}): the document states {stated}; stated excl. VAT + VAT gives {recomputed}.',
    sec_nc: 'Not reported as changes', nc_renamed: 'Renamed line', nc_reordered: 'Row order changed.', nc_none: 'Nothing.',
    tech: 'Technical details', tech_line: 'Reading {a} ms + {b} ms · comparison {c} ms · server total {d} ms · method: {m}',
    warnings: 'Warnings',
    v_title: 'Change sources', v_close: 'Close', v_orig: 'Original offer — page {p}', v_rev: 'Revised offer — page {p}', v_orig_g: 'Original offer — {p}', v_rev_g: 'Revised offer — {p}',
    loc_line: 'line {r}', loc_table: '{g}, row {r}', loc_item: 'item {r}', loc_field: 'field “{k}”', loc_cell: 'cell {k}',
    gname: { Tableau: 'Table', Texte: 'Text', Fichier: 'File', 'Éléments': 'Items', Champs: 'Fields' },
    v_absent: 'This line does not exist in this version.', v_fail: 'The document cannot be displayed in this browser.',
  },
};

const SAMPLES = {
  normal: ['offer_original.pdf', 'offer_revised.pdf'], format: ['offer_original.pdf', 'offer_original_reformatted.pdf'],
  ambiguous: ['offer_original.pdf', 'offer_revised_ambiguous.pdf'], scanned: ['offer_original.pdf', 'offer_revised_scanned.pdf'],
  mixed: ['offer_original.xlsx', 'offer_revised.docx'],
};
const MIME = { pdf: 'application/pdf', xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' };

let lang = (navigator.language || 'en').toLowerCase().startsWith('fr') ? 'fr' : 'en';
const state = { files: { original: null, revised: null }, pdf: {}, overrides: { pairs: [], removed: [], added: [] }, report: null, busy: false };

const $ = (s, r = document) => r.querySelector(s);
const t = (k, p = {}) => (I18N[lang][k] ?? k).replace(/\{(\w+)\}/g, (_, n) => (p[n] ?? ''));

function el(tag, props = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v == null || v === false) continue;
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? '' : v);
  }
  for (const c of kids.flat()) if (c != null && c !== false) e.append(c.nodeType ? c : document.createTextNode(String(c)));
  return e;
}

/* ---------- formats ---------- */
const locale = () => (lang === 'fr' ? 'fr-FR' : 'en-GB');
function currency() {
  const r = state.report;
  return (r && (r.documents.original.currency || r.documents.revised.currency)) || 'EUR';
}
function money(v) {
  if (v == null) return '—';
  return new Intl.NumberFormat(locale(), { style: 'currency', currency: currency() }).format(Number(v));
}
function signed(v) {
  const n = Number(v);
  return (n > 0 ? '+' : n < 0 ? '−' : '') + money(Math.abs(n));
}
function dateTxt(v) {
  if (!v) return '—';
  if (/^\d{4}-\d{2}-\d{2}$/.test(v)) return new Intl.DateTimeFormat(locale(), { dateStyle: 'medium' }).format(new Date(v + 'T12:00:00'));
  return v;
}
const deltaEl = (v) => el('span', { class: 'delta ' + (Number(v) > 0 ? 'pos' : Number(v) < 0 ? 'neg' : '') }, signed(v));

/* ---------- statique / langue ---------- */
function applyStatic() {
  document.documentElement.lang = lang;
  document.title = t('title');
  const set = (id, k) => { $(id).textContent = t(k); };
  set('#t-title', 'title'); set('#t-intro', 'intro'); set('#t-hero', 'hero'); set('#t-inputs', 'inputs'); set('#t-orig', 'orig'); set('#t-rev', 'rev');
  set('#t-samples', 'samples'); set('#t-limits', 'limits'); set('#viewer-title', 'v_title'); set('#viewer-close', 'v_close');
  $('#btn-compare').textContent = state.busy ? t('comparing') : t('compare');
  for (const b of document.querySelectorAll('[data-sample]')) b.textContent = t('s_' + b.dataset.sample);
  for (const b of document.querySelectorAll('[data-lang]')) b.setAttribute('aria-pressed', String(b.dataset.lang === lang));
  for (const side of ['original', 'revised']) $('#name-' + side).textContent = state.files[side] ? state.files[side].name : t('choose');
}

/* ---------- fichiers ---------- */
function setFile(side, file) {
  state.files[side] = file;
  state.overrides = { pairs: [], removed: [], added: [] };
  state.pdf[side] = null;
  if (file && window.pdfjsLib && /\.pdf$/i.test(file.name)) {
    state.pdf[side] = file.arrayBuffer().then((buf) => pdfjsLib.getDocument({ data: buf }).promise).catch(() => null);
  }
  applyStatic();
}

async function loadSample(kind) {
  const [o, r] = SAMPLES[kind];
  for (const [side, name] of [['original', o], ['revised', r]]) {
    const blob = await (await fetch('samples/' + name)).blob();
    setFile(side, new File([blob], name, { type: MIME[name.split('.').pop()] || '' }));
  }
  runCompare();
}

/* ---------- appel API ---------- */
async function runCompare() {
  if (state.busy) return;
  const status = $('#status');
  if (!state.files.original || !state.files.revised) { status.replaceChildren(el('p', { class: 'hint' }, t('needBoth'))); return; }
  state.busy = true; applyStatic(); $('#btn-compare').disabled = true;
  status.replaceChildren(el('span', { class: 'spin', 'aria-hidden': 'true' }), t('comparing'));
  try {
    const fd = new FormData();
    fd.append('original', state.files.original); fd.append('revised', state.files.revised);
    const o = state.overrides;
    if (o.pairs.length || o.removed.length || o.added.length) fd.append('overrides', JSON.stringify(o));
    const r = await fetch('api/compare', { method: 'POST', body: fd });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(typeof j.detail === 'string' ? j.detail : 'HTTP ' + r.status);
    }
    state.report = await r.json();
    status.replaceChildren();
    renderReport();
  } catch (e) {
    state.report = null;
    $('#result').replaceChildren(el('div', { class: 'banner bad', role: 'alert' }, el('h2', {}, t('err')), el('p', {}, e instanceof TypeError ? t('errNet') : e.message)));
    status.replaceChildren();
  } finally {
    state.busy = false; $('#btn-compare').disabled = false; applyStatic();
  }
}

/* ---------- rendu du rapport ---------- */
const gname = (g) => { const m = /^(\S+)(.*)$/.exec(g || ''); const tr = I18N[lang].gname; return m && tr[m[1]] ? tr[m[1]] + m[2] : g; };

/* Emplacement lisible d'une source : PDF -> « p.2 l.3 » ; Excel -> « Offre!A7:F7 » ; Word/HTML -> « Tableau 1, ligne 3 »... */
function where(s) {
  const b = s.bbox || {};
  if (!s.style) return `${t('page')}${s.page} ${s.block === 'totals' ? t('src_totals') : t('line') + s.row_number}`;
  if (s.style === 'a1') return b.ref || '';
  if (s.style === 'field') return t('loc_field', { k: b.ref });
  if (s.style === 'item') return t('loc_item', { r: b.top });
  if (s.style === 'table') return t('loc_table', { g: gname(s.grid), r: b.top + 1 });
  return t('loc_line', { r: b.top + 1 });
}

function srcBtn(side, s, change) {
  if (!s) return null;
  return el('button', { type: 'button', onclick: () => openViewer(change) }, `${t(side === 'original' ? 'src_orig' : 'src_rev')} ${where(s)}`);
}

function banner(r) {
  const n = r.summary.confirmed_changes;
  const k = { conclude: 'ok', no_changes: 'ok', conclude_partially_and_ask: 'warn', decline: 'bad' }[r.decision];
  const root = el('div', { class: 'banner ' + k, role: 'region', 'aria-label': 'summary' });
  if (r.decision === 'conclude') {
    root.append(el('h2', {}, t('d_conclude')), el('p', {}, t('d_conclude_sub', { n }) + (r.summary.arithmetic_discrepancies ? t('d_conclude_arith') : '')));
  } else if (r.decision === 'no_changes') {
    root.append(el('h2', {}, t('d_no_changes')), el('p', {}, t('d_no_changes_sub')));
  } else if (r.decision === 'conclude_partially_and_ask') {
    root.append(el('h2', {}, t('d_ask', { n: r.uncertain.length })), el('p', {}, t('d_ask_sub')));
  } else {
    root.append(el('h2', {}, t('d_decline')), el('p', {}, t('d_decline_sub')), ...r.decision_reasons.map((c) => el('p', {}, '• ' + t('r_' + c))));
  }
  return root;
}

function netEffect(r) {
  const ne = r.net_effect;
  if (!ne) return null;
  const dl = el('dl', { class: 'kv' });
  const row = (k, a, b, d) => dl.append(el('dt', {}, k), el('dd', {}, `${money(a)} `, el('span', { class: 'arrow' }, '→'), ` ${money(b)} (`, deltaEl(d), ')'));
  if (ne.stated.ht) row(t('stated'), ne.stated.ht.original, ne.stated.ht.revised, ne.stated.ht.delta);
  if (ne.recomputed_ht) row(t('recomputed'), ne.recomputed_ht.original, ne.recomputed_ht.revised, ne.recomputed_ht.delta);
  if (r.uncertain.length) dl.append(el('dt', {}, t('unattributed')), el('dd', {}, deltaEl(ne.unattributed_by_uncertain_items)));
  return el('section', { class: 'card' }, el('h2', {}, t('sec_net')), dl);
}

function changeCells(c) {
  const lab = c.revised?.label || c.original?.label || '';
  const was = c.original && c.revised && c.original.label !== c.revised.label ? el('div', { class: 'muted small' }, t('was') + c.original.label) : null;
  let before, after, impact;
  if (c.type === 'unit_price') { before = money(c.from); after = money(c.to); impact = deltaEl(c.line_total_delta); }
  else if (c.type === 'quantity') { before = c.from; after = c.to; impact = deltaEl(c.line_total_delta); }
  else if (c.type === 'delivery_date') { before = dateTxt(c.from); after = dateTxt(c.to); impact = '—'; }
  else if (c.type === 'scope_removed') { before = `${c.original.qty} × ${money(c.original.unit_price)}`; after = '—'; impact = deltaEl(c.line_total_delta); }
  else if (c.type === 'scope_added') { before = '—'; after = `${c.revised.qty} × ${money(c.revised.unit_price)}`; impact = deltaEl(c.line_total_delta); }
  else {
    const f = c.fields;
    const lines = (key) => f[key] && el('div', {}, `${t('f_' + key)} : ${money(f[key].from)} → ${money(f[key].to)}`);
    return { label: '—', was: null, before: null, after: null, impact: f.ht ? deltaEl(f.ht.delta) : '—', multi: [lines('ht'), lines('vat'), lines('ttc')] };
  }
  return { label: lab, was, before, after, impact };
}

function changesSection(r) {
  if (!r.changes.length) return null;
  const tb = el('tbody');
  for (const c of r.changes) {
    const x = changeCells(c);
    const typeKey = { unit_price: 'b-price', quantity: 'b-qty', delivery_date: 'b-date', scope_removed: 'b-removed', scope_added: 'b-added', stated_total: 'b-total' }[c.type];
    tb.append(el('tr', {},
      el('td', {}, c.type === 'stated_total' ? '—' : [x.label, x.was]),
      el('td', {}, el('span', { class: 'badge ' + typeKey }, t('ty_' + c.type))),
      el('td', {}, x.multi ? x.multi : [x.before, ' ', el('span', { class: 'arrow' }, '→'), ' ', x.after]),
      el('td', { class: 'num' }, x.impact),
      el('td', {}, el('div', { class: 'src' }, srcBtn('original', c.sources.original, c), srcBtn('revised', c.sources.revised, c)))));
  }
  return el('section', { class: 'card' }, el('h2', {}, t('sec_changes')),
    el('table', { class: 'responsive' }, el('thead', {}, el('tr', {}, el('th', {}, t('th_item')), el('th', {}, t('th_type')), el('th', {}, t('th_change')), el('th', { class: 'num' }, t('th_impact')), el('th', {}, t('th_src')))), tb));
}

function decide(kind, g) {
  const o = state.overrides;
  const addUnique = (arr, v) => { if (!arr.includes(v)) arr.push(v); };
  if (kind.type === 'same') {
    const p = [g.original[0].index, g.revised[0].index];
    if (!o.pairs.some((q) => q[0] === p[0] && q[1] === p[1])) o.pairs.push(p);
  }
  if (kind.type === 'diff' || kind.type === 'allnew') {
    g.original.forEach((l) => addUnique(o.removed, l.index));
    g.revised.forEach((l) => addUnique(o.added, l.index));
  }
  if (kind.type === 'pick') {
    o.pairs.push([kind.o, kind.r]);
    g.original.filter((l) => l.index !== kind.o).forEach((l) => addUnique(o.removed, l.index));
    g.revised.filter((l) => l.index !== kind.r).forEach((l) => addUnique(o.added, l.index));
  }
  runCompare();
}

function lineList(items, side, g) {
  return el('ul', {}, items.map((l) => el('li', {}, `${l.label} — ${l.qty} × ${money(l.unit_price)} · ${dateTxt(l.delivery)} `,
    el('button', { type: 'button', class: 'link small', onclick: () => openViewer({ sources: side === 'original' ? { original: l.source, revised: null } : { original: null, revised: l.source } }) }, where(l.source)))));
}

function uncertainSection(r) {
  if (!r.uncertain.length) return null;
  const sec = el('section', { class: 'card' }, el('h2', {}, t('sec_ask')), el('p', { class: 'muted' }, t('ask_intro')));
  for (const g of r.uncertain) {
    const btns = el('div', { class: 'btns' });
    if (g.kind === 'one_to_one') {
      btns.append(el('button', { type: 'button', class: 'primary', onclick: () => decide({ type: 'same' }, g) }, t('a_same')),
        el('button', { type: 'button', onclick: () => decide({ type: 'diff' }, g) }, t('a_diff')));
    } else {
      if (g.kind === 'split_or_merge') {
        for (const c of g.candidates) btns.append(el('button', { type: 'button', onclick: () => decide({ type: 'pick', o: c.orig, r: c.rev }, g) }, t('a_pick', { o: c.orig, r: c.rev })));
      }
      btns.append(el('button', { type: 'button', onclick: () => decide({ type: 'allnew' }, g) }, t('a_all_new')));
    }
    const ifSame = g.if_same_item
      ? el('p', { class: 'small' }, t('u_if_same'), g.if_same_item.length
        ? g.if_same_item.map((d, i) => `${i ? ' · ' : ''}${t('ty_' + d.type)} : ${d.type === 'unit_price' ? money(d.from) + ' → ' + money(d.to) : d.type === 'delivery_date' ? dateTxt(d.from) + ' → ' + dateTxt(d.to) : d.from + ' → ' + d.to}`).join('')
        : t('u_if_same_none')) : null;
    sec.append(el('div', { class: 'group' },
      el('p', {}, el('strong', {}, t('u_' + g.reason_code))),
      el('div', { class: 'cols' }, el('div', {}, el('strong', { class: 'small' }, t('u_orig_lines')), lineList(g.original, 'original', g)),
        el('div', {}, el('strong', { class: 'small' }, t('u_rev_lines')), lineList(g.revised, 'revised', g))),
      el('p', { class: 'small muted' }, t('u_stake', { a: money(g.amount_at_stake.original), b: money(g.amount_at_stake.revised), d: signed(g.amount_at_stake.delta) })),
      ifSame, btns));
  }
  const o = state.overrides;
  if (o.pairs.length || o.removed.length || o.added.length) {
    sec.append(el('button', { type: 'button', class: 'ghost', onclick: () => { state.overrides = { pairs: [], removed: [], added: [] }; runCompare(); } }, t('a_reset')));
  }
  return sec;
}

function arithSection(r) {
  if (!r.arithmetic.length) return null;
  const docName = (d) => t(d === 'original' ? 'doc_original' : 'doc_revised');
  const ul = el('ul');
  for (const a of r.arithmetic) {
    const txt = t('x_' + a.code, { doc: docName(a.document), n: a.source?.row_number, stated: money(a.stated), recomputed: money(a.recomputed), diff: signed(a.difference) });
    const fake = { sources: { original: a.document === 'original' ? a.source : null, revised: a.document === 'revised' ? a.source : null } };
    ul.append(el('li', {}, txt + ' ', srcBtn(a.document, a.source, fake)));
  }
  return el('section', { class: 'card' }, el('h2', {}, t('sec_arith')), ul, el('p', { class: 'hint' }, t('arith_note')));
}

function ncSection(r) {
  const nc = r.non_commercial;
  if (!nc) return null;
  const items = [...nc.renamed.map((x) => `${t('nc_renamed')} : ${x.from} → ${x.to}`), nc.reordered ? t('nc_reordered') : null].filter(Boolean);
  return el('section', { class: 'card' }, el('h2', {}, t('sec_nc')), items.length ? el('ul', {}, items.map((x) => el('li', {}, x))) : el('p', { class: 'muted' }, t('nc_none')));
}

function techSection(r) {
  const o = r.documents.original, v = r.documents.revised;
  return el('details', { class: 'card' }, el('summary', {}, t('tech')),
    el('p', { class: 'small muted' }, t('tech_line', { a: o.extract_ms, b: v.extract_ms, c: r.compare_ms ?? 0, d: r.total_ms, m: `${o.method} / ${v.method}` })),
    r.warnings.length ? el('div', {}, el('strong', { class: 'small' }, t('warnings')), el('ul', {}, r.warnings.map((w) => el('li', { class: 'small' }, w)))) : null);
}

function renderReport() {
  const r = state.report;
  $('#result').replaceChildren(...[banner(r), netEffect(r), changesSection(r), uncertainSection(r), arithSection(r), ncSection(r), techSection(r)].filter(Boolean));
}

/* ---------- visionneuse de sources ---------- */
async function renderPage(side, src) {
  const box = $('#page-' + side);
  box.replaceChildren();
  const cap = $('#vc-' + (side === 'original' ? 'orig' : 'rev'));
  if (src && src.style) cap.textContent = t(side === 'original' ? 'v_orig_g' : 'v_rev_g', { p: src.style === 'a1' ? src.grid : gname(src.grid) });
  else cap.textContent = t(side === 'original' ? 'v_orig' : 'v_rev', { p: src ? src.page : '—' });
  if (!src) { box.append(el('p', { class: 'muted small', style: 'padding:12px' }, t('v_absent'))); return; }
  if (src.style) { renderGrid(box, side, src); return; }
  try {
    const pdf = await state.pdf[side];
    if (!pdf) throw new Error('no pdf');
    const page = await pdf.getPage(src.page);
    const vp = page.getViewport({ scale: 2 });
    const canvas = el('canvas', { width: Math.round(vp.width), height: Math.round(vp.height) });
    box.append(canvas);
    await page.render({ canvasContext: canvas.getContext('2d'), viewport: vp }).promise;
    const W = vp.width / 2, H = vp.height / 2;   // points PDF (même repère que pdfplumber : origine en haut à gauche)
    const add = (b, cls) => b && box.append(el('div', { class: 'hl ' + cls, style: `left:${(b.x0 / W) * 100}%;top:${(b.top / H) * 100}%;width:${((b.x1 - b.x0) / W) * 100}%;height:${((b.bottom - b.top) / H) * 100}%` }));
    if (src.cell) { add(src.bbox, 'row'); add(src.cell, ''); } else { add(src.bbox, ''); }
    box.querySelector('.hl:last-child')?.scrollIntoView({ block: 'center' });
  } catch (e) {
    box.append(el('p', { class: 'muted small', style: 'padding:12px' }, t('v_fail')));
  }
}

/* Formats non PDF : le serveur renvoie le contenu lu ; on l'affiche en tableau avec la ligne et la cellule en surbrillance. */
function renderGrid(box, side, src) {
  const g = (state.report?.documents?.[side]?.preview?.tables || [])[src.page - 1];
  if (!g) { box.append(el('p', { class: 'muted small', style: 'padding:12px' }, t('v_fail'))); return; }
  const a1 = src.style === 'a1';
  const row = src.bbox.top, col = src.cell ? src.cell.x0 : -1;
  const head = a1 ? [el('th', {})].concat(g.rows[0].map((_, i) => el('th', {}, colName(i)))) : null;
  const body = g.rows.map((cells, r) => el('tr', { class: r === row ? 'hit' : '' },
    el('th', { class: 'rn' }, String(a1 ? r + 1 : r + (src.style === 'item' ? 0 : 1))),
    cells.map((c, i) => el('td', { class: r === row && i === col ? 'hitc' : '' }, c))));
  const table = el('table', { class: 'sheet' }, head ? el('thead', {}, el('tr', {}, head)) : null, el('tbody', {}, body));
  const wrap = el('div', { class: 'sheet-wrap' }, table);
  box.append(wrap);
  box.querySelector('tr.hit')?.scrollIntoView({ block: 'center' });
}
const colName = (i) => { let s = ''; for (i += 1; i; i = Math.floor((i - 1) / 26)) s = String.fromCharCode(65 + ((i - 1) % 26)) + s; return s; };

function openViewer(change) {
  const dlg = $('#viewer');
  const s = change.sources || {};
  if (!dlg.open) { dlg.showModal(); dlg.classList.remove('fly'); void dlg.offsetWidth; dlg.classList.add('fly'); }
  renderPage('original', s.original);
  renderPage('revised', s.revised);
}

/* ---------- init ---------- */
function init() {
  if (window.pdfjsLib) pdfjsLib.GlobalWorkerOptions.workerSrc = 'vendor/pdf.worker.min.js';
  for (const side of ['original', 'revised']) {
    $('#file-' + side).addEventListener('change', (e) => e.target.files[0] && setFile(side, e.target.files[0]));
    const zone = $('#drop-' + side);
    zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('over'));
    zone.addEventListener('drop', (e) => { e.preventDefault(); zone.classList.remove('over'); const f = e.dataTransfer.files[0]; if (f) setFile(side, f); });
  }
  $('#btn-compare').addEventListener('click', runCompare);
  for (const b of document.querySelectorAll('[data-sample]')) b.addEventListener('click', () => loadSample(b.dataset.sample));
  for (const b of document.querySelectorAll('[data-lang]')) b.addEventListener('click', () => { lang = b.dataset.lang; applyStatic(); if (state.report) renderReport(); });
  const app = $('#app-window');   // fenêtre principale : même inclinaison 3D, plus discrète
  if (app && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    addEventListener('pointermove', (e) => {
      app.style.setProperty('--wy', ((e.clientX / innerWidth - .5) * 4).toFixed(2) + 'deg');
      app.style.setProperty('--wx', ((.5 - e.clientY / innerHeight) * 2.5).toFixed(2) + 'deg');
    }, { passive: true });
  }
  const win = $('#viewer');   // fenêtre volante : légère inclinaison 3D qui suit le pointeur (désactivée si mouvement réduit)
  const calm = matchMedia('(prefers-reduced-motion: reduce)');
  win.addEventListener('pointermove', (e) => {
    if (calm.matches) return;
    const r = win.getBoundingClientRect();
    win.style.setProperty('--ry', (((e.clientX - r.left) / r.width - .5) * 3).toFixed(2) + 'deg');
    win.style.setProperty('--rx', ((.5 - (e.clientY - r.top) / r.height) * 2).toFixed(2) + 'deg');
  });
  win.addEventListener('pointerleave', () => { win.style.setProperty('--ry', '0deg'); win.style.setProperty('--rx', '0deg'); });
  $('#viewer-close').addEventListener('click', () => $('#viewer').close());
  $('#viewer').addEventListener('click', (e) => { if (e.target === $('#viewer')) $('#viewer').close(); });
  applyStatic();
}
init();
