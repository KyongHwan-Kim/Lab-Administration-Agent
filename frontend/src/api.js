export async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, {
    ...options,
    headers,
    credentials: "include",
  });
  if (response.status === 204) return null;

  const contentType = response.headers.get("content-type") || "";
  if (!response.ok) {
    let detail = "요청에 실패했습니다.";
    if (contentType.includes("application/json")) {
      const data = await response.json();
      if (typeof data.detail === "string") detail = data.detail;
    }
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  if (contentType.includes("application/pdf") || contentType.startsWith("image/")) return response.blob();
  if (contentType.includes("application/json")) return response.json();
  return null;
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
