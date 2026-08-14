// Popup: loads the user's Application Packs from the API, matches one to the
// active tab, and hands it to the page's content script to fill. The popup
// never touches the page's submit button — filling + highlighting only.

const $ = (id) => document.getElementById(id);

const CONTACT_KEYS = ["name", "email", "phone", "location", "linkedin", "company"];
const DEFAULT_API = "http://localhost:8000";

let rows = [];
let chosen = null;
let settings = {};

async function loadSettings() {
  const stored = await chrome.storage.sync.get(["contact", "apiUrl", "apiToken"]);
  settings = {
    contact: stored.contact || {},
    apiUrl: stored.apiUrl || DEFAULT_API,
    apiToken: stored.apiToken || "",
  };
  for (const key of CONTACT_KEYS) $(`c-${key}`).value = settings.contact[key] || "";
  $("c-api").value = settings.apiUrl;
  $("c-token").value = settings.apiToken;
}

async function saveSettings() {
  const contact = {};
  for (const key of CONTACT_KEYS) contact[key] = $(`c-${key}`).value.trim();
  settings = {
    contact,
    apiUrl: $("c-api").value.trim() || DEFAULT_API,
    apiToken: $("c-token").value.trim(),
  };
  await chrome.storage.sync.set(settings);
  $("status").textContent = "Saved.";
  void init();
}

function api(path) {
  const headers = settings.apiToken ? { Authorization: `Bearer ${settings.apiToken}` } : {};
  return fetch(`${settings.apiUrl}${path}`, { headers }).then((res) => {
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  });
}

function choosePack(row, matchedAutomatically) {
  chosen = row;
  $("pack-title").textContent = row.job_title || row.job_id;
  $("pack-company").textContent =
    (row.company || "") + (matchedAutomatically ? " · matched to this page" : "");
  $("fill").disabled = false;
}

async function init() {
  try {
    rows = (await api("/api/v1/me/applications")).filter((r) => r.status !== "withdrawn");
  } catch (e) {
    $("status").textContent =
      "Couldn't reach JobPilot (" + e.message + "). Check the API URL under settings.";
    $("settings").open = true;
    return;
  }
  if (rows.length === 0) {
    $("status").textContent =
      "No Application Packs yet — approve a tailored CV in the JobPilot app first.";
    return;
  }

  $("pack-area").hidden = false;
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const onAts = /greenhouse\.io|lever\.co/.test(tab?.url || "");
  const matched = onAts ? jpMatchPack(tab.url, rows) : null;

  if (matched) {
    $("status").textContent = "Pack matched to this application page:";
    choosePack(matched, true);
  } else {
    $("status").textContent = onAts
      ? "No pack matches this page automatically — pick one:"
      : "Open a Greenhouse or Lever application page, then pick a pack:";
    choosePack(rows[0], false);
  }

  if (rows.length > 1 || !matched) {
    const select = $("pack-select");
    select.hidden = false;
    $("pack-select-label").hidden = false;
    select.innerHTML = "";
    for (const row of rows) {
      const opt = document.createElement("option");
      opt.value = row.job_id;
      opt.textContent = `${row.job_title || row.job_id} — ${row.company || ""}`;
      opt.selected = chosen && row.job_id === chosen.job_id;
      select.appendChild(opt);
    }
    select.onchange = () => {
      const row = rows.find((r) => r.job_id === select.value);
      if (row) choosePack(row, false);
    };
  }

  $("fill").disabled = !onAts;
  if (!onAts) $("fill").textContent = "Open an application page to fill";
}

async function fill() {
  if (!chosen) return;
  $("result").textContent = "Filling…";
  try {
    const pack = await api(`/api/v1/me/applications/${chosen.job_id}/pack`);
    const contact = {
      full_name: settings.contact.name || "",
      email: settings.contact.email || "",
      phone: settings.contact.phone || "",
      location: settings.contact.location || "",
      linkedin: settings.contact.linkedin || "",
      current_company: settings.contact.company || "",
    };
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const result = await chrome.tabs.sendMessage(tab.id, {
      type: "JP_FILL",
      payload: { pack, contact },
    });
    $("result").className = "ok";
    $("result").textContent =
      `Filled ${result.filled} field${result.filled === 1 ? "" : "s"}` +
      (result.attached ? ", CV attached" : "") +
      ". Review the form, then press submit yourself.";
  } catch (e) {
    $("result").className = "warn";
    $("result").textContent =
      "Couldn't fill this page (" + e.message + "). Refresh the page and try again.";
  }
}

$("fill").addEventListener("click", () => void fill());
$("save").addEventListener("click", () => void saveSettings());
void loadSettings().then(init);
