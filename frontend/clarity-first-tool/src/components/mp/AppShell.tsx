import { Link, useRouterState } from "@tanstack/react-router";
import type { ReactNode } from "react";
import {
  LayoutDashboard,
  Settings as SettingsIcon,
  Shield,
  Sparkles,
  UserCog,
  LogOut,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";

import { api } from "@/lib/api/client";
import { cn } from "@/lib/utils";

function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const credits = useQuery({ queryKey: ["credits"], queryFn: api.credits.get });
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings.get });

  const mainNavItems = [
    { title: "Meetings", url: "/dashboard", icon: LayoutDashboard },
    { title: "Settings", url: "/settings", icon: SettingsIcon },
    { title: "Onboarding", url: "/onboarding", icon: UserCog },
  ];

  if (settings.data?.is_admin) {
    mainNavItems.push({ title: "Admin", url: "/admin", icon: Shield });
  }

  const isActive = (url: string) =>
    url === "/dashboard" ? pathname === "/dashboard" || pathname.startsWith("/dashboard/") : pathname === url;

  return (
    <Sidebar collapsible="icon">
      <SidebarContent className="bg-sidebar">
        <div className="flex items-center gap-2 px-3 py-4">
          <span aria-hidden className="inline-block h-2.5 w-2.5 shrink-0 rounded-full bg-signal" />
          {!collapsed && <span className="font-display text-lg">MeetingPilot</span>}
        </div>

        <SidebarGroup>
          <SidebarGroupLabel className="font-mono text-[10px] uppercase tracking-wider">
            Workspace
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {mainNavItems.map((item) => (
                <SidebarMenuItem key={item.url}>
                  <SidebarMenuButton asChild isActive={isActive(item.url)}>
                    <Link to={item.url} className="flex items-center gap-2">
                      <item.icon className="h-4 w-4" />
                      {!collapsed && <span>{item.title}</span>}
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {!collapsed && (
          <SidebarGroup>
            <SidebarGroupLabel className="font-mono text-[10px] uppercase tracking-wider">
              Credits
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <div className="mx-2 rounded-md border border-rule bg-paper-elevated p-3">
                <div className="flex items-baseline justify-between">
                  <span className="font-display text-2xl">{credits.data?.used_count ?? "—"}</span>
                  <span className="font-mono text-[10px] uppercase tracking-wider text-muted-ink">
                    of {credits.data?.total_allowed ?? "—"}
                  </span>
                </div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full bg-signal transition-[width] duration-700"
                    style={{
                      width: credits.data
                        ? `${Math.min(100, (credits.data.used_count / credits.data.total_allowed) * 100)}%`
                        : "0%",
                    }}
                  />
                </div>
                <div className="mt-2 text-[11px] text-muted-ink">Rolls over 1 month.</div>
              </div>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        <div className="mt-auto border-t border-sidebar-border p-3">
          <button
            onClick={() => {
              localStorage.removeItem("mp_access_token");
              window.location.href = "/";
            }}
            className={cn(
              "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm text-muted-ink hover:bg-sidebar-accent hover:text-foreground",
            )}
          >
            <LogOut className="h-4 w-4" />
            {!collapsed && <span>Sign out</span>}
          </button>
        </div>
      </SidebarContent>
    </Sidebar>
  );
}

export function AppShell({
  children,
  title,
  subtitle,
  actions,
}: {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-paper">
        <AppSidebar />
        <div className="flex min-w-0 flex-1 flex-col">

          <header className="flex items-center justify-between gap-4 border-b border-rule bg-paper px-4 py-3 sm:px-6">
            <div className="flex min-w-0 items-center gap-3">
              <SidebarTrigger />
              <div className="min-w-0">
                {subtitle && (
                  <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-ink">
                    {subtitle}
                  </div>
                )}
                {title && (
                  <h1 className="truncate font-display text-2xl leading-tight sm:text-3xl">
                    {title}
                  </h1>
                )}
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {actions}
              <Link
                to="/onboarding"
                className="hidden items-center gap-2 rounded-md border border-rule bg-paper-elevated px-3 py-1.5 text-xs font-medium text-foreground hover:bg-secondary sm:inline-flex"
              >
                <Sparkles className="h-3.5 w-3.5 text-signal" />
                Finish setup
              </Link>
            </div>
          </header>
          <main className="min-w-0 flex-1">{children}</main>
        </div>
      </div>
    </SidebarProvider>
  );
}
