/** 将后端 ISO 时间转换为上海时区的可读时间。 */
export function formatDateTime(value: string): string {
  const date = new Date(value)

  // 避免后端意外返回非法时间时页面直接显示 Invalid Date。
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  })
    .format(date)
    .replace(/\//g, '-')
}