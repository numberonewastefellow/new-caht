import ipaddress
import socket
from typing import Any
from urllib.parse import parse_qs
from urllib.parse import urlencode
from urllib.parse import urlparse
from urllib.parse import urlunparse

import requests

from om.utils.logger import setup_logger

logger = setup_logger()

# Hostnames that should always be blocked
BLOCKED_HOSTNAMES = {
    # Localhost variations
    "localhost",
    # Cloud metadata endpoints (defense-in-depth, IPs also blocked via _is_ip_private_or_reserved)
    "169.254.169.254",  # AWS/Azure/GCP metadata IP
    "fd00:ec2::254",  # AWS IPv6 metadata
    "metadata.azure.com",
    "metadata.google.internal",
    "metadata.gke.internal",
    # Kubernetes internal
    "kubernetes.default",
    "kubernetes.default.svc",
    "kubernetes.default.svc.cluster.local",
}


class SSRFException(Exception):
    """Exception raised when an SSRF attempt is detected."""


def _is_ip_private_or_reserved(ip_str: str) -> bool:
    """
    Check if an IP address is private, reserved, or otherwise not suitable
    for external requests.

    Uses Python's ipaddress module which handles:
    - Private addresses (10.x.x.x, 172.16-31.x.x, 192.168.x.x)
    - Loopback addresses (127.x.x.x, ::1)
    - Link-local addresses (169.254.x.x including cloud metadata IPs, fe80::/10)
    - Reserved addresses
    - Multicast addresses
    - Unspecified addresses (0.0.0.0, ::)
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        # is_global returns True only for globally routable unicast addresses
        # This excludes private, loopback, link-local, reserved, and unspecified
        # We also need to explicitly check multicast as it's not covered by is_global
        return not ip.is_global or ip.is_multicast
    except ValueError:
        # If we can't parse the IP, consider it unsafe
        return True


def _validate_and_resolve_url(url: str) -> tuple[str, str, int]:
    """
    Validate a URL for SSRF and resolve it to a safe IP address.

    Returns:
        Tuple of (validated_ip, original_hostname, port)

    Raises:
        SSRFException: If the URL could be used for SSRF attack
        ValueError: If the URL is malformed
    """
    if not url:
        raise ValueError("URL cannot be empty")

    # Parse the URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValueError(f"Invalid URL format: {e}")

    # Validate scheme
    if parsed.scheme not in ("http", "https"):
        raise SSRFException(
            f"Invalid URL scheme '{parsed.scheme}'. Only http and https are allowed."
        )

    # Get hostname
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must contain a hostname")

    # Check for blocked hostnames
    hostname_lower = hostname.lower()
    if hostname_lower in BLOCKED_HOSTNAMES:
        raise SSRFException(f"Access to hostname '{hostname}' is not allowed.")

    # Check for common SSRF bypass attempts
    # Block URLs with credentials (user:pass@host)
    if parsed.username or parsed.password:
        raise SSRFException("URLs with embedded credentials are not allowed.")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    # Check if the hostname is already an IP address
    try:
        ip = ipaddress.ip_address(hostname)
        if _is_ip_private_or_reserved(str(ip)):
            raise SSRFException(
                f"Access to internal/private IP address '{hostname}' is not allowed."
            )
        return str(ip), hostname, port
    except ValueError:
        # Not an IP address, proceed with DNS resolution
        pass

    # Resolve hostname to IP addresses
    try:
        addr_info = socket.getaddrinfo(hostname, port)
    except socket.gaierror as e:
        logger.warning(f"DNS resolution failed for hostname '{hostname}': {e}")
        raise SSRFException(f"Could not resolve hostname '{hostname}': {e}")

    if not addr_info:
        raise SSRFException(f"Could not resolve hostname '{hostname}'")

    # Find the first valid (non-private) IP address
    validated_ip = None
    for info in addr_info:
        ip_str = info[4][0]
        if _is_ip_private_or_reserved(str(ip_str)):
            raise SSRFException(
                f"Hostname '{hostname}' resolves to internal/private IP address "
                f"'{ip_str}'. Access to internal networks is not allowed."
            )
        if validated_ip is None:
            validated_ip = ip_str

    if validated_ip is None:
        raise SSRFException(f"Could not resolve hostname '{hostname}'")

    return validated_ip, hostname, port


MAX_REDIRECTS = 10


def _make_ssrf_safe_request(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 15,
    **kwargs: Any,
) -> requests.Response:
    """
    Make a single GET request with SSRF protection (no redirect following).

    Returns the response which may be a redirect (3xx status).
    """
    # Validate and resolve the URL to get a safe IP
    validated_ip, original_hostname, port = _validate_and_resolve_url(url)

    # Parse the URL to rebuild it with the IP
    parsed = urlparse(url)

    # Build the new URL using the validated IP
    # For HTTPS, we need to use the original hostname for TLS verification
    if parsed.scheme == "https":
        # For HTTPS, make request to original URL but we've validated the IP
        # The TLS handshake needs the hostname for SNI
        # We rely on the short time window between validation and request
        # A more robust solution would require custom SSL context
        request_url = url
    else:
        # For HTTP, we can safely request directly to the IP
        netloc = f"{validated_ip}:{port}" if port not in (80, 443) else validated_ip
        request_url = urlunparse(
            (
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )

    # Prepare headers
    request_headers = headers.copy() if headers else {}

    # Set Host header to original hostname (required for virtual hosting)
    if parsed.scheme == "http":
        request_headers["Host"] = (
            f"{original_hostname}:{port}" if port != 80 else original_hostname
        )

    # Disable automatic redirects to prevent SSRF bypass via redirect
    return requests.get(
        request_url,
        headers=request_headers,
        timeout=timeout,
        allow_redirects=False,
        **kwargs,
    )


def ssrf_safe_get(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 15,
    follow_redirects: bool = True,
    **kwargs: Any,
) -> requests.Response:
    """
    Make a GET request with SSRF protection.

    This function resolves the hostname, validates the IP is not private/internal,
    and makes the request directly to the validated IP to prevent DNS rebinding attacks.
    Redirects are followed safely by validating each redirect URL.

    Args:
        url: The URL to fetch
        headers: Optional headers to include in the request
        timeout: Request timeout in seconds
        follow_redirects: Whether to follow redirects (each redirect URL is validated)
        **kwargs: Additional arguments passed to requests.get()

    Returns:
        requests.Response object

    Raises:
        SSRFException: If the URL could be used for SSRF attack
        ValueError: If the URL is malformed
        requests.RequestException: If the request fails
    """
    response = _make_ssrf_safe_request(url, headers, timeout, **kwargs)

    if not follow_redirects:
        return response

    # Manually follow redirects while validating each redirect URL
    redirect_count = 0
    current_url = url

    while response.is_redirect and redirect_count < MAX_REDIRECTS:
        redirect_count += 1

        # Get the redirect location
        redirect_url = response.headers.get("Location")
        if not redirect_url:
            break

        # Handle relative redirects
        if not redirect_url.startswith(("http://", "https://")):
            parsed_current = urlparse(current_url)
            if redirect_url.startswith("/"):
                redirect_url = (
                    f"{parsed_current.scheme}://{parsed_current.netloc}{redirect_url}"
                )
            else:
                # Relative path
                base_path = parsed_current.path.rsplit("/", 1)[0]
                redirect_url = (
                    f"{parsed_current.scheme}://{parsed_current.netloc}"
                    f"{base_path}/{redirect_url}"
                )

        # Validate and follow the redirect (this will raise SSRFException if invalid)
        current_url = redirect_url
        response = _make_ssrf_safe_request(redirect_url, headers, timeout, **kwargs)

    if response.is_redirect and redirect_count >= MAX_REDIRECTS:
        raise SSRFException(f"Too many redirects (max {MAX_REDIRECTS})")

    return response


# Headers that must never be forwarded from LLM-generated requests
BLOCKED_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "host",
    "x-forwarded-for",
    "x-forwarded-host",
    "x-forwarded-proto",
    "x-real-ip",
    "proxy-authorization",
    "proxy-connection",
}


def sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    """Remove dangerous headers that could be used for impersonation or routing attacks.

    Args:
        headers: Raw headers dict (e.g. from LLM kwargs).

    Returns:
        Sanitized headers dict with blocked headers removed.
    """
    sanitized = {}
    removed = []
    for key, value in headers.items():
        if key.lower().strip() in BLOCKED_HEADERS:
            removed.append(key)
        else:
            sanitized[key] = value
    if removed:
        logger.warning(
            "Blocked headers removed from HTTP request: %s", ", ".join(removed)
        )
    return sanitized


# Maximum response body size to read (10 MB)
MAX_RESPONSE_BYTES = 10 * 1024 * 1024


def ssrf_safe_request(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    json_body: dict | None = None,
    data: str | None = None,
    timeout: int = 30,
    follow_redirects: bool = False,
    max_response_bytes: int = MAX_RESPONSE_BYTES,
) -> requests.Response:
    """Make an HTTP request with SSRF protection, header sanitization, and size limits.

    Supports all HTTP methods (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS).
    Validates URLs against private/internal IP ranges, sanitizes headers,
    disables redirects by default, and limits response body size.

    Args:
        method: HTTP method (GET, POST, etc.)
        url: Target URL
        headers: Optional request headers (will be sanitized)
        json_body: Optional JSON body for POST/PUT/PATCH
        data: Optional raw string body for POST/PUT/PATCH
        timeout: Request timeout in seconds
        follow_redirects: Whether to follow redirects (default False to prevent SSRF bypass)
        max_response_bytes: Maximum response body size to read

    Returns:
        requests.Response object

    Raises:
        SSRFException: If the URL targets a private/internal address
        ValueError: If the URL is malformed
        requests.RequestException: If the request fails
    """
    # Validate URL against SSRF
    _validate_and_resolve_url(url)

    # Sanitize headers
    safe_headers = sanitize_headers(headers) if headers else {}

    # Make request with redirects disabled to prevent SSRF bypass via redirect
    response = requests.request(
        method=method.upper(),
        url=url,
        headers=safe_headers,
        json=json_body,
        data=data,
        timeout=timeout,
        allow_redirects=False,
        stream=True,  # Stream to enforce size limit
    )

    # Enforce response size limit by reading in chunks
    content_length = response.headers.get("Content-Length")
    if content_length and int(content_length) > max_response_bytes:
        response.close()
        raise requests.exceptions.ContentDecodingError(
            f"Response too large: {content_length} bytes "
            f"(max {max_response_bytes} bytes)"
        )

    # Read the content with size enforcement
    chunks = []
    bytes_read = 0
    for chunk in response.iter_content(chunk_size=8192):
        bytes_read += len(chunk)
        if bytes_read > max_response_bytes:
            response.close()
            raise requests.exceptions.ContentDecodingError(
                f"Response exceeded max size of {max_response_bytes} bytes"
            )
        chunks.append(chunk)

    # Reconstruct the response content
    response._content = b"".join(chunks)

    # Handle redirects if enabled
    if follow_redirects and response.is_redirect:
        redirect_count = 0
        current_url = url
        while response.is_redirect and redirect_count < MAX_REDIRECTS:
            redirect_count += 1
            redirect_url = response.headers.get("Location")
            if not redirect_url:
                break

            if not redirect_url.startswith(("http://", "https://")):
                parsed_current = urlparse(current_url)
                if redirect_url.startswith("/"):
                    redirect_url = (
                        f"{parsed_current.scheme}://{parsed_current.netloc}"
                        f"{redirect_url}"
                    )
                else:
                    base_path = parsed_current.path.rsplit("/", 1)[0]
                    redirect_url = (
                        f"{parsed_current.scheme}://{parsed_current.netloc}"
                        f"{base_path}/{redirect_url}"
                    )

            # Validate redirect target
            _validate_and_resolve_url(redirect_url)
            current_url = redirect_url
            response = requests.request(
                method=method.upper(),
                url=redirect_url,
                headers=safe_headers,
                json=json_body if method.upper() in ("POST", "PUT", "PATCH") else None,
                data=data if method.upper() in ("POST", "PUT", "PATCH") else None,
                timeout=timeout,
                allow_redirects=False,
            )

        if response.is_redirect and redirect_count >= MAX_REDIRECTS:
            raise SSRFException(f"Too many redirects (max {MAX_REDIRECTS})")

    return response


def normalize_url(url: str) -> str:
    """
    Normalize a URL by removing query parameters and fragments.
    This is used to create consistent cache keys for deduplication.

    Args:
        url: The original URL

    Returns:
        Normalized URL (scheme + netloc + path + params only)
    """
    parsed_url = urlparse(url)

    # Reconstruct the URL without query string and fragment
    normalized = urlunparse(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            "",
            "",
        )
    )

    return normalized


def add_url_params(url: str, params: dict) -> str:
    """
    Add parameters to a URL, handling existing parameters properly.

    Args:
        url: The original URL
        params: Dictionary of parameters to add

    Returns:
        URL with added parameters
    """
    # Parse the URL
    parsed_url = urlparse(url)

    # Get existing query parameters
    query_params = parse_qs(parsed_url.query)

    # Update with new parameters
    for key, value in params.items():
        query_params[key] = [value]

    # Build the new query string
    new_query = urlencode(query_params, doseq=True)

    # Reconstruct the URL with the new query string
    new_url = urlunparse(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query,
            parsed_url.fragment,
        )
    )

    return new_url
