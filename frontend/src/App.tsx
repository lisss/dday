import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  CountryDetail,
  CountrySummary,
  PredictRequest,
  PredictResponse,
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
  activityLevel: PredictRequest["activity_level"];
  smoking: PredictRequest["smoking"];
};

const initialForm: FormState = {
  birthDate: "1990-01-01",
  gender: "other",
  countryCode: "US",
  education: "secondary",
  incomeLevel: "average",
  activityLevel: "moderate",
  smoking: "never",
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
  const [form, setForm] = useState<FormState>(initialForm);
  const [countryDetail, setCountryDetail] = useState<CountryDetail | null>(null);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCountries()
      .then((data) => setCountries(data.countries))
      .catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!form.countryCode) return;
    fetchCountry(form.countryCode)
      .then(setCountryDetail)
      .catch(() => setCountryDetail(null));
  }, [form.countryCode]);

  const selectedCountry = useMemo(
    () => countries.find((c) => c.code === form.countryCode),
    [countries, form.countryCode],
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload: PredictRequest = {
        birth_date: form.birthDate,
        gender: form.gender,
        country_code: form.countryCode,
        education: form.education,
        income_level: form.incomeLevel,
        activity_level: form.activityLevel,
        smoking: form.smoking,
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

  return (
    <div className="page">
      <header className="hero">
        <p className="eyebrow">Statistical life estimator</p>
        <h1>When might you die?</h1>
        <p className="subtitle">
          Uses public data on life expectancy, income, education, ethnicity, and weather
          by country — then adjusts for your profile.
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

            <label>
              Country
              <select
                value={form.countryCode}
                onChange={(e) => update("countryCode", e.target.value)}
              >
                {countries.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.name} ({c.code})
                  </option>
                ))}
                {!countries.length && <option value="US">United States (US)</option>}
              </select>
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
              Physical activity
              <select
                value={form.activityLevel}
                onChange={(e) =>
                  update("activityLevel", e.target.value as FormState["activityLevel"])
                }
              >
                <option value="sedentary">Sedentary</option>
                <option value="moderate">Moderate</option>
                <option value="active">Active</option>
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
                    {key}: {val > 0 ? "+" : ""}
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
