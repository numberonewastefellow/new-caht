"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { Route } from "next";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { MagnifyingGlass } from "@phosphor-icons/react";
import { SvgTrash } from "@opal/icons";
import { Button } from "@opal/components";

import { AdminPageTitle } from "@/components/admin/Title";
import { ClipboardIcon, EditIcon } from "@/components/icons/icons";
import {
  Table,
  TableHeader,
  TableHead,
  TableRow,
  TableBody,
  TableCell,
} from "@/components/ui/table";
import Text from "@/components/ui/text";
import CardSection from "@/components/admin/CardSection";
import Separator from "@/refresh-components/Separator";
import CreateButton from "@/refresh-components/buttons/CreateButton";
import { ThreeDotsLoader } from "@/components/Loading";
import { ErrorCallout } from "@/components/ErrorCallout";
import { toast } from "@/hooks/useToast";
import { PageSelector } from "@/components/PageSelector";
import { useUser } from "@/providers/UserProvider";
import { StandardAnswer, StandardAnswerCategory } from "@/lib/types";

import ConfigPanel from "./ConfigPanel";
import { useStandardAnswers, useStandardAnswerCategories } from "./hooks";
import { deleteStandardAnswer, deleteStandardAnswerCategory } from "./lib";

const PAGE_SIZE = 10;
// Seeded catch-all category (backend refuses to delete it); hide its delete affordance.
const DEFAULT_CATEGORY_ID = 0;

function CategoryManager({
  categories,
  refresh,
}: {
  categories: StandardAnswerCategory[];
  refresh: () => void;
}) {
  if (categories.length === 0) return null;

  async function handleDelete(id: number, name: string) {
    if (!window.confirm(`Delete category "${name}"?`)) return;
    const response = await deleteStandardAnswerCategory(id);
    if (response.ok) {
      toast.success(`Category "${name}" deleted`);
      refresh();
    } else {
      const body = await response.json().catch(() => ({}));
      toast.error(body.detail || "Failed to delete category");
    }
  }

  return (
    <CardSection className="mb-6">
      <Text className="mb-1 font-semibold">Categories</Text>
      <Text className="mb-3 text-subtle">
        New categories are created from the answer form. A category in use by an
        answer or Slack channel can&apos;t be deleted.
      </Text>
      <div className="flex flex-wrap gap-2">
        {categories.map((c) => (
          <span
            key={c.id}
            className="inline-flex items-center gap-1 rounded-full bg-accent-background-hovered px-3 py-1 text-xs font-semibold text-emphasis"
          >
            {c.name}
            {c.id !== DEFAULT_CATEGORY_ID && (
              <button
                className="ml-1 text-subtle hover:text-emphasis"
                aria-label={`Delete category ${c.name}`}
                onClick={() => handleDelete(c.id, c.name)}
              >
                &times;
              </button>
            )}
          </span>
        ))}
      </div>
    </CardSection>
  );
}

function ModeBadge({ answer }: { answer: StandardAnswer }) {
  const label = answer.match_regex
    ? "Regex"
    : answer.match_any_keywords
      ? "Match any"
      : "Match all";
  return (
    <span
      className="inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium"
      style={{
        backgroundColor: "var(--virtualai-accent-subtle, var(--accent-background-hovered))",
        color: "var(--virtualai-accent, var(--theme-primary-05))",
      }}
    >
      {label}
    </span>
  );
}

function CategoryPill({ name }: { name: string }) {
  return (
    <span className="mb-1 mr-1 inline-block w-fit rounded-full bg-accent-background-hovered px-2 py-1 text-xs font-semibold text-emphasis">
      {name}
    </span>
  );
}

