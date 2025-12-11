"use client";

import * as React from "react";
import { Suspense } from "react";
import { usePathname, useSearchParams, useRouter } from "next/navigation";
import { PlayCircle, Radio, Edit } from "lucide-react";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import AtomIcon from "@/components/icons/atom";
import BracketsIcon from "@/components/icons/brackets";
import ProcessorIcon from "@/components/icons/proccesor";
import CuteRobotIcon from "@/components/icons/cute-robot";
import EmailIcon from "@/components/icons/email";
import GearIcon from "@/components/icons/gear";
import MonkeyIcon from "@/components/icons/monkey";
import DotsVerticalIcon from "@/components/icons/dots-vertical";
import { Bullet } from "@/components/ui/bullet";
import LockIcon from "@/components/icons/lock";
import Image from "next/image";
import { useIsV0 } from "@/lib/v0-context";
import type { NFLMode } from "@/components/nfl/mode-selector";

// This is sample data for the sidebar
const data = {
  // navMain: [
  //   {
  //     title: "Tools",
  //     items: [
  //       {
  //         title: "Overview",
  //         url: "/",
  //         icon: BracketsIcon,
  //         isActive: true,
  //       },
  //       {
  //         title: "Laboratory",
  //         url: "/laboratory",
  //         icon: AtomIcon,
  //         isActive: false,
  //       },
  //       {
  //         title: "Devices",
  //         url: "/devices",
  //         icon: ProcessorIcon,
  //         isActive: false,
  //       },
  //       {
  //         title: "Security",
  //         url: "/security",
  //         icon: CuteRobotIcon,
  //         isActive: false,
  //       },
  //       {
  //         title: "Communication",
  //         url: "/communication",
  //         icon: EmailIcon,
  //         isActive: false,
  //       },
  //       {
  //         title: "Admin Settings",
  //         url: "/admin",
  //         icon: GearIcon,
  //         isActive: false,
  //         locked: true,
  //       },
  //     ],
  //   },
  // ],
  desktop: {
    title: "Desktop (Online)",
    status: "online",
  },
  user: {
    name: "KRIMSON",
    email: "krimson@joyco.studio",
    avatar: "/avatars/user_krimson.png",
  },
};

function NFLModeSelector() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const currentMode = (searchParams.get("mode") || "simulation") as NFLMode;

  const handleModeChange = (mode: NFLMode) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("mode", mode);
    router.push(`${pathname}?${params.toString()}`);
  };

  const nflModes: Array<{
    mode: NFLMode;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
  }> = [
    { mode: "simulation", label: "Simulation", icon: PlayCircle },
    { mode: "live", label: "Live", icon: Radio },
    { mode: "manual", label: "Manual", icon: Edit },
  ];

  return (
    <SidebarGroup>
      <SidebarGroupLabel>
        <Bullet className="mr-2" />
        NFL Mode
      </SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          {nflModes.map((modeItem) => {
            const Icon = modeItem.icon;
            const isActive = currentMode === modeItem.mode;
            return (
              <SidebarMenuItem key={modeItem.mode}>
                <SidebarMenuButton
                  isActive={isActive}
                  onClick={() => handleModeChange(modeItem.mode)}
                  className="cursor-pointer"
                >
                  <Icon className="size-5" />
                  <span>{modeItem.label}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            );
          })}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}

export function DashboardSidebar({
  className,
  ...props
}: React.ComponentProps<typeof Sidebar>) {
  const isV0 = useIsV0();
  const pathname = usePathname();
  const isNFLPage = pathname === "/nfl" || pathname === "/";

  return (
    <Sidebar {...props} className={cn("py-sides", className)}>
      <SidebarHeader className="rounded-t-lg flex gap-3 flex-row rounded-b-none">
        <div className="flex overflow-clip size-12 shrink-0 items-center justify-center rounded bg-sidebar-primary-foreground/10 transition-colors group-hover:bg-sidebar-primary text-sidebar-primary-foreground">
          <MonkeyIcon className="size-10 group-hover:scale-[1.7] origin-top-left transition-transform" />
        </div>
        <div className="grid flex-1 text-left text-sm leading-tight">
          <span className="text-2xl font-display">N.F.L. Analytics</span>
          <span className="text-xs uppercase">Dashboard</span>
        </div>
      </SidebarHeader>

      <SidebarContent>
        {/* NFL Mode Selector - Only show on NFL page */}
        {isNFLPage && (
          <Suspense fallback={null}>
            <NFLModeSelector />
          </Suspense>
        )}
      </SidebarContent>

      <SidebarRail />
    </Sidebar>
  );
}
