import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { memo, useCallback, useEffect, useRef } from 'react'
import api from '../../../shared/api/api'

marked.setOptions({ breaks: true })

function detectBlockType(text) {
  const t = text.trim()
  if (t.startsWith('|')) return 'table'
  if (t.startsWith('- ') || /^\d+\./.test(t)) return 'list'
  if (t.startsWith('```')) return 'code'
  if (t.startsWith('#')) return 'heading'
  if (t.startsWith('>')) return 'quote'
  if (t.startsWith('---')) return 'divider'
  return 'paragraph'
}

function renderMarkdown(content) {
  let html = marked.parse(content || '')
  if (html.startsWith('<p>') && html.endsWith('</p>\n')) {
    html = html.slice(3, -5)
  }
  return DOMPurify.sanitize(html)
}

function getCursorOffset(el) {
  const sel = window.getSelection()
  if (!sel?.rangeCount) return 0
  const { startContainer, startOffset } = sel.getRangeAt(0)
  let offset = 0
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_ALL)
  let node = walker.nextNode()
  while (node) {
    if (node === startContainer) {
      if (node.nodeType === Node.TEXT_NODE) offset += startOffset
      break
    }
    if (node.nodeType === Node.TEXT_NODE) {
      offset += node.length
    } else if (node.nodeName === 'BR') {
      offset += 1
    }
    node = walker.nextNode()
  }
  return offset
}

function caretAtStart(el) {
  const sel = window.getSelection()
  if (!sel?.rangeCount || !sel.getRangeAt(0).collapsed) return false
  return getCursorOffset(el) === 0
}

function getRawText(el) {
  let text = ''
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_ALL)
  let node = walker.nextNode()
  while (node) {
    if (node.nodeType === Node.TEXT_NODE) {
      text += node.data
    } else if (node.nodeName === 'BR') {
      text += '\n'
    }
    node = walker.nextNode()
  }
  return text
}

function isFullySelected(el) {
  const sel = window.getSelection()
  if (!sel?.rangeCount) return false
  const selected = sel.getRangeAt(0).toString()
  const content  = el.innerText.trimEnd()
  return selected.length > 0 && selected.length >= content.length
}

function moveCursorTo(el, position = 'end') {
  el.focus()
  const range = document.createRange()
  const sel   = window.getSelection()
  range.selectNodeContents(el)
  range.collapse(position === 'start')
  sel.removeAllRanges()
  sel.addRange(range)
}

function generatePosition(prevPos, nextPos) {
  const GAP = 1000.0
  const p = prevPos ? parseFloat(prevPos) : null
  const n = nextPos ? parseFloat(nextPos) : null

  let result
  if (p === null && n === null) {
    result = GAP
  } else if (p === null) {
    result = n / 2.0
  } else if (n === null) {
    result = p + GAP
  } else {
    result = (p + n) / 2.0
  }
  return String(result)
}

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

  useEffect(() => {
    if (!elRef.current || isFocusedRef.current) return
    elRef.current.innerHTML = renderMarkdown(block.content)
  }, [block.content])

  useEffect(() => {
    if (block._focusOnMount && elRef.current) {
      if (document.activeElement !== elRef.current) {
        moveCursorTo(elRef.current, block._cursorAt || 'start')
      }
    }
  }, [block._focusOnMount, block._cursorAt, block.block_id])

  const handleFocus = useCallback(() => {
    if (isReadOnly) return
    isFocusedRef.current = true
    isTypingRef.current  = true
    if (elRef.current) {
      const domText  = elRef.current.innerText.trimEnd()
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
    const content = elRef.current.innerText
    const type    = detectBlockType(content)
    onUpdate(block.block_id, content, type)
    elRef.current.innerHTML = renderMarkdown(content)
  }, [block.block_id, onUpdate, isTypingRef])

  const handleInput = useCallback(() => {
    if (!elRef.current) return
    const content = elRef.current.innerText
    const type    = detectBlockType(content)
    onUpdate(block.block_id, content, type)
  }, [block.block_id, onUpdate])

  const onAddAfterImmediate = useCallback(async (blockId, content, type, cursorAt) => {
    const blocks = documentData?.blocks || []
    const idx    = blocks.findIndex(b => b.block_id == blockId)
    if (idx === -1) return

    const prevKey = blocks[idx].position_key
    const nextKey = blocks[idx+1]?.position_key || null
    const positionKey = generatePosition(prevKey, nextKey)

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
    }
  }, [docId, documentData, lastSnapshotRef, onAddAfter, setDocumentData])

  const handleKeyDown = useCallback((e) => {
    const el = elRef.current
    if (!el) return

    if ((e.key === 'Delete' || e.key === 'Backspace') && multiSelectedCount > 1) {
      if (isReadOnly) { e.preventDefault(); return }
      e.preventDefault()
      onDeleteSelected()
      return
    }

    if (e.key === 'Backspace') {
      if (isFullySelected(el)) {
        e.preventDefault()
        el.innerText = ''
        onUpdate(block.block_id, '', 'paragraph')
        return
      }

      if (el.innerText.trim() === '') {
        e.preventDefault()
        onDelete(block.block_id, el)
        return
      }

      if (caretAtStart(el)) {
        e.preventDefault()
        onMergeWithPrev(block.block_id, el)
      }
      return
    }

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

    if (e.key === 'Enter' && e.shiftKey) {
      e.preventDefault()
      const sel = window.getSelection()
      if (!sel?.rangeCount) return
      const range = sel.getRangeAt(0)
      range.deleteContents()
      const br = document.createElement('br')
      range.insertNode(br)
      if (!br.nextSibling || (br.nextSibling.nodeType === Node.TEXT_NODE && br.nextSibling.data === '')) {
        const trailingBr = document.createElement('br')
        br.parentNode.insertBefore(trailingBr, br.nextSibling)
      }
      const newRange = document.createRange()
      newRange.setStartAfter(br)
      newRange.collapse(true)
      sel.removeAllRanges()
      sel.addRange(newRange)
      handleInput()
      return
    }

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

    if (e.key === 'Enter') {
      e.preventDefault()
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
    const isTableLine = (l) => l.includes('|')
    if (!text.includes('\n') && !isTableLine(text.trim())) return

    e.preventDefault()
    const rawLines = text.split(/\r?\n/)
    const processed = []
    let currentTable = null

    for (const line of rawLines) {
      const trimmed = line.trim()
      const isTable = isTableLine(line)
      
      if (isTable) {
        if (currentTable) {
          currentTable.content += '\n' + line
        } else {
          currentTable = { type: 'table', content: line }
          processed.push(currentTable)
        }
      } else if (currentTable && (trimmed === '' || trimmed === '>' || trimmed === '√')) {
        currentTable.content += '\n' + line
      } else {
        currentTable = null
        if (trimmed !== '') {
          processed.push({ type: detectBlockType(line), content: line })
        }
      }
    }

    if (processed.length === 0) return

    const el = elRef.current
    const cursor = getCursorOffset(el)
    const raw = getRawText(el)
    const beforePart = raw.slice(0, cursor)
    const afterPart = raw.slice(cursor)
    
    const first = processed[0]
    const newCurrent = beforePart + first.content + (processed.length === 1 ? afterPart : '')
    el.innerText = newCurrent
    onUpdate(block.block_id, newCurrent, processed.length === 1 ? first.type : detectBlockType(newCurrent), true)

    if (processed.length === 1) return

    const initialBlocks = documentData?.blocks || []
    const initialIdx = initialBlocks.findIndex(b => b.block_id === block.block_id)
    const originalNextBlock = initialIdx !== -1 ? initialBlocks[initialIdx + 1] : null
    const originalNextId = originalNextBlock ? originalNextBlock.block_id : null

    const optimisticBlocks = []
    let rollingPrevKey = block.position_key
    let targetNextKey = originalNextBlock?.position_key || null
    
    if (targetNextKey && parseFloat(targetNextKey) <= parseFloat(rollingPrevKey)) {
      targetNextKey = null
    }

    for (let i = 1; i < processed.length; i++) {
      const item = processed[i]
      const content = i === processed.length - 1 ? item.content + afterPart : item.content
      const newKey = generatePosition(rollingPrevKey, targetNextKey)
      const tempId = 'temp_paste_' + Date.now() + '_' + i + '_' + Math.random().toString(36).slice(2)
      
      optimisticBlocks.push({
        block_id: tempId, localId: tempId,
        content: content, type: item.type,
        position_key: newKey, _focusOnMount: i === processed.length - 1
      })
      rollingPrevKey = newKey
    }

    setDocumentData(prev => {
      if (!prev) return prev
      const newBlocks = [...prev.blocks]
      newBlocks.splice(initialIdx + 1, 0, ...optimisticBlocks)
      newBlocks.sort((a, b) => parseFloat(a.position_key) - parseFloat(b.position_key))
      const next = { ...prev, blocks: newBlocks }
      lastSnapshotRef.current = JSON.stringify(next)
      return next
    })

    let anchorId = block.block_id
    for (const opt of optimisticBlocks) {
      try {
        const data = await onAddAfter(docId, anchorId, originalNextId, opt.content, opt.type, opt.block_id, opt.position_key)
        if (data) anchorId = data.block_id
      } catch (err) {
        console.error('[handlePaste] Failed to save segment:', err)
      }
    }

    try {
      const res = await api.get(`/api/documents/${docId}`)
      const freshData = { ...res.data, blocks: (res.data.blocks || []).map(b => ({ ...b, localId: b.block_id })) }
      setDocumentData(freshData)
      lastSnapshotRef.current = JSON.stringify(freshData)
      
      setTimeout(() => {
        const lastEl = document.querySelector(`[data-id="${anchorId}"]`)
        if (lastEl) moveCursorTo(lastEl, 'end')
      }, 50)
    } catch (err) {
      console.error('[handlePaste] Final refresh failed:', err)
    }
  }, [block.block_id, block.position_key, docId, documentData, lastSnapshotRef, onAddAfter, onUpdate, setDocumentData])

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
