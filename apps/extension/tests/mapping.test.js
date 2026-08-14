// Pure-logic tests for the autofill mapping (run with `node --test`).
const test = require("node:test");
const assert = require("node:assert/strict");

const {
  jpAnswerField,
  jpYesNo,
  jpSplitName,
  jpMatchPack,
  jpAnswerFor,
} = require("../src/lib/mapping.js");

test("labels map to CopyAnswer fields", () => {
  assert.equal(jpAnswerField("What is your notice period?"), "notice_period");
  assert.equal(jpAnswerField("Salary expectations (GBP)"), "salary_expectation");
  assert.equal(jpAnswerField("Desired compensation"), "salary_expectation");
  assert.equal(jpAnswerField("Do you have the right to work in the UK?"), "right_to_work");
  assert.equal(jpAnswerField("Are you eligible to work in the United Kingdom?"), "right_to_work");
  assert.equal(jpAnswerField("Will you now or in the future require sponsorship?"), "sponsorship");
  assert.equal(jpAnswerField("Do you require visa sponsorship?"), "sponsorship");
  assert.equal(jpAnswerField("Why do you want to work at Monzo?"), "why_this_company");
  assert.equal(jpAnswerField("Cover letter"), "why_this_company");
});

test("unrelated labels map to nothing", () => {
  assert.equal(jpAnswerField("First name"), null);
  assert.equal(jpAnswerField("How did you hear about us?"), null);
  assert.equal(jpAnswerField(""), null);
  assert.equal(jpAnswerField(undefined), null);
});

test("yes/no detection from answer text", () => {
  assert.equal(jpYesNo("Yes — full right to work in the UK"), "yes");
  assert.equal(jpYesNo("No sponsorship required"), "no");
  assert.equal(jpYesNo("One month"), null);
});

test("name splitting", () => {
  assert.deepEqual(jpSplitName("Jane Doe"), { first: "Jane", last: "Doe" });
  assert.deepEqual(jpSplitName("Jane Anne van der Doe"), {
    first: "Jane",
    last: "Anne van der Doe",
  });
  assert.deepEqual(jpSplitName("Cher"), { first: "Cher", last: "" });
  assert.deepEqual(jpSplitName("  "), { first: "", last: "" });
});

const ROWS = [
  {
    job_id: "job-1",
    job_title: "Senior Python Engineer",
    company: "Monzo Bank",
    apply_url: "https://boards.greenhouse.io/monzo-bank/jobs/123",
  },
  {
    job_id: "job-2",
    job_title: "Backend Engineer",
    company: "Starling",
    apply_url: "https://jobs.lever.co/starling/abc-def",
  },
];

test("pack matching: exact url prefix wins", () => {
  const hit = jpMatchPack("https://boards.greenhouse.io/monzo-bank/jobs/123?gh_src=x", ROWS);
  assert.equal(hit.job_id, "job-1");
});

test("pack matching: same host + company slug in path", () => {
  const hit = jpMatchPack("https://jobs.lever.co/starling/other-posting/apply", ROWS);
  assert.equal(hit.job_id, "job-2");
});

test("pack matching: unrelated site matches nothing", () => {
  assert.equal(jpMatchPack("https://example.com/careers", ROWS), null);
  assert.equal(jpMatchPack("not a url", ROWS), null);
});

test("answer lookup", () => {
  const pack = { answers: [{ field: "notice_period", text: "One month" }] };
  assert.equal(jpAnswerFor(pack, "notice_period"), "One month");
  assert.equal(jpAnswerFor(pack, "sponsorship"), null);
  assert.equal(jpAnswerFor(null, "sponsorship"), null);
});
