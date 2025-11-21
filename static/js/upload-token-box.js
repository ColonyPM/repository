// upload-token-box.js

const DEFAULT_TOKEN_ENDPOINT = "/api/users/upload-token";
const DEFAULT_TOKEN_LIFETIME_SECONDS = 30; // seconds

class UploadTokenBox extends HTMLElement {
  static get observedAttributes() {
    return ["endpoint", "lifetime"];
  }

  constructor() {
    super();
    this._endpoint = DEFAULT_TOKEN_ENDPOINT;
    this._lifetimeSeconds = DEFAULT_TOKEN_LIFETIME_SECONDS;

    this._refreshTimeout = null;
    this._initialized = false;
    this._running = false;

    this._tokenEl = null;
    this._barEl = null;
    this._copyBtnEl = null;
    this._currentToken = "";

    this._fetchToken = this._fetchToken.bind(this);
  }

  connectedCallback() {
    this._applyAttributes();

    if (!this._initialized) {
      this._render();
      this._cacheElements();
      this._bindCopyButton();
      this._initialized = true;
    }
    // no auto-start here – controlled from the outside (modal events)
  }

  disconnectedCallback() {
    this.stop();
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue === newValue) return;

    if (name === "endpoint") {
      this._endpoint = newValue || DEFAULT_TOKEN_ENDPOINT;
    }

    if (name === "lifetime") {
      this._setLifetimeFromAttr(newValue);
    }

    // If it's already running and config changes, refresh now
    if (this._running) {
      this._fetchToken();
    }
  }

  // --- public API ---

  start() {
    if (this._running) return;
    this._running = true;
    this._fetchToken();
  }

  stop() {
    this._running = false;
    this._clearRefreshTimeout();

    if (this._barEl) {
      this._barEl.style.transition = "none";
      this._barEl.style.width = "0%";
    }

    if (this._tokenEl) {
      this._tokenEl.textContent = "…";
      this._currentToken = "";
    }
  }

  // --- internal helpers ---

  _applyAttributes() {
    const endpointAttr = this.getAttribute("endpoint");
    if (endpointAttr) this._endpoint = endpointAttr;

    const lifetimeAttr = this.getAttribute("lifetime");
    if (lifetimeAttr) {
      this._setLifetimeFromAttr(lifetimeAttr);
    }
  }

  _setLifetimeFromAttr(value) {
    const parsed = parseInt(value, 10);
    if (!Number.isNaN(parsed) && parsed > 0) {
      this._lifetimeSeconds = parsed;
    } else {
      this._lifetimeSeconds = DEFAULT_TOKEN_LIFETIME_SECONDS;
    }
  }

  _render() {
    // Single bordered box, truncated token, larger copy icon
    this.innerHTML = `
      <div class="border border-secondary rounded px-3 py-3 bg-dark">
        <div class="d-flex align-items-center gap-2 mb-2">
          <span class="small text-muted">Token:</span>
          <code
            data-role="token-value"
            class="flex-grow-1 small text-truncate d-block user-select-none"
            style="max-width: 100%;"
          >loading…</code>
          <button
            type="button"
            class="btn btn-sm border-0 px-2 d-inline-flex align-items-center justify-content-center text-light"
            data-role="copy-btn"
            title="Copy token"
          >
            <span class="visually-hidden">Copy token</span>
            <span aria-hidden="true" class="fs-5 lh-1">⧉</span>
          </button>
        </div>
        <div class="progress" style="height: 0.45rem;">
          <div
            class="progress-bar bg-success"
            role="progressbar"
            aria-valuemin="0"
            aria-valuemax="100"
            data-role="progress-bar"
            style="width: 100%;"
          ></div>
        </div>
      </div>
    `;
  }

  _cacheElements() {
    this._tokenEl = this.querySelector('[data-role="token-value"]');
    this._barEl = this.querySelector('[data-role="progress-bar"]');
    this._copyBtnEl = this.querySelector('[data-role="copy-btn"]');
  }

  _bindCopyButton() {
    if (!this._copyBtnEl) return;

    this._copyBtnEl.addEventListener("click", async () => {
      const token =
        this._currentToken || (this._tokenEl?.textContent ?? "").trim();
      if (!token) return;

      try {
        await navigator.clipboard.writeText(token);

        // Tiny feedback: change title + briefly show a checkmark
        const originalTitle =
          this._copyBtnEl.getAttribute("title") || "Copy token";
        const originalIcon = this._copyBtnEl.innerHTML;

        this._copyBtnEl.setAttribute("title", "Copied!");
        this._copyBtnEl.innerHTML = `
          <span class="visually-hidden">Copied</span>
          <span aria-hidden="true">✔</span>
        `;

        setTimeout(() => {
          this._copyBtnEl.setAttribute("title", originalTitle);
          this._copyBtnEl.innerHTML = originalIcon;
        }, 1200);
      } catch (err) {
        console.error("Clipboard write failed:", err);
        // Fallback if clipboard is blocked
        window.prompt("Copy token:", token);
      }
    });
  }

  _clearRefreshTimeout() {
    if (this._refreshTimeout) {
      clearTimeout(this._refreshTimeout);
      this._refreshTimeout = null;
    }
  }

  async _fetchToken() {
    this._clearRefreshTimeout();

    if (!this._running) return;
    if (!this._tokenEl || !this._barEl) return;

    // Reset bar instantly
    this._barEl.style.transition = "none";
    this._barEl.style.width = "100%";

    try {
      const res = await fetch(this._endpoint, {
        credentials: "include",
      });

      if (!res.ok) {
        this._tokenEl.textContent = "error";
        this._currentToken = "";
        return;
      }

      const data = await res.json();
      this._currentToken = data.token;
      this._tokenEl.textContent = data.token;

      const lifetimeMs = this._lifetimeSeconds * 1000;

      if (!this._running) return;

      // Animate bar from 100% -> 0% over lifetime
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (!this._running) return;
          this._barEl.style.transition = `width ${lifetimeMs}ms linear`;
          this._barEl.style.width = "0%";
        });
      });

      // Schedule next refresh
      this._refreshTimeout = setTimeout(() => {
        this._fetchToken();
      }, lifetimeMs);
    } catch (err) {
      console.error("Token error:", err);
      this._tokenEl.textContent = "error";
      this._currentToken = "";
    }
  }
}

customElements.define("upload-token-box", UploadTokenBox);
