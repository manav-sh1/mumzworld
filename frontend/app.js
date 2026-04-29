/* ═══════════════════════════════════════════════════════════════════
   Mumzworld Gift Finder — Application Logic
   ═══════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  // ── State ────────────────────────────────────────────────────────
  let currentLang = "en";
  let lastResponse = null;

  // ── i18n Strings ─────────────────────────────────────────────────
  const i18n = {
    en: {
      title: "Mumzworld Gift Finder",
      subtitle: "AI-powered baby gift recommendations",
      searchLabel: "Describe the gift you're looking for...",
      placeholder:
        'e.g. thoughtful gift for a friend with a 6-month-old, under 200 AED',
      btnText: "Find Gifts",
      examplesLabel: "Try:",
      resultsHeading: "Recommended Gifts",
      toggleLang: "العربية",
      confidence: { high: "High Match", medium: "Medium Match", low: "Low Match" },
      errorGeneric: "Something went wrong. Please try again.",
      errorEmpty: "Please enter a gift query.",
    },
    ar: {
      title: "مُمزورلد — مساعد الهدايا",
      subtitle: "توصيات هدايا ذكية للأطفال",
      searchLabel: "صِف الهدية التي تبحث عنها...",
      placeholder:
        "مثال: هدية لصديقتي عندها طفل عمره 6 أشهر، الميزانية 200 درهم",
      btnText: "ابحث عن هدايا",
      examplesLabel: "جرّب:",
      resultsHeading: "الهدايا المقترحة",
      toggleLang: "English",
      confidence: { high: "تطابق عالي", medium: "تطابق متوسط", low: "تطابق منخفض" },
      errorGeneric: "حدث خطأ. يرجى المحاولة مرة أخرى.",
      errorEmpty: "يرجى إدخال وصف للهدية المطلوبة.",
    },
  };

  // ── DOM Refs ─────────────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);
  const root = document.documentElement;

  const elTitle = $("app-title");
  const elSubtitle = $("app-subtitle");
  const elSearchLabel = $("search-label");
  const elInput = $("query-input");
  const elBtn = $("search-btn");
  const elBtnText = $("btn-text");
  const elBtnSpinner = $("btn-spinner");
  const elExamplesLabel = $("examples-label");
  const elLangToggle = $("lang-toggle");
  const elLangText = elLangToggle.querySelector(".lang-toggle-text");
  const elMessagesArea = $("messages-area");
  const elMessageCard = $("message-card");
  const elMessageIcon = $("message-icon");
  const elMessageText = $("message-text");
  const elResultsArea = $("results-area");
  const elResultsHeading = $("results-heading");
  const elResultsGrid = $("results-grid");
  const cardTemplate = $("card-template");

  // ── Language Toggle ──────────────────────────────────────────────
  function applyLanguage(lang) {
    currentLang = lang;
    const t = i18n[lang];
    root.setAttribute("dir", lang === "ar" ? "rtl" : "ltr");
    root.setAttribute("lang", lang);

    elTitle.textContent = t.title;
    elSubtitle.textContent = t.subtitle;
    elSearchLabel.textContent = t.searchLabel;
    elInput.setAttribute("placeholder", t.placeholder);
    elBtnText.textContent = t.btnText;
    elExamplesLabel.textContent = t.examplesLabel;
    elLangText.textContent = t.toggleLang;
    elResultsHeading.textContent = t.resultsHeading;

    // Re-render results if we have any
    if (lastResponse) {
      renderResponse(lastResponse);
    }
  }

  elLangToggle.addEventListener("click", () => {
    applyLanguage(currentLang === "en" ? "ar" : "en");
  });

  // ── Example Chips ────────────────────────────────────────────────
  document.querySelectorAll(".example-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      elInput.value = chip.dataset.query;
      elInput.focus();
    });
  });

  // ── Search ───────────────────────────────────────────────────────
  elBtn.addEventListener("click", handleSearch);
  elInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleSearch();
  });

  async function handleSearch() {
    const query = elInput.value.trim();
    if (!query) {
      showMessage("⚠️", i18n[currentLang].errorEmpty, "message-clarification");
      return;
    }

    setLoading(true);
    hideAll();

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 65000);

    try {
      const res = await fetch("/api/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!res.ok) {
        const err = await res.json().catch(() => null);
        const detail =
          err?.detail?.error || err?.detail || i18n[currentLang].errorGeneric;
        showMessage("❌", detail, "message-error");
        return;
      }

      const data = await res.json();
      lastResponse = data;
      renderResponse(data);
    } catch (err) {
      clearTimeout(timeoutId);
      console.error(err);
      const msg = err.name === "AbortError"
        ? (currentLang === "ar" ? "انتهت مهلة الطلب. يرجى المحاولة مرة أخرى." : "Request timed out. Please try again.")
        : i18n[currentLang].errorGeneric;
      showMessage("❌", msg, "message-error");
    } finally {
      setLoading(false);
    }
  }

  // ── Render Logic ─────────────────────────────────────────────────
  function renderResponse(data) {
    hideAll();

    // Out of scope
    if (data.out_of_scope) {
      const reason = data.refusal_reason
        || (currentLang === "ar"
          ? "هذا الطلب خارج نطاق ما يمكنني المساعدة فيه."
          : "This query is outside what I can help with.");
      showMessage("🚫", reason, "message-refusal");
      return;
    }

    // Clarification needed
    if (data.clarification_needed) {
      showMessage("💬", data.clarification_needed, "message-clarification");
      // Still render any recommendations below
    }

    // No recommendations
    const recs = Array.isArray(data.recommendations) ? data.recommendations : [];
    if (recs.length === 0) {
      if (!data.clarification_needed) {
        showMessage(
          "🔍",
          currentLang === "ar"
            ? "لم أجد منتجات مناسبة لطلبك. جرّب تعديل الميزانية أو العمر."
            : "No matching products found. Try adjusting budget or age.",
          "message-clarification"
        );
      }
      return;
    }

    // Sort by confidence: high → medium → low
    const confidenceOrder = { high: 0, medium: 1, low: 2 };
    recs.sort((a, b) => (confidenceOrder[a.confidence] ?? 3) - (confidenceOrder[b.confidence] ?? 3));

    // Render cards
    elResultsGrid.innerHTML = "";
    recs.forEach((rec) => {
      const card = renderCard(rec);
      elResultsGrid.appendChild(card);
    });

    elResultsArea.hidden = false;
  }

  function renderCard(rec) {
    const fragment = cardTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".gift-card");

    // Confidence badge
    const badge = card.querySelector(".confidence-badge");
    badge.dataset.confidence = rec.confidence;
    badge.querySelector(".badge-text").textContent =
      i18n[currentLang].confidence[rec.confidence] || rec.confidence;

    // Price
    const price = card.querySelector(".card-price");
    price.textContent = rec.price_aed != null ? `AED ${rec.price_aed}` : "—";

    // Name
    card.querySelector(".card-name").textContent = rec.name;

    // Category
    card.querySelector(".card-category").textContent = rec.category;

    // Reason — pick language-appropriate reason
    const reasonEl = card.querySelector(".reason-text");
    if (currentLang === "ar") {
      reasonEl.textContent = rec.reason_ar;
      reasonEl.setAttribute("dir", "rtl");
    } else {
      reasonEl.textContent = rec.reason_en;
      reasonEl.setAttribute("dir", "ltr");
    }

    // Tags
    const tagsContainer = card.querySelector(".card-tags");
    (rec.tags || []).forEach((tag) => {
      const span = document.createElement("span");
      span.className = "tag";
      span.textContent = tag;
      tagsContainer.appendChild(span);
    });

    return fragment;
  }

  // ── Helpers ──────────────────────────────────────────────────────
  function showMessage(icon, text, cssClass) {
    elMessageIcon.textContent = icon;
    elMessageText.textContent = text;
    elMessageCard.className = "message-card glass-card " + (cssClass || "");

    // Set direction based on text content
    const arabicRatio =
      [...text].filter((c) => c.charCodeAt(0) >= 0x0600 && c.charCodeAt(0) <= 0x06ff).length /
      Math.max(text.length, 1);
    elMessageText.setAttribute("dir", arabicRatio > 0.3 ? "rtl" : "ltr");

    elMessagesArea.hidden = false;
  }

  function hideAll() {
    elMessagesArea.hidden = true;
    elResultsArea.hidden = true;
  }

  function setLoading(on) {
    elBtn.disabled = on;
    elBtnText.hidden = on;
    elBtnSpinner.hidden = !on;
  }

  // ── Init ─────────────────────────────────────────────────────────
  applyLanguage("en");
})();
