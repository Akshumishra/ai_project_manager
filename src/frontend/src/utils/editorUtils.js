/**
 * Returns the caret character offset from the start of `el`, counting
 * <br> elements as a '\n' character.
 */
export function getCursorOffset(el) {
  const sel = window.getSelection();
  if (!sel?.rangeCount) return 0;
  const { startContainer, startOffset } = sel.getRangeAt(0);
  let offset = 0;
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_ALL);
  let node = walker.nextNode();
  while (node) {
    if (node === startContainer) {
      if (node.nodeType === Node.TEXT_NODE) offset += startOffset;
      break;
    }
    if (node.nodeType === Node.TEXT_NODE) {
      offset += node.length;
    } else if (node.nodeName === 'BR') {
      offset += 1;
    }
    node = walker.nextNode();
  }
  return offset;
}

/** True when the caret is collapsed at the very beginning of `el`. */
export function caretAtStart(el) {
  const sel = window.getSelection();
  if (!sel?.rangeCount || !sel.getRangeAt(0).collapsed) return false;
  return getCursorOffset(el) === 0;
}

/**
 * Read raw text from a contentEditable element, converting <br> → '\n'.
 */
export function getRawText(el) {
  let text = '';
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_ALL);
  let node = walker.nextNode();
  while (node) {
    if (node.nodeType === Node.TEXT_NODE) {
      text += node.data;
    } else if (node.nodeName === 'BR') {
      text += '\n';
    }
    node = walker.nextNode();
  }
  return text;
}

/** True when the entire content of `el` is selected. */
export function isFullySelected(el) {
  const sel = window.getSelection();
  if (!sel?.rangeCount) return false;
  const selected = sel.getRangeAt(0).toString();
  const content = el.innerText.trimEnd();
  return selected.length > 0 && selected.length >= content.length;
}

/** Moves the cursor to the start or end of the element. */
export function moveCursorTo(el, position = 'end') {
  el.focus();
  const range = document.createRange();
  const sel = window.getSelection();
  range.selectNodeContents(el);
  range.collapse(position === 'start');
  sel.removeAllRanges();
  sel.addRange(range);
}
