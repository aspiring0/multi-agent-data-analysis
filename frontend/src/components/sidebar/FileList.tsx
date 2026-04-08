'use client'

import { useState } from 'react'
import { useAppStore, type UploadedFileMeta } from '@/lib/store'
import * as api from '@/lib/api'
import { cn } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

interface FileListProps {
  collapsed: boolean
  sessionId: string | null
}

export function FileList({ collapsed, sessionId }: FileListProps) {
  const uploadedFiles = useAppStore((s) => s.uploadedFiles)
  const activeFileId = useAppStore((s) => s.activeFileId)
  const setActiveFileId = useAppStore((s) => s.setActiveFileId)
  const removeUploadedFile = useAppStore((s) => s.removeUploadedFile)
  const [previewData, setPreviewData] = useState<Record<string, unknown> | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)

  if (!sessionId || uploadedFiles.length === 0) {
    return null
  }

  const handleDelete = async (fileId: string) => {
    setDeleting(fileId)
    const res = await api.deleteUploadedFile(sessionId, fileId)
    if (res.ok) {
      removeUploadedFile(fileId)
    }
    setDeleting(null)
  }

  const handlePreview = async (fileId: string) => {
    const res = await api.previewUploadedFile(sessionId, fileId)
    if (res.ok && res.data) {
      setPreviewData(res.data as Record<string, unknown>)
    }
  }

  const handleDownload = (fileId: string, filename: string) => {
    const url = api.getDownloadUrl(sessionId, fileId)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
  }

  if (collapsed) {
    return (
      <div className="flex flex-col items-center gap-1 py-2">
        {uploadedFiles.slice(0, 3).map((file) => (
          <button
            key={file.id}
            onClick={() => setActiveFileId(file.id)}
            className={cn(
              'w-10 h-10 rounded-xl flex items-center justify-center text-sm',
              'backdrop-blur-md border transition-all',
              file.id === activeFileId
                ? 'bg-green-500/30 border-green-500/50'
                : 'bg-white/30 dark:bg-white/5 border-white/20 hover:bg-white/50'
            )}
            title={`${file.filename}\n${file.rows} rows x ${file.columns} cols`}
          >
            📄
          </button>
        ))}
      </div>
    )
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="px-3 py-2 text-xs font-medium text-muted-foreground">
        Uploaded Files ({uploadedFiles.length})
      </div>
      <ScrollArea className="flex-1">
        <div className="px-2 space-y-1">
          {uploadedFiles.map((file) => (
            <div
              key={file.id}
              className={cn(
                'group p-2 rounded-lg cursor-pointer transition-all',
                file.id === activeFileId
                  ? 'bg-green-500/20 border border-green-500/30'
                  : 'bg-white/20 hover:bg-white/30 border border-transparent'
              )}
              onClick={() => setActiveFileId(file.id)}
            >
              <div className="flex items-start gap-2">
                <span className="text-lg">📄</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{file.filename}</div>
                  <div className="text-xs text-muted-foreground">
                    {formatFileSize(file.size_bytes)} - {file.rows} rows x {file.columns} cols
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={(e) => { e.stopPropagation(); handlePreview(file.id) }}
                  className="text-xs text-purple-500 hover:text-purple-600"
                >
                  Preview
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDownload(file.id, file.filename) }}
                  className="text-xs text-blue-500 hover:text-blue-600"
                >
                  Download
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(file.id) }}
                  disabled={deleting === file.id}
                  className="text-xs text-red-500 hover:text-red-600 disabled:opacity-50"
                >
                  {deleting === file.id ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>

      {/* Preview Modal */}
      {previewData && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setPreviewData(null)}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-lg p-4 max-w-2xl max-h-[80vh] overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-semibold">Data Preview</h3>
              <button onClick={() => setPreviewData(null)} className="text-gray-500 hover:text-gray-700">
                ✕
              </button>
            </div>
            <div className="text-xs space-y-2">
              <div><strong>Columns:</strong> {(previewData.columns as string[]).join(', ')}</div>
              <div><strong>Data Types:</strong></div>
              <pre className="bg-gray-100 dark:bg-gray-900 p-2 rounded text-xs overflow-x-auto">
                {JSON.stringify(previewData.dtypes, null, 2)}
              </pre>
              <div><strong>First {(previewData.preview_rows as unknown[][]).length} rows:</strong></div>
              <div className="overflow-x-auto">
                <table className="text-xs border-collapse">
                  <thead>
                    <tr>
                      {(previewData.columns as string[]).map((col) => (
                        <th key={col} className="border px-2 py-1 bg-gray-100 dark:bg-gray-900">{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(previewData.preview_rows as unknown[][]).map((row, i) => (
                      <tr key={i}>
                        {row.map((cell, j) => (
                          <td key={j} className="border px-2 py-1">{String(cell)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div><strong>Missing Values:</strong></div>
              <pre className="bg-gray-100 dark:bg-gray-900 p-2 rounded text-xs">
                {JSON.stringify(previewData.missing_values, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}