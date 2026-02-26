import Link from "next/link";
import { OnyxIcon } from "../icons/icons";

/**
 * Brand gradient from the VertualAI logo: pink → fuchsia → violet → indigo.
 * Used as accent colors for the branding panel.
 */
const BRAND_COLORS = {
  pink: "#E8449A",
  fuchsia: "#C026D3",
  violet: "#7C3AED",
  indigo: "#4338CA",
};

function BrandingPanel() {
  return (
    <div
      className="flex flex-col items-center justify-center h-full w-full relative overflow-hidden"
      style={{
        background: `linear-gradient(160deg, #120618 0%, #0d0a1f 40%, #0a0e2a 100%)`,
      }}
    >
      {/* Brand-colored decorative blurred circles */}
      <div className="absolute inset-0 pointer-events-none">
        <div
          className="absolute rounded-full"
          style={{
            width: 400,
            height: 400,
            top: "-10%",
            left: "-10%",
            background: BRAND_COLORS.pink,
            opacity: 0.08,
            filter: "blur(80px)",
          }}
        />
        <div
          className="absolute rounded-full"
          style={{
            width: 350,
            height: 350,
            top: "30%",
            right: "-5%",
            background: BRAND_COLORS.violet,
            opacity: 0.1,
            filter: "blur(70px)",
          }}
        />
        <div
          className="absolute rounded-full"
          style={{
            width: 300,
            height: 300,
            bottom: "-5%",
            left: "20%",
            background: BRAND_COLORS.indigo,
            opacity: 0.12,
            filter: "blur(60px)",
          }}
        />
        <div
          className="absolute rounded-full"
          style={{
            width: 200,
            height: 200,
            top: "60%",
            left: "-5%",
            background: BRAND_COLORS.fuchsia,
            opacity: 0.06,
            filter: "blur(50px)",
          }}
        />
        {/* Theme-aware accent glow — blends the current theme primary into the panel */}
        <div
          className="absolute rounded-full"
          style={{
            width: 250,
            height: 250,
            top: "15%",
            right: "15%",
            background: "var(--theme-primary-05)",
            opacity: 0.07,
            filter: "blur(60px)",
          }}
        />
      </div>

      {/* Main branding content */}
      <div className="relative z-10 flex flex-col items-center gap-8 px-12 text-center">
        {/* Logo — the original VertualAI dot cluster icon */}
        <div className="virtualai-pulse-ring rounded-full p-5 bg-white/5 backdrop-blur-sm border border-white/10">
          <OnyxIcon size={72} className="flex-shrink-0" />
        </div>

        {/* Brand name with the original logo gradient */}
        <h1
          className="text-4xl font-bold tracking-tight"
          style={{
            background: `linear-gradient(135deg, ${BRAND_COLORS.pink} 0%, ${BRAND_COLORS.fuchsia} 35%, ${BRAND_COLORS.violet} 65%, ${BRAND_COLORS.indigo} 100%)`,
            backgroundClip: "text",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          VertualAI
        </h1>

        {/* Tagline */}
        <p className="text-white/60 text-lg max-w-xs leading-relaxed">
          Your AI platform for work
        </p>

        {/* Decorative separator */}
        <div
          className="w-16 h-px rounded-full"
          style={{
            background: `linear-gradient(90deg, transparent 0%, ${BRAND_COLORS.violet}40 50%, transparent 100%)`,
          }}
        />

        {/* Feature highlights */}
        <div className="flex flex-col gap-4 text-sm mt-2">
          {[
            "Enterprise-grade AI assistance",
            "Connect all your knowledge sources",
            "Secure and private by design",
          ].map((text) => (
            <div key={text} className="flex items-center gap-3">
              <div
                className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                style={{
                  background: `linear-gradient(135deg, ${BRAND_COLORS.pink}, ${BRAND_COLORS.violet})`,
                }}
              />
              <span className="text-white/50">{text}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function FooterLinks({
  authState,
  footerContent,
}: {
  authState?: "signup" | "login" | "join";
  footerContent?: React.ReactNode;
}) {
  return (
    <>
      {authState === "login" && (
        <div className="text-sm mt-6 text-center w-full text-text-03 mainUiBody mx-auto">
          {footerContent ?? (
            <>
              New to VertualAI?{" "}
              <Link
                href="/auth/signup"
                className="text-text-05 mainUiAction underline transition-colors duration-200"
              >
                Create an Account
              </Link>
            </>
          )}
        </div>
      )}
      {authState === "signup" && (
        <div className="text-sm mt-6 text-center w-full text-text-03 mainUiBody mx-auto">
          Already have an account?{" "}
          <Link
            href="/auth/login?autoRedirectToSignup=false"
            className="text-text-05 mainUiAction underline transition-colors duration-200"
          >
            Sign In
          </Link>
        </div>
      )}
    </>
  );
}

export default function AuthFlowContainer({
  children,
  authState,
  footerContent,
  variant = "card",
}: {
  children: React.ReactNode;
  authState?: "signup" | "login" | "join";
  footerContent?: React.ReactNode;
  variant?: "card" | "split";
}) {
  if (variant === "split") {
    return (
      <div className="flex min-h-screen">
        {/* Left panel — branding (hidden on mobile) */}
        <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden">
          <BrandingPanel />
        </div>

        {/* Right panel — form */}
        <div className="w-full lg:w-1/2 flex flex-col items-center justify-center min-h-screen bg-background p-6 sm:p-8 lg:p-12 relative">
          {/* Subtle brand accent glow at top of right panel */}
          <div
            className="absolute top-0 left-0 right-0 h-1 pointer-events-none"
            style={{
              background: `linear-gradient(90deg, ${BRAND_COLORS.pink}, ${BRAND_COLORS.fuchsia}, ${BRAND_COLORS.violet}, ${BRAND_COLORS.indigo})`,
              opacity: 0.6,
            }}
          />

          {/* Mobile-only compact branding header */}
          <div className="lg:hidden mb-8 flex items-center gap-2">
            <OnyxIcon size={28} className="flex-shrink-0" />
            <span
              className="text-lg font-bold"
              style={{
                background: `linear-gradient(135deg, ${BRAND_COLORS.pink} 0%, ${BRAND_COLORS.fuchsia} 35%, ${BRAND_COLORS.violet} 65%, ${BRAND_COLORS.indigo} 100%)`,
                backgroundClip: "text",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              VertualAI
            </span>
          </div>

          {/* Form card */}
          <div className="w-full max-w-md animate-fadeIn bg-background-tint-00 rounded-16 p-8 shadow-02 border border-border-01">
            {children}
          </div>

          <FooterLinks authState={authState} footerContent={footerContent} />
        </div>
      </div>
    );
  }

  // Default "card" variant — original layout
  return (
    <div className="p-4 flex flex-col items-center justify-center min-h-screen bg-background">
      <div className="w-full max-w-md flex items-start flex-col bg-background-tint-00 rounded-16 shadow-lg shadow-02 p-6">
        <OnyxIcon size={44} className="text-theme-primary-05" />
        <div className="w-full mt-3">{children}</div>
      </div>
      <FooterLinks authState={authState} footerContent={footerContent} />
    </div>
  );
}
