export function formatDate(date: string | Date, fmt = 'YYYY-MM-DD HH:mm'): string {
  const d = new Date(date)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  return fmt.replace('YYYY', String(year)).replace('MM', month).replace('DD', day).replace('HH', hours).replace('mm', minutes)
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

export function statusText(status: string): string {
  const map: Record<string, string> = {
    draft: '草稿', pending: '待处理', generating: '生成中', in_review: '审核中',
    approved: '已通过', rejected: '已驳回', published: '已发布', scheduled: '已排期',
    active: '活跃', suspended: '已暂停', archived: '已归档',
  }
  return map[status] || status
}

export function statusType(status: string): '' | 'success' | 'warning' | 'info' | 'danger' {
  const map: Record<string, '' | 'success' | 'warning' | 'info' | 'danger'> = {
    draft: 'info', approved: 'success', rejected: 'danger', published: 'success',
    active: 'success', suspended: 'warning', archived: 'info', pending: 'warning',
    in_review: 'warning', generating: 'warning', scheduled: 'info',
  }
  return map[status] || 'info'
}
