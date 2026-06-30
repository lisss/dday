import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  ActivityOption,
  ActivityType,
  CountryDetail,
  CountrySummary,
  PredictRequest,
  PredictResponse,
  fetchActivityOptions,
  fetchCountries,
  fetchCountry,
  predictDeath,
} from "./api";

type FormState = {
  birthDate: string;
  gender: PredictRequest["gender"];
  countryCode: string;
  education: PredictRequest["education"];
  incomeLevel: PredictRequest["income_level"];
  smoking: PredictRequest["smoking"];
  alcohol: PredictRequest["alcohol"];
  readingHoursPerMonth: number;
  activityHours: Record<ActivityType, number>;
};

const EMPTY_ACTIVITY_HOURS = (): Record<ActivityType, number> => ({
  running: 0,
  gym: 0,
  tennis: 0,
  cycling: 0,
  swimming: 0,
  walking: 0,
  yoga: 0,
  team_sports: 0,
});

const initialForm: FormState = {
  birthDate: "1990-01-01",
  gender: "other",
  countryCode: "GB",
  education: "secondary",
  incomeLevel: "average",
  smoking: "never",
  alcohol: "none",
  readingHoursPerMonth: 12,
  activityHours: EMPTY_ACTIVITY_HOURS(),
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function formatMoney(value?: number): string {
  if (value == null) return "—";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

function ZeroFriendlyNumberInput({
  value,
  onChange,
  min = 0,
  max,
  step = 1,
}: {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
}) {
  function clamp(n: number): number {
    return Math.min(max ?? Infinity, Math.max(min, n));
  }

  return (
    <input
      type="number"
      min={min}
      max={max}
      step={step}
      placeholder="0"
      value={value === 0 ? "" : value}
      onChange={(e) => {
        const raw = e.target.value;
        if (raw === "") {
          onChange(0);
          return;
        }
        const parsed = Number(raw);
        if (!Number.isNaN(parsed)) {
          onChange(clamp(parsed));
        }
      }}
      onBlur={(e) => {
        const raw = e.target.value;
        if (raw === "") {
          onChange(0);
          return;
        }
        const parsed = Number(raw);
        onChange(Number.isNaN(parsed) ? 0 : clamp(parsed));
      }}
    />
  );
}

function parseLocalDate(iso: string): Date {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day, 0, 0, 0, 0);
}

function splitRemainingSeconds(totalSeconds: number) {
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return { days, hours, minutes, seconds };
}

function useCountdown(targetDateIso: string | null) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!targetDateIso) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [targetDateIso]);

  return useMemo(() => {
    if (!targetDateIso) return null;
    const target = parseLocalDate(targetDateIso);
    const totalSeconds = Math.max(0, Math.floor((target.getTime() - now) / 1000));
    return { ...splitRemainingSeconds(totalSeconds), totalSeconds };
  }, [targetDateIso, now]);
}

function Countdown({ targetDate }: { targetDate: string }) {
  const left = useCountdown(targetDate);
  if (!left) return null;

  return (
    <div className="countdown">
      <div className="countdown-clock" aria-live="polite">
        <span className="countdown-clock-segment countdown-clock-segment--days">
          <span className="countdown-digit">{left.days.toLocaleString()}</span>
          <span className="countdown-unit">days</span>
        </span>
        <span className="countdown-sep">:</span>
        <span className="countdown-clock-segment">
          <span className="countdown-digit">{pad2(left.hours)}</span>
          <span className="countdown-unit">hrs</span>
        </span>
        <span className="countdown-sep">:</span>
        <span className="countdown-clock-segment">
          <span className="countdown-digit">{pad2(left.minutes)}</span>
          <span className="countdown-unit">min</span>
        </span>
        <span className="countdown-sep">:</span>
        <span className="countdown-clock-segment">
          <span className="countdown-digit">{pad2(left.seconds)}</span>
          <span className="countdown-unit">sec</span>
        </span>
      </div>
      <p className="countdown-seconds">
        {left.totalSeconds.toLocaleString()} seconds remaining
      </p>
    </div>
  );
}

