/* ============================================================
   INSUREAI
   COMPLETE FRONTEND APPLICATION
   Flask ML Backend + Local Storage
============================================================ */

"use strict";

/* ============================================================
   1. FORM CONFIGURATION
============================================================ */

const formData = [
  {
    title: "01. Policyholder information",
    description: "Personal details and insurance policy information.",
    fields: [
      {
        name: "months_as_customer",
        label: "Months as customer",
        type: "number",
        placeholder: "Example: 120",
        min: 0,
        integer: true
      },
      {
        name: "age",
        label: "Age",
        type: "number",
        placeholder: "Example: 35",
        min: 0,
        max: 120,
        integer: true
      },
      {
        name: "policy_bind_date",
        label: "Policy bind date",
        type: "date"
      },
      {
        name: "policy_state",
        label: "Policy state",
        type: "select",
        options: ["OH", "IN", "IL"]
      },
      {
        name: "policy_csl",
        label: "Policy CSL",
        type: "select",
        options: ["100/300", "250/500", "500/1000"]
      },
      {
        name: "policy_deductable",
        label: "Policy deductible ($)",
        type: "number",
        min: 0
      },
      {
        name: "policy_annual_premium",
        label: "Annual premium ($)",
        type: "number",
        min: 0,
        step: "any"
      },
      {
        name: "umbrella_limit",
        label: "Umbrella limit ($)",
        type: "number"
      },
      {
        name: "insured_zip",
        label: "Insured ZIP code",
        type: "text",
        placeholder: "Enter ZIP code"
      },
      {
        name: "insured_sex",
        label: "Insured sex",
        type: "select",
        options: ["MALE", "FEMALE"]
      },
      {
        name: "insured_education_level",
        label: "Education level",
        type: "select",
        options: [
          "High School",
          "College",
          "Associate",
          "Masters",
          "MD",
          "JD",
          "PhD"
        ]
      },
      {
        name: "insured_occupation",
        label: "Occupation",
        type: "text",
        placeholder: "Enter occupation"
      },
      {
        name: "insured_hobbies",
        label: "Hobbies",
        type: "text",
        placeholder: "Enter hobbies"
      },
      {
        name: "insured_relationship",
        label: "Relationship",
        type: "select",
        options: [
          "husband",
          "wife",
          "own-child",
          "unmarried",
          "other-relative",
          "not-in-family"
        ]
      },
      {
        name: "capital-gains",
        label: "Capital gains ($)",
        type: "number",
        step: "any"
      },
      {
        name: "capital-loss",
        label: "Capital loss ($)",
        type: "number",
        step: "any"
      }
    ]
  },

  {
    title: "02. Incident information",
    description: "Details about the reported incident and circumstances.",
    fields: [
      {
        name: "incident_date",
        label: "Incident date",
        type: "date"
      },
      {
        name: "incident_type",
        label: "Incident type",
        type: "select",
        options: [
          "Single Vehicle Collision",
          "Multi-vehicle Collision",
          "Parked Car",
          "Vehicle Theft"
        ]
      },
      {
        name: "collision_type",
        label: "Collision type",
        type: "select",
        options: [
          "Front Collision",
          "Rear Collision",
          "Side Collision",
          "?"
        ]
      },
      {
        name: "incident_severity",
        label: "Incident severity",
        type: "select",
        options: [
          "Trivial Damage",
          "Minor Damage",
          "Major Damage",
          "Total Loss"
        ]
      },
      {
        name: "authorities_contacted",
        label: "Authorities contacted",
        type: "select",
        options: [
          "Police",
          "Fire",
          "Ambulance",
          "Other",
          "None"
        ]
      },
      {
        name: "incident_state",
        label: "Incident state",
        type: "select",
        options: ["OH", "IN", "IL"]
      },
      {
        name: "incident_city",
        label: "Incident city",
        type: "text"
      },
      {
        name: "incident_location",
        label: "Incident location",
        type: "text"
      },
      {
        name: "incident_hour_of_the_day",
        label: "Incident hour (0–23)",
        type: "number",
        min: 0,
        max: 23,
        integer: true
      },
      {
        name: "number_of_vehicles_involved",
        label: "Number of vehicles involved",
        type: "number",
        min: 0,
        integer: true
      },
      {
        name: "property_damage",
        label: "Property damage",
        type: "select",
        options: ["YES", "NO", "?"]
      },
      {
        name: "bodily_injuries",
        label: "Bodily injuries",
        type: "number",
        min: 0,
        integer: true
      },
      {
        name: "witnesses",
        label: "Number of witnesses",
        type: "number",
        min: 0,
        integer: true
      },
      {
        name: "police_report_available",
        label: "Police report available",
        type: "select",
        options: ["YES", "NO", "?"]
      }
    ]
  },

  {
    title: "03. Financial information",
    description: "Enter the financial amounts associated with this claim (USD).",
    fields: [
      {
        name: "total_claim_amount",
        label: "Total claim amount ($)",
        type: "number",
        min: 0,
        step: "any"
      },
      {
        name: "injury_claim",
        label: "Injury claim ($)",
        type: "number",
        min: 0,
        step: "any"
      },
      {
        name: "property_claim",
        label: "Property claim ($)",
        type: "number",
        min: 0,
        step: "any"
      },
      {
        name: "vehicle_claim",
        label: "Vehicle claim ($)",
        type: "number",
        min: 0,
        step: "any"
      }
    ]
  },

  {
    title: "04. Vehicle information",
    description: "Details of the vehicle associated with the insurance policy.",
    fields: [
      {
        name: "auto_make",
        label: "Vehicle make",
        type: "text",
        placeholder: "Example: Toyota"
      },
      {
        name: "auto_model",
        label: "Vehicle model",
        type: "text",
        placeholder: "Example: Camry"
      },
      {
        name: "auto_year",
        label: "Vehicle year",
        type: "number",
        min: 1900,
        max: 2100,
        integer: true
      }
    ]
  }
];


/* ============================================================
   2. APPLICATION CONFIGURATION
============================================================ */

const STORAGE_KEY = "insureAI_claim_history";

const API_BASE_URL = (window.INSUREAI_API_BASE ||
  (location.hostname === "localhost" || location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:5000"
    : "https://insureai-backend-ar1y.onrender.com")).replace(/\/+$/, "");
const API_URL = `${API_BASE_URL}/api/analyze`;

let notificationTimer = null;
let confirmedDocumentDetails = null;


/* ============================================================
   3. SAFE HTML HELPER
============================================================ */

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, function (character) {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    };

    return entities[character];
  });
}


/* ============================================================
   4. LOCAL STORAGE
============================================================ */

function getClaimHistory() {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    const claims = JSON.parse(data || "[]");

    return Array.isArray(claims) ? claims : [];

  } catch (error) {
    console.error("Error reading claim history:", error);
    return [];
  }
}


function saveClaimHistory(claims) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(claims));
    return true;

  } catch (error) {
    console.error("Error saving claim history:", error);
    return false;
  }
}


/* ============================================================
   5. FORMATTING HELPERS
============================================================ */

function formatCurrency(amount) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2
  }).format(Number(amount) || 0);
}


function formatDate(value, includeTime = false) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleString(
    "en-IN",
    includeTime
      ? {
          dateStyle: "medium",
          timeStyle: "short"
        }
      : {
          day: "2-digit",
          month: "short",
          year: "numeric"
        }
  );
}


function generateClaimReference() {
  const claims = getClaimHistory();

  let reference;

  do {
    reference = "INS-" + Math.floor(
      100000 + Math.random() * 900000
    );

  } while (
    claims.some(
      claim => claim.claimReference === reference
    )
  );

  return reference;
}


/* ============================================================
   6. NOTIFICATIONS
============================================================ */

function showNotification(message, type = "success") {
  const region = document.getElementById("notificationRegion");

  if (!region) return;

  region.innerHTML = "";

  const notification = document.createElement("div");

  notification.className =
    type === "error"
      ? "notification notification-error"
      : "notification";

  const mark = document.createElement("span");
  mark.className = "notification-mark";
  mark.textContent = type === "error" ? "!" : "✓";

  const text = document.createElement("span");
  text.textContent = message;

  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.setAttribute("aria-label", "Dismiss notification");
  closeButton.textContent = "×";

  closeButton.addEventListener("click", function () {
    notification.remove();
  });

  notification.append(mark, text, closeButton);
  region.appendChild(notification);

  clearTimeout(notificationTimer);

  notificationTimer = setTimeout(function () {
    notification.remove();
  }, 3500);
}


/* ============================================================
   7. NAVIGATION
============================================================ */

function navigateTo(sectionName) {
  const sections = document.querySelectorAll(".content-section");
  const buttons = document.querySelectorAll(".menu-item");

  const target = document.getElementById(sectionName);

  if (!target || !target.classList.contains("content-section")) {
    console.error("Navigation target not found:", sectionName);
    return;
  }

  sections.forEach(function (section) {
    section.classList.toggle("active", section === target);
  });

  buttons.forEach(function (button) {
    button.classList.toggle(
      "active",
      button.dataset.section === sectionName
    );
  });

  const titles = {
    dashboard: "Dashboard",
    "new-claim": "New Claim Analysis",
    results: "Analysis Results",
    history: "Claim History"
  };

  const pageTitle = document.getElementById("pageTitle");

  if (pageTitle) {
    pageTitle.textContent = titles[sectionName] || "InsureAI";
  }

  if (sectionName === "dashboard") {
    updateDashboard();
  }

  if (sectionName === "history") {
    displayClaimHistory();
  }

  closeMobileNavigation();

  window.scrollTo({
    top: 0,
    behavior: "smooth"
  });
}


/* ============================================================
   8. MOBILE NAVIGATION
============================================================ */

function closeMobileNavigation() {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("mobileOverlay");
  const menu = document.getElementById("mobileMenu");

  if (sidebar) {
    sidebar.classList.remove("sidebar-open");
  }

  if (overlay) {
    overlay.classList.remove("visible");
  }

  if (menu) {
    menu.setAttribute("aria-expanded", "false");
  }
}


function initializeNavigation() {
  const menuItems = document.querySelectorAll(".menu-item");

  menuItems.forEach(function (item) {
    item.addEventListener("click", function () {
      navigateTo(item.dataset.section);
    });
  });

  document.querySelectorAll("[data-go]").forEach(function (button) {
    button.addEventListener("click", function (event) {
      event.preventDefault();
      navigateTo(button.dataset.go);
    });
  });

  const mobileMenu = document.getElementById("mobileMenu");
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("mobileOverlay");

  if (mobileMenu && sidebar && overlay) {
    mobileMenu.addEventListener("click", function () {
      const isOpen = sidebar.classList.toggle("sidebar-open");

      overlay.classList.toggle("visible", isOpen);

      mobileMenu.setAttribute(
        "aria-expanded",
        String(isOpen)
      );
    });

    overlay.addEventListener("click", closeMobileNavigation);
  }
}


/* ============================================================
   9. DYNAMIC FORM GENERATION
============================================================ */

function generateForm() {
  const formSections = document.getElementById("formSections");

  if (!formSections) {
    console.error("Form container #formSections not found.");
    return;
  }

  formSections.innerHTML = "";

  formData.forEach(function (section) {
    const sectionElement = document.createElement("section");

    sectionElement.className = "form-section";

    const fieldsHTML = section.fields.map(function (field) {
      const id = escapeHTML(field.name);

      let control = "";

      if (field.type === "select") {
        const options = field.options.map(function (option) {
          return `
            <option value="${escapeHTML(option)}">
              ${escapeHTML(option)}
            </option>
          `;
        }).join("");

        control = `
          <select
            id="${id}"
            name="${id}"
            required
          >
            <option value="">
              Choose ${escapeHTML(field.label.toLowerCase())}
            </option>
            ${options}
          </select>
        `;

      } else {
        const attributes = [];

        if (field.placeholder) {
          attributes.push(
            `placeholder="${escapeHTML(field.placeholder)}"`
          );
        }

        if (field.min !== undefined) {
          attributes.push(`min="${field.min}"`);
        }

        if (field.max !== undefined) {
          attributes.push(`max="${field.max}"`);
        }

        attributes.push(
          `step="${field.step || (field.integer ? "1" : "any")}"`
        );

        control = `
          <input
            type="${escapeHTML(field.type)}"
            id="${id}"
            name="${id}"
            ${attributes.join(" ")}
            required
          >
        `;
      }

      return `
        <div class="form-group">
          <label for="${id}">
            ${escapeHTML(field.label)}
            <span class="required-mark">*</span>
          </label>

          ${control}

          <small class="field-error" aria-live="polite"></small>
        </div>
      `;
    }).join("");

    sectionElement.innerHTML = `
      <div class="form-section-heading">
        <span class="section-index">
          ${escapeHTML(section.title.slice(0, 2))}
        </span>

        <div>
          <h3>${escapeHTML(section.title.slice(4))}</h3>
          <p>${escapeHTML(section.description)}</p>
        </div>
      </div>

      <div class="form-grid">
        ${fieldsHTML}
      </div>
    `;

    formSections.appendChild(sectionElement);
  });

  updateFormProgress();

  console.log("Claim form generated successfully.");
}


/* ============================================================
   10. FORM PROGRESS
============================================================ */

function updateFormProgress() {
  const claimForm = document.getElementById("claimForm");

  if (!claimForm) return;

  const fields = Array.from(
    claimForm.querySelectorAll(
      "#formSections input, #formSections select"
    )
  );

  const completed = fields.filter(function (field) {
    return String(field.value).trim() !== "";
  }).length;

  const total = fields.length;

  const percentage = total
    ? Math.round((completed / total) * 100)
    : 0;

  const bar = document.getElementById("formProgressBar");
  const text = document.getElementById("formProgressText");
  const details = document.getElementById("formProgressDetails");
  const track = document.getElementById("formProgressTrack");

  if (bar) {
    bar.style.width = percentage + "%";
  }

  if (text) {
    text.textContent = percentage + "%";
  }

  if (details) {
    details.textContent =
      `${completed} of ${total} fields completed`;
  }

  if (track) {
    track.setAttribute("aria-valuenow", String(percentage));
  }
}


/* ============================================================
   11. CLEAR FORM ERRORS
============================================================ */

function clearFormErrors() {
  const claimForm = document.getElementById("claimForm");

  if (!claimForm) return;

  claimForm.querySelectorAll(".input-invalid").forEach(function (field) {
    field.classList.remove("input-invalid");
  });

  claimForm.querySelectorAll(".field-error").forEach(function (error) {
    error.textContent = "";
  });
}


/* ============================================================
   12. FORM VALIDATION
============================================================ */

function validateClaimForm() {
  const claimForm = document.getElementById("claimForm");

  if (!claimForm) return false;

  const fields = Array.from(
    claimForm.querySelectorAll(
      "#formSections input, #formSections select"
    )
  );

  for (const field of fields) {
    const group = field.closest(".form-group");
    const error = group?.querySelector(".field-error");

    if (error) {
      error.textContent = "";
    }

    field.classList.remove("input-invalid");

    if (!String(field.value).trim()) {
      if (error) {
        error.textContent = "This field is required.";
      }

      field.classList.add("input-invalid");
      field.focus();

      showNotification(
        "Please complete all required fields.",
        "error"
      );

      return false;
    }

    if (field.type === "number") {
      const value = Number(field.value);

      if (!Number.isFinite(value)) {
        if (error) {
          error.textContent = "Enter a valid number.";
        }

        field.classList.add("input-invalid");
        field.focus();

        return false;
      }

      if (field.min !== "" && value < Number(field.min)) {
        if (error) {
          error.textContent =
            `Value must be at least ${field.min}.`;
        }

        field.classList.add("input-invalid");
        field.focus();

        return false;
      }

      if (field.max !== "" && value > Number(field.max)) {
        if (error) {
          error.textContent =
            `Value cannot exceed ${field.max}.`;
        }

        field.classList.add("input-invalid");
        field.focus();

        return false;
      }

      if (field.step === "1" && !Number.isInteger(value)) {
        if (error) {
          error.textContent = "Enter a whole number.";
        }

        field.classList.add("input-invalid");
        field.focus();

        return false;
      }
    }
  }

  const incidentDate =
    claimForm.elements.namedItem("incident_date")?.value;

  const policyDate =
    claimForm.elements.namedItem("policy_bind_date")?.value;

  if (
    incidentDate &&
    policyDate &&
    new Date(incidentDate) < new Date(policyDate)
  ) {
    const field =
      claimForm.elements.namedItem("incident_date");

    const error = field
      ?.closest(".form-group")
      ?.querySelector(".field-error");

    if (error) {
      error.textContent =
        "Incident date cannot be earlier than the policy bind date.";
    }

    field?.classList.add("input-invalid");
    field?.focus();

    showNotification(
      "Please check the incident and policy dates.",
      "error"
    );

    return false;
  }

  return true;
}


/* ============================================================
   13. COLLECT FORM DATA
============================================================ */

function collectClaimData() {
  const claimForm = document.getElementById("claimForm");

  const claim = {};

  new FormData(claimForm).forEach(function (value, key) {
    claim[key] = String(value).trim();
  });

  return claim;
}


/* ============================================================
   14. DISPLAY CLAIM RESULTS
============================================================ */

