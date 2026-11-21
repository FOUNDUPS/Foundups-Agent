// Browser-local templates. Skin and tone never select an audience or change facts.
export const SKINS = Object.freeze({
  vote: Object.freeze({ title: 'Your voice. Your words.', intro: "I'm calling to share my view.", request: '', reason: '' }),
  hpc: Object.freeze({
    title: 'HPC · Make your voice heard.',
    intro: "I'm calling in support of the independent Hasan Piker Coalition campaign.",
    request: 'Please register my opposition to Hakeem Jeffries and my request for a protest vote for Hasan Piker.',
    reason: 'I want leadership that listens to independent creators and stands up to authoritarianism.',
  }),
});
const TONES = Object.freeze([
  ['I would appreciate your attention to this.', 'Please consider this request.', 'This matters to me, and I hope you will listen.'],
  ['I am frustrated, and I want a clear response.', 'I expect more from our leadership.', 'I am asking you to take this concern seriously.'],
  ['I am furious with the status quo. I want action, not excuses.', 'My patience has run out. This deserves a direct answer.', 'I am angry, and I want my objection clearly on the record.'],
]);
const CLOSES = ['Please record my position and let me know your response. Thank you.', 'Will you pass this request to the member and tell me their position? Thank you.', 'Please confirm that my request has been recorded. I would appreciate a response.'];
const clean = (value, max) => typeof value === 'string' ? value.replace(/[\u0000-\u001f\u007f]/g, ' ').trim().slice(0, max) : '';
export function resolveSkin(value) { return Object.hasOwn(SKINS, value) ? value : 'vote'; }
export function createCallScript(input = {}) {
  const tone = Number.isInteger(input.tone) && input.tone >= 0 && input.tone < TONES.length ? input.tone : 0;
  const variant = Number.isSafeInteger(input.variant) && input.variant >= 0 ? input.variant % 3 : 0;
  const intro = clean(input.intro, 300);
  const callback = clean(input.callback, 60);
  const request = clean(input.request, 700);
  const reason = clean(input.reason, 700);
  if (!request) return '';
  return [
    ['Hello.', intro, callback ? `My callback number is ${callback}.` : ''].filter(Boolean).join(' '),
    request,
    [TONES[tone][variant], reason].filter(Boolean).join(' '),
    CLOSES[variant],
  ].join('\n\n');
}
