import { points, context } from './anchor.js';
const SKIP = 'script,style,noscript,nav,button,input,textarea,select,[data-annotation-ignore]';
export function textMap(container) {
  if (!(container instanceof Element)) throw new TypeError('container must be an Element');
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, {
    acceptNode(node) { return node.parentElement?.closest(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT; }
  });
  const nodes = []; let text = '', node;
  while ((node = walker.nextNode())) { const start = points(text).length; nodes.push({ node, start, length: points(node.textContent).length }); text += node.textContent; }
  return { text, nodes };
}
export function selectionAnchor(container, selection = window.getSelection()) {
  if (!selection || selection.isCollapsed || !selection.rangeCount) return null;
  const range = selection.getRangeAt(0);
  if (!container.contains(range.startContainer) || !container.contains(range.endContainer)) return null;
  const { text, nodes } = textMap(container);
  const startNode = nodes.find(item => item.node === range.startContainer);
  const endNode = nodes.find(item => item.node === range.endContainer);
  if (!startNode || !endNode) return null;
  const start = startNode.start + points(startNode.node.textContent.slice(0, range.startOffset)).length;
  const end = endNode.start + points(endNode.node.textContent.slice(0, range.endOffset)).length;
  if (end <= start) return null;
  const anchor = context(text, start, end);
  return anchor.quote.trim() && anchor.quote === range.toString() ? anchor : null;
}
export function rangeFor(container, anchor) {
  const { text, nodes } = textMap(container);
  let at = locateAnchor(text, anchor);
  if (at.status === 'unresolved') at = locateAnchor(text, { ...anchor, start: null, end: null });
  if (at.status === 'unresolved') at = locateAnchor(text, { quote: anchor.quote });
  if (at.status === 'unresolved') return null;
  function boundary(offset, end = false) {
    const item = nodes.find(n => end ? n.start < offset && offset <= n.start + n.length : n.start <= offset && offset < n.start + n.length);
    if (!item) return null;
    const unitOffset = points(item.node.textContent).slice(0, offset - item.start).join('').length;
    return [item.node, unitOffset];
  }
  const a = boundary(at.start), b = boundary(at.end, true);
  if (!a || !b) return null;
  const r = document.createRange(); r.setStart(...a); r.setEnd(...b); return r;
}
import { locate as locateAnchor } from './anchor.js';
