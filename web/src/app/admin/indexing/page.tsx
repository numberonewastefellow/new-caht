import { redirect } from "next/navigation";

export default function IndexingPage() {
  redirect("/admin/indexing/status");
}
