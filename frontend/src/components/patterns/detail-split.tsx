import * as React from "react"
import { XIcon } from "lucide-react"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable"
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet"
import { useMediaQuery } from "@/hooks/use-media-query"
import { useSearchParam } from "@/hooks/use-search-param"

interface DetailContextValue {
  mode: "sheet" | "panel"
  /** Respects the unsaved-changes guard. */
  close: () => void
  /** Open another item in place (one detail at a time). */
  open: (id: string) => void
  setDirty: (dirty: boolean) => void
}

const DetailContext = React.createContext<DetailContextValue | null>(null)

export function useDetail() {
  const context = React.useContext(DetailContext)
  if (!context) throw new Error("useDetail must be used inside DetailSplit")
  return context
}

/** For list rows: the selected id and a setter, synced to `?<param>=<id>`. */
export function useDetailParam(param: string) {
  return useSearchParam(param)
}

interface DetailSplitProps {
  /** Query parameter that holds the selected id, e.g. "asset" for ?asset=AST-10482. */
  param: string
  /** Accessible name for the detail region. */
  label: string
  /** The list or table. Rows open a detail through useDetailParam. */
  list: React.ReactNode
  children: (id: string) => React.ReactNode
  /** Docked split view at or above this width; modal sheet below it. */
  wideQuery?: string
}

/**
 * List plus detail (DESIGN.md: Context stays put). At 1536px and wider the detail docks in a
 * resizable panel beside the list; below that it opens in a sheet. The URL always holds the selection.
 */
export function DetailSplit({ param, label, list, children, wideQuery = "(min-width: 1536px)" }: DetailSplitProps) {
  const [id, setId] = useSearchParam(param)
  const wide = useMediaQuery(wideQuery)
  const [dirty, setDirty] = React.useState(false)
  const [guardOpen, setGuardOpen] = React.useState(false)

  React.useEffect(() => setDirty(false), [id])

  const close = React.useCallback(() => {
    if (dirty) setGuardOpen(true)
    else setId(null)
  }, [dirty, setId])

  const context = React.useMemo<DetailContextValue>(
    () => ({ mode: wide ? "panel" : "sheet", close, open: (next) => setId(next), setDirty }),
    [wide, close, setId]
  )

  const content = id ? <DetailContext.Provider value={context}>{children(id)}</DetailContext.Provider> : null

  const guard = (
    <AlertDialog open={guardOpen} onOpenChange={setGuardOpen}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Discard unsaved changes?</AlertDialogTitle>
          <AlertDialogDescription>Your edits to this item will be lost.</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Keep editing</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            onClick={() => {
              setDirty(false)
              setId(null)
            }}
          >
            Discard changes
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )

  if (wide) {
    return (
      <>
        <ResizablePanelGroup orientation="horizontal" data-slot="detail-split" className="h-full min-h-0">
          <ResizablePanel id={`${param}-list`} minSize="35%" className="min-w-0">
            {list}
          </ResizablePanel>
          {id && (
            <>
              <ResizableHandle withHandle aria-label={`Resize ${label.toLowerCase()}`} />
              <ResizablePanel id={`${param}-detail`} defaultSize="40%" minSize="25%" maxSize="55%">
                <aside
                  aria-label={label}
                  onKeyDown={(event) => event.key === "Escape" && close()}
                  className="flex h-full min-h-0 flex-col border-l bg-surface"
                >
                  {content}
                </aside>
              </ResizablePanel>
            </>
          )}
        </ResizablePanelGroup>
        {guard}
      </>
    )
  }

  return (
    <>
      {list}
      <Sheet open={!!id} onOpenChange={(next) => !next && close()}>
        <SheetContent side="right" showCloseButton={false} className="w-full gap-0 p-0 sm:max-w-xl xl:max-w-2xl">
          <SheetTitle className="sr-only">{label}</SheetTitle>
          <SheetDescription className="sr-only">Details for the selected item</SheetDescription>
          {content}
        </SheetContent>
      </Sheet>
      {guard}
    </>
  )
}

interface DetailLayoutProps {
  /** Usually an <EntityHeader />. */
  header: React.ReactNode
  children: React.ReactNode
  /** Sticky actions; primary action last. */
  footer?: React.ReactNode
}

/** Fixed anatomy for every detail: header, scrolling body, sticky footer. */
export function DetailLayout({ header, children, footer }: DetailLayoutProps) {
  const { close } = useDetail()
  return (
    <div data-slot="detail-layout" className="flex h-full min-h-0 flex-col">
      <div className="relative border-b px-6 pt-5 pr-12 pb-4">
        {header}
        <Button variant="ghost" size="icon-sm" onClick={close} aria-label="Close details" className="absolute top-3 right-3">
          <XIcon aria-hidden="true" />
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">{children}</div>
      {footer && <div className="flex items-center justify-end gap-2 border-t bg-surface px-6 py-3">{footer}</div>}
    </div>
  )
}