function displayClaimResults(claim) {
  const resultsCard = document.getElementById("resultsCard");

  if (!resultsCard || !claim) return;

  const analysis = claim.analysis || null;

  const details = [
    ["Claim reference", claim.claimReference],
    ["Submission date", formatDate(claim.submissionDate, true)],
    ["Policyholder age", claim.age],
    ["Months as customer", claim.months_as_customer],
    ["Policy state", claim.policy_state],
    ["Policy CSL", claim.policy_csl],
    ["Incident type", claim.incident_type],
    ["Collision type", claim.collision_type],
    ["Incident severity", claim.incident_severity],
    ["Incident date", formatDate(claim.incident_date)],
    [
      "Incident location",
      [claim.incident_city, claim.incident_state]
        .filter(Boolean)
        .join(", ")
    ],
    ["Vehicles involved", claim.number_of_vehicles_involved],
    ["Claim amount", formatCurrency(claim.total_claim_amount)],
    ["Injury claim", formatCurrency(claim.injury_claim)],
    ["Property claim", formatCurrency(claim.property_claim)],
    ["Vehicle claim", formatCurrency(claim.vehicle_claim)],
    [
      "Vehicle",
      [claim.auto_year, claim.auto_make, claim.auto_model]
        .filter(Boolean)
        .join(" ")
    ],
    ["Current status", claim.status || "Pending Analysis"]
  ];

  const detailHTML = details.map(function ([label, value]) {
    return `
      <div class="analysis-item">
        <span>${escapeHTML(label)}</span>
        <strong>${escapeHTML(value || "—")}</strong>
      </div>
    `;
  }).join("");

  let analysisHTML = "";

  if (analysis) {
    analysisHTML = `
      <div class="report-section-title">
        <h3>Machine learning assessment</h3>
        <span>MODEL PREDICTIONS</span>
      </div>

      <div class="analysis-grid">
        <div class="analysis-item">
          <span>Fraud probability</span>
          <strong>${escapeHTML(analysis.fraud_probability)}%</strong>
        </div>

        <div class="analysis-item">
          <span>Fraud risk level</span>
          <strong>${escapeHTML(analysis.risk_band || analysis.risk_state)}</strong>
        </div>

        <div class="analysis-item">
          <span>Expected claim cost</span>
          <strong>${escapeHTML(formatCurrency(analysis.expected_cost))}</strong>
        </div>

        <div class="analysis-item">
          <span>Claim complexity</span>
          <strong>${escapeHTML(analysis.complexity)}</strong>
        </div>

        <div class="analysis-item">
          <span>Recommended action</span>
          <strong>${escapeHTML(analysis.decision)}</strong>
        </div>
      </div>

      <div class="report-notice">
        <div class="notice-icon">i</div>
        <div>
          <h3>Assessment indicators and review notes</h3>
          <ul>${(analysis.indicators || []).map(item => `<li>${escapeHTML(item)}</li>`).join("")}</ul>
          <ul>${(analysis.explanations || []).map(item => `<li>${escapeHTML(item)}</li>`).join("")}</ul>
          <p>${analysis.manual_verification_required ? "Manual verification is recommended." : "No manual review was triggered by the configured model rules; verify claim documents through normal review."} Missing OCR fields are not fraud findings.</p>
        </div>
      </div>

      ${claim.document_details ? `
      <div class="report-section-title"><h3>Document details captured by OCR</h3><span>UNVERIFIED</span></div>
      <div class="analysis-grid">${Object.entries(claim.document_details).filter(([, value]) => value).map(([key, value]) => `
        <div class="analysis-item"><span>${escapeHTML(key.replaceAll("_", " "))}</span><strong>${escapeHTML(value)}</strong></div>
      `).join("") || '<p>No values were recognized; enter and verify claim details manually.</p>'}</div>
      ` : ""}

      <div class="report-notice">
        <div class="notice-icon">✓</div>
        <div>
          <h3>Claim analysis completed</h3>
          <p>
            The trained fraud detection model estimated the fraud
            probability, the cost model predicted the expected claim
            cost, and the decision system generated a recommendation.
            This is an automated assessment, not a final insurance
            decision.
          </p>
        </div>
      </div>
    `;

  } else {
    analysisHTML = `
      <div class="report-notice">
        <div class="notice-icon">i</div>
        <div>
          <h3>Machine learning assessment unavailable</h3>
          <p>
            This claim does not contain a completed model assessment.
            Submit a new claim while the Flask backend is running
            to generate predictions.
          </p>
        </div>
      </div>
    `;
  }

  const statusClass = "pending-badge";

  resultsCard.innerHTML = `
    <article class="analysis-report">

      <div class="report-topline">
        <span class="eyebrow">INSUREAI / CLAIM REPORT</span>

        <span class="status-badge ${statusClass}">
          ${escapeHTML(claim.status || "Pending Analysis")}
        </span>
      </div>

      <div class="report-header">
        <div>
          <span class="report-label">CLAIM ASSESSMENT REPORT</span>

          <h2>Claim overview</h2>

          <p>
            Reference
            <strong>${escapeHTML(claim.claimReference)}</strong>
          </p>
        </div>

        <div class="report-reference-mark">
          IA<span>REPORT</span>
        </div>
      </div>

      <div class="report-summary">
        <div>
          <span>Submitted claim amount</span>
          <strong>${escapeHTML(formatCurrency(claim.total_claim_amount))}</strong>
        </div>

        <div>
          <span>Incident category</span>
          <strong>${escapeHTML(claim.incident_type)}</strong>
        </div>

        <div>
          <span>Submitted on</span>
          <strong>${escapeHTML(formatDate(claim.submissionDate, true))}</strong>
        </div>
      </div>

      <div class="report-section-title">
        <h3>Submitted claim information</h3>
        <span>RECORDED DETAILS</span>
      </div>

      <div class="analysis-grid">
        ${detailHTML}
      </div>

      ${analysisHTML}

      <div class="report-actions">
        <button
          type="button"
          class="secondary-button"
          id="printReport"
        >
          Print report
        </button>

        <button
          type="button"
          class="primary-button"
          id="newClaimButton"
        >
          Create another claim <span>→</span>
        </button>
      </div>

    </article>
  `;

  document.getElementById("printReport")?.addEventListener(
    "click",
    function () {
      window.print();
    }
  );

  document.getElementById("newClaimButton")?.addEventListener(
    "click",
    function () {
      const claimForm = document.getElementById("claimForm");

      claimForm?.reset();

      clearFormErrors();
      updateFormProgress();

      navigateTo("new-claim");
    }
  );
}


/* ============================================================
   15. FORM SUBMISSION AND ML BACKEND INTEGRATION
============================================================ */

function initializeClaimForm() {
  const claimForm = document.getElementById("claimForm");

  if (!claimForm) return;

  claimForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    if (!validateClaimForm()) return;

    const submitButton = claimForm.querySelector(
      'button[type="submit"], input[type="submit"]'
    );

    const originalButtonText = submitButton
      ? submitButton.textContent
      : "";

    try {
      // Prevent duplicate submissions
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Analyzing claim...";
      }

      showNotification(
        "Sending claim to the machine learning models..."
      );

      // Collect form information
      const claim = collectClaimData();
      if (confirmedDocumentDetails) {
        claim.document_details = confirmedDocumentDetails;
      }

      // Send claim data to Flask backend
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(claim)
      });

      const result = await response.json();

      // Handle backend errors
      if (!response.ok || result.status !== "success") {
        throw new Error(
          result.message || "Claim analysis failed."
        );
      }

      // Attach ML predictions to the claim
      claim.claimReference = generateClaimReference();
      claim.submissionDate = new Date().toISOString();

      claim.analysis = result;
      claim.status = result.decision;

      // Save analyzed claim in browser storage
      const claims = getClaimHistory();

      claims.unshift(claim);

      if (!saveClaimHistory(claims)) {
        throw new Error(
          "Analysis completed, but the claim could not be saved."
        );
      }

      // Update application sections
      displayClaimResults(claim);
      updateDashboard();
      displayClaimHistory();

      // Open results page
      navigateTo("results");

      showNotification(
        "Claim analyzed successfully!"
      );

      // Reset form after successful analysis
      claimForm.reset();
      document.getElementById("removeOcrFile")?.click();

      clearFormErrors();
      updateFormProgress();

    } catch (error) {
      console.error("Claim submission error:", error);

      const errorMessage = String(error.message || "");

      showNotification(
        errorMessage.includes("Failed to fetch")
          ? "Cannot connect to Flask. Make sure the backend is running."
          : errorMessage,
        "error"
      );

    } finally {
      // Restore submit button
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = originalButtonText;
      }
    }
  });

  const resetButton = document.getElementById("resetForm");

  if (resetButton) {
    resetButton.addEventListener("click", function () {
      claimForm.reset();
      document.getElementById("removeOcrFile")?.click();

      clearFormErrors();
      updateFormProgress();

      showNotification("Form has been reset.");
    });
  }

  const formSections = document.getElementById("formSections");

  if (formSections) {
    formSections.addEventListener("input", function () {
      updateFormProgress();
    });

    formSections.addEventListener("change", function () {
      updateFormProgress();
    });
  }
}

