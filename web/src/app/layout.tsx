import "./globals.css";

import {
  fetchEnterpriseSettingsSS,
  fetchSettingsSS,
} from "@/components/settings/lib";
import {
  CUSTOM_ANALYTICS_ENABLED,
  GTM_ENABLED,
  NEXT_PUBLIC_CLOUD_ENABLED,
  MODAL_ROOT_ID,
} from "@/lib/constants";
import { Metadata } from "next";
import { buildClientUrl } from "@/lib/utilsSS";
import localFont from "next/font/local";
import { EnterpriseSettings } from "./admin/settings/interfaces";
import AppProvider from "@/providers/AppProvider";
import { PHProvider } from "./providers";
import { getAuthTypeMetadataSS, getCurrentUserSS } from "@/lib/userSS";
import { Suspense } from "react";
import PostHogPageView from "./PostHogPageView";
import Script from "next/script";
import { WebVitals } from "./web-vitals";
import { ThemeProvider } from "next-themes";
import { VirtualAIThemeProvider } from "@/providers/VirtualAIThemeProvider";
import { UiConfigProvider } from "@/providers/UiConfigProvider";
import CloudError from "@/components/errorPages/CloudErrorPage";
import Error from "@/components/errorPages/ErrorPage";
import { TooltipProvider } from "@/components/ui/tooltip";
import { fetchAppSidebarMetadata } from "@/lib/appSidebarSS";
import StatsOverlayLoader from "@/components/dev/StatsOverlayLoader";

const inter = localFont({
  src: [
    { path: "../../public/fonts/inter-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "../../public/fonts/inter-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "../../public/fonts/inter-latin-600-normal.woff2", weight: "600", style: "normal" },
    { path: "../../public/fonts/inter-latin-700-normal.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-inter",
  display: "swap",
});

const geist = localFont({
  src: [
    { path: "../../public/fonts/geist-sans-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "../../public/fonts/geist-sans-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "../../public/fonts/geist-sans-latin-600-normal.woff2", weight: "600", style: "normal" },
    { path: "../../public/fonts/geist-sans-latin-700-normal.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-geist",
  display: "swap",
});

const plusJakarta = localFont({
  src: [
    { path: "../../public/fonts/plus-jakarta-sans-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "../../public/fonts/plus-jakarta-sans-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "../../public/fonts/plus-jakarta-sans-latin-600-normal.woff2", weight: "600", style: "normal" },
    { path: "../../public/fonts/plus-jakarta-sans-latin-700-normal.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-plus-jakarta",
  display: "swap",
});

const hanken = localFont({
  src: [
    { path: "../../public/fonts/hanken-grotesk-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "../../public/fonts/hanken-grotesk-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "../../public/fonts/hanken-grotesk-latin-600-normal.woff2", weight: "600", style: "normal" },
    { path: "../../public/fonts/hanken-grotesk-latin-700-normal.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-hanken",
  display: "swap",
});

const spaceGrotesk = localFont({
  src: [
    { path: "../../public/fonts/space-grotesk-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "../../public/fonts/space-grotesk-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "../../public/fonts/space-grotesk-latin-600-normal.woff2", weight: "600", style: "normal" },
    { path: "../../public/fonts/space-grotesk-latin-700-normal.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-space-grotesk",
  display: "swap",
});

export async function generateMetadata(): Promise<Metadata> {
  let logoLocation = buildClientUrl("/vertuelai-favicon.svg");
  let enterpriseSettings: EnterpriseSettings | null = null;
  try {
    const res = await fetchEnterpriseSettingsSS();
    if (res.ok) {
      enterpriseSettings = await res.json();
      logoLocation =
        enterpriseSettings && enterpriseSettings.use_custom_logo
          ? "/api/enterprise-settings/logo"
          : buildClientUrl("/vertuelai-favicon.svg");
    }
  } catch (e) {
    // Fall through with defaults
  }

  return {
    title: enterpriseSettings?.application_name || "VertualAI",
    description: "Question answering for your documents",
    icons: {
      icon: logoLocation,
    },
  };
}

export const dynamic = "force-dynamic";

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [combinedSettings, user, authTypeMetadata] = await Promise.all([
    fetchSettingsSS(),
    getCurrentUserSS(),
    getAuthTypeMetadataSS(),
  ]);

  const { folded } = await fetchAppSidebarMetadata(user);

  // Web-only, runtime-switchable UI version default. Plain (non-NEXT_PUBLIC_)
  // env read server-side here so changing it only needs a container restart,
  // not a rebuild. Injected to client hooks via UiConfigProvider.
  const defaultUiVersion =
    process.env.DEFAULT_UI_VERSION?.toLowerCase() === "legacy"
      ? "legacy"
      : "new";

  const getPageContent = async (content: React.ReactNode) => (
    <html
      lang="en"
      className={`${inter.variable} ${geist.variable} ${plusJakarta.variable} ${hanken.variable} ${spaceGrotesk.variable}`}
      suppressHydrationWarning
    >
      <head>
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0, interactive-widget=resizes-content"
        />
        {/* Apply the stored font preference before first paint to avoid a flash
            (mirrors how next-themes applies the color scheme). The provider and
            the account preference reconcile this on hydration. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var f=localStorage.getItem('virtualai-font-preference');if(f&&f!=='inter'){document.documentElement.classList.add('font-pref-'+f);}}catch(e){}})();`,
          }}
        />
        {CUSTOM_ANALYTICS_ENABLED &&
          combinedSettings?.customAnalyticsScript && (
            <script
              type="text/javascript"
              dangerouslySetInnerHTML={{
                __html: combinedSettings.customAnalyticsScript,
              }}
            />
          )}

        {GTM_ENABLED && (
          <Script
            id="google-tag-manager"
            strategy="afterInteractive"
            dangerouslySetInnerHTML={{
              __html: `
               (function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
               new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
               j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
               'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
               })(window,document,'script','dataLayer','GTM-PZXS36NG');
             `,
            }}
          />
        )}
      </head>

      <body className={`relative ${inter.variable}`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <VirtualAIThemeProvider>
            <div className="text-text min-h-screen bg-background">
              <TooltipProvider>
                <PHProvider>{content}</PHProvider>
              </TooltipProvider>
            </div>
          </VirtualAIThemeProvider>
        </ThemeProvider>
      </body>
    </html>
  );

  if (!combinedSettings) {
    return getPageContent(
      NEXT_PUBLIC_CLOUD_ENABLED ? <CloudError /> : <Error />
    );
  }

  // WS-A: the license/billing paywall (GatedContentWrapper + AccessRestrictedPage)
  // was removed — the app is never gated, so children always render.
  const content = children;

  return getPageContent(
    <AppProvider
      authTypeMetadata={authTypeMetadata}
      user={user}
      settings={combinedSettings}
      folded={folded}
    >
      <Suspense fallback={null}>
        <PostHogPageView />
      </Suspense>
      <div id={MODAL_ROOT_ID} className="h-screen w-screen">
        <UiConfigProvider defaultUiVersion={defaultUiVersion}>
          {content}
        </UiConfigProvider>
      </div>
      {process.env.NEXT_PUBLIC_POSTHOG_KEY && <WebVitals />}
      {process.env.NEXT_PUBLIC_ENABLE_STATS === "true" && (
        <StatsOverlayLoader />
      )}
    </AppProvider>
  );
}
