import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import {
  ClipboardCheck,
  Download,
  FolderOpen,
  LayoutDashboard,
  LifeBuoy,
  Upload,
  type LucideIcon,
} from "lucide-react";

import { DocketLogo } from "@/components/DocketLogo";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui/button";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import { useLogout, useMe } from "@/features/auth/hooks";
import type { Role } from "@/features/auth/schemas";

type NavTo = "/queue" | "/applications" | "/import" | "/dashboard" | "/export" | "/help";

interface NavItem {
  to: NavTo;
  label: string;
  icon: LucideIcon;
  roles: Role[];
}

/** Plain task names: what the person does there, not the module it lives in. */
const WORK: NavItem[] = [
  { to: "/queue", label: "Review queue", icon: ClipboardCheck, roles: ["verifier"] },
  { to: "/applications", label: "Applications", icon: FolderOpen, roles: ["staff", "verifier"] },
  { to: "/import", label: "Import applications", icon: Upload, roles: ["staff"] },
  { to: "/export", label: "Export verified list", icon: Download, roles: ["staff"] },
];

const INSIGHT: NavItem[] = [
  { to: "/dashboard", label: "Overview", icon: LayoutDashboard, roles: ["staff", "verifier"] },
  { to: "/help", label: "Help Center", icon: LifeBuoy, roles: ["staff", "verifier"] },
];

const ROLE_WORDS: Record<Role, string> = { staff: "Staff", verifier: "Verifier" };

/** The focus ring and hover of the ghost buttons on the deep teal ground. */
const ON_DEEP =
  "text-header-foreground hover:bg-header-foreground/15 hover:text-header-foreground focus-visible:ring-header-foreground";

function Group({ label, items, role }: { label: string; items: NavItem[]; role: Role }) {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const { setOpenMobile } = useSidebar();
  const visible = items.filter((item) => item.roles.includes(role));
  if (visible.length === 0) {
    return null;
  }
  return (
    <SidebarGroup>
      <SidebarGroupLabel>{label}</SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          {visible.map((item) => (
            <SidebarMenuItem key={item.to}>
              <SidebarMenuButton
                asChild
                size="lg"
                isActive={pathname === item.to || pathname.startsWith(`${item.to}/`)}
              >
                <Link
                  to={item.to}
                  activeProps={{ "aria-current": "page" }}
                  onClick={() => {
                    setOpenMobile(false);
                  }}
                >
                  <item.icon aria-hidden="true" />
                  <span>{item.label}</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}

/** The signed-in shell's navigation: logo, the work for this role, overview and help, then the person. */
export function AppSidebar() {
  const { data: me } = useMe();
  const logout = useLogout();
  const navigate = useNavigate();
  return (
    <Sidebar>
      <SidebarHeader className="px-4 pt-5 pb-3">
        <Link
          to="/"
          aria-label="Docket"
          className="inline-flex min-h-11 items-center rounded-md focus-visible:ring-2 focus-visible:ring-header-foreground focus-visible:outline-none"
        >
          <DocketLogo withName />
        </Link>
      </SidebarHeader>
      <SidebarContent>
        <nav aria-label="Main" className="flex flex-col gap-2">
          {me && <Group label="Work" items={WORK} role={me.role} />}
          {me && <Group label="Overview and help" items={INSIGHT} role={me.role} />}
        </nav>
      </SidebarContent>
      <SidebarFooter className="gap-3 border-t border-sidebar-border p-4">
        {me && (
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">{me.display_name}</p>
            <p className="text-xs text-sidebar-foreground/80">{ROLE_WORDS[me.role]}</p>
          </div>
        )}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            className={`min-h-11 flex-1 border border-header-foreground/40 lg:min-h-8 ${ON_DEEP}`}
            disabled={logout.isPending}
            onClick={() => {
              logout.mutate(undefined, {
                onSettled: () => {
                  void navigate({ to: "/sign-in" });
                },
              });
            }}
          >
            Sign out
          </Button>
          <ThemeToggle className={ON_DEEP} />
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
