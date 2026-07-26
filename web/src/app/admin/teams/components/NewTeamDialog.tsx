"use client";

import { useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import { User } from "@/lib/types";
import { toast } from "@/hooks/useToast";
import Modal from "@/refresh-components/Modal";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import Checkbox from "@/refresh-components/inputs/Checkbox";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import InputTextArea from "@/refresh-components/inputs/InputTextArea";
import {
  SvgCheck,
  SvgChevronLeft,
  SvgGlobe,
  SvgLock,
  SvgUsers,
  SvgX,
} from "@opal/icons";
import { createTeam } from "../lib";
import { UserAvatar } from "./shared";

interface NewTeamDialogProps {
  open: boolean;
  onClose: () => void;
  allUsers: User[];
  onCreated: (newTeamId?: number) => void;
}

export default function NewTeamDialog({
  open,
  onClose,
  allUsers,
  onCreated,
}: NewTeamDialogProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const filteredUsers = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return allUsers;
    return allUsers.filter((u) => u.email.toLowerCase().includes(q));
  }, [allUsers, query]);

  function reset() {
    setStep(1);
    setName("");
    setDescription("");
    setIsPublic(false);
    setTagInput("");
    setTags([]);
    setSelected([]);
    setQuery("");
    setSubmitting(false);
  }

  function close() {
    onClose();
    reset();
  }

  function addTag() {
    const t = tagInput.trim();
    if (t && !tags.includes(t)) setTags((prev) => [...prev, t]);
    setTagInput("");
  }

  async function submit() {
    setSubmitting(true);
    try {
      const res = await createTeam({
        name: name.trim(),
        description: description.trim() || undefined,
        is_public: isPublic,
        tags,
        user_ids: selected,
        cc_pair_ids: [],
      });
      if (res.ok) {
        toast.success("Team created");
        let newId: number | undefined;
        try {
          const body = await res.json();
          newId = body?.id;
        } catch {
          // ignore parse errors — the list refresh still runs
        }
        onCreated(newId);
        close();
      } else {
        const body = await res.json().catch(() => ({}));
        toast.error(
          `Failed to create team - ${body.detail || body.message || res.status}`
        );
        setSubmitting(false);
      }
    } catch (e: any) {
      toast.error(`Failed to create team - ${e?.message ?? "unknown error"}`);
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onOpenChange={(o) => !o && close()}>
      <Modal.Content width="md" height="lg">
        <Modal.Header
          icon={SvgUsers}
          title="Create a new team"
          description={
            step === 1
              ? "Give your team a name and set its visibility."
              : "Add existing members now, or skip and add them later."
          }
          onClose={close}
        >
          <div className="mt-3 flex items-center gap-3 w-full">
            <StepDot n={1} active={step === 1} done={step > 1} label="Details" />
            <div className="h-px flex-1 bg-border-02" />
            <StepDot n={2} active={step === 2} done={false} label="Members" />
          </div>
        </Modal.Header>

        <Modal.Body>
          {step === 1 ? (
            <div className="flex flex-col gap-4 w-full">
              <Field label="Team name">
                <InputTypeIn
                  autoFocus
                  showClearButton={false}
                  placeholder="e.g. AI Platform"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </Field>

              <Field label="Description">
                <InputTextArea
                  placeholder="What does this team work on?"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                />
              </Field>

              <Field label="Visibility">
                <div className="grid grid-cols-2 gap-3">
                  <VisibilityCard
                    active={!isPublic}
                    icon={SvgLock}
                    title="Private"
                    description="Only added members can access this team."
                    onClick={() => setIsPublic(false)}
                  />
                  <VisibilityCard
                    active={isPublic}
                    icon={SvgGlobe}
                    title="Public"
                    description="Anyone in your org can discover this team."
                    onClick={() => setIsPublic(true)}
                  />
                </div>
              </Field>

              <Field label="Tags">
                <div className="flex flex-wrap items-center gap-1.5 rounded-08 border p-2 bg-background-neutral-00">
                  {tags.map((t) => (
                    <span
                      key={t}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-secondary-body text-xs"
                      style={{
                        backgroundColor: "var(--background-tint-02)",
                        color: "var(--text-03)",
                      }}
                    >
                      {t}
                      <button
                        type="button"
                        onClick={() =>
                          setTags((prev) => prev.filter((x) => x !== t))
                        }
                        className="hover:text-text-05"
                      >
                        <SvgX className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                  <input
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        addTag();
                      }
                    }}
                    placeholder={tags.length === 0 ? "Add tag and press Enter" : ""}
                    className="flex-1 min-w-[120px] bg-transparent px-1 py-0.5 text-sm outline-none placeholder:text-text-02"
                  />
                </div>
              </Field>
            </div>
          ) : (
            <div className="flex flex-col gap-3 w-full">
              {selected.length > 0 && (
                <div className="flex flex-wrap gap-1.5 rounded-12 border bg-background-tint-02 p-2">
                  {selected.map((id) => {
                    const u = allUsers.find((x) => x.id === id);
                    if (!u) return null;
                    return (
                      <span
                        key={id}
                        className="inline-flex items-center gap-1.5 pl-1 pr-1.5 py-1 rounded-full bg-background-neutral-00 border"
                      >
                        <UserAvatar id={u.id} email={u.email} size={18} />
                        <Text secondaryBody text04 className="text-xs">
                          {u.email}
                        </Text>
                        <button
                          type="button"
                          onClick={() =>
                            setSelected((prev) => prev.filter((x) => x !== id))
                          }
                          className="hover:text-text-05"
                        >
                          <SvgX className="w-3 h-3" />
                        </button>
                      </span>
                    );
                  })}
                </div>
              )}

              <InputTypeIn
                leftSearchIcon
                placeholder="Search by email"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />

              <div className="max-h-[300px] overflow-y-auto rounded-12 border divide-y divide-border-01">
                {filteredUsers.map((u) => {
                  const isSel = selected.includes(u.id);
                  return (
                    <label
                      key={u.id}
                      className={cn(
                        "flex cursor-pointer items-center gap-3 px-3 py-2.5 transition-colors hover:bg-background-tint-02",
                        isSel && "bg-background-tint-02"
                      )}
                    >
                      <Checkbox
                        checked={isSel}
                        onCheckedChange={() =>
                          setSelected((prev) =>
                            prev.includes(u.id)
                              ? prev.filter((x) => x !== u.id)
                              : [...prev, u.id]
                          )
                        }
                      />
                      <UserAvatar id={u.id} email={u.email} size={30} />
                      <Text mainUiBody text04 className="truncate flex-1 text-sm">
                        {u.email}
                      </Text>
                      {isSel && (
                        <SvgCheck
                          className="w-4 h-4"
                          style={{
                            color:
                              "var(--virtualai-accent, var(--theme-primary-05))",
                          }}
                        />
                      )}
                    </label>
                  );
                })}
                {filteredUsers.length === 0 && (
                  <div className="px-3 py-8 text-center">
                    <Text secondaryBody text03 className="text-sm">
                      No users found.
                    </Text>
                  </div>
                )}
              </div>

              <Text secondaryBody text03 className="text-xs">
                {selected.length} member{selected.length === 1 ? "" : "s"} selected
                · You will be the owner.
              </Text>
            </div>
          )}
        </Modal.Body>

        <Modal.Footer>
          {step === 1 ? (
            <>
              <Button main tertiary onClick={close}>
                Cancel
              </Button>
              <Button
                action
                disabled={!name.trim()}
                onClick={() => setStep(2)}
              >
                Continue
              </Button>
            </>
          ) : (
            <>
              <Button
                main
                tertiary
                leftIcon={SvgChevronLeft}
                onClick={() => setStep(1)}
              >
                Back
              </Button>
              <Button
                main
                secondary
                disabled={submitting}
                onClick={submit}
              >
                Skip & create
              </Button>
              <Button action disabled={submitting} onClick={submit}>
                {submitting ? "Creating…" : "Create team"}
              </Button>
            </>
          )}
        </Modal.Footer>
      </Modal.Content>
    </Modal>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5 w-full">
      <Text mainUiBody text04 className="text-sm">
        {label}
      </Text>
      {children}
    </div>
  );
}