function initializeClaimOcr() {
  const input = document.getElementById("claimDocument");
  const zone = document.getElementById("ocrDropzone");
  const extract = document.getElementById("extractOcr");
  const preview = document.getElementById("ocrFilePreview");
  const remove = document.getElementById("removeOcrFile");
  const message = document.getElementById("ocrMessage");
  const review = document.getElementById("ocrReview");
  let resultData = null;
  let previewUrl = null;
  if (!input) return;

  const setFile = file => {
    review.hidden = true;
    resultData = null;
    confirmedDocumentDetails = null;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
    message.textContent = "";
    if (!file) {
      input.value = ""; preview.hidden = true; remove.hidden = true; extract.disabled = true; return;
    }
    const allowed = ["image/jpeg", "image/png", "application/pdf"];
    if (!allowed.includes(file.type) || file.size > 12 * 1024 * 1024) {
      message.textContent = file.size > 12 * 1024 * 1024 ? "File exceeds the 12 MB limit." : "Choose a JPG, PNG, or PDF file.";
      message.className = "ocr-message error"; input.value = ""; return;
    }
    previewUrl = URL.createObjectURL(file);
    preview.innerHTML = file.type === "application/pdf"
      ? `<div class="pdf-preview">PDF</div><div><strong>${escapeHTML(file.name)}</strong><span>${(file.size / 1024 / 1024).toFixed(2)} MB · document ready</span></div>`
      : `<img src="${previewUrl}" alt="Selected claim document preview"><div><strong>${escapeHTML(file.name)}</strong><span>${(file.size / 1024 / 1024).toFixed(2)} MB · image ready</span></div>`;
    preview.hidden = false; remove.hidden = false; extract.disabled = false;
    message.className = "ocr-message";
  };
  input.addEventListener("change", () => setFile(input.files[0]));
  remove.addEventListener("click", () => setFile(null));
  ["dragenter", "dragover"].forEach(name => zone.addEventListener(name, e => { e.preventDefault(); zone.classList.add("dragging"); }));
  ["dragleave", "drop"].forEach(name => zone.addEventListener(name, e => { e.preventDefault(); zone.classList.remove("dragging"); }));
  zone.addEventListener("drop", e => { if (e.dataTransfer.files[0]) { input.files = e.dataTransfer.files; setFile(input.files[0]); } });
  extract.addEventListener("click", async () => {
    const file = input.files[0]; if (!file) return;
    const progress = document.getElementById("ocrProgress");
    progress.hidden = false; extract.disabled = true; remove.disabled = true;
    message.textContent = ""; review.hidden = true;
    const bar = document.getElementById("ocrProgressBar");
    try {
      const body = new FormData(); body.append("file", file);
      const data = await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", `${API_BASE_URL}/api/claims/ocr`);
        xhr.upload.onprogress = event => {
          if (!event.lengthComputable) return;
          bar.style.width = `${Math.max(5, Math.round(event.loaded / event.total * 60))}%`;
          document.getElementById("ocrProgressText").textContent = `Uploading document… ${Math.round(event.loaded / event.total * 100)}%`;
        };
        xhr.upload.onload = () => {
          bar.style.width = "68%";
          document.getElementById("ocrProgressText").textContent = "Upload complete · extracting text…";
        };
        xhr.onerror = () => reject(new Error("Failed to fetch"));
        xhr.onload = () => {
          let payload;
          try { payload = JSON.parse(xhr.responseText); } catch { reject(new Error("OCR service returned an invalid response.")); return; }
          if (xhr.status < 200 || xhr.status >= 300 || payload.status !== "success") reject(new Error(payload.message || "OCR processing failed."));
          else resolve(payload);
        };
        xhr.send(body);
      });
      resultData = data;
      document.getElementById("ocrRawText").textContent = data.extracted_text;
      const labels = {claimant_name:"Claimant / patient name", policy_number:"Policy number", claim_number:"Claim number", hospital_workshop_name:"Hospital / workshop", invoice_number:"Invoice / bill number", incident_date:"Date of incident", treatment_repair_date:"Date of treatment / repair", claim_amount:"Claim amount", total_bill_amount:"Total bill amount", description_of_incident:"Incident description", contact_information:"Contact information"};
      document.getElementById("ocrFields").innerHTML = Object.entries(data.claim_information).map(([key, value]) => `<label class="ocr-field"><span>${labels[key] || key}<small class="${value == null ? "manual-origin" : "auto-origin"}">${value == null ? "Needs manual entry" : "OCR detected · verify"}</small></span><input data-ocr-field="${key}" value="${escapeHTML(value ?? "")}" placeholder="Not found · enter manually"></label>`).join("");
      review.hidden = false; bar.style.width = "100%";
      message.textContent = `Text extracted from ${data.pages_processed} page(s). Review all values before applying.`;
      message.className = "ocr-message success";
    } catch (error) {
      message.textContent = error.message.includes("Failed to fetch") ? "Could not reach the OCR service. Confirm the backend is running and supports this endpoint." : error.message;
      message.className = "ocr-message error";
    } finally {
      setTimeout(() => { progress.hidden = true; bar.style.width = "0"; }, 500);
      extract.disabled = false; remove.disabled = false;
    }
  });
  document.getElementById("applyOcr").addEventListener("click", () => {
    if (!resultData) return;
    const fields = Object.fromEntries([...document.querySelectorAll("[data-ocr-field]")].map(el => [el.dataset.ocrField, el.value.trim()]));
    confirmedDocumentDetails = fields;
    const mapping = {incident_date:"incident_date"};
    Object.entries(mapping).forEach(([source, target]) => {
      const value = fields[source]; if (!value) return;
      const control = document.querySelector(`#claimForm [name="${target}"]`);
      if (control && (!control.value || source !== "claim_amount")) control.value = value;
    });
    const amount = fields.claim_amount || fields.total_bill_amount;
    const amountControl = document.querySelector('#claimForm [name="total_claim_amount"]');
    if (amount && amountControl) amountControl.value = amount;
    updateFormProgress();
    document.getElementById("formSections").scrollIntoView({behavior:"smooth", block:"start"});
    showNotification("Reviewed OCR details applied. Complete the remaining required claim fields.");
  });
}


