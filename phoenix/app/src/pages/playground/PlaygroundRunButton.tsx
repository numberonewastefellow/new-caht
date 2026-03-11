import { css } from "@emotion/react";
import { useCallback } from "react";
import { useHotkeys } from "react-hotkeys-hook";

import {
  Button,
  Icon,
  Icons,
  Keyboard,
  VisuallyHidden,
} from "@phoenix/components";
import { usePlaygroundContext } from "@phoenix/contexts/PlaygroundContext";
import { useModifierKey } from "@phoenix/hooks/useModifierKey";

const runButtonCSS = css`
  &[data-variant="primary"] {
    background: var(--vai-gradient) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600;
    transition: box-shadow 0.2s ease, opacity 0.2s ease;
    &:hover:not([disabled]) {
      box-shadow: 0 0 16px rgba(124, 58, 237, 0.4), 0 0 6px rgba(192, 38, 211, 0.3);
      opacity: 0.95;
    }
    &:active:not([disabled]) {
      opacity: 0.9;
    }
  }
`;

const cancelButtonCSS = css`
  &[data-variant="primary"] {
    background: var(--global-color-danger-700) !important;
    border-color: var(--global-color-danger-700) !important;
    &:hover:not([disabled]) {
      background: var(--global-color-danger-900) !important;
      box-shadow: 0 0 12px rgba(220, 38, 38, 0.3);
    }
  }
`;

export function PlaygroundRunButton() {
  const modifierKey = useModifierKey();
  const { runPlaygroundInstances, cancelPlaygroundInstances } =
    usePlaygroundContext((state) => ({
      runPlaygroundInstances: state.runPlaygroundInstances,
      cancelPlaygroundInstances: state.cancelPlaygroundInstances,
    }));
  const isRunning = usePlaygroundContext((state) =>
    state.instances.some((instance) => instance.activeRunId != null)
  );
  const toggleRunning = useCallback(() => {
    if (isRunning) {
      cancelPlaygroundInstances();
    } else {
      runPlaygroundInstances();
    }
  }, [isRunning, cancelPlaygroundInstances, runPlaygroundInstances]);
  useHotkeys(
    "mod+enter",
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      toggleRunning();
    },
    {
      enableOnFormTags: true,
      enableOnContentEditable: true,
      preventDefault: true,
    }
  );
  return (
    <Button
      css={isRunning ? cancelButtonCSS : runButtonCSS}
      variant="primary"
      leadingVisual={
        <Icon
          svg={
            isRunning ? <Icons.LoadingOutline /> : <Icons.PlayCircleOutline />
          }
        />
      }
      size="S"
      onPress={() => {
        toggleRunning();
      }}
      trailingVisual={
        <Keyboard>
          <VisuallyHidden>{modifierKey}</VisuallyHidden>
          <span aria-hidden="true">{modifierKey === "Cmd" ? "⌘" : "Ctrl"}</span>
          <VisuallyHidden>enter</VisuallyHidden>
          <span aria-hidden="true">⏎</span>
        </Keyboard>
      }
    >
      {isRunning ? "Cancel" : "Run"}
    </Button>
  );
}