function VisibilityCard({
  active,
  icon: Icon,
  title,
  description,
  onClick,
}: {
  active: boolean;
  icon: React.FunctionComponent<{ className?: string }>;
  title: string;
  description: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-start gap-3 rounded-12 border p-3 text-left transition-colors",
        active
          ? "bg-background-tint-02"
          : "border-border-01 hover:bg-background-tint-02"
      )}
      style={
        active
          ? {
              borderColor:
                "var(--virtualai-accent, var(--theme-primary-05))",
            }
          : undefined
      }
    >
      <div
        className="mt-0.5 rounded-08 p-1.5"
        style={{
          backgroundColor: "var(--background-tint-02)",
          color: "var(--virtualai-accent, var(--theme-primary-05))",
        }}
      >
        <Icon className="w-4 h-4" />
      </div>
      <div>
        <Text mainUiBody text04 className="text-sm">
          {title}
        </Text>
        <Text as="p" secondaryBody text03 className="text-xs">
          {description}
        </Text>
      </div>
    </button>
  );
}

function StepDot({
  n,
  active,
  done,
  label,
}: {
  n: number;
  active: boolean;
  done: boolean;
  label: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <div
        className="flex h-6 w-6 items-center justify-center rounded-full text-[0.7rem] font-main-ui-body"
        style={
          done || active
            ? {
                backgroundColor:
                  "var(--virtualai-accent, var(--theme-primary-05))",
                color: "var(--text-inverted-05)",
              }
            : {
                backgroundColor: "var(--background-tint-02)",
                color: "var(--text-03)",
              }
        }
      >
        {done ? <SvgCheck className="w-3.5 h-3.5" /> : n}
      </div>
      <Text
        secondaryBody
        text03={!active}
        text04={active}
        className="text-sm"
      >
        {label}
      </Text>
    </div>
  );
}
