import { NotFoundState } from "@/components/patterns"

/** Any route without a screen. */
export function NotFoundPage() {
  return (
    <main className="flex min-h-dvh items-center justify-center">
      <NotFoundState kind="page" action={<a href="/" className="text-sm text-brand underline-offset-4 hover:underline">Go to the Inbox</a>} />
    </main>
  )
}
