import { marked } from 'marked';
import DOMPurify from 'dompurify';

marked.setOptions({ breaks: true });

/** Detects the block type based on its text content. */
export function detectBlockType(text) {
  const t = text.trim();
  if (t.startsWith('|')) return 'table';
  if (t.startsWith('- ') || /^\d+\./.test(t)) return 'list';
  if (t.startsWith('```')) return 'code';
  if (t.startsWith('#')) return 'heading';
  if (t.startsWith('>')) return 'quote';
  if (t.startsWith('---')) return 'divider';
  return 'paragraph';
}

/** Renders markdown content to sanitized HTML string. */
export function renderMarkdown(content) {
  let html = marked.parse(content || '');
  if (html.startsWith('<p>') && html.endsWith('</p>\n')) {
    html = html.slice(3, -5);
  }
  return DOMPurify.sanitize(html);
}

/** Generates a fractional position between two keys for stable collaborative ordering. */
export function generatePosition(prevPos, nextPos) {
  const GAP = 1000.0;
  const p = prevPos ? parseFloat(prevPos) : null;
  const n = nextPos ? parseFloat(nextPos) : null;

  let result;
  if (p === null && n === null) {
    result = GAP;
  } else if (p === null) {
    result = n / 2.0;
  } else if (n === null) {
    result = p + GAP;
  } else {
    result = (p + n) / 2.0;
  }
  return String(result);
}