/* ============================================================
   16. CLAIM HISTORY DISPLAY
============================================================ */

function displayClaimHistory(claimList = null) {
  const historyTableBody =
    document.getElementById("historyTableBody");

  const historyTotal =
    document.getElementById("historyTotal");

  if (!historyTableBody) return;

  const claims = claimList || getClaimHistory();

  if (historyTotal) {
    historyTotal.textContent = claims.length;
  }

  if (claims.length === 0) {
    historyTableBody.innerHTML = `
      <tr>
        <td colspan="6" class="empty-cell">
          No claim records found.
        </td>
      </tr>
    `;

    return;
  }

  historyTableBody.innerHTML = claims.map(function (claim) {
    return `
      <tr>
        <td>${escapeHTML(claim.claimReference)}</td>

        <td>${escapeHTML(claim.incident_type)}</td>

        <td>${escapeHTML(formatCurrency(claim.total_claim_amount))}</td>

        <td>${escapeHTML(formatDate(claim.submissionDate))}</td>

        <td>
          <span class="status-badge pending-badge">
            ${escapeHTML(claim.status || "Pending Analysis")}
          </span>
        </td>

        <td>
          <button
            type="button"
            class="table-action"
            data-action="view"
            data-reference="${escapeHTML(claim.claimReference)}"
          >
            View
          </button>

          <button
            type="button"
            class="table-action"
            data-action="delete"
            data-reference="${escapeHTML(claim.claimReference)}"
          >
            Delete
          </button>
        </td>
      </tr>
    `;
  }).join("");
}


/* ============================================================
   17. CLAIM HISTORY SEARCH
============================================================ */

function initializeHistorySearch() {
  const historySearch =
    document.getElementById("historySearch");

  if (!historySearch) return;

  historySearch.addEventListener("input", function () {
    const searchValue = this.value.toLowerCase().trim();

    const filteredClaims = getClaimHistory().filter(function (claim) {
      const searchableValues = [
        claim.claimReference,
        claim.incident_type,
        claim.incident_city,
        claim.status
      ];

      return searchableValues.some(function (value) {
        return String(value || "")
          .toLowerCase()
          .includes(searchValue);
      });
    });

    displayClaimHistory(filteredClaims);
  });
}


/* ============================================================
   18. VIEW AND DELETE CLAIMS
============================================================ */

function initializeHistoryActions() {
  const historyTableBody =
    document.getElementById("historyTableBody");

  if (!historyTableBody) return;

  historyTableBody.addEventListener("click", function (event) {
    const button = event.target.closest("[data-action]");

    if (!button) return;

    const action = button.dataset.action;
    const reference = button.dataset.reference;

    const claims = getClaimHistory();

    const claim = claims.find(function (item) {
      return item.claimReference === reference;
    });

    if (!claim) return;

    if (action === "view") {
      displayClaimResults(claim);
      navigateTo("results");
    }

    if (action === "delete") {
      const confirmed = window.confirm(
        "Are you sure you want to delete this claim?"
      );

      if (!confirmed) return;

      const updatedClaims = claims.filter(function (item) {
        return item.claimReference !== reference;
      });

      if (!saveClaimHistory(updatedClaims)) {
        showNotification(
          "Unable to delete the claim.",
          "error"
        );

        return;
      }

      displayClaimHistory();
      updateDashboard();

      showNotification("Claim deleted successfully.");
    }
  });
}


