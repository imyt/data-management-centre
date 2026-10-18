// DESIGN.md: time and locale correct. Local time on screen, UTC on hover, locale formats.

const absolute = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" })
const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" })

/** Local date and time, e.g. "17 Oct 2026, 08:42". Put the ISO string in a title for UTC on hover. */
export function formatTimestamp(date: Date) {
  return absolute.format(date)
}

/** "4 minutes ago", "in 2 hours", relative to `now`. */
export function formatRelative(date: Date, now: number) {
  const s = (date.getTime() - now) / 1000
  const a = Math.abs(s)
  if (a < 60) return rtf.format(Math.round(s), "second")
  if (a < 3600) return rtf.format(Math.round(s / 60), "minute")
  if (a < 86400) return rtf.format(Math.round(s / 3600), "hour")
  return rtf.format(Math.round(s / 86400), "day")
}
