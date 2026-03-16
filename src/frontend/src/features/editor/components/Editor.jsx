import { useCallback, useRef, useState } from 'react'
import EditorBlock from './EditorBlock'
import api from '../../../shared/api/api'

export default function Editor({
  docId,
  documentData,
  lastSnapshotRef,
  isTypingRef,
  isSelectingRef,
  setDocumentData,
  onUpdate,
  onDelete,
  onAddAfter,
  isReadOnly,
}) {
  const [selectedBlocks, setSelectedBlocks] = useState(new Set())
  const anchorElRef = useRef(null)
  const isDraggingRef = useRef(false)

  const getAllBlocks = () =>
    Array.from(document.querySelectorAll('#editor .block'))

  const clearSelections = useCallback(() => {
    setSelectedBlocks(new Set())
  }, [])

  const extendSelection = useCallback((anchorEl, targetEl) => {
    const all = getAllBlocks()
    const iA = all.indexOf(anchorEl)
    const iT = all.indexOf(targetEl)
    if (iA === -1 || iT === -1) return
    const start = Math.min(iA, iT)
    const end = Math.max(iA, iT)
    const ids = new Set()
    for (let i = start; i <= end; i++) {
      ids.add(all[i].dataset.id)
    }
    setSelectedBlocks(ids)
  }, [])

  const handleMouseDown = useCallback((e, el) => {
    isSelectingRef.current = true
    if (!e.shiftKey) {
      clearSelections()
      anchorElRef.current = el
    } else if (anchorElRef.current) {
      e.preventDefault()
      extendSelection(anchorElRef.current, el)
    }
    isDraggingRef.current = true

    const onUp = () => {
      isDraggingRef.current = false
      isSelectingRef.current = false
      setSelectedBlocks(prev => (prev.size === 1 ? new Set() : prev))
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mouseup', onUp)
  }, [clearSelections, extendSelection, isSelectingRef])

  const handleMouseOver = useCallback((e, el) => {
    if (isDraggingRef.current && anchorElRef.current && e.buttons === 1) {
      extendSelection(anchorElRef.current, el)
    }
  }, [extendSelection])

  const handleDeleteSelected = useCallback(async () => {
    if (selectedBlocks.size === 0 || isReadOnly) return

    const all = getAllBlocks()
    const selArr = [...selectedBlocks]
    const blocks = documentData?.blocks || []
    const isDeletingAll = selArr.length >= blocks.length

    const lastEl = all.find(el => el.dataset.id === selArr[selArr.length - 1])
    const nextFocus = lastEl
      ? lastEl.nextElementSibling || lastEl.previousElementSibling
      : null

    for (let i = 0; i < selArr.length; i++) {
      const id = selArr[i]
      if (id && !id.startsWith('temp_')) {
        if (isDeletingAll && i === selArr.length - 1) {
          await onUpdate(id, '', 'paragraph')
        } else {
          await onDelete(id)
        }
      }
    }

    clearSelections()
    if (nextFocus?.classList.contains('block')) {
      nextFocus.focus()
    }
  }, [selectedBlocks, onDelete, onUpdate, clearSelections, isReadOnly, documentData])

  const inferType = (text) => {
    const t = text.trim()
    if (t.startsWith('|')) return 'table'
    if (t.startsWith('- ') || /^\d+\./.test(t)) return 'list'
    if (t.startsWith('```')) return 'code'
    if (t.startsWith('#')) return 'heading'
    if (t.startsWith('>')) return 'quote'
    if (t.startsWith('---')) return 'divider'
    return 'paragraph'
  }

  const handleMergeWithPrev = useCallback(async (blockId, blockEl) => {
    const blocks = documentData?.blocks || []
    const idx = blocks.findIndex(b => b.block_id == blockId)
    if (idx <= 0) return

    const prevBlock = blocks[idx - 1]
    const prevEl = blockEl.previousElementSibling
    if (!prevEl) return

    const prevText = prevEl.innerText.replace(/\n$/, '')
    const curText  = blockEl.innerText.replace(/\n$/, '')
    const merged   = prevText + curText
    const mergedType = inferType(merged)

    const updatedBlocks = blocks
      .map(b =>
        b.block_id == prevBlock.block_id
          ? { ...b, content: merged, type: mergedType, _focusOnMount: true, _cursorAt: 'end' }
          : b
      )
      .filter(b => b.block_id != blockId)

    setDocumentData(prev => {
      const next = { ...prev, blocks: updatedBlocks }
      lastSnapshotRef.current = JSON.stringify(next)
      return next
    })

    isTypingRef.current = true
    try {
      await api.patch(`/api/block/${prevBlock.block_id}`, { content: merged, type: mergedType })
      await api.delete(`/api/block/${blockId}`)
    } finally {
      isTypingRef.current = false
    }
  }, [documentData, isTypingRef, lastSnapshotRef, setDocumentData])

  const blocks = documentData?.blocks || []

  return (
    <div id="editor" className="editor">
      {blocks.map(block => (
        <EditorBlock
          key={block.localId || block.block_id}
          block={block}
          isSelected={selectedBlocks.has(String(block.block_id))}
          isTypingRef={isTypingRef}
          docId={docId}
          documentData={documentData}
          lastSnapshotRef={lastSnapshotRef}
          setDocumentData={setDocumentData}
          onMouseDown={handleMouseDown}
          onMouseOver={handleMouseOver}
          onUpdate={onUpdate}
          onDelete={onDelete}
          onMergeWithPrev={handleMergeWithPrev}
          onAddAfter={onAddAfter}
          multiSelectedCount={selectedBlocks.size}
          onDeleteSelected={handleDeleteSelected}
          isReadOnly={isReadOnly}
        />
      ))}
      {blocks.length === 0 && (
        <p className="editor-empty">Open a document to start editing…</p>
      )}
      <span id="__selectedCount" style={{ display: 'none' }}>{selectedBlocks.size}</span>
    </div>
  )
}
