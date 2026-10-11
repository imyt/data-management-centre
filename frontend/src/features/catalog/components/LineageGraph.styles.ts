export const lineageGraphStyles = {
  container:
    "flex flex-col w-full h-full min-h-[500px] bg-card/60 backdrop-blur-md rounded-xl border border-border/80 shadow-sm overflow-hidden select-none",
  toolbar:
    "flex items-center justify-between px-4 py-2.5 border-b border-border/70 bg-muted/30 backdrop-blur-sm shrink-0 gap-3",
  toolbarGroup: "flex items-center gap-2",
  titleText: "text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5",
  statsBadge:
    "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-secondary text-secondary-foreground border border-border/50",
  controlButton:
    "inline-flex items-center justify-center p-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted/80 border border-transparent hover:border-border/60 transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed",
  selectInput:
    "h-7 text-xs bg-background border border-border/80 rounded-md px-2 py-0.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer",
  viewport:
    "flex-1 relative w-full h-[540px] overflow-auto bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-muted/20 via-background to-background p-6",
  svgCanvas:
    "absolute inset-0 w-full h-full pointer-events-none z-0 overflow-visible",
  columnsLayout:
    "relative z-10 flex items-stretch justify-between gap-12 min-w-[760px] h-full",
  column:
    "flex flex-col items-center justify-center gap-6 flex-1 min-w-[210px] max-w-[260px]",
  columnHeader:
    "text-[10px] font-bold uppercase tracking-wider text-muted-foreground/80 flex items-center gap-1.5 px-3 py-1 rounded-full bg-muted/40 border border-border/40 mb-2 shrink-0",
  nodeCard:
    "relative w-full rounded-xl p-3.5 bg-card/90 hover:bg-card border border-border/70 hover:border-primary/60 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer group flex flex-col gap-2",
  nodeCardCenter:
    "relative w-full rounded-xl p-4 bg-gradient-to-b from-primary/10 via-card to-card border-2 border-primary shadow-lg shadow-primary/5 transition-all duration-200 cursor-pointer group flex flex-col gap-2.5 ring-2 ring-primary/20",
  nodeHeader: "flex items-center justify-between gap-2 w-full",
  nodeTitle:
    "text-xs font-bold text-foreground truncate group-hover:text-primary transition-colors",
  activeBadge:
    "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider bg-primary text-primary-foreground shadow-sm animate-pulse shrink-0",
  statusBadgePublished:
    "px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20",
  statusBadgeDraft:
    "px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20",
  statusBadgeDefault:
    "px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase bg-muted text-muted-foreground border border-border/60",
  directionBadge:
    "text-[10px] font-medium text-muted-foreground flex items-center gap-1",
  edgePill:
    "text-[9px] font-mono font-medium px-2 py-0.5 rounded-full bg-background/95 border border-border/80 text-foreground shadow-xs pointer-events-auto hover:border-primary/60 transition-colors",
  emptyContainer:
    "flex flex-col items-center justify-center h-full min-h-[360px] text-center p-8 space-y-3",
  loadingOverlay:
    "flex items-center justify-center absolute inset-0 bg-background/60 backdrop-blur-xs z-30",
} as const;
