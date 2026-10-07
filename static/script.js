const input = document.querySelector('#text-input');
const checkButton = document.querySelector('#check-button');
const statusNode = document.querySelector('#status');
const suggestionList = document.querySelector('#suggestion-list');
let analysis = null;
let dismissed = new Set();
let activeFilter = 'all';
let currentSuggestions = [];

function escapeHTML(value) {
  return String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
}

function liveStats() {
  const text = input.value;
  const words = text.match(/[\p{L}\p{N}]+(?:['’][\p{L}\p{N}]+)*/gu) || [];
  document.querySelector('#live-word-count').textContent = words.length;
  document.querySelector('#live-char-count').textContent = text.length;
  document.querySelector('#reading-time').textContent = `${Math.max(1, Math.ceil(words.length / 220))} min read`;
}

function updateHighlight(errors = []) {
  const layer = document.querySelector('#highlight-layer');
  const source = input.value;
  const spans = [...errors].filter(e => e.end > e.start).sort((a,b) => a.start - b.start || b.end - a.end);
  let html = '', cursor = 0;
  for (const error of spans) {
    if (error.start < cursor || error.start < 0 || error.end > source.length) continue;
    html += escapeHTML(source.slice(cursor, error.start));
    const type = /punct/i.test(error.error_type) ? 'punctuation' : /article|agreement|tense|number|pronoun|verb/i.test(error.error_type) ? 'grammar' : 'style';
    html += `<mark class="mark-${type}">${escapeHTML(source.slice(error.start, error.end))}</mark>`;
    cursor = error.end;
  }
  layer.innerHTML = html + escapeHTML(source.slice(cursor)) + (source.endsWith('\n') ? ' ' : '');
  layer.scrollTop = input.scrollTop;
  layer.scrollLeft = input.scrollLeft;
}

function errorSuggestion(error, index) {
  return {id:`error-${index}`, category:'correctness', title:error.error_type,
    before:error.original || '∅', after:error.corrected || '∅', description:error.message,
    start:error.start, end:error.end, replacement:error.corrected, source:'error'};
}

function renderSuggestionList() {
  suggestionList.replaceChildren();
  const visible = currentSuggestions.filter(item => !dismissed.has(item.id) && (activeFilter === 'all' || item.category === activeFilter));
  const errors = currentSuggestions.filter(s => s.category === 'correctness' && !dismissed.has(s.id)).length;
  const styles = currentSuggestions.filter(s => s.category === 'clarity' && !dismissed.has(s.id)).length;
  document.querySelector('#all-count').textContent = errors + styles;
  document.querySelector('#correctness-count').textContent = errors;
  document.querySelector('#style-count').textContent = styles;
  document.querySelector('#issue-count').textContent = errors + styles;
  document.querySelector('#fix-all-button').disabled = !analysis || errors === 0;
  document.querySelector('#review-summary-text').textContent = errors + styles
    ? `${errors} correction${errors === 1 ? '' : 's'} · ${styles} writing tip${styles === 1 ? '' : 's'}`
    : analysis ? 'No active suggestions. Nice work.' : 'Check your writing to see suggestions.';
  if (!visible.length) {
    const box = document.createElement('div'); box.className = 'empty-review';
    const strong = document.createElement('strong'); strong.textContent = analysis ? 'All clear' : 'Ready when you are';
    const p = document.createElement('p'); p.textContent = analysis ? 'There are no suggestions in this view.' : 'Run a check to see grammar, punctuation, and writing suggestions.';
    box.append(strong, p); suggestionList.append(box); return;
  }
  visible.forEach(item => {
    const card = document.createElement('article'); card.className = `suggestion-card ${item.category}`;
    const titleRow = document.createElement('div'); titleRow.className = 'suggestion-title-row';
    const title = document.createElement('strong'); title.textContent = item.title;
    const badge = document.createElement('span'); badge.className = `category-badge ${item.category}`; badge.textContent = item.category === 'correctness' ? 'Correctness' : 'Style';
    titleRow.append(title, badge);
    const change = document.createElement('div'); change.className = 'suggestion-change';
    const old = document.createElement('span'); old.className = 'suggestion-before'; old.textContent = item.before;
    const arrow = document.createElement('span'); arrow.className = 'suggestion-arrow'; arrow.textContent = '→';
    const replacement = document.createElement('span'); replacement.className = 'suggestion-after'; replacement.textContent = item.after;
    change.append(old, arrow, replacement);
    const explanation = document.createElement('p'); explanation.className = 'suggestion-explanation'; explanation.textContent = item.description;
    card.append(titleRow, change, explanation);
    const actions = document.createElement('div'); actions.className = 'suggestion-actions';
    if (item.source === 'error') {
      const accept = document.createElement('button'); accept.className = 'accept-button'; accept.textContent = 'Accept'; accept.addEventListener('click', () => acceptSuggestion(item)); actions.append(accept);
    } else if (item.source === 'rewrite') {
      const apply = document.createElement('button'); apply.className = 'accept-button'; apply.textContent = 'Use rewrite'; apply.addEventListener('click', () => { input.value = item.text; onTextChanged(); runCheck(); }); actions.append(apply);
    }
    const ignore = document.createElement('button'); ignore.className = 'ignore-button'; ignore.textContent = 'Dismiss'; ignore.addEventListener('click', () => { dismissed.add(item.id); renderSuggestionList(); }); actions.append(ignore);
    card.append(actions); suggestionList.append(card);
  });
}

function acceptSuggestion(item) {
  if (item.start == null || item.end == null || item.start < 0 || item.end > input.value.length) return;
  input.value = input.value.slice(0,item.start) + item.replacement + input.value.slice(item.end);
  onTextChanged(); runCheck();
}

function render(data) {
  analysis = data; dismissed = new Set();
  const engineStatus = document.querySelector('#engine-status');
  engineStatus.textContent = data.grammar_engine || 'Grammar engine status unavailable.';
  engineStatus.classList.toggle('engine-fallback', !String(data.grammar_engine || '').startsWith('LanguageTool'));
  document.querySelector('#analysis-details').classList.remove('hidden');
  document.querySelector('#correction-preview').classList.remove('hidden');
  document.querySelector('#corrected-text').textContent = data.corrected_text;
  document.querySelector('#correction-label').textContent = data.error_count ? `${data.error_count} suggested change${data.error_count === 1 ? '' : 's'}` : 'No changes recommended';
  document.querySelector('#score').textContent = data.grammar_score;
  document.querySelector('#score-label').textContent = data.score_label;
  document.querySelector('#sentence-count').textContent = data.sentence_count;
  document.querySelector('#vocabulary-count').textContent = data.stats.vocabulary_size;
  document.querySelector('#reading-level').textContent = data.stats.average_sentence_length;
  document.querySelector('#save-state').textContent = 'Checked just now';
  document.querySelector('#copy-button').disabled = false;
  document.querySelector('#download-button').disabled = false;
  document.querySelector('#document-name').textContent = input.value.trim().split(/\s+/).slice(0,5).join(' ') || 'Untitled document';
  updateHighlight(data.errors);

  currentSuggestions = data.errors.map(errorSuggestion);
  data.writing_alternatives.forEach((option,index) => currentSuggestions.push({id:`rewrite-${index}`,category:'clarity',title:option.label,before:'Current phrasing',after:option.text,description:option.reason,source:'rewrite',text:option.text}));
  data.structure_issues.forEach((issue,index) => currentSuggestions.push({id:`structure-${index}`,category:'clarity',title:issue.type,before:issue.original,after:issue.suggestion,description:issue.explanation,source:'structure'}));
  renderSuggestionList();

  const structure = document.querySelector('#structure-results'); structure.replaceChildren();
  if (!data.structure_issues.length) structure.textContent = 'No likely fragment or comma-splice patterns found by the current checks.';
  data.structure_issues.forEach(issue => { const p=document.createElement('p'); p.textContent=`${issue.type}: ${issue.explanation}`; structure.append(p); });
  const posBody = document.querySelector('#pos-body'); posBody.replaceChildren();
  data.pos_tags.forEach(tag => { const row=document.createElement('tr'); [tag.token,tag.pos||tag.tag,tag.lemma,tag.morphology].forEach(value=>{const td=document.createElement('td');td.textContent=value??'';row.append(td)});posBody.append(row); });
  document.querySelector('#nlp-mode').textContent = `Analysis method: ${data.nlp_mode}`;
  const ng=document.querySelector('#ngram-results');ng.replaceChildren();
  for(const [name,value] of Object.entries(data.ngram)) if(typeof value==='object'&&value!==null){const p=document.createElement('p');p.textContent=`${name}: perplexity ${value.perplexity??'n/a'}`;ng.append(p)}
  const refs=document.querySelector('#reference-results');refs.replaceChildren();
  (data.references.links||[]).forEach(link=>{const p=document.createElement('p');p.textContent=`${link.antecedent} → ${link.pronoun}`;refs.append(p)});
  if(!data.references.links.length) refs.textContent='No likely reference links found.';
}

async function runCheck() {
  statusNode.textContent='';
  if(!input.value.trim()){statusNode.textContent='Add some text to check.';input.focus();return}
  checkButton.disabled=true;checkButton.classList.add('loading');checkButton.innerHTML='<span class="spinner"></span> Checking writing…';
  try {
    const response=await fetch('/check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:input.value,goal:document.querySelector('#writing-goal').value})});
    const data=await response.json();if(!response.ok)throw new Error(data.error||'Could not check this text.');render(data);
  } catch(error){statusNode.textContent=error.message||'Could not connect to the checker.'}
  finally{checkButton.disabled=false;checkButton.classList.remove('loading');checkButton.innerHTML='<span class="check-icon">✓</span> Check writing'}
}

function onTextChanged() {
  liveStats();
  document.querySelector('#save-state').textContent = input.value.trim() ? 'Draft · not checked' : 'Not checked';
  updateHighlight([]);
  document.querySelector('#correction-preview').classList.add('hidden');
  if(analysis){analysis=null;currentSuggestions=[];document.querySelector('#save-state').textContent='Changes to check';document.querySelector('#fix-all-button').disabled=true;updateHighlight([]);renderSuggestionList()}
}

checkButton.addEventListener('click',runCheck);
input.addEventListener('input',onTextChanged);
input.addEventListener('scroll',()=>{const layer=document.querySelector('#highlight-layer');layer.scrollTop=input.scrollTop;layer.scrollLeft=input.scrollLeft});
input.addEventListener('keydown',event=>{if((event.metaKey||event.ctrlKey)&&event.key==='Enter'){event.preventDefault();runCheck()}});

document.querySelectorAll('.filter-tab').forEach(tab=>tab.addEventListener('click',()=>{document.querySelectorAll('.filter-tab').forEach(x=>x.classList.remove('active'));tab.classList.add('active');activeFilter=tab.dataset.filter;renderSuggestionList()}));
document.querySelector('#fix-all-button').addEventListener('click',()=>{if(analysis){input.value=analysis.corrected_text;onTextChanged();runCheck()}});
document.querySelector('#sample-button').addEventListener('click',()=>{input.value='She go to college every day. Yesterday, he have a books. i dont know nothing';onTextChanged();runCheck()});
document.querySelector('#rewrite-sample-button').addEventListener('click',()=>{input.value='We went to the baseball game, and after that, we stopped to get something to eat.';onTextChanged();runCheck()});
document.querySelector('#clear-button').addEventListener('click',()=>{input.value='';onTextChanged();input.focus();document.querySelector('#analysis-details').classList.add('hidden');document.querySelector('#save-state').textContent='Not checked';statusNode.textContent=''});
document.querySelector('#new-button').addEventListener('click',()=>document.querySelector('#clear-button').click());
document.querySelector('#writing-goal').addEventListener('change',event=>{const messages={general:'Suggestions for everyday writing.',academic:'Suggestions favoring formal, precise academic phrasing.',business:'Suggestions favoring clear, professional workplace phrasing.',casual:'Suggestions that preserve a relaxed, conversational voice.'};document.querySelector('#goal-description').textContent=messages[event.target.value];if(input.value.trim())runCheck()});

document.querySelector('#copy-button').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(analysis?.corrected_text||input.value);statusNode.textContent='Corrected text copied.'}catch{input.select();document.execCommand('copy');statusNode.textContent='Text copied.'}});
document.querySelector('#download-button').addEventListener('click',()=>{const blob=new Blob([analysis?.corrected_text||input.value],{type:'text/plain;charset=utf-8'});const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download='grammar-checker-corrected.txt';link.click();URL.revokeObjectURL(link.href)});
document.querySelector('#copy-correction').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(analysis?.corrected_text||'');statusNode.textContent='Corrected text copied.'}catch{statusNode.textContent='Clipboard access is unavailable.'}});
document.querySelector('#apply-correction').addEventListener('click',()=>{if(analysis){input.value=analysis.corrected_text;onTextChanged();runCheck();input.focus()}});

