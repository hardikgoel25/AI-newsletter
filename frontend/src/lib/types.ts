/** Types mirroring backend/app/schemas.py. Keep in sync. */

export type Theme = "dark" | "light";
export type TemplateId = "modern" | "editorial" | "minimal" | "bold" | (string & {});

export interface Highlight {
  icon: string;
  title: string;
  subtitle: string;
}

export interface Section {
  id: string;
  icon: string;
  title: string;
  content: string;
}

export interface Stat {
  value: string;
  label: string;
}

export interface Quote {
  text: string;
  attribution: string;
}

export interface CTA {
  label: string;
  url: string;
}

export interface Socials {
  linkedin: string;
  x: string;
  instagram: string;
  facebook: string;
  youtube: string;
  github: string;
}

export interface Footer {
  tagline: string;
  website: string;
  contact_email: string;
  phone: string;
  address: string;
  socials: Socials;
  copyright: string;
  subscription_note: string;
  privacy_url: string;
  terms_url: string;
  unsubscribe_url: string;
}

export interface ImageCredit {
  name: string;
  url: string;
  source: string;
  source_url: string;
}

export type HeroKind = "upload" | "unsplash" | "generated" | "url" | "none";

export interface HeroImage {
  kind: HeroKind;
  src: string;
  alt: string;
  credit: ImageCredit | null;
}

export interface Newsletter {
  company_name: string;
  newsletter_type: string;
  language: string;
  hero_title: string;
  subtitle: string;
  summary: string;
  date: string;
  estimated_read_time: string;
  highlights: Highlight[];
  sections: Section[];
  stats: Stat[];
  quote: Quote | null;
  cta: CTA | null;
  image_keywords: string[];
  hero_image: HeroImage;
  footer: Footer;
}

export type LogoInvert = "never" | "on-dark" | "always";

export interface BrandKit {
  id: string;
  name: string;
  company_name: string;
  tagline: string;
  logo: string;
  logo_invert: LogoInvert;
  primary: string;
  secondary: string;
  accent: string;
  font_heading: string;
  font_body: string;
  website: string;
  contact_email: string;
  phone: string;
  address: string;
  socials: Socials;
  subscription_note: string;
  privacy_url: string;
  terms_url: string;
  unsubscribe_url: string;
}

export const NEWSLETTER_TYPES = [
  "Corporate",
  "Weekly Update",
  "Monthly Update",
  "Product Launch",
  "Investor Update",
  "Internal Newsletter",
  "HR Newsletter",
  "Marketing",
  "Engineering",
  "Community",
  "Custom",
] as const;
export type NewsletterType = (typeof NEWSLETTER_TYPES)[number];

export const TONES = [
  "Professional",
  "Executive",
  "Friendly",
  "Technical",
  "Marketing",
  "Minimal",
  "Inspirational",
  "Playful",
] as const;
export type Tone = (typeof TONES)[number];

export const READING_TIMES = ["Auto", "2 min read", "3 min read", "5 min read", "7 min read", "10 min read"] as const;

export interface GenerateOptions {
  newsletter_type: NewsletterType;
  custom_type_instruction: string;
  tone: Tone;
  language: string;
  reading_time: string;
  highlight_count: number;
  section_count: number;
  include_stats: boolean;
  include_quote: boolean;
  include_cta: boolean;
  publication_date: string;
  hero_title_override: string;
  summary_override: string;
  cta_override: CTA | null;
  extra_instructions: string;
}

export type Provider = "groq" | "openai" | "gemini" | "ollama";

export interface LLMOptions {
  provider: Provider | null;
  model: string | null;
  temperature: number;
}

export interface RenderOptions {
  template: TemplateId;
  theme: Theme;
}

export type SourceKind = "text" | "file" | "url" | "feed";

export interface Source {
  id: string;
  kind: SourceKind;
  label: string;
  text: string;
}

export type AutoHero = "unsplash" | "generated" | "none";

export interface GenerateRequest {
  sources: Omit<Source, "id">[];
  options: GenerateOptions;
  brand: BrandKit;
  render: RenderOptions;
  llm: LLMOptions;
  hero_image: HeroImage | null;
  auto_hero: AutoHero;
}

export interface GenerateResponse {
  newsletter: Newsletter;
  html: string;
  warnings: string[];
  usage: Record<string, number>;
  model: string;
  provider: string;
  elapsed_ms: number;
}

export interface TemplateInfo {
  id: TemplateId;
  name: string;
  description: string;
  supports: Theme[];
  default_fonts: { heading: string; body: string };
  tags: string[];
}

export interface ModelInfo {
  provider: Provider;
  id: string;
  label: string;
  default: boolean;
  available: boolean;
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  providers: Provider[];
  unsplash: boolean;
  access_key_required: boolean;
}

export interface UploadImageResponse {
  data_uri: string;
  mime: string;
  width: number;
  height: number;
  bytes: number;
}

export interface ExtractResponse {
  filename: string;
  kind: string;
  text: string;
  chars: number;
  pages: number | null;
}

export interface FetchUrlResponse {
  url: string;
  title: string;
  site: string;
  text: string;
  chars: number;
}

export interface FeedItem {
  title: string;
  summary: string;
  link: string;
  published: string;
}

export interface FetchFeedResponse {
  title: string;
  items: FeedItem[];
  text: string;
}

export interface ImageSearchResult {
  id: string;
  thumb: string;
  regular: string;
  alt: string;
  author: string;
  author_url: string;
  download_location: string;
  width: number;
  height: number;
}

export type ExportFormat = "html" | "email" | "markdown" | "json" | "text";

export interface HistoryEntry {
  id: string;
  createdAt: number;
  title: string;
  company: string;
  newsletter: Newsletter;
  brand: BrandKit;
  render: RenderOptions;
}

export const EMPTY_SOCIALS: Socials = { linkedin: "", x: "", instagram: "", facebook: "", youtube: "", github: "" };

export const DEFAULT_BRAND: BrandKit = {
  id: "custom",
  name: "Custom",
  company_name: "",
  tagline: "",
  logo: "",
  logo_invert: "never",
  primary: "#6366f1",
  secondary: "#8b5cf6",
  accent: "#06b6d4",
  font_heading: "",
  font_body: "",
  website: "",
  contact_email: "",
  phone: "",
  address: "",
  socials: { ...EMPTY_SOCIALS },
  subscription_note: "",
  privacy_url: "",
  terms_url: "",
  unsubscribe_url: "",
};

export const DEFAULT_OPTIONS: GenerateOptions = {
  newsletter_type: "Corporate",
  custom_type_instruction: "",
  tone: "Professional",
  language: "English",
  reading_time: "Auto",
  highlight_count: 4,
  section_count: 4,
  include_stats: true,
  include_quote: false,
  include_cta: true,
  publication_date: "",
  hero_title_override: "",
  summary_override: "",
  cta_override: null,
  extra_instructions: "",
};
