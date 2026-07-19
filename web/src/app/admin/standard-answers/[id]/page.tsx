import { AdminPageTitle } from "@/components/admin/Title";
import BackButton from "@/refresh-components/buttons/BackButton";
import { ClipboardIcon } from "@/components/icons/icons";
import { ErrorCallout } from "@/components/ErrorCallout";
import { fetchSS } from "@/lib/utilsSS";
import { StandardAnswer, StandardAnswerCategory } from "@/lib/types";
import StandardAnswerForm from "../StandardAnswerForm";

export default async function Page(props: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await props.params;
  const [answersResponse, categoriesResponse] = await Promise.all([
    fetchSS("/nexus/admin/standard-answer"),
    fetchSS("/nexus/admin/standard-answer/category"),
  ]);

  if (!answersResponse || !answersResponse.ok) {
    return (
      <ErrorCallout
        errorTitle="Something went wrong"
        errorMsg={`Failed to load standard answers${
          answersResponse ? ` - ${await answersResponse.text()}` : ""
        }`}
      />
    );
  }
  if (!categoriesResponse || !categoriesResponse.ok) {
    return (
      <ErrorCallout
        errorTitle="Something went wrong"
        errorMsg={`Failed to load categories${
          categoriesResponse ? ` - ${await categoriesResponse.text()}` : ""
        }`}
      />
    );
  }

  const answers = (await answersResponse.json()) as StandardAnswer[];
  const existing = answers.find((a) => a.id.toString() === id);
  if (!existing) {
    return (
      <ErrorCallout
        errorTitle="Not found"
        errorMsg={`No standard answer with id ${id}.`}
      />
    );
  }
  const categories =
    (await categoriesResponse.json()) as StandardAnswerCategory[];

  return (
    <>
      <BackButton />
      <AdminPageTitle
        title="Edit Standard Answer"
        icon={<ClipboardIcon size={32} />}
      />
      <StandardAnswerForm categories={categories} existing={existing} />
    </>
  );
}
