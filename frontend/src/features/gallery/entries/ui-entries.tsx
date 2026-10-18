import { ChevronDownIcon, DownloadIcon, PlusIcon, SearchIcon, TrashIcon } from "lucide-react"
import { toast } from "sonner"

import type { GalleryEntry } from "@/features/gallery/specimen"
import { Badge } from "@/components/ui/badge"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

const S = { "data-gallery-subject": "" } as const

function DomainSelect(props: { disabled?: boolean; invalid?: boolean; subject?: boolean; id: string }) {
  return (
    <Select disabled={props.disabled}>
      <SelectTrigger id={props.id} aria-label="Domain" aria-invalid={props.invalid || undefined} className="w-48" {...(props.subject ? S : {})}>
        <SelectValue placeholder="Choose a domain" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="finance">Finance</SelectItem>
        <SelectItem value="marketing">Marketing</SelectItem>
        <SelectItem value="operations">Operations</SelectItem>
      </SelectContent>
    </Select>
  )
}

function MiniTable({ rows }: { rows: { id: string; name: string; owner: string; rows: string }[] }) {
  return (
    <Table aria-label="Assets">
      <TableHeader>
        <TableRow>
          <TableHead>ID</TableHead>
          <TableHead>Asset</TableHead>
          <TableHead className="text-right">Rows</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((r) => (
          <TableRow key={r.id}>
            <TableCell className="mono">{r.id}</TableCell>
            <TableCell>{r.name}</TableCell>
            <TableCell className="text-right tabular-nums">{r.rows}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function TabPanels() {
  return (
    <>
      {["details", "lineage", "history"].map((value) => (
        <TabsContent key={value} value={value} forceMount className="text-sm text-muted-foreground data-[state=inactive]:hidden">
          {value === "details" ? "Owned by Finance." : value === "lineage" ? "3 upstream sources." : "12 changes this month."}
        </TabsContent>
      ))}
    </>
  )
}

const sampleRows = [
  { id: "AST-004821", name: "Customer master", owner: "David Vance", rows: "1,284,902" },
  { id: "AST-004822", name: "Payment events", owner: "Elena Rostova", rows: "48,113,067" },
]

export const uiEntries: GalleryEntry[] = [
  {
    id: "button",
    name: "Button",
    layer: "ui",
    summary:
      "One primary (default) action per view; secondary and ghost (tertiary) for everything else. Destructive is danger text, confirmed in a dialog. Disabled always says why.",
    variants: (
      <div className="flex flex-wrap items-center gap-2">
        <Button>
          <PlusIcon /> Create asset
        </Button>
        <Button variant="secondary">
          <DownloadIcon /> Export CSV
        </Button>
        <Button variant="outline">Filters</Button>
        <Button variant="ghost">View history</Button>
        <Button variant="destructive">
          <TrashIcon /> Delete dataset
        </Button>
        <Button variant="link">Open lineage</Button>
        <Button variant="ghost" size="icon" aria-label="Search">
          <SearchIcon />
        </Button>
      </div>
    ),
    states: {
      default: <Button>Save policy</Button>,
      hover: <Button {...S}>Save policy</Button>,
      focus: <Button {...S}>Save policy</Button>,
      disabled: (
        <Button disabled disabledReason="Add a data owner before submitting.">
          Submit for approval
        </Button>
      ),
      loading: <Button loading>Saving</Button>,
      error: { na: "a button carries no error of its own; the form or toast reports the failure." },
      empty: { na: "a button always has a label." },
    },
  },
  {
    id: "input",
    name: "Input",
    layer: "ui",
    summary: "Single-line text. Always paired with a label above (see Field). Placeholder is never the only label.",
    states: {
      default: <Input aria-label="Asset name" defaultValue="Customer master" />,
      hover: <Input aria-label="Asset name" defaultValue="Customer master" {...S} />,
      focus: <Input aria-label="Asset name" defaultValue="Customer master" {...S} />,
      disabled: <Input aria-label="Asset name" defaultValue="Customer master" disabled />,
      loading: <Skeleton className="h-(--control-height) w-full" />,
      error: <Input aria-label="Retention days" defaultValue="-30" aria-invalid />,
      empty: <Input aria-label="Asset name" placeholder="For example, Customer master" />,
    },
  },
  {
    id: "textarea",
    name: "Textarea",
    layer: "ui",
    summary: "Multi-line text, for reasons, resolution notes and comments. Grows with its content.",
    states: {
      default: <Textarea aria-label="Reason" defaultValue="Retention extended to cover the audit window." />,
      hover: <Textarea aria-label="Reason" defaultValue="Retention extended." {...S} />,
      focus: <Textarea aria-label="Reason" defaultValue="Retention extended." {...S} />,
      disabled: <Textarea aria-label="Reason" defaultValue="Locked while under review." disabled />,
      loading: <Skeleton className="h-20 w-full" />,
      error: <Textarea aria-label="Reason" aria-invalid />,
      empty: <Textarea aria-label="Reason" placeholder="Add a short reason" />,
    },
  },
  {
    id: "select",
    name: "Select",
    layer: "ui",
    summary: "Pick one value from a short, known list. Use Command for long or searchable lists.",
    states: {
      default: <DomainSelect id="select-default" />,
      hover: <DomainSelect id="select-hover" subject />,
      focus: <DomainSelect id="select-focus" subject />,
      disabled: <DomainSelect id="select-disabled" disabled />,
      loading: <Skeleton className="h-(--control-height) w-48" />,
      error: <DomainSelect id="select-error" invalid />,
      empty: <DomainSelect id="select-empty" />,
    },
  },
  {
    id: "checkbox",
    name: "Checkbox",
    layer: "ui",
    summary: "Multi-select in lists and tables, and yes/no settings that apply on save.",
    states: {
      default: (
        <Label>
          <Checkbox defaultChecked /> Includes personal data
        </Label>
      ),
      hover: (
        <Label>
          <Checkbox {...S} /> Includes personal data
        </Label>
      ),
      focus: (
        <Label>
          <Checkbox {...S} /> Includes personal data
        </Label>
      ),
      disabled: (
        <Label>
          <Checkbox disabled defaultChecked /> Includes personal data
        </Label>
      ),
      loading: { na: "the value is known before the control renders; the form shows loading." },
      error: (
        <Label>
          <Checkbox aria-invalid /> I confirm the export is approved
        </Label>
      ),
      empty: (
        <Label>
          <Checkbox checked="indeterminate" /> Some rows selected
        </Label>
      ),
    },
  },
  {
    id: "switch",
    name: "Switch",
    layer: "ui",
    summary: "A setting that takes effect immediately. Use Checkbox when the change waits for Save.",
    states: {
      default: (
        <Label>
          <Switch defaultChecked /> Notify owners
        </Label>
      ),
      hover: (
        <Label>
          <Switch {...S} /> Notify owners
        </Label>
      ),
      focus: (
        <Label>
          <Switch {...S} /> Notify owners
        </Label>
      ),
      disabled: (
        <Label>
          <Switch disabled /> Notify owners
        </Label>
      ),
      loading: { na: "a switch applies instantly; a failure rolls back with a toast." },
      error: { na: "a failed change rolls back and reports through a toast." },
      empty: { na: "a switch is always on or off." },
    },
  },
  {
    id: "label",
    name: "Label",
    layer: "ui",
    summary: "Names a control. Always above inputs (see Field); beside checkboxes and switches.",
    states: {
      default: <Label>Data owner</Label>,
      hover: { na: "labels are not interactive; clicking one focuses its control." },
      focus: { na: "focus lands on the control, not the label." },
      disabled: (
        <Label>
          <Checkbox disabled /> Archived
        </Label>
      ),
      loading: <Skeleton className="h-4 w-24" />,
      error: { na: "the error message goes under the control (see Field)." },
      empty: { na: "every control has a label." },
    },
  },
  {
    id: "badge",
    name: "Badge",
    layer: "ui",
    summary: "A small tag. Status badges always carry an icon and label (see StatusBadge); no colour-only badges.",
    variants: (
      <div className="flex flex-wrap gap-2">
        <Badge variant="secondary">Draft</Badge>
        <Badge variant="outline">PII</Badge>
        <Badge variant="success">Compliant</Badge>
        <Badge variant="warning">Due in 2h</Badge>
        <Badge variant="destructive">Breached</Badge>
      </div>
    ),
    states: {
      default: <Badge variant="secondary">Draft</Badge>,
      hover: { na: "badges are not interactive." },
      focus: { na: "badges are not interactive." },
      disabled: { na: "badges are not interactive." },
      loading: <Skeleton className="h-5 w-16" />,
      error: <Badge variant="destructive">Breached</Badge>,
      empty: { na: "an empty value renders an em dash, not an empty badge." },
    },
  },
  {
    id: "skeleton",
    name: "Skeleton",
    layer: "ui",
    summary: "The loading placeholder. Skeletons over spinners, shaped like the content they replace.",
    states: {
      default: (
        <div className="flex w-full flex-col gap-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      ),
      hover: { na: "not interactive." },
      focus: { na: "not interactive." },
      disabled: { na: "not interactive." },
      loading: <Skeleton className="h-(--row-height) w-full" />,
      error: { na: "replaced by an error state once loading fails." },
      empty: { na: "replaced by an empty state once loading returns nothing." },
    },
  },
  {
    id: "separator",
    name: "Separator",
    layer: "ui",
    summary: "A hairline. Use sparingly; prefer larger gaps over dividers.",
    states: {
      default: (
        <div className="flex w-full flex-col gap-3 text-sm">
          <span>Ownership</span>
          <Separator />
          <span>Lineage</span>
        </div>
      ),
      hover: { na: "not interactive." },
      focus: { na: "not interactive." },
      disabled: { na: "not interactive." },
      loading: { na: "decorative." },
      error: { na: "decorative." },
      empty: { na: "decorative." },
    },
  },
  {
    id: "tooltip",
    name: "Tooltip",
    layer: "ui",
    summary: "The full value behind truncation, the name of an icon-only button, or why something is disabled.",
    states: {
      default: (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Download CSV">
              <DownloadIcon />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Download CSV</TooltipContent>
        </Tooltip>
      ),
      hover: (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Download CSV" {...S}>
              <DownloadIcon />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Download CSV</TooltipContent>
        </Tooltip>
      ),
      focus: (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Download CSV" {...S}>
              <DownloadIcon />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Download CSV</TooltipContent>
        </Tooltip>
      ),
      disabled: (
        <Button disabled disabledReason="You need the Steward role to export.">
          Export
        </Button>
      ),
      loading: { na: "tooltip text is static." },
      error: { na: "errors are shown inline, never only in a tooltip." },
      empty: { na: "no tooltip when there is nothing to add." },
    },
  },
  {
    id: "popover",
    name: "Popover",
    layer: "ui",
    summary: "Small non-modal detail anchored to a trigger, such as a filter editor. shadow-sm, no border.",
    states: {
      default: (
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="outline">
              Owner <ChevronDownIcon />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="flex flex-col gap-2">
            <Label htmlFor="owner-filter">Owner</Label>
            <Input id="owner-filter" placeholder="Search people" />
          </PopoverContent>
        </Popover>
      ),
      hover: (
        <Button variant="outline" {...S}>
          Owner <ChevronDownIcon />
        </Button>
      ),
      focus: (
        <Button variant="outline" {...S}>
          Owner <ChevronDownIcon />
        </Button>
      ),
      disabled: (
        <Button variant="outline" disabled disabledReason="Choose a domain first.">
          Owner <ChevronDownIcon />
        </Button>
      ),
      loading: { na: "content loads inside it using skeletons." },
      error: { na: "content shows its own error state." },
      empty: { na: "content shows its own empty state." },
    },
  },
  {
    id: "dropdown-menu",
    name: "Dropdown menu",
    layer: "ui",
    summary: "Secondary actions on a record or row. Destructive items use danger text and confirm in a dialog.",
    states: {
      default: (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline">
              Actions <ChevronDownIcon />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem>Reassign</DropdownMenuItem>
            <DropdownMenuItem>Duplicate</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive">Delete</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
      hover: (
        <Button variant="outline" {...S}>
          Actions <ChevronDownIcon />
        </Button>
      ),
      focus: (
        <Button variant="outline" {...S}>
          Actions <ChevronDownIcon />
        </Button>
      ),
      disabled: (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline">
              Actions <ChevronDownIcon />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem>Reassign</DropdownMenuItem>
            <DropdownMenuItem disabled>Delete (locked by Sarah Chen)</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
      loading: { na: "menu items are known up front." },
      error: { na: "actions report failures through a toast." },
      empty: { na: "hide the menu when no action is available to the role." },
    },
  },
  {
    id: "dialog",
    name: "Dialog",
    layer: "ui",
    summary: "Focused, interruptive tasks only. One title, one primary action, Esc closes.",
    states: {
      default: (
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="destructive">Delete 3 datasets</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete 3 datasets?</DialogTitle>
              <DialogDescription>Their lineage and history stay in the audit log. This can't be undone.</DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="secondary">Cancel</Button>
              </DialogClose>
              <Button variant="destructive">Delete 3 datasets</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      ),
      hover: { na: "see the trigger's button states." },
      focus: { na: "focus moves into the dialog and returns to the trigger on close." },
      disabled: { na: "hide the trigger, or disable it with a reason." },
      loading: (
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="secondary">Open while saving</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Reject request</DialogTitle>
              <DialogDescription>A comment is required when rejecting.</DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button loading>Rejecting</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      ),
      error: (
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="secondary">Open with error</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Reject request</DialogTitle>
              <DialogDescription>A comment is required when rejecting.</DialogDescription>
            </DialogHeader>
            <Textarea aria-label="Comment" aria-invalid />
            <p className="text-xs text-danger">Add a comment so the requester knows what to change.</p>
            <DialogFooter>
              <Button>Reject</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      ),
      empty: { na: "a dialog always has a task." },
    },
  },
  {
    id: "sheet",
    name: "Sheet",
    layer: "ui",
    summary: "Record detail as an overlay on the Compact tier (1280 to 1535px); a side-by-side pane on wider screens.",
    states: {
      default: (
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="secondary">Open AST-004821</Button>
          </SheetTrigger>
          <SheetContent>
            <SheetHeader>
              <SheetTitle>Customer master</SheetTitle>
              <SheetDescription className="mono">AST-004821</SheetDescription>
            </SheetHeader>
          </SheetContent>
        </Sheet>
      ),
      hover: { na: "see the trigger's button states." },
      focus: { na: "focus moves into the sheet and returns to the trigger on close." },
      disabled: { na: "hide the trigger when there is no detail to show." },
      loading: (
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="secondary">Open while loading</Button>
          </SheetTrigger>
          <SheetContent>
            <SheetHeader>
              <SheetTitle>Loading record</SheetTitle>
              <SheetDescription>Fetching details.</SheetDescription>
            </SheetHeader>
            <div className="flex flex-col gap-2 px-4">
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          </SheetContent>
        </Sheet>
      ),
      error: { na: "the sheet body shows ErrorState." },
      empty: { na: "the sheet body shows EmptyState." },
    },
  },
  {
    id: "tabs",
    name: "Tabs",
    layer: "ui",
    summary: "Switch between sections of one record (Details, Lineage, History). Text first, an accent line marks the active tab.",
    states: {
      default: (
        <Tabs defaultValue="details">
          <TabsList>
            <TabsTrigger value="details">Details</TabsTrigger>
            <TabsTrigger value="lineage">Lineage</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>
          <TabPanels />
        </Tabs>
      ),
      hover: (
        <Tabs defaultValue="details">
          <TabsList>
            <TabsTrigger value="details">Details</TabsTrigger>
            <TabsTrigger value="lineage" {...S}>
              Lineage
            </TabsTrigger>
          </TabsList>
          <TabPanels />
        </Tabs>
      ),
      focus: (
        <Tabs defaultValue="details">
          <TabsList>
            <TabsTrigger value="details" {...S}>
              Details
            </TabsTrigger>
            <TabsTrigger value="lineage">Lineage</TabsTrigger>
          </TabsList>
          <TabPanels />
        </Tabs>
      ),
      disabled: (
        <Tabs defaultValue="details">
          <TabsList>
            <TabsTrigger value="details">Details</TabsTrigger>
            <TabsTrigger value="history" disabled>
              History
            </TabsTrigger>
          </TabsList>
          <TabPanels />
        </Tabs>
      ),
      loading: { na: "panel content loads with skeletons; tabs are static." },
      error: { na: "the panel shows ErrorState." },
      empty: { na: "the panel shows EmptyState." },
    },
  },
  {
    id: "table",
    name: "Table",
    layer: "ui",
    wide: true,
    summary: "The shadcn table primitives. Use DataTable for any real list; it adds sorting, selection and states.",
    states: {
      default: <MiniTable rows={sampleRows} />,
      hover: { na: "see DataTable; rows highlight on hover." },
      focus: { na: "see DataTable; rows are focusable when they open a detail panel." },
      disabled: { na: "rows are never disabled; explain read-only instead." },
      loading: { na: "see DataTable skeleton rows." },
      error: { na: "see DataTable error state." },
      empty: { na: "see DataTable empty state." },
    },
  },
  {
    id: "breadcrumb",
    name: "Breadcrumb",
    layer: "ui",
    summary: "Where a record sits (domain, then asset). Quiet and text-first.",
    states: {
      default: (
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink href="#breadcrumb">Finance</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>Customer master</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      ),
      hover: (
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink href="#breadcrumb" {...S}>
                Finance
              </BreadcrumbLink>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      ),
      focus: (
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink href="#breadcrumb" {...S}>
                Finance
              </BreadcrumbLink>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      ),
      disabled: { na: "the current page is plain text, not a disabled link." },
      loading: <Skeleton className="h-4 w-40" />,
      error: { na: "navigation context; the page reports errors." },
      empty: { na: "top-level pages have no breadcrumb." },
    },
  },
  {
    id: "command",
    name: "Command",
    layer: "ui",
    summary: "Powers the ⌘K palette, the primary navigation. Also for long, searchable pick lists.",
    states: {
      default: (
        <Command className="w-full rounded-md" label="Search">
          <CommandInput placeholder="Search assets, policies, people" />
          <CommandList>
            <CommandGroup heading="Assets">
              <CommandItem>Customer master</CommandItem>
              <CommandItem>Payment events</CommandItem>
            </CommandGroup>
          </CommandList>
        </Command>
      ),
      hover: { na: "items highlight on pointer and arrow keys alike (see default)." },
      focus: (
        <Command className="w-full rounded-md" label="Search">
          <CommandInput placeholder="Search" {...S} />
          <CommandList>
            <CommandItem>Customer master</CommandItem>
          </CommandList>
        </Command>
      ),
      disabled: (
        <Command className="w-full rounded-md" label="Search">
          <CommandInput placeholder="Search" />
          <CommandList>
            <CommandItem disabled>Retention policy (no access)</CommandItem>
          </CommandList>
        </Command>
      ),
      loading: (
        <Command className="w-full rounded-md" label="Search">
          <CommandInput placeholder="Search" />
          <CommandList aria-busy="true">
            <div className="flex flex-col gap-2 p-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          </CommandList>
        </Command>
      ),
      error: { na: "search failures show a toast and keep the query." },
      empty: (
        <Command className="w-full rounded-md" label="Search">
          <CommandInput placeholder="Search" />
          <CommandList>
            <CommandEmpty>No matches. Try a record ID.</CommandEmpty>
          </CommandList>
        </Command>
      ),
    },
  },
  {
    id: "toast",
    name: "Toast",
    layer: "ui",
    summary: "Short confirmation after an action, with undo where possible. Status toasts keep their icon.",
    states: {
      default: (
        <Button variant="secondary" onClick={() => toast("Policy saved", { action: { label: "Undo", onClick: () => undefined } })}>
          Show toast
        </Button>
      ),
      hover: { na: "toasts pause on hover; see the live example." },
      focus: { na: "toasts are announced in a live region." },
      disabled: { na: "not interactive." },
      loading: (
        <Button variant="secondary" onClick={() => toast.loading("Exporting 1,284 rows")}>
          Show loading toast
        </Button>
      ),
      error: (
        <Button variant="secondary" onClick={() => toast.error("Couldn't save. Your changes are kept; try again.")}>
          Show error toast
        </Button>
      ),
      empty: { na: "no toast without a message." },
    },
  },
]
