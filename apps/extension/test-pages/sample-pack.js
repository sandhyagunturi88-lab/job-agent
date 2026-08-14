// Sample payload matching what the popup sends the content scripts —
// the same shape the API's /api/v1/me/applications/{job_id}/pack returns.
const JP_SAMPLE_PAYLOAD = {
  pack: {
    job_id: "job-monzo-001",
    job_title: "Senior Python Engineer",
    company: "Monzo Bank",
    apply_url: "https://boards.greenhouse.io/monzo-bank/jobs/123",
    tailored_cv: {
      job_id: "job-monzo-001",
      changes: [],
      full_text:
        "Senior Python engineer, 8 years. Cut API p95 latency 40%. FastAPI, PostgreSQL, AWS.",
      needs_manual_edit: false,
    },
    answers: [
      { field: "notice_period", text: "One month" },
      { field: "salary_expectation", text: "£85,000+ depending on total package" },
      { field: "right_to_work", text: "Yes — full right to work in the UK" },
      { field: "sponsorship", text: "No sponsorship required" },
      {
        field: "why_this_company",
        text: "Monzo's payments platform is exactly where my recent latency and reliability work applies directly.",
      },
    ],
  },
  contact: {
    full_name: "Jane Doe",
    email: "jane@example.com",
    phone: "07700 900123",
    location: "London",
    linkedin: "https://linkedin.com/in/janedoe",
    current_company: "Acme Fintech",
  },
};
