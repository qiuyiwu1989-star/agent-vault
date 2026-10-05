// Offsets are Unicode code points, never JavaScript UTF-16 code units.
export const points = text => Array.from(text);
export const context = (text, start, end, size = 40) => {
  const chars = points(text);
  if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end > chars.length || start >= end) throw new RangeError('Invalid annotation range');
  return { start, end, quote: chars.slice(start, end).join(''), prefix: chars.slice(Math.max(0, start - size), start).join(''), suffix: chars.slice(end, end + size).join('') };
};
export function locate(text, anchor) {
  const chars = points(text), quote = points(anchor.quote || '');
  if (!quote.length) return { status: 'unresolved' };
  if (Number.isInteger(anchor.start) && Number.isInteger(anchor.end) && chars.slice(anchor.start, anchor.end).join('') === anchor.quote) return { start: anchor.start, end: anchor.end, status: 'exact' };
  const candidates = [];
  for (let i = 0; i <= chars.length - quote.length; i++) {
    if (chars.slice(i, i + quote.length).join('') !== anchor.quote) continue;
    if (anchor.prefix && chars.slice(Math.max(0, i - points(anchor.prefix).length), i).join('') !== anchor.prefix) continue;
    if (anchor.suffix && chars.slice(i + quote.length, i + quote.length + points(anchor.suffix).length).join('') !== anchor.suffix) continue;
    candidates.push(i);
  }
  return candidates.length === 1 ? { start: candidates[0], end: candidates[0] + quote.length, status: 'relocated' } : { status: 'unresolved' };
}
