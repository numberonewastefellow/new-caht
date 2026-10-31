import {
  DEFAULT_VIRTUALAI_DOMAIN,
  CHROME_SPECIFIC_STORAGE_KEYS,
} from "./constants.js";

export async function getVirtualAIDomain() {
  const result = await chrome.storage.local.get({
    [CHROME_SPECIFIC_STORAGE_KEYS.VIRTUALAI_DOMAIN]: DEFAULT_VIRTUALAI_DOMAIN,
  });
  return result[CHROME_SPECIFIC_STORAGE_KEYS.VIRTUALAI_DOMAIN];
}

export function setVirtualAIDomain(domain, callback) {
  chrome.storage.local.set(
    { [CHROME_SPECIFIC_STORAGE_KEYS.VIRTUALAI_DOMAIN]: domain },
    callback,
  );
}

export function getVirtualAIDomainSync() {
  return new Promise((resolve) => {
    getVirtualAIDomain(resolve);
  });
}
