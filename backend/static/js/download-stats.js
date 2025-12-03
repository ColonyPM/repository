class DownloadStats extends HTMLElement {
  static get observedAttributes() {
    return ["endpoint", "slug", "api-base", "data-slug", "data-api-base"];
  }

  static _stylesInjected = false;

  constructor() {
    super();
    this._slug = "";
    this._apiBase = "/api";
    this._endpoint = "";
    this._chart = null;
  }

  connectedCallback() {
    this._applyAttributes();
    this._injectStyles();
    this._render();
    this._fetchAndRender();
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue === newValue) return;
    this._applyAttributes();
    this._fetchAndRender();
  }

  _applyAttributes() {
    const endpointAttr = this.getAttribute("endpoint");
    if (endpointAttr) this._endpoint = endpointAttr;

    const slugAttr =
      this.getAttribute("slug") || this.getAttribute("data-slug");
    if (slugAttr) this._slug = slugAttr;

    const apiBaseAttr =
      this.getAttribute("api-base") || this.getAttribute("data-api-base");
    if (apiBaseAttr) this._apiBase = apiBaseAttr;
  }

  _resolvedEndpoint() {
    if (this._endpoint) return this._endpoint;
    if (this._slug) return `${this._apiBase}/packages/${this._slug}/downloads`;
    return "";
  }

  _render() {
    this.innerHTML = `
      <div class="downloads-card">
        <div class="downloads-card-row">
          <div class="downloads-left">
            <div class="downloads-label">
              <svg class="downloads-icon" aria-hidden="true" viewBox="0 0 16 16">
                <path d="M8 12 3 7h3V2h4v5h3zM2 13h12v1H2z" fill="currentColor"/>
              </svg>
              <span class="downloads-title">Daily Downloads</span>
            </div>
            <div class="downloads-metric" data-role="hover-count">–</div>
            <div class="downloads-date" data-role="hover-date"></div>
          </div>
          <div class="downloads-sparkline-wrapper">
            <canvas data-role="sparkline"></canvas>
          </div>
        </div>
      </div>
    `;
  }

  _injectStyles() {
    if (DownloadStats._stylesInjected) return;
    const style = document.createElement("style");
    style.id = "download-stats-styles";
    style.textContent = `
      download-stats .downloads-card {
        padding: 0.1rem 0;
        background: transparent;
        box-shadow: none;
        font-family: inherit;
      }
      download-stats .downloads-card-row {
        display: flex;
        align-items: center;
        gap: 0.6rem;
      }
      download-stats .downloads-left {
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
      }
      download-stats .downloads-label {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        color: #9ca3af;
      }
      download-stats .downloads-icon {
        width: 14px;
        height: 14px;
        color: #9ca3af;
        flex-shrink: 0;
      }
      download-stats .downloads-title {
        font-size: 0.8rem;
        line-height: 1.1;
        color: #e5e7eb;
      }
      download-stats .downloads-metric {
        color: #f9fafb;
        font-weight: 600;
        font-size: 1.1rem;
        line-height: 1.1;
        min-width: 82px;
      }
      download-stats .downloads-date {
        font-size: 0.7rem;
        color: #9ca3af;
      }
      download-stats .downloads-sparkline-wrapper {
        flex: 1;
        height: 40px;
        position: relative;
      }
      download-stats canvas {
        width: 100%;
        height: 100%;
        background: transparent;
        display: block;
      }
    `;
    document.head.appendChild(style);
    DownloadStats._stylesInjected = true;
  }

  async _fetchAndRender() {
    const endpoint = this._resolvedEndpoint();
    if (!endpoint) return;

    const hoverCountEl = this.querySelector('[data-role="hover-count"]');
    const hoverDateEl = this.querySelector('[data-role="hover-date"]');
    const canvas = this.querySelector('[data-role="sparkline"]');
    if (!hoverCountEl || !hoverDateEl || !canvas) return;

    try {
      const resp = await fetch(endpoint);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const payload = await resp.json();

      const labels = payload.labels || [];
      const data = payload.data || [];

      const updateHover = (idx) => {
        if (idx == null || idx < 0 || idx >= data.length) {
          hoverCountEl.textContent = "–";
          hoverDateEl.textContent = "";
          return;
        }
        hoverCountEl.textContent = Number(data[idx]).toLocaleString();
        hoverDateEl.textContent = labels[idx] || "";
      };

      const defaultIdx = data.length ? data.length - 1 : null;
      updateHover(defaultIdx);

      const chart = this._renderChart(
        canvas,
        labels,
        data,
        updateHover,
        defaultIdx,
      );
    } catch (err) {
      console.error("Failed to load download stats", err);
      hoverCountEl.textContent = "–";
      hoverDateEl.textContent = "";
      this._renderChart(canvas, [], [], () => {});
    }
  }

  _renderChart(canvas, labels, data, updateHover, defaultIdx) {
    const ctx = canvas.getContext("2d");
    const height = canvas.height || canvas.clientHeight || 22;
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, "rgba(139, 92, 246, 0.35)");
    gradient.addColorStop(1, "rgba(139, 92, 246, 0)");

    if (this._chart) {
      this._chart.data.labels = labels;
      this._chart.data.datasets[0].data = data;
      this._chart.update();
      return;
    }

    this._chart = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            data,
            borderColor: "#8b5cf6",
            backgroundColor: gradient,
            borderWidth: 2,
            tension: 0.35,
            pointRadius: 0,
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "nearest",
          intersect: false,
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            enabled: false,
          },
        },
        scales: {
          x: { display: false, grid: { display: false } },
          y: { display: false, grid: { display: false } },
        },
        elements: {
          line: { borderCapStyle: "round" },
        },
      },
    });

    const handleHover = (_, activeEls) => {
      if (activeEls && activeEls.length) {
        updateHover(activeEls[0].index);
      } else {
        updateHover(defaultIdx);
      }
    };

    this._chart.options.onHover = handleHover;
    this._chart.update();
    return this._chart;
  }
}

customElements.define("download-stats", DownloadStats);
