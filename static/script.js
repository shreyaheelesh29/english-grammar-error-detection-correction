const input = document.querySelector('#text-input');
const checkButton = document.querySelector('#check-button');
const statusNode = document.querySelector('#status');
const results = document.querySelector('#results');

function cell(row, value) {
  const td = document.createElement('td');
  td.textContent = value ?? '';
  row.appendChild(td);
}

function render(data) {
  document.querySelector('#sentence-count').textContent = data.sentence_count;
  document.querySelector('#word-count').textContent = data.word_count;
  document.querySelector('#error-count').textContent = data.error_count;
  document.querySelector('#corrected-text').textContent = data.corrected_text;
  const errorBody = document.querySelector('#error-table tbody');
  errorBody.replaceChildren();
  data.errors.forEach(error => {
    const row = document.createElement('tr');
    [error.original, error.error_type, error.message, error.corrected].forEach(value => cell(row, value));
    errorBody.appendChild(row);
  });
  document.querySelector('#error-table').classList.toggle('hidden', data.errors.length === 0);
  document.querySelector('#no-errors').classList.toggle('hidden', data.errors.length !== 0);
  const posBody = document.querySelector('#pos-body');
  posBody.replaceChildren();
  data.pos_tags.forEach(tag => {
    const row = document.createElement('tr');
    [tag.token, tag.pos || tag.tag, tag.lemma, tag.morphology].forEach(value => cell(row, value));
    posBody.appendChild(row);
  });
  document.querySelector('#nlp-mode').textContent = `Analysis mode: ${data.nlp_mode}`;
  results.classList.remove('hidden');
}

checkButton.addEventListener('click', async () => {
  statusNode.textContent = '';
  if (!input.value.trim()) { statusNode.textContent = 'Please enter some text to check.'; input.focus(); return; }
  checkButton.disabled = true;
  checkButton.textContent = 'Analyzing…';
  try {
    const response = await fetch('/check', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text: input.value})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Analysis failed.');
    render(data);
  } catch (error) {
    statusNode.textContent = error.message || 'Could not connect to the server.';
  } finally {
    checkButton.disabled = false;
    checkButton.textContent = 'Check Grammar';
  }
});

document.querySelector('#clear-button').addEventListener('click', () => {
  input.value = ''; statusNode.textContent = ''; results.classList.add('hidden'); input.focus();
});
