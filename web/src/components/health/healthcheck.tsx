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
  const { error } = useSWR("/api/heartbeat", errorHandlingFetcher, {
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
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-mask-03 backdrop-blur-03">
      <div className="mx-4 w-full max-w-[26rem] overflow-hidden rounded-16 border bg-background-tint-00 virtualai-glow-border">
        {/* Top accent bar */}
        <div className="h-1 w-full bg-gradient-to-r from-[var(--theme-orange-05)] via-[var(--theme-amber-04)] to-[var(--theme-orange-05)]" />

        <div className="px-8 pb-8 pt-7">
          {/* Icon */}
          <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-12 bg-[var(--status-warning-01)]">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-6 w-6 text-[var(--status-text-warning-05)]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.75}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
              />
            </svg>
          </div>

          {/* Title */}
          <h2 className="mb-2 text-center text-lg font-semibold text-text-05">
            Service Unavailable
          </h2>

          {/* Description */}
          <p className="mb-6 text-center text-sm leading-relaxed text-text-03">
            The backend is currently unavailable or under maintenance.
            {" "}If this is your initial setup, the backend may still be
            starting up. This will automatically dismiss once the
            service is back online.
          </p>

          {/* Connection status */}
          <div className="mb-6 flex items-center justify-center gap-2.5 rounded-08 bg-background-tint-01 px-4 py-2.5">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--theme-orange-05)] opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-[var(--theme-orange-05)]" />
            </span>
            <span className="text-xs font-medium text-text-03">
              Attempting to reconnect...
            </span>
          </div>

          {/* Action button */}
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
            className="w-full rounded-08 bg-[var(--theme-primary-05)] px-4 py-2.5 text-sm font-medium text-[var(--text-inverted-05)] transition-colors hover:bg-[var(--theme-primary-04)]"
          >
            Close & Go to Login
          </button>
        </div>
      </div>
    </div>
  );
};
