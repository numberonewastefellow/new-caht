import { AdminPageTitle } from "@/components/admin/Title";
import BackButton from "@/refresh-components/buttons/BackButton";
import { ClipboardIcon } from "@/components/icons/icons";
import { ErrorCallout } from "@/components/ErrorCallout";
import { fetchSS } from "@/lib/utilsSS";
import { StandardAnswerCategory } from "@/lib/types";
import StandardAnswerForm from "../StandardAnswerForm";

export default async function Page() {
  const response = await fetchSS("/nexus/admin/standard-answer/category");
  if (!response || !response.ok) {
    return (
      <ErrorCallout
        errorTitle="Something went wrong"
        errorMsg={`Failed to load categories${
          response ? ` - ${await response.text()}` : ""
        }`}
      />
    );
  }
  const categories = (await response.json()) as StandardAnswerCategory[];

  return (
    <>
      <BackButton />
      <AdminPageTitle
        title="New Standard Answer"
        icon={<ClipboardIcon size={32} />}
      />
      <StandardAnswerForm categories={categories} />
    </>
  );
}
