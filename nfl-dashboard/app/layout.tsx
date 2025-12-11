import { Roboto_Mono } from "next/font/google";
import "./globals.css";
import { Metadata } from "next";
import Image from "next/image";
import { V0Provider } from "@/lib/v0-context";
import localFont from "next/font/local";
import { SidebarProvider } from "@/components/ui/sidebar";
import { MobileHeader } from "@/components/dashboard/mobile-header";
import { DashboardSidebar } from "@/components/dashboard/sidebar";
import mockDataJson from "@/mock.json";
import type { MockData } from "@/types/dashboard";
import Widget from "@/components/dashboard/widget";

const mockData = mockDataJson as MockData;

const robotoMono = Roboto_Mono({
  variable: "--font-roboto-mono",
  subsets: ["latin"],
});

const rebelGrotesk = localFont({
  src: "../public/fonts/Rebels-Fett.woff2",
  variable: "--font-rebels",
  display: "swap",
});

const isV0 = process.env["VERCEL_URL"]?.includes("vusercontent.net") ?? false;

export const metadata: Metadata = {
  title: {
    template: "%s – N.F.L. Analytics",
    default: "N.F.L. Analytics",
  },
  description: "The ultimate NFL analytics platform.",
  generator: "nfl-analytics.com",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          rel="preload"
          href="/fonts/Rebels-Fett.woff2"
          as="font"
          type="font/woff2"
          crossOrigin="anonymous"
        />
      </head>
      <body
        className={`${rebelGrotesk.variable} ${robotoMono.variable} antialiased`}
      >
        <V0Provider isV0={isV0}>
          <SidebarProvider>
            {/* Mobile Header - only visible on mobile */}
            {/* <MobileHeader mockData={mockData} /> */}

            {/* Desktop Layout */}
            <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-gap lg:px-sides">
              <div className="hidden lg:block col-span-2 top-0 relative">
                <DashboardSidebar />
              </div>
              <div className="col-span-1 lg:col-span-7">{children}</div>
              <div className="col-span-3 hidden lg:block">
                <div className="space-y-gap py-sides min-h-screen max-h-screen sticky top-0 overflow-clip">
                  <Widget widgetData={mockData.widgetData} />
                  <div className="relative w-full aspect-auto">
                    <Image
                      src="/nflpic.jpeg"
                      alt="NFL Analytics"
                      width={800}
                      height={600}
                      className="w-full h-auto rounded-lg object-cover"
                      priority={false}
                    />
                  </div>
                </div>
              </div>
            </div>
          </SidebarProvider>
        </V0Provider>
      </body>
    </html>
  );
}
