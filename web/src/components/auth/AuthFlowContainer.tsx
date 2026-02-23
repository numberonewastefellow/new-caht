import Link from "next/link";
import { OnyxIcon } from "../icons/icons";

function BrandingPanel() {
  return (
    <div
      className="flex flex-col items-center justify-center h-full w-full relative"
      style={{
        background: `linear-gradient(135deg, var(--theme-gradient-00) 0%, var(--theme-gradient-05) 50%, var(--theme-primary-05) 100%)`,
      }}
    >
      {/* Decorative blurred circles for depth */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div
          className="absolute rounded-full opacity-10"
          style={{
            width: 300,
            height: 300,
            top: "10%",
            left: "-5%",
            background: "var(--theme-primary-04)",
            filter: "blur(60px)",
          }}
        />
        <div
          className="absolute rounded-full opacity-10"
          style={{
            width: 200,
            height: 200,
            bottom: "15%",
            right: "-3%",
            background: "var(--theme-gradient-05)",
            filter: "blur(40px)",
          }}
        />
        <div
          className="absolute rounded-full opacity-5"
          style={{
            width: 150,
            height: 150,
            top: "50%",
            left: "30%",
            background: "var(--theme-gradient-00)",
            filter: "blur(50px)",
          }}
        />
      </div>

      {/* Main branding content */}
      <div className="relative z-10 flex flex-col items-center gap-6 px-12 text-center">
        {/* Logo with pulse ring effect */}
        <div className="virtualai-pulse-ring rounded-full p-4 bg-[rgba(255,255,255,0.08)] backdrop-blur-sm">
          <OnyxIcon size={64} className="text-[var(--text-inverted-05)]" />
        </div>

        {/* Brand name */}
        <h1
          className="text-4xl font-semibold tracking-tight"
          style={{
            background:
              "linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.7) 100%)",
            backgroundClip: "text",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          VertualAI
        </h1>

        {/* Tagline */}
        <p className="text-[var(--text-inverted-03)] text-lg max-w-xs leading-relaxed">
          Your AI platform for work
        </p>

        {/* Decorative separator */}
        <div
          className="w-12 h-0.5 rounded-full opacity-30"
          style={{ background: "var(--theme-gradient-00)" }}
        />

        {/* Feature highlights */}
        <div className="flex flex-col gap-3 text-[var(--text-inverted-03)] text-sm mt-4">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--text-inverted-03)] opacity-50" />
            <span>Enterprise-grade AI assistance</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--text-inverted-03)] opacity-50" />
            <span>Connect all your knowledge sources</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--text-inverted-03)] opacity-50" />
            <span>Secure and private by design</span>
          </div>
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
        <div className="w-full lg:w-1/2 flex flex-col items-center justify-center min-h-screen bg-background-tint-00 p-6 sm:p-8 lg:p-12">
          {/* Mobile-only compact branding header */}
          <div className="lg:hidden mb-8 flex flex-col items-center gap-2">
            <OnyxIcon size={36} className="text-theme-primary-05" />
            <span className="virtualai-gradient-text text-xl font-semibold">
              VertualAI
            </span>
          </div>

          {/* Form content */}
          <div className="w-full max-w-md animate-fadeIn">
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
