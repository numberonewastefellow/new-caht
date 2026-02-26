"use client";

import Text from "@/refresh-components/texts/Text";
import { Persona } from "./interfaces";
import { useRouter } from "next/navigation";
import { toast } from "@/hooks/useToast";
import { useState, useMemo, useEffect } from "react";
import {
  deletePersona,
  personaComparator,
  togglePersonaDefault,
  togglePersonaVisibility,
} from "./lib";
import ConfirmationModalLayout from "@/refresh-components/layouts/ConfirmationModalLayout";
import Button from "@/refresh-components/buttons/Button";
import IconButton from "@/refresh-components/buttons/IconButton";
import {
  SvgAlertCircle,
  SvgEdit,
  SvgEye,
  SvgEyeClosed,
  SvgGlobe,
  SvgMoreHorizontal,
  SvgStar,
  SvgTrash,
  SvgUser,
  SvgUsers,
} from "@opal/icons";
import Popover, { PopoverMenu } from "@/refresh-components/Popover";
import LineItem from "@/refresh-components/buttons/LineItem";
import AgentAvatar from "@/refresh-components/avatars/AgentAvatar";
import { cn } from "@/lib/utils";
import type { Route } from "next";

/** Status badge colors */
function TypeBadge({ persona }: { persona: Persona }) {
  if (persona.builtin_persona) {
    return (
      <span
        className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[0.6875rem] font-medium border"
        style={{
          backgroundColor: "var(--background-tint-02)",
          color: "var(--text-03)",
          borderColor: "var(--border-02)",
        }}
      >
        Built-In
      </span>
    );
  }
  if (persona.is_public) {
    return (
      <span
        className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[0.6875rem] font-medium border"
        style={{
          backgroundColor: "var(--theme-blue-01)",
          color: "var(--theme-blue-05)",
          borderColor: "var(--theme-blue-02)",
        }}
      >
        <SvgGlobe className="w-3 h-3" />
        Public
      </span>
    );
  }
  if (persona.groups.length > 0 || persona.users.length > 0) {
    return (
      <span
        className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[0.6875rem] font-medium border"
        style={{
          backgroundColor: "var(--theme-purple-01)",
          color: "var(--theme-purple-05)",
          borderColor: "var(--theme-purple-02)",
        }}
      >
        <SvgUsers className="w-3 h-3" />
        Shared
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[0.6875rem] font-medium border"
      style={{
        backgroundColor: "var(--background-tint-02)",
        color: "var(--text-03)",
        borderColor: "var(--border-02)",
      }}
    >
      <SvgUser className="w-3 h-3" />
      Personal
    </span>
  );
}

function FeaturedBadge() {
  return (
    <span
      className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[0.6875rem] font-medium border"
      style={{
        backgroundColor: "var(--theme-amber-01)",
        color: "var(--theme-amber-05)",
        borderColor: "var(--theme-amber-02)",
      }}
    >
      <SvgStar className="w-3 h-3" />
      Featured
    </span>
  );
}

function HiddenBadge() {
  return (
    <span
      className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[0.6875rem] font-medium border"
      style={{
        backgroundColor: "var(--theme-red-01)",
        color: "var(--theme-red-05)",
        borderColor: "var(--theme-red-02)",
      }}
    >
      <SvgEyeClosed className="w-3 h-3" />
      Hidden
    </span>
  );
}

function PersonaCard({
  persona,
  isEditable,
  onEdit,
  onToggleDefault,
  onToggleVisibility,
  onDelete,
}: {
  persona: Persona;
  isEditable: boolean;
  onEdit: () => void;
  onToggleDefault: () => void;
  onToggleVisibility: () => void;
  onDelete: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);

  // Accent color follows the user's accent theme (ocean/emerald/violet)
  // --virtualai-accent and --theme-primary-04 adapt to the chosen theme
  const accentColor = persona.is_public
    ? "var(--virtualai-accent, var(--theme-primary-05))"
    : persona.groups.length > 0 || persona.users.length > 0
      ? "var(--theme-primary-04)"
      : persona.is_default_persona
        ? "var(--virtualai-accent, var(--theme-primary-05))"
        : "var(--border-03)";

  return (
    <div
      className={cn(
        "group/card relative flex flex-col rounded-xl border overflow-hidden",
        "border-border-02 bg-background-tint-01",
        "hover:border-border-03 hover:shadow-md hover:-translate-y-1",
        "transition-all duration-200 ease-out"
      )}
    >
      {/* Colored accent bar at top */}
      <div
        className="h-[3px] w-full flex-shrink-0"
        style={{ backgroundColor: accentColor }}
      />

      {/* Card content */}
      <div className="flex flex-col gap-3 p-4">
      {/* Top row: Avatar + Name + Menu */}
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">
          <AgentAvatar agent={persona} size={40} />
        </div>
        <div className="flex-1 min-w-0">
          <Text as="p" mainContentBody className="font-semibold truncate">
            {persona.name}
          </Text>
          {persona.owner && (
            <Text as="p" className="text-[0.6875rem] text-text-03 truncate">
              by {persona.owner.email}
            </Text>
          )}
        </div>

        {/* Actions — visible on hover + when menu is open */}
        <div className={cn(
          "flex items-center gap-1 flex-shrink-0",
          "opacity-0 group-hover/card:opacity-100 transition-opacity",
          menuOpen && "opacity-100"
        )}>
          {isEditable && (
            <IconButton
              icon={SvgEdit}
              tertiary
              onClick={onEdit}
              tooltip="Edit"
            />
          )}
          <Popover open={menuOpen} onOpenChange={setMenuOpen}>
            <Popover.Trigger asChild>
              <IconButton
                icon={SvgMoreHorizontal}
                tertiary
                tooltip="More actions"
              />
            </Popover.Trigger>
            <Popover.Content align="end">
              <PopoverMenu>
                {[
                  isEditable && (
                    <LineItem
                      key="edit"
                      icon={SvgEdit}
                      onClick={() => { onEdit(); setMenuOpen(false); }}
                    >
                      Edit Assistant
                    </LineItem>
                  ),
                  <LineItem
                    key="featured"
                    icon={SvgStar}
                    onClick={() => { onToggleDefault(); setMenuOpen(false); }}
                  >
                    {persona.is_default_persona ? "Remove Featured" : "Set as Featured"}
                  </LineItem>,
                  <LineItem
                    key="visibility"
                    icon={persona.is_visible ? SvgEyeClosed : SvgEye}
                    onClick={() => { onToggleVisibility(); setMenuOpen(false); }}
                  >
                    {persona.is_visible ? "Hide Assistant" : "Show Assistant"}
                  </LineItem>,
                  isEditable && (
                    <LineItem
                      key="delete"
                      icon={SvgTrash}
                      onClick={() => { onDelete(); setMenuOpen(false); }}
                    >
                      Delete
                    </LineItem>
                  ),
                ].filter(Boolean)}
              </PopoverMenu>
            </Popover.Content>
          </Popover>
        </div>
      </div>

      {/* Description */}
      <Text as="p" secondaryBody text03 className="line-clamp-2 min-h-[2.5rem]">
        {persona.description || "No description"}
      </Text>

      {/* Badges */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <TypeBadge persona={persona} />
        {persona.is_default_persona && <FeaturedBadge />}
        {!persona.is_visible && <HiddenBadge />}
      </div>
      </div>
    </div>
  );
}

export function PersonasTable({
  personas,
  refreshPersonas,
  currentPage,
  pageSize,
}: {
  personas: Persona[];
  refreshPersonas: () => void;
  currentPage: number;
  pageSize: number;
}) {
  const router = useRouter();

  const editablePersonas = useMemo(() => {
    return personas.filter((p) => !p.builtin_persona);
  }, [personas]);

  const editablePersonaIds = useMemo(() => {
    return new Set(editablePersonas.map((p) => p.id.toString()));
  }, [editablePersonas]);

  const [finalPersonas, setFinalPersonas] = useState<Persona[]>([]);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [personaToDelete, setPersonaToDelete] = useState<Persona | null>(null);
  const [defaultModalOpen, setDefaultModalOpen] = useState(false);
  const [personaToToggleDefault, setPersonaToToggleDefault] =
    useState<Persona | null>(null);

  useEffect(() => {
    const editable = [...editablePersonas].sort(personaComparator);
    const nonEditable = personas
      .filter((p) => !editablePersonaIds.has(p.id.toString()))
      .sort(personaComparator);
    setFinalPersonas([...editable, ...nonEditable]);
  }, [editablePersonas, personas, editablePersonaIds]);

  const openDeleteModal = (persona: Persona) => {
    setPersonaToDelete(persona);
    setDeleteModalOpen(true);
  };

  const closeDeleteModal = () => {
    setDeleteModalOpen(false);
    setPersonaToDelete(null);
  };

  const handleDeletePersona = async () => {
    if (personaToDelete) {
      const response = await deletePersona(personaToDelete.id);
      if (response.ok) {
        refreshPersonas();
        closeDeleteModal();
      } else {
        toast.error(`Failed to delete persona - ${await response.text()}`);
      }
    }
  };

  const openDefaultModal = (persona: Persona) => {
    setPersonaToToggleDefault(persona);
    setDefaultModalOpen(true);
  };

  const closeDefaultModal = () => {
    setDefaultModalOpen(false);
    setPersonaToToggleDefault(null);
  };

  const handleToggleDefault = async () => {
    if (personaToToggleDefault) {
      const response = await togglePersonaDefault(
        personaToToggleDefault.id,
        personaToToggleDefault.is_default_persona
      );
      if (response.ok) {
        refreshPersonas();
        closeDefaultModal();
      } else {
        toast.error(`Failed to update persona - ${await response.text()}`);
      }
    }
  };

  const handleToggleVisibility = async (persona: Persona) => {
    const response = await togglePersonaVisibility(
      persona.id,
      persona.is_visible
    );
    if (response.ok) {
      refreshPersonas();
    } else {
      toast.error(`Failed to update persona - ${await response.text()}`);
    }
  };

  return (
    <div>
      {/* Delete confirmation modal */}
      {deleteModalOpen && personaToDelete && (
        <ConfirmationModalLayout
          icon={SvgAlertCircle}
          title="Delete Assistant"
          onClose={closeDeleteModal}
          submit={<Button onClick={handleDeletePersona}>Delete</Button>}
        >
          {`Are you sure you want to delete ${personaToDelete.name}?`}
        </ConfirmationModalLayout>
      )}

      {/* Featured confirmation modal */}
      {defaultModalOpen &&
        personaToToggleDefault &&
        (() => {
          const isDefault = personaToToggleDefault.is_default_persona;
          const title = isDefault
            ? "Remove Featured Assistant"
            : "Set Featured Assistant";
          const buttonText = isDefault ? "Remove Feature" : "Set as Featured";
          const text = isDefault
            ? `Are you sure you want to remove the featured status of ${personaToToggleDefault.name}?`
            : `Are you sure you want to set the featured status of ${personaToToggleDefault.name}?`;
          const additionalText = isDefault
            ? `Removing "${personaToToggleDefault.name}" as a featured assistant will not affect its visibility or accessibility.`
            : `Setting "${personaToToggleDefault.name}" as a featured assistant will make it public and visible to all users. This action cannot be undone.`;

          return (
            <ConfirmationModalLayout
              icon={SvgAlertCircle}
              title={title}
              onClose={closeDefaultModal}
              submit={
                <Button onClick={handleToggleDefault}>{buttonText}</Button>
              }
            >
              <div className="flex flex-col gap-2">
                <Text as="p">{text}</Text>
                <Text as="p" text03>
                  {additionalText}
                </Text>
              </div>
            </ConfirmationModalLayout>
          );
        })()}

      {/* Card grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {finalPersonas.map((persona) => {
          const isEditable = editablePersonas.includes(persona);
          return (
            <PersonaCard
              key={persona.id}
              persona={persona}
              isEditable={isEditable}
              onEdit={() =>
                router.push(
                  `/app/agents/edit/${persona.id}?u=${Date.now()}&admin=true` as Route
                )
              }
              onToggleDefault={() => openDefaultModal(persona)}
              onToggleVisibility={() => handleToggleVisibility(persona)}
              onDelete={() => openDeleteModal(persona)}
            />
          );
        })}
      </div>
    </div>
  );
}