/* ============================================================
   19. EXPORT CLAIM HISTORY AS CSV
============================================================ */

function initializeExport() {
  const exportButton =
    document.getElementById("exportClaims");

  if (!exportButton) return;

  exportButton.addEventListener("click", function () {
    const claims = getClaimHistory();

    if (claims.length === 0) {
      showNotification(
        "There are no claims to export.",
        "error"
      );

      return;
    }

    const headers = Object.keys(claims[0]);

    const rows = [
      headers.join(","),
      ...claims.map(function (claim) {
        return headers.map(function (header) {
          const value = String(claim[header] ?? "");

          return `"${value.replace(/"/g, '""')}"`;
        }).join(",");
      })
    ];

    const csvContent = "\uFEFF" + rows.join("\n");

    const blob = new Blob([csvContent], {
      type: "text/csv;charset=utf-8;"
    });

    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");

    link.href = url;
    link.download = "InsureAI_Claim_History.csv";

    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);

    showNotification(
      "Claim history exported successfully."
    );
  });
}


/* ============================================================
   20. DASHBOARD UPDATE
============================================================ */

function updateDashboard() {
  const claims = getClaimHistory();

  const totalClaims =
    document.getElementById("totalClaims");

  const pendingClaims =
    document.getElementById("pendingClaims");

  const totalClaimValue =
    document.getElementById("totalClaimValue");

  const latestSubmission =
    document.getElementById("latestSubmission");

  const recentClaimsBody =
    document.getElementById("recentClaimsBody");

  if (totalClaims) {
    totalClaims.textContent = claims.length;
  }

  if (pendingClaims) {
    const pending = claims.filter(function (claim) {
      return claim.status === "Pending Analysis";
    }).length;

    pendingClaims.textContent = pending;
  }

  if (totalClaimValue) {
    const total = claims.reduce(function (sum, claim) {
      return sum + (Number(claim.total_claim_amount) || 0);
    }, 0);

    totalClaimValue.textContent = formatCurrency(total);
  }

  if (latestSubmission) {
    latestSubmission.textContent = claims.length
      ? formatDate(claims[0].submissionDate)
      : "No submissions yet";
  }

  if (!recentClaimsBody) return;

  const recentClaims = claims.slice(0, 5);

  if (recentClaims.length === 0) {
    recentClaimsBody.innerHTML = `
      <tr>
        <td colspan="6" class="empty-cell">
          No recent claims yet. Your submitted claims will appear here.
        </td>
      </tr>
    `;

    return;
  }

  recentClaimsBody.innerHTML = recentClaims.map(function (claim) {
    return `
      <tr>
        <td>${escapeHTML(claim.claimReference)}</td>

        <td>${escapeHTML(claim.incident_type)}</td>

        <td>${escapeHTML(formatCurrency(claim.total_claim_amount))}</td>

        <td>${escapeHTML(formatDate(claim.submissionDate))}</td>

        <td>
          <span class="status-badge pending-badge">
            ${escapeHTML(claim.status || "Pending Analysis")}
          </span>
        </td>

        <td>
          <button
            type="button"
            class="table-action"
            data-recent-reference="${escapeHTML(claim.claimReference)}"
          >
            View
          </button>
        </td>
      </tr>
    `;
  }).join("");
}


/* ============================================================
   21. RECENT CLAIM VIEW
============================================================ */

function initializeRecentClaims() {
  const recentClaimsBody =
    document.getElementById("recentClaimsBody");

  if (!recentClaimsBody) return;

  recentClaimsBody.addEventListener("click", function (event) {
    const button = event.target.closest("[data-recent-reference]");

    if (!button) return;

    const reference = button.dataset.recentReference;

    const claim = getClaimHistory().find(function (item) {
      return item.claimReference === reference;
    });

    if (!claim) return;

    displayClaimResults(claim);
    navigateTo("results");
  });
}


/* ============================================================
   22. APPLICATION INITIALIZATION
============================================================ */

function initializeInsureAI() {
  console.log("Initializing InsureAI...");

  try {
    initializeNavigation();

    generateForm();

    initializeClaimForm();
    initializeClaimOcr();

    initializeHistorySearch();

    initializeHistoryActions();

    initializeExport();

    initializeRecentClaims();

    updateDashboard();

    displayClaimHistory();

    updateFormProgress();

    console.log("InsureAI initialized successfully.");

  } catch (error) {
    console.error("InsureAI initialization error:", error);

    showNotification(
      "Something went wrong while loading the application. Check the browser console.",
      "error"
    );
  }
}


/* ============================================================
   23. START APPLICATION
============================================================ */

if (document.readyState === "loading") {
  document.addEventListener(
    "DOMContentLoaded",
    initializeInsureAI
  );

} else {
  initializeInsureAI();
}