function AnswersTable({
  answers,
  categories,
  refresh,
}: {
  answers: StandardAnswer[];
  categories: StandardAnswerCategory[];
  refresh: () => void;
}) {
  const [query, setQuery] = useState("");
  const [activeCategoryId, setActiveCategoryId] = useState<number | null>(null);
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return answers.filter((a) => {
      const textMatch =
        !q ||
        a.keyword.toLowerCase().includes(q) ||
        a.answer.toLowerCase().includes(q);
      const categoryMatch =
        activeCategoryId === null ||
        a.categories.some((c) => c.id === activeCategoryId);
      return textMatch && categoryMatch;
    });
  }, [answers, query, activeCategoryId]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const start = (page - 1) * PAGE_SIZE;
  const pageItems = filtered.slice(start, start + PAGE_SIZE);

  async function handleDelete(id: number) {
    if (!window.confirm("Delete this standard answer?")) return;
    const response = await deleteStandardAnswer(id);
    if (response.ok) {
      toast.success(`Standard answer ${id} deleted`);
    } else {
      toast.error(`Failed to delete standard answer - ${await response.text()}`);
    }
    refresh();
  }

  return (
    <div className="py-2">
      <div className="flex items-center rounded-lg border-2 border-border px-4 py-2 focus-within:border-accent">
        <MagnifyingGlass />
        <input
          className="ml-2 h-6 flex-grow bg-transparent placeholder-subtle outline-none"
          placeholder="Search by keyword or answer text..."
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPage(1);
          }}
        />
      </div>

      {categories.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          <button
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              activeCategoryId === null
                ? "bg-accent-background-hovered text-emphasis"
                : "text-subtle"
            }`}
            onClick={() => {
              setActiveCategoryId(null);
              setPage(1);
            }}
          >
            All categories
          </button>
          {categories.map((c) => (
            <button
              key={c.id}
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                activeCategoryId === c.id
                  ? "bg-accent-background-hovered text-emphasis"
                  : "text-subtle"
              }`}
              onClick={() => {
                setActiveCategoryId(c.id);
                setPage(1);
              }}
            >
              {c.name}
            </button>
          ))}
        </div>
      )}

      <div className="mt-4">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8" />
              <TableHead>Trigger</TableHead>
              <TableHead>Mode</TableHead>
              <TableHead>Categories</TableHead>
              <TableHead>Answer</TableHead>
              <TableHead className="w-8" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {pageItems.map((a) => (
              <TableRow key={a.id}>
                <TableCell>
                  <Link
                    href={`/admin/standard-answers/${a.id}` as Route}
                    aria-label="Edit standard answer"
                  >
                    <EditIcon />
                  </Link>
                </TableCell>
                <TableCell className="max-w-[16rem] break-words">
                  <ReactMarkdown>
                    {a.match_regex ? `\`${a.keyword}\`` : a.keyword}
                  </ReactMarkdown>
                </TableCell>
                <TableCell>
                  <ModeBadge answer={a} />
                </TableCell>
                <TableCell>
                  {a.categories.map((c) => (
                    <CategoryPill key={c.id} name={c.name} />
                  ))}
                </TableCell>
                <TableCell className="max-w-[28rem] overflow-auto">
                  <div className="prose dark:prose-invert">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {a.answer}
                    </ReactMarkdown>
                  </div>
                </TableCell>
                <TableCell>
                  <Button
                    icon={SvgTrash}
                    prominence="tertiary"
                    onClick={() => handleDelete(a.id)}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        {pageItems.length === 0 && (
          <div className="flex justify-center py-6">
            <Text>No standard answers match your filters.</Text>
          </div>
        )}

        {filtered.length > PAGE_SIZE && (
          <div className="mt-4 flex justify-center">
            <PageSelector
              currentPage={page}
              totalPages={totalPages}
              onPageChange={setPage}
              shouldScroll
            />
          </div>
        )}
      </div>
    </div>
  );
}

function Main() {
  const {
    data: answers,
    error: answersError,
    isLoading: answersLoading,
    refreshStandardAnswers,
  } = useStandardAnswers();
  const {
    data: categories,
    error: categoriesError,
    isLoading: categoriesLoading,
    refreshStandardAnswerCategories,
  } = useStandardAnswerCategories();

  if (answersLoading || categoriesLoading) return <ThreeDotsLoader />;

  if (answersError || !answers) {
    return (
      <ErrorCallout
        errorTitle="Error loading standard answers"
        errorMsg={answersError?.message}
      />
    );
  }
  if (categoriesError || !categories) {
    return (
      <ErrorCallout
        errorTitle="Error loading categories"
        errorMsg={categoriesError?.message}
      />
    );
  }

  return (
    <div className="mb-8">
      <Text className="mb-4 text-subtle">
        Post pre-written answers to Slack when a message matches a keyword or
        pattern. Answers are scoped by category; assign categories to a channel
        on its{" "}
        <a className="text-link" href="/admin/bots">
          Slack bot
        </a>{" "}
        configuration.
      </Text>

      <ConfigPanel />

      <CategoryManager
        categories={categories}
        refresh={refreshStandardAnswerCategories}
      />

      <div className="mb-2 flex items-center justify-between">
        <Text className="font-semibold">Answers</Text>
        <CreateButton href="/admin/standard-answers/new">
          New standard answer
        </CreateButton>
      </div>
      <Separator />

      <AnswersTable
        answers={answers}
        categories={categories}
        refresh={refreshStandardAnswers}
      />
    </div>
  );
}

export default function Page() {
  const { isAdmin, isCurator } = useUser();

  return (
    <>
      <AdminPageTitle
        icon={<ClipboardIcon size={32} />}
        title="Standard Answers"
        description="Keyword & regex canned answers for the Slack bot."
      />
      {isAdmin || isCurator ? (
        <Main />
      ) : (
        <ErrorCallout
          errorTitle="Access restricted"
          errorMsg="You need administrator or curator access to manage standard answers."
        />
      )}
    </>
  );
}
