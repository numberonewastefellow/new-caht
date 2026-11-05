import type { CombinedSettings } from "@/app/admin/settings/interfaces";

export interface AdminEntry {
  href: string;
  label: string;
}

export interface AdminEntryArgs {
  isAdmin: boolean;
  isCurator: boolean;
  settings: CombinedSettings | null;
}

/**
 * Where the admin door leads and what it is called — shared so nav v1
 * (`UserAvatarPopover`) and v2 (`AdminEntryTab`) can never drift apart.
 *
 * Returns `null` when the user has no admin area to enter. This only hides the
 * link; `requireAdminAuth` is the actual gate.
 */
export function adminEntry({
  isAdmin,
  isCurator,
  settings,
}: AdminEntryArgs): AdminEntry | null {
  if (!isAdmin && !isCurator) return null;

  // Without a vector DB the data-sources landing page has nothing to show, so
  // send admins and curators to agents instead.
  const vectorDbEnabled = settings?.settings?.vector_db_enabled !== false;

  return {
    href: vectorDbEnabled ? "/admin/workflows" : "/admin/assistants",
    label: isAdmin ? "Admin Panel" : "Curator Panel",
  };
}