export default function App() {
  const [countries, setCountries] = useState<CountrySummary[]>([]);
  const [countriesLoading, setCountriesLoading] = useState(true);
  const [countriesError, setCountriesError] = useState<string | null>(null);
  const [activityOptions, setActivityOptions] = useState<ActivityOption[]>([]);
  const [form, setForm] = useState<FormState>(initialForm);
  const [countryDetail, setCountryDetail] = useState<CountryDetail | null>(null);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setCountriesLoading(true);
    setCountriesError(null);
    fetchCountries()
      .then((data) => {
        setCountries(data.countries);
        if (data.countries.length > 0) {
          setForm((prev) => {
            const hasSelection = data.countries.some((c) => c.code === prev.countryCode);
            return hasSelection ? prev : { ...prev, countryCode: data.countries[0].code };
          });
        }
      })
      .catch((err: Error) => setCountriesError(err.message))
      .finally(() => setCountriesLoading(false));
    fetchActivityOptions()
      .then((data) => setActivityOptions(data.activities))
      .catch(() => setActivityOptions([]));
  }, []);

  useEffect(() => {
    if (!form.countryCode) return;
    fetchCountry(form.countryCode)
      .then(setCountryDetail)
      .catch(() => setCountryDetail(null));
  }, [form.countryCode]);

  const sortedCountries = useMemo(
    () => [...countries].sort((a, b) => a.name.localeCompare(b.name)),
    [countries],
  );

  const selectedCountry = useMemo(
    () => countries.find((c) => c.code === form.countryCode),
    [countries, form.countryCode],
  );

  const weeklyActivityTotal = useMemo(
    () => Object.values(form.activityHours).reduce((sum, hrs) => sum + hrs, 0),
    [form.activityHours],
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const activities = (Object.entries(form.activityHours) as [ActivityType, number][])
        .filter(([, hours]) => hours > 0)
        .map(([type, hours_per_week]) => ({ type, hours_per_week }));

      const payload: PredictRequest = {
        birth_date: form.birthDate,
        gender: form.gender,
        country_code: form.countryCode,
        education: form.education,
        income_level: form.incomeLevel,
        smoking: form.smoking,
        alcohol: form.alcohol,
        reading_hours_per_month: form.readingHoursPerMonth,
        activities,
      };
      const prediction = await predictDeath(payload);
      setResult(prediction);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prediction failed");
    } finally {
      setLoading(false);
    }
  }

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function updateActivityHours(type: ActivityType, hours: number) {
    setForm((prev) => ({
      ...prev,
      activityHours: {
        ...prev.activityHours,
        [type]: Math.min(40, Math.max(0, hours)),
      },
    }));
  }

  return (
    <div className="page">
      <header className="hero">
        <div className="hero-banner">
          <img
            src="/highgate-headstone.png"
            alt="Victorian Highgate Cemetery headstone with RIP, bear and penguin"
            className="hero-banner-img"
          />
        </div>
        <p className="eyebrow">Statistical life estimator</p>
        <h1>When might you die?</h1>
        <p className="subtitle">
          Uses public data on life expectancy, income, education, and weather across{" "}
          {countries.length > 0 ? `${countries.length} countries` : "the world"} — then
          adjusts for your lifestyle.
        </p>
      </header>

      <main className="layout">
        <section className="panel form-panel">
          <h2>Your details</h2>
          <form onSubmit={handleSubmit} className="form-grid">
            <label>
              Birth date
              <input
                type="date"
                required
                value={form.birthDate}
                onChange={(e) => update("birthDate", e.target.value)}
              />
            </label>

            <label>
              Gender
              <select
                value={form.gender}
                onChange={(e) => update("gender", e.target.value as FormState["gender"])}
              >
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="other">Other / prefer not to say</option>
              </select>
            </label>

            <label className="wide">
              Country
              <select
                value={form.countryCode}
                disabled={countriesLoading || sortedCountries.length === 0}
                onChange={(e) => update("countryCode", e.target.value)}
              >
                {countriesLoading && <option value={form.countryCode}>Loading countries…</option>}
                {!countriesLoading && sortedCountries.length === 0 && (
                  <option value="">No countries available</option>
                )}
                {sortedCountries.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.name} ({c.code})
                    {c.life_expectancy != null ? ` — ${c.life_expectancy} yrs` : ""}
                  </option>
                ))}
              </select>
              {countriesError && (
                <span className="field-hint error">Failed to load countries: {countriesError}</span>
              )}
            </label>

            <label>
              Education
              <select
                value={form.education}
                onChange={(e) =>
                  update("education", e.target.value as FormState["education"])
                }
              >
                <option value="none">None</option>
                <option value="primary">Primary</option>
                <option value="secondary">Secondary</option>
                <option value="tertiary">Tertiary / university</option>
              </select>
            </label>

            <label>
              Income level
              <select
                value={form.incomeLevel}
                onChange={(e) =>
                  update("incomeLevel", e.target.value as FormState["incomeLevel"])
                }
              >
                <option value="low">Below average</option>
                <option value="average">Average</option>
                <option value="high">Above average</option>
              </select>
            </label>

            <label>
              Smoking
              <select
                value={form.smoking}
                onChange={(e) => update("smoking", e.target.value as FormState["smoking"])}
              >
                <option value="never">Never</option>
                <option value="former">Former smoker</option>
                <option value="current">Current smoker</option>
              </select>
            </label>

            <label>
              Alcohol consumption
              <select
                value={form.alcohol}
                onChange={(e) => update("alcohol", e.target.value as FormState["alcohol"])}
              >
                <option value="none">None</option>
                <option value="light">Light (1–7 drinks/week)</option>
                <option value="moderate">Moderate (8–14 drinks/week)</option>
                <option value="heavy">Heavy (15+ drinks/week)</option>
              </select>
            </label>

            <label>
              Reading
              <ZeroFriendlyNumberInput
                min={0}
                max={250}
                step={1}
                value={form.readingHoursPerMonth}
                onChange={(v) => update("readingHoursPerMonth", v)}
              />
              <span className="field-hint">hours per month</span>
            </label>

            <fieldset className="activity-fieldset wide">
              <legend>
                Physical activities — hours per week
                <span className="field-hint"> ({weeklyActivityTotal.toFixed(1)} hrs total)</span>
              </legend>
              <div className="activity-grid">
                {(activityOptions.length
                  ? activityOptions
                  : Object.entries(EMPTY_ACTIVITY_HOURS()).map(([type]) => ({
                      type: type as ActivityType,
                      label: type,
                    }))
                ).map(({ type, label }) => (
                  <label key={type} className="activity-row">
                    <span className="activity-label">{label}</span>
                    <ZeroFriendlyNumberInput
                      min={0}
                      max={40}
                      step={0.5}
                      value={form.activityHours[type]}
                      onChange={(hours) => updateActivityHours(type, hours)}
                    />
                  </label>
                ))}
              </div>
            </fieldset>

            <button type="submit" disabled={loading} className="submit-btn">
              {loading ? "Calculating…" : "Calculate my estimate"}
            </button>
          </form>
          {error && <p className="error">{error}</p>}
        </section>

        <section className="panel stats-panel">
          <h2>
            {countryDetail?.name ?? selectedCountry?.name ?? form.countryCode} snapshot
          </h2>
          {countryDetail ? (
            <div className="stats-grid">
              <Stat label="Avg. life expectancy" value={`${countryDetail.life_expectancy ?? "—"} yrs`} />
              <Stat label="GDP per capita" value={formatMoney(countryDetail.gdp_per_capita_usd)} />
              <Stat
                label="Secondary school enrollment"
                value={
                  countryDetail.school_enrollment_secondary_pct != null
                    ? `${countryDetail.school_enrollment_secondary_pct.toFixed(1)}%`
                    : "—"
                }
              />
              <Stat label="Region" value={countryDetail.region ?? "—"} />
              <Stat
                label="Current weather"
                value={countryDetail.weather_description ?? "—"}
              />
              {countryDetail.weather?.temperature_c != null && (
                <Stat
                  label="Temperature"
                  value={`${countryDetail.weather.temperature_c}°C`}
                />
              )}
              <div className="stat wide">
                <span className="stat-label">Ethnic composition</span>
                <ul className="ethnicity-list">
                  {(countryDetail.ethnicity ?? []).map((row) => (
                    <li key={row.group}>
                      {row.group}: {row.share}%
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <p className="muted">Loading country data…</p>
          )}
        </section>

        {result && (
          <section className="panel result-panel">
            <h2>Your estimate</h2>
            <Countdown targetDate={result.predicted_death_date} />
            <p className="result-date">{formatDate(result.predicted_death_date)}</p>
            <p className="result-range">
              Likely range: {formatDate(result.earliest_death_date)} —{" "}
              {formatDate(result.latest_death_date)}
            </p>
            <div className="result-meta">
              <Stat label="Remaining years (est.)" value={`~${result.remaining_years}`} />
              <Stat
                label="Country baseline"
                value={`${result.life_expectancy_at_birth} yrs (${result.country})`}
              />
              <Stat
                label="Adjusted for you"
                value={`${result.adjusted_life_expectancy} yrs`}
              />
            </div>
            <div className="factors">
              <h3>Factor adjustments (years)</h3>
              <ul>
                {Object.entries(result.factors_applied).map(([key, val]) => (
                  <li key={key}>
                    {key.replace(/_/g, " ")}: {val > 0 ? "+" : ""}
                    {val}
                  </li>
                ))}
              </ul>
            </div>
            <p className="disclaimer">{result.disclaimer}</p>
          </section>
        )}
      </main>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </div>
  );
}
