import { NotFoundState } from "@/components/patterns"

/** Any route without a screen yet, including the header sections until their slices ship. */
export function NotFoundPage() {
  return (
    <main className="flex min-h-dvh items-center justify-center">
      <NotFoundState kind="page" action={<a href="/gallery" className="text-sm text-brand underline-offset-4 hover:underline">Go to the gallery</a>} />
    </main>
  )
}
