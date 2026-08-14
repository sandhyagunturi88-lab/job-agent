/**
 * Shared TypeScript types for JobPilot UK.
 * Mirrors packages/schemas/jobpilot_schemas/models.py — keep in sync.
 */

export type ContractType =
  | "permanent"
  | "contract"
  | "temporary"
  | "part_time"
  | "internship";

export type JobSource =
  | "adzuna"
  | "reed"
  | "dwp_find_a_job"
  | "greenhouse"
  | "lever"
  | "workable";

export interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  salary_min?: number | null;
  salary_max?: number | null;
  contract_type?: ContractType | null;
  ir35_flag?: boolean | null;
  source: JobSource;
  url: string;
  jd_text: string;
  posted_at: string; // ISO datetime
}

export interface JobMatch {
  job: Job;
  score: number; // 0–100
  matched_skills: string[];
  gaps: string[];
  verdict: string;
}

export interface DismissedJob {
  job_id: string;
  reason: string;
}

export interface PreferenceProfile {
  desired_titles: string[];
  locations: string[];
  min_salary?: number | null;
  contract_types: ContractType[];
  avoid_keywords: string[];
  notes: string[];
}

export interface CVInventoryItem {
  id: string;
  kind: "role" | "achievement" | "skill" | "education" | "certification";
  text: string;
  source_span?: string | null;
}

export interface CVChange {
  section: string;
  before?: string | null;
  after: string;
  evidence_ids: string[];
}

export interface TailoredCV {
  job_id: string;
  changes: CVChange[];
  full_text: string;
  needs_manual_edit: boolean;
}

export interface CopyAnswer {
  field:
    | "notice_period"
    | "salary_expectation"
    | "right_to_work"
    | "sponsorship"
    | "why_this_company";
  text: string;
}

export interface ApplicationPack {
  job_id: string;
  tailored_cv: TailoredCV;
  answers: CopyAnswer[];
  apply_url: string;
}

/** Graph run status streamed over WebSocket. */
export type RunPhase =
  | "retrieve"
  | "llm_rerank"
  | "awaiting_job_picks" // interrupt 1
  | "tailor_cv"
  | "validate_cv"
  | "awaiting_cv_approval" // interrupt 2
  | "build_application_pack"
  | "done";

export interface RunStateUpdate {
  thread_id: string;
  phase: RunPhase;
  interrupt?: unknown; // payload of the pending interrupt, if any
  matches?: JobMatch[];
  tailored_cvs?: TailoredCV[];
  application_packs?: ApplicationPack[];
}
