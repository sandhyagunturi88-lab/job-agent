import { useCallback, useEffect, useState } from "react";
import {
  type BillingStatus,
  devDowngrade,
  devUpgrade,
  getBilling,
  startCheckout,
  startPortal,
} from "../lib/api";

/** Plan + weekly quota status with an honest upgrade/cancel path. */
export default function PlanCard() {
  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    void getBilling()
      .then(setBilling)
      .catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (!billing) return null;
  const pro = billing.limits === null;

  const upgrade = async () => {
    setBusy(true);
    setError(null);
    try {
      const { url } = await startCheckout();
      if (url) {
        window.location.href = url; // Stripe-hosted checkout
      } else {
        await devUpgrade(); // offline dev mode
        refresh();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const manage = async () => {
    setBusy(true);
    setError(null);
    try {
      const { url } = await startPortal();
      if (url) {
        window.location.href = url; // Stripe portal: update card, cancel, invoices
      } else {
        await devDowngrade();
        refresh();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm">
      <div className="flex items-baseline justify-between">
        <h3 className="text-sm font-semibold">
          Plan: {pro ? "Pro" : "Free"}
        </h3>
        {!pro && <span className="text-xs text-slate-500">Pro is {billing.pro_price}</span>}
      </div>

      {pro ? (
        <p className="mt-1 text-sm text-slate-500">
          Unlimited matches and tailored CVs. Cancel anytime — you keep everything you've
          already generated.
        </p>
      ) : (
        <p className="mt-1 text-sm text-slate-500">
          This week: {billing.used.matches} of {billing.limits!.matches} matches ·{" "}
          {billing.used.cvs} of {billing.limits!.cvs} tailored CV
          {billing.limits!.cvs === 1 ? "" : "s"}. Quota resets Monday.
        </p>
      )}

      {error && <p className="mt-2 rounded-lg bg-red-50 p-2 text-xs text-red-700">{error}</p>}

      <button
        onClick={() => void (pro ? manage() : upgrade())}
        disabled={busy}
        className={`mt-3 w-full rounded-xl py-2.5 text-sm font-semibold disabled:opacity-50 ${
          pro ? "bg-slate-100 text-slate-700" : "bg-brand-600 text-white"
        }`}
      >
        {busy
          ? "One moment…"
          : pro
            ? billing.dev_billing
              ? "Switch back to Free (dev)"
              : "Manage or cancel subscription"
            : `Upgrade to Pro — ${billing.pro_price}`}
      </button>
      {!pro && (
        <p className="mt-2 text-center text-xs text-slate-400">
          No trial countdowns, no auto-upgrades — Free stays useful forever.
        </p>
      )}
    </div>
  );
}