document.querySelectorAll('[data-open-analysis]').forEach(link=>link.addEventListener('click',async event=>{event.preventDefault();if(!analysis)await runCheck();if(!analysis)return;const details=document.querySelector('#nlp-analysis');details.open=true;document.querySelector(link.getAttribute('href')).scrollIntoView({behavior:'smooth',block:'center'})}));

document.querySelector('#parse-button').addEventListener('click',async()=>{const out=document.querySelector('#parse-result');try{const response=await fetch('/api/parse',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:input.value})});const data=await response.json();if(!response.ok)throw new Error(data.error);out.textContent=`Accepted: ${data.accepted}\nGrammar: ${data.grammar.join(' | ')}\nCYK chart: ${JSON.stringify(data.cyk_table)}\nTree: ${JSON.stringify(data.parse_tree,null,2)}\n${data.note}`}catch(e){out.textContent=e.message||'Could not parse this text.'}out.classList.remove('hidden')});
document.querySelector('#semantic-button').addEventListener('click',async()=>{const out=document.querySelector('#semantic-results');out.textContent='Looking up words…';try{const response=await fetch('/api/semantics',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:input.value})});const data=await response.json();out.replaceChildren();if(!data.available){out.textContent=`${data.note} Run: ${data.install_command}`;return}data.words.forEach(item=>{const p=document.createElement('p');const sense=item.senses[0];p.textContent=sense?`${item.word}: ${sense.definition} · synonyms: ${sense.synonyms.join(', ')||'—'}`:`${item.word}: no entry`;out.append(p)});if(!data.words.length)out.textContent='No content words found.'}catch(e){out.textContent=e.message||'Lexical lookup failed.'}});

liveStats();
