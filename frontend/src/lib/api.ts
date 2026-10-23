import type {
  BrandKit,
  ExportFormat,
  ExtractResponse,
  FetchFeedResponse,
  FetchUrlResponse,
  GenerateRequest,
  GenerateResponse,
  HealthResponse,
  HeroImage,
  ImageSearchResult,
  LLMOptions,
  ModelInfo,
  Newsletter,
  RenderOptions,
  Section,
  TemplateInfo,
  Theme,
  UploadImageResponse,
} from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

const ACCESS_KEY_STORAGE = "ains.accessKey";

export class ApiError extends Error {
  status: number;
  errors?: { loc: string; msg: string }[];
  requestId?: string;
  constructor(message: string, status: number, extra?: { errors?: { loc: string; msg: string }[]; requestId?: string }) {
    super(message);
    this.status = status;
    this.errors = extra?.errors;
    this.requestId = extra?.requestId;
  }
}

export function getAccessKey(): string {
  try {
    return localStorage.getItem(ACCESS_KEY_STORAGE) || "";
  } catch {
    return "";
  }
}

export function setAccessKey(value: string) {
  try {
    if (value) localStorage.setItem(ACCESS_KEY_STORAGE, value);
    else localStorage.removeItem(ACCESS_KEY_STORAGE);
  } catch {
    /* ignore */
  }
}

interface RequestOptions {
  method?: "GET" | "POST";
  body?: unknown;
  form?: FormData;
  signal?: AbortSignal;
  timeoutMs?: number;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const res = await raw(path, opts);
  const text = await res.text();
  return (text ? JSON.parse(text) : null) as T;
}

async function raw(path: string, opts: RequestOptions = {}): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(new DOMException("timeout", "AbortError")), opts.timeoutMs ?? 120_000);
  if (opts.signal) opts.signal.addEventListener("abort", () => controller.abort(opts.signal?.reason), { once: true });

  const headers: Record<string, string> = {};
  const key = getAccessKey();
  if (key) headers["X-App-Key"] = key;
  let body: BodyInit | undefined;
  if (opts.form) {
    body = opts.form;
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: opts.method ?? (body ? "POST" : "GET"),
      headers,
      body,
      signal: controller.signal,
    });
  } catch (err) {
    clearTimeout(timeout);
    if ((err as Error).name === "AbortError") {
      throw new ApiError("The request timed out. The server may be waking up; please try again.", 0);
    }
    throw new ApiError("Could not reach the API. Check that the backend is running and NEXT_PUBLIC_API_URL is correct.", 0);
  }
  clearTimeout(timeout);

  if (!res.ok) {
    let detail = `Request failed (${res.status}).`;
    let errors: { loc: string; msg: string }[] | undefined;
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") detail = data.detail;
      if (Array.isArray(data?.errors)) {
        errors = data.errors;
        detail += " " + data.errors.map((e: { loc: string; msg: string }) => `${e.loc}: ${e.msg}`).join("; ");
      }
    } catch {
      /* non-JSON error */
    }
    if (res.status === 401) detail = "This server requires an access key. Add it under Settings → Access key.";
    if (res.status === 429) detail = "Too many requests. Please wait a moment and try again.";
    throw new ApiError(detail, res.status, { errors, requestId: res.headers.get("x-request-id") ?? undefined });
  }
  return res;
}

export const api = {
  health: () => request<HealthResponse>("/api/health", { timeoutMs: 20_000 }),
  templates: () => request<TemplateInfo[]>("/api/templates"),
  fonts: () => request<string[]>("/api/fonts"),
  presets: () => request<BrandKit[]>("/api/brands/presets"),
  models: () => request<ModelInfo[]>("/api/models", { timeoutMs: 20_000 }),

  generate: (body: GenerateRequest, signal?: AbortSignal) =>
    request<GenerateResponse>("/api/generate", { body, signal, timeoutMs: 180_000 }),

  regenerateSection: (body: {
    newsletter: Newsletter;
    section_index: number;
    instruction: string;
    tone: string;
    language: string;
    llm: LLMOptions;
  }) => request<{ section: Section; usage: Record<string, number>; model: string }>("/api/regenerate-section", { body }),

  render: (newsletter: Newsletter, brand: BrandKit, render: RenderOptions, signal?: AbortSignal) =>
    request<{ html: string }>("/api/render", { body: { newsletter, brand, render }, signal, timeoutMs: 30_000 }),

  export: async (newsletter: Newsletter, brand: BrandKit, render: RenderOptions, format: ExportFormat) => {
    const res = await raw("/api/export", { body: { newsletter, brand, render, format }, timeoutMs: 60_000 });
    const blob = await res.blob();
    const filename = res.headers.get("x-filename") || `newsletter.${format === "markdown" ? "md" : format === "email" ? "email.html" : format === "text" ? "txt" : format}`;
    return { blob, filename };
  },

  uploadImage: (file: File, kind: "logo" | "hero") => {
    const form = new FormData();
    form.append("file", file);
    return request<UploadImageResponse>(`/api/upload/image?kind=${kind}`, { form, timeoutMs: 60_000 });
  },

  extract: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<ExtractResponse>("/api/extract", { form, timeoutMs: 60_000 });
  },

  fetchUrl: (url: string) => request<FetchUrlResponse>("/api/fetch-url", { body: { url }, timeoutMs: 30_000 }),
  fetchFeed: (url: string, limit = 8) => request<FetchFeedResponse>("/api/fetch-feed", { body: { url, limit }, timeoutMs: 30_000 }),

  searchImages: (query: string, per_page = 9) =>
    request<ImageSearchResult[]>("/api/images/search", { body: { query, per_page }, timeoutMs: 20_000 }),
  selectImage: (r: ImageSearchResult) =>
    request<HeroImage>("/api/images/select", {
      body: { id: r.id, regular: r.regular, download_location: r.download_location, author: r.author, author_url: r.author_url, alt: r.alt },
      timeoutMs: 40_000,
    }),
  generatedBanner: (brand: BrandKit, theme: Theme, company_name: string) =>
    request<HeroImage>("/api/images/generated", { body: { brand, theme, template: "modern", company_name } }),
};
