export interface CountrySummary {
  code: string;
  name: string;
  life_expectancy: number | null;
  region: string | null;
}

export interface CountryDetail {
  code: string;
  name: string;
  region?: string;
  subregion?: string;
  capital?: string;
  population?: number;
  languages?: string[];
  life_expectancy?: number;
  gdp_per_capita_usd?: number;
  school_enrollment_secondary_pct?: number;
  ethnicity?: Array<{ group: string; share: number; note?: string }>;
  weather?: {
    temperature_c?: number;
    humidity_pct?: number;
    precipitation_mm?: number;
    weather_code?: number;
  };
  weather_description?: string;
}

export type ActivityType =
  | "running"
  | "gym"
  | "tennis"
  | "cycling"
  | "swimming"
  | "walking"
  | "yoga"
  | "team_sports";

export interface ActivityOption {
  type: ActivityType;
  label: string;
}

export interface ActivityEntry {
  type: ActivityType;
  hours_per_week: number;
}

export interface PredictRequest {
  birth_date: string;
  gender: "male" | "female" | "other";
  country_code: string;
  education: "none" | "primary" | "secondary" | "tertiary";
  income_level: "low" | "average" | "high";
  smoking: "never" | "former" | "current";
  alcohol: "none" | "light" | "moderate" | "heavy";
  reading_hours_per_month: number;
  activities: ActivityEntry[];
  ethnicity_group?: string;
}

export interface PredictResponse {
  predicted_death_date: string;
  earliest_death_date: string;
  latest_death_date: string;
  remaining_years: number;
  life_expectancy_at_birth: number;
  adjusted_life_expectancy: number;
  country: string;
  factors_applied: Record<string, number>;
  disclaimer: string;
}

const API_BASE = import.meta.env.VITE_API_URL ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export function fetchCountries(): Promise<{ countries: CountrySummary[]; updated_at?: string }> {
  return request("/countries");
}

export function fetchCountry(code: string): Promise<CountryDetail> {
  return request(`/countries/${code}`);
}

export function fetchActivityOptions(): Promise<{ activities: ActivityOption[] }> {
  return request("/activities");
}

export function predictDeath(body: PredictRequest): Promise<PredictResponse> {
  return request("/predict", { method: "POST", body: JSON.stringify(body) });
}
