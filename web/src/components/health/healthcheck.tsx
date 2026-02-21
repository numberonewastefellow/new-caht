"use client";

import { errorHandlingFetcher, RedirectError } from "@/lib/fetcher";
import useSWR from "swr";
import Modal from "@/refresh-components/Modal";
import { useCallback, useEffect, useState, useRef } from "react";
import { getSecondsUntilExpiration } from "@/lib/time";
import { User } from "@/lib/types";
import { refreshToken } from "./refreshUtils";
import { NEXT_PUBLIC_CUSTOM_REFRESH_URL } from "@/lib/constants";
import Button from "@/refresh-components/buttons/Button";
import { logout } from "@/lib/user";
import { usePathname, useRouter } from "next/navigation";
import { SvgLogOut } from "@opal/icons";
const DISMISSED_KEY = "healthcheck-overlay-dismissed";

export const HealthCheckBanner = () => {
  const router = useRouter();
  const [dismissedOverlay, setDismissedOverlay] = useState(() => {
    try {
      return sessionStorage.getItem(DISMISSED_KEY) === "true";
    } catch {
      return false;
    }
  });
  const { error } = useSWR("/api/health", errorHandlingFetcher, {
    // Only poll frequently when there's an error so auto-recovery works;
    // when healthy, fall back to default SWR revalidation (no polling).
    refreshInterval: (data: unknown) => (data ? 0 : 10000),
  });
  const [expired, setExpired] = useState(false);
  const [showLoggedOutModal, setShowLoggedOutModal] = useState(false);
  const pathname = usePathname();
  const expirationTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const refreshIntervalRef = useRef<NodeJS.Timer | null>(null);

  // Reduce revalidation frequency with dedicated SWR config
  const {
    data: user,
    mutate: mutateUser,
    error: userError,
  } = useSWR<User>("/api/me", errorHandlingFetcher, {
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
    dedupingInterval: 30000, // 30 seconds
  });

  // Handle 403 errors from the /api/me endpoint
  useEffect(() => {
    if (userError && userError.status === 403) {
      logout().then(() => {
        if (!pathname?.includes("/auth")) {
          setShowLoggedOutModal(true);
        }
      });
    }
  }, [userError, pathname]);

  // Function to handle the "Log in" button click
  const handleLogin = () => {
    setShowLoggedOutModal(false);
    router.push("/auth/login");
  };

  // Function to set up expiration timeout
  const setupExpirationTimeout = useCallback(
    (secondsUntilExpiration: number) => {
      // Clear any existing timeout
      if (expirationTimeoutRef.current) {
        clearTimeout(expirationTimeoutRef.current);
      }

      // Set timeout to show logout modal when session expires
      const timeUntilExpire = (secondsUntilExpiration + 10) * 1000;
      expirationTimeoutRef.current = setTimeout(() => {
        setExpired(true);

        if (!pathname?.includes("/auth")) {
          setShowLoggedOutModal(true);
        }
      }, timeUntilExpire);
    },
    [pathname]
  );

  // Clean up any timeouts/intervals when component unmounts
  useEffect(() => {
    return () => {
      if (expirationTimeoutRef.current) {
        clearTimeout(expirationTimeoutRef.current);
      }

      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, []);

  // Set up token refresh logic if custom refresh URL exists
  useEffect(() => {
    if (!user) return;

    const secondsUntilExpiration = getSecondsUntilExpiration(user);
    if (secondsUntilExpiration === null) return;

    // Set up expiration timeout based on current user data
    setupExpirationTimeout(secondsUntilExpiration);

    if (NEXT_PUBLIC_CUSTOM_REFRESH_URL) {
      const refreshUrl = NEXT_PUBLIC_CUSTOM_REFRESH_URL;

      const attemptTokenRefresh = async () => {
        let retryCount = 0;
        const maxRetries = 3;

        while (retryCount < maxRetries) {
          try {
            const refreshTokenData = await refreshToken(refreshUrl);
            if (!refreshTokenData) {
              throw new Error("Failed to refresh token");
            }

            const response = await fetch(
              "/api/enterprise-settings/refresh-token",
              {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                },
                body: JSON.stringify(refreshTokenData),
              }
            );
            if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`);
            }

            // Wait for backend to process the token
            await new Promise((resolve) => setTimeout(resolve, 4000));

            // Get updated user data
            const updatedUser = await mutateUser();

            if (updatedUser) {
              // Reset expiration timeout with new expiration time
              const newSecondsUntilExpiration =
                getSecondsUntilExpiration(updatedUser);
              if (newSecondsUntilExpiration !== null) {
                setupExpirationTimeout(newSecondsUntilExpiration);
                console.debug(
                  `Token refreshed, new expiration in ${newSecondsUntilExpiration} seconds`
                );
              }
            }

            break; // Success - exit the retry loop
          } catch (error) {
            console.error(
              `Error refreshing token (attempt ${
                retryCount + 1
              }/${maxRetries}):`,
              error
            );
            retryCount++;

            if (retryCount === maxRetries) {
              console.error("Max retry attempts reached");
            } else {
              // Wait before retrying (exponential backoff)
              await new Promise((resolve) =>
                setTimeout(resolve, Math.pow(2, retryCount) * 1000)
              );
            }
          }
        }
      };

      // Set up refresh interval
      const refreshInterval = 60 * 15; // 15 mins

      // Clear any existing interval
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }

      refreshIntervalRef.current = setInterval(
        attemptTokenRefresh,
        refreshInterval * 1000
      );

      // If we're going to expire before the next refresh, kick off a refresh now
      if (secondsUntilExpiration < refreshInterval) {
        attemptTokenRefresh();
      }
    }
  }, [user, setupExpirationTimeout, mutateUser]);

  // Reset dismissed state when backend recovers
  useEffect(() => {
    if (!error) {
      setDismissedOverlay(false);
      try {
        sessionStorage.removeItem(DISMISSED_KEY);
      } catch {
        // sessionStorage may be unavailable
      }
    }
  }, [error]);

  // Logged out modal
  if (showLoggedOutModal) {
    return (
      <Modal open>
        <Modal.Content width="sm" height="sm">
          <Modal.Header icon={SvgLogOut} title="You Have Been Logged Out" />
          <Modal.Body>
            <p className="text-sm">
              Your session has expired. Please log in again to continue.
            </p>
          </Modal.Body>
          <Modal.Footer>
            <Button onClick={handleLogin}>Log In</Button>
          </Modal.Footer>
        </Modal.Content>
      </Modal>
    );
  }

  if (!error && !expired) {
    return null;
  }

  if (error instanceof RedirectError || expired) {
    if (!pathname?.includes("/auth")) {
      setShowLoggedOutModal(true);
    }
    return null;
  }

  // Backend unavailable — full-screen overlay
  if (dismissedOverlay) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-md rounded-2xl bg-white p-8 text-center shadow-2xl dark:bg-neutral-900">
        {/* Maintenance icon */}
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-8 w-8 text-red-600 dark:text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>

        <h2 className="mb-2 text-xl font-bold text-neutral-900 dark:text-neutral-100">
          Service Unavailable
        </h2>
        <p className="mb-6 text-sm text-neutral-600 dark:text-neutral-400">
          The backend is currently unavailable or under maintenance. If
          this is your initial setup, the backend may still be starting
          up. Please wait a moment — this overlay will automatically
          dismiss once the service is back online.
        </p>

        {/* Polling indicator */}
        <div className="mb-6 flex items-center justify-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
          <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-red-500" />
          Checking connection...
        </div>

        <button
          onClick={() => {
            setDismissedOverlay(true);
            try {
              sessionStorage.setItem(DISMISSED_KEY, "true");
            } catch {
              // sessionStorage may be unavailable
            }
            router.push("/auth/login");
          }}
          className="w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neutral-800 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-neutral-200"
        >
          Close &amp; Go to Login
        </button>
      </div>
    </div>
  );
};
