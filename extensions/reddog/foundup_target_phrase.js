const QUANTIFIERS = new Set(['all', 'another', 'any', 'both', 'each', 'every', 'few', 'fewer', 'less', 'many', 'more', 'multiple', 'no', 'one', 'other', 'several', 'some', 'two']);
const BEFORE_RELATIONS = new Set(['a', 'an', 'as', 'existing', 'is', 'new', 'our', 'registered', 'the', 'this', 'which', ...QUANTIFIERS]);
const AFTER_RELATIONS = new Set(['a', 'an', 'as', 'called', 'known', 'named', 'the']);

function tokens(value) {
  return String(value || '').normalize('NFKC').toLowerCase().replace(/found[\s-]?ups?/g, 'foundup')
    .replace(/[_-]+/g, ' ').replace(/[^a-z0-9]+/g, ' ').trim().split(/\s+/).filter(Boolean);
}

function occurrences(values, phrase) {
  const found = [];
  for (let index = 0; index <= values.length - phrase.length; index += 1) {
    if (phrase.every((token, offset) => values[index + offset] === token)) found.push(index);
  }
  return found;
}

function referenceNearFoundup(taskText, reference) {
  const values = tokens(taskText);
  const phrase = tokens(reference);
  if (!phrase.length) return false;
  const foundups = occurrences(values, ['foundup']);
  for (const start of occurrences(values, phrase)) {
    const end = start + phrase.length;
    for (const foundup of foundups) {
      if (end <= foundup && values.slice(end, foundup).every((token) => BEFORE_RELATIONS.has(token))) return true;
      if (foundup < start && values.slice(foundup + 1, start).every((token) => AFTER_RELATIONS.has(token))) return true;
    }
  }
  return false;
}

module.exports = { referenceNearFoundup };
