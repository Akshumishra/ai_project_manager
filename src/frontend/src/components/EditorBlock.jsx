import { memo, useCallback, useEffect, useRef } from 'react'
import api from '../api'
import { API } from '../config'
import { getCursorOffset, caretAtStart, getRawText, isFullySelected, moveCursorTo } from '../utils/editorUtils'
import { detectBlockType, renderMarkdown, generatePosition } from '../utils/blockUtils'

// ------------------------------------------------------------------

function EditorBlock({
  block,
  isSelected,
  isTypingRef,
  docId,
  documentData,
  lastSnapshotRef,
  onMouseDown,
  onMouseOver,
  onUpdate,
  onDelete,
  onMergeWithPrev,
  onAddAfter,
  setDocumentData,
  multiSelectedCount,
  onDeleteSelected,
  isReadOnly,
}) {
  const elRef = useRef(null)
  const isFocusedRef = useRef(false)

  // ── Render markdown into DOM, but ONLY when not being edited ──────
  useEffect(() => {
    if (!elRef.current || isFocusedRef.current) return
    elRef.current.innerHTML = renderMarkdown(block.content)
  }, [block.content])

  // ── Focus this element when created / merged into ─────────────────
  // IMPORTANT: block.content intentionally NOT in deps — adding it would
  // re-run on every keystroke and jump the cursor to the start.
  useEffect(() => {
    if (block._focusOnMount && elRef.current) {
      if (document.activeElement !== elRef.current) {
        moveCursorTo(elRef.current, block._cursorAt || 'start')
      }
    }
  }, [block._focusOnMount, block._cursorAt, block.block_id])

  // ── Event handlers ────────────────────────────────────────────────

  const handleFocus = useCallback(() => {
    if (isReadOnly) return
    isFocusedRef.current = true
    isTypingRef.current  = true
    if (elRef.current) {
      // Switch from rendered-HTML to raw-text editing mode.
      const domText  = getRawText(elRef.current).trimEnd()
      const expected = (block.content || '').trimEnd()
      if (domText !== expected) {
        elRef.current.innerText = block.content || ''
      }
    }
  }, [block.content, isTypingRef, isReadOnly])

  const handleBlur = useCallback(() => {
    isFocusedRef.current = false
    isTypingRef.current  = false
    if (!elRef.current) return
    const content = getRawText(elRef.current)
    const type    = detectBlockType(content)
    onUpdate(block.block_id, content, type)
    elRef.current.innerHTML = renderMarkdown(content)
  }, [block.block_id, onUpdate, isTypingRef])

  const handleInput = useCallback(() => {
    if (!elRef.current) return
    const content = getRawText(elRef.current)
    const type    = detectBlockType(content)
    onUpdate(block.block_id, content, type)
  }, [block.block_id, onUpdate])

  // ── onAddAfterImmediate (defined before handleKeyDown uses it) ────

  const onAddAfterImmediate = useCallback(async (blockId, content, type, cursorAt) => {
    const blocks = documentData?.blocks || []
    const idx    = blocks.findIndex(b => b.block_id == blockId)
    if (idx === -1) return

    // Explicitly find prev/next keys including temp blocks for stable positioning
    const prevKey = blocks[idx].position_key
    const nextKey = blocks[idx+1]?.position_key || null
    const positionKey = generatePosition(prevKey, nextKey)

    // Find nearest real previous and next blocks for the backend position logic (REST fallback)
    let realPrevId = null
    for (let i = idx; i >= 0; i--) {
      if (!String(blocks[i].block_id).startsWith('temp_')) { realPrevId = blocks[i].block_id; break }
    }

    let realNextId = null
    for (let j = idx + 1; j < blocks.length; j++) {
      if (!String(blocks[j].block_id).startsWith('temp_')) { realNextId = blocks[j].block_id; break }
    }

    const tempId    = 'temp_' + Date.now() + '_' + Math.random().toString(36).slice(2)
    const tempEntry = { 
      block_id: tempId, 
      localId: tempId, 
      content, 
      type, 
      position_key: positionKey,
      _focusOnMount: true, 
      _cursorAt: cursorAt 
    }

    setDocumentData(prev => {
      if (!prev) return prev
      const newBlocks = [...prev.blocks]
      newBlocks.splice(idx + 1, 0, tempEntry)
      const next = { ...prev, blocks: newBlocks }
      lastSnapshotRef.current = JSON.stringify(next)
      return next
    })

    const data = await onAddAfter(docId, realPrevId, realNextId, content, type, tempId, positionKey)
    if (data) {
      setDocumentData(prev => {
        if (!prev) return prev
        const newBlocks = prev.blocks.map(b =>
          b.block_id === tempId
            ? { ...b, block_id: data.block_id, _focusOnMount: true }
            : b
        )
        const next = { ...prev, blocks: newBlocks }
        lastSnapshotRef.current = JSON.stringify(next)
        return next
      })

      // Sync latest local state to the new real ID
      if (elRef.current) {
        // Find the newly resolved block in the DOM
        const currentEl = document.querySelector(`[data-id="${data.block_id}"]`)
        if (currentEl) {
          const currentText = currentEl.innerText
          onUpdate(data.block_id, currentText, detectBlockType(currentText))
        }
      }
    }
  }, [docId, documentData, lastSnapshotRef, onAddAfter, onUpdate, setDocumentData])

  // ── handleKeyDown — all custom keyboard logic lives here ──────────
  // Using onKeyDown instead of onBeforeInput because:
  //  • onBeforeInput doesn't fire when the element is empty (nothing to delete)
  //  • onKeyDown always fires, giving us reliable Backspace handling

  const handleKeyDown = useCallback((e) => {
    const el = elRef.current
    if (!el) return

    // ── Multi-select delete ────────────────────────────────────────
    if ((e.key === 'Delete' || e.key === 'Backspace') && multiSelectedCount > 1) {
      if (isReadOnly) { e.preventDefault(); return }
      e.preventDefault()
      onDeleteSelected()
      return
    }

    // ── Backspace logic ────────────────────────────────────────────
    if (e.key === 'Backspace') {
      // All content selected → clear block (don't delete it)
      if (isFullySelected(el)) {
        e.preventDefault()
        el.innerText = ''
        onUpdate(block.block_id, '', 'paragraph')
        return
      }

      // Block is empty → delete the whole block, focus previous
      // innerText.trim() handles the trailing \n browsers add
      if (el.innerText.trim() === '') {
        e.preventDefault()
        const prev = el.previousElementSibling
        if (prev) {
          moveCursorTo(prev, 'end')
        }
        onDelete(block.block_id, el)
        return
      }

      // Cursor at position 0 of non-empty block → merge with previous
      if (caretAtStart(el)) {
        e.preventDefault()
        onMergeWithPrev(block.block_id, el)
      }
      return
    }

    // ── Arrow navigation across blocks ────────────────────────────
    const rawText = getRawText(el)
    const cursor  = getCursorOffset(el)

    if (e.key === 'ArrowDown' && cursor >= rawText.length) {
      const next = el.nextElementSibling
      if (next) { e.preventDefault(); moveCursorTo(next, 'start') }
    }
    if (e.key === 'ArrowUp' && cursor === 0) {
      const prev = el.previousElementSibling
      if (prev) { e.preventDefault(); moveCursorTo(prev, 'end') }
    }

    // ── Shift+Enter: insert a visible <br> line-break ─────────────
    // execCommand('insertText', '\n') inserts a literal \n character in the
    // text node which browsers do NOT render as a line break inside a <div>.
    // We must insert an actual <br> element using the Range API instead.
    if (e.key === 'Enter' && e.shiftKey) {
      e.preventDefault()
      const sel = window.getSelection()
      if (!sel?.rangeCount) return
      const range = sel.getRangeAt(0)
      range.deleteContents()
      const br = document.createElement('br')
      range.insertNode(br)
      // If the <br> is at the very end, we need a second <br> so the cursor
      // lands on a new visible line (browsers require a trailing node).
      if (!br.nextSibling || (br.nextSibling.nodeType === Node.TEXT_NODE && br.nextSibling.data === '')) {
        const trailingBr = document.createElement('br')
        br.parentNode.insertBefore(trailingBr, br.nextSibling)
      }
      // Move cursor to just after the inserted <br>
      const newRange = document.createRange()
      newRange.setStartAfter(br)
      newRange.collapse(true)
      sel.removeAllRanges()
      sel.addRange(newRange)
      // Sync updated content to state
      handleInput()
      return
    }

    // ── Enter in table: exit on blank last row ─────────────────────
    if (e.key === 'Enter' && detectBlockType(rawText) === 'table') {
      const lines = rawText.split('\n')
      const last  = lines[lines.length - 1]
      if (last.trim() === '') {
        e.preventDefault()
        const trimmed = lines.slice(0, -1).join('\n')
        el.innerText = trimmed
        onUpdate(block.block_id, trimmed, 'table')
        onAddAfterImmediate(block.block_id, '', 'paragraph', 'start')
      }
      return
    }

    // ── Enter: split block ─────────────────────────────────────────
    if (e.key === 'Enter') {
      e.preventDefault()
      // getRawText correctly converts <br> → '\n' without trailing junk.
      // getCursorOffset counts <br> nodes as 1 char, matching getRawText.
      const before = rawText.slice(0, cursor)
      const after  = rawText.slice(cursor)
      el.innerText = before
      onUpdate(block.block_id, before, detectBlockType(before))
      onAddAfterImmediate(block.block_id, after, detectBlockType(after), 'start')
    }
  }, [
    block.block_id, multiSelectedCount,
    onDeleteSelected, onDelete, onMergeWithPrev, onUpdate, onAddAfterImmediate, handleInput,
    isReadOnly
  ])

  const handlePaste = useCallback(async (e) => {
    const text = e.clipboardData.getData('text/plain')
    
    // If it's a table, paste it directly into the current block to keep it together
    if (text.trim().startsWith('|')) {
      e.preventDefault();
      const sel = window.getSelection();
      if (!sel.rangeCount) return;
      sel.deleteFromDocument();
      sel.getRangeAt(0).insertNode(document.createTextNode(text));
      sel.collapseToEnd();
      handleInput(); // Sync to state
      return;
    }

    e.preventDefault()
    const lines = text.split(/\r?\n/)
    if (lines.length === 0) return

    if (lines.length === 1) {
      document.execCommand('insertText', false, lines[0])
      return
    }

    const el = elRef.current
    const cursor = getCursorOffset(el)
    const raw = getRawText(el)
    const before = raw.slice(0, cursor)
    const after = raw.slice(cursor)

    // Capture initial nextId to keep it stable during sequential insertions.
    // We skip 'temp_' blocks to give the backend a reliable reference.
    const blocks = documentData?.blocks || []
    const idx = blocks.findIndex(b => b.block_id == block.block_id)
    let stableNextId = null
    if (idx !== -1) {
      for (let j = idx + 1; j < blocks.length; j++) {
        if (!String(blocks[j].block_id).startsWith('temp_')) {
          stableNextId = blocks[j].block_id
          break
        }
      }
    }

    // 1. Update current block with 'before' text + first pasted line
    const firstLineContent = before + lines[0]
    el.innerText = firstLineContent
    onUpdate(block.block_id, firstLineContent, detectBlockType(firstLineContent))

    let prevId = block.block_id
    
    // 2. Insert middle lines as new blocks
    for (let i = 1; i < lines.length - 1; i++) {
      const line = lines[i]
      const data = await onAddAfter(docId, prevId, stableNextId, line, detectBlockType(line))
      if (data) prevId = data.block_id
    }

    // 3. Insert last line + 'after' text as the final new block
    const lastLineContent = lines[lines.length - 1] + after
    const data = await onAddAfter(docId, prevId, stableNextId, lastLineContent, detectBlockType(lastLineContent))
    if (data) prevId = data.block_id

    // 4. Force a refresh to sync all new blocks and move cursor
    try {
      const { data: freshData } = await api.get(`/api/documents/${docId}`)
      setDocumentData(freshData)
      lastSnapshotRef.current = JSON.stringify(freshData)
      setTimeout(() => {
        const lastEl = document.querySelector(`[data-id="${prevId}"]`)
        if (lastEl) moveCursorTo(lastEl, 'end')
      }, 50)
    } catch (err) {
      console.error('Failed to refresh document after paste:', err)
    }
  }, [block.block_id, docId, documentData, lastSnapshotRef, onAddAfter, onUpdate, setDocumentData])

  const handleMouseDown = useCallback((e) => onMouseDown(e, elRef.current), [onMouseDown])
  const handleMouseOver = useCallback((e) => onMouseOver(e, elRef.current), [onMouseOver])

  return (
    <div
      ref={elRef}
      className={`block${isSelected ? ' selected' : ''}${isReadOnly ? ' read-only' : ''}`}
      contentEditable={!isReadOnly}
      suppressContentEditableWarning
      data-id={block.block_id}
      spellCheck={false}
      onFocus={handleFocus}
      onBlur={handleBlur}
      onInput={handleInput}
      onKeyDown={handleKeyDown}
      onPaste={handlePaste}
      onMouseDown={handleMouseDown}
      onMouseOver={handleMouseOver}
    />
  )
}

export default memo(EditorBlock)
