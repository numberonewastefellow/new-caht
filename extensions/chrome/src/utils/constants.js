export const THEMES = {
  LIGHT: "light",
  DARK: "dark",
};

export const DEFAULT_VIRTUALAI_DOMAIN = "http://localhost:3000";

export const SIDE_PANEL_PATH = "/chat/nrf/side-panel";

export const ACTIONS = {
  GET_SELECTED_TEXT: "getSelectedText",
  GET_CURRENT_VIRTUALAI_DOMAIN: "getCurrentVirtualAIDomain",
  UPDATE_PAGE_URL: "updatePageUrl",
  SEND_TO_VIRTUALAI: "sendToVirtualAI",
  OPEN_SIDE_PANEL: "openSidePanel",
  TOGGLE_NEW_TAB_OVERRIDE: "toggleNewTabOverride",
  OPEN_SIDE_PANEL_WITH_INPUT: "openSidePanelWithInput",
  OPEN_VIRTUALAI_WITH_INPUT: "openVirtualAIWithInput",
  CLOSE_SIDE_PANEL: "closeSidePanel",
};

export const CHROME_SPECIFIC_STORAGE_KEYS = {
  VIRTUALAI_DOMAIN: "virtualaiExtensionDomain",
  USE_VIRTUALAI_AS_DEFAULT_NEW_TAB: "virtualaiExtensionDefaultNewTab",
  THEME: "virtualaiExtensionTheme",
  BACKGROUND_IMAGE: "virtualaiExtensionBackgroundImage",
  DARK_BG_URL: "virtualaiExtensionDarkBgUrl",
  LIGHT_BG_URL: "virtualaiExtensionLightBgUrl",
  ONBOARDING_COMPLETE: "virtualaiExtensionOnboardingComplete",
};

export const CHROME_MESSAGE = {
  PREFERENCES_UPDATED: "PREFERENCES_UPDATED",
  VIRTUALAI_APP_LOADED: "VIRTUALAI_APP_LOADED",
  SET_DEFAULT_NEW_TAB: "SET_DEFAULT_NEW_TAB",
  LOAD_NEW_CHAT_PAGE: "LOAD_NEW_CHAT_PAGE",
  LOAD_NEW_PAGE: "LOAD_NEW_PAGE",
  AUTH_REQUIRED: "AUTH_REQUIRED",
};

export const WEB_MESSAGE = {
  PAGE_CHANGE: "PAGE_CHANGE",
};
