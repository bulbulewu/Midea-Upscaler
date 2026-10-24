/**
 * Media Toolkit Pro V3 â€” Multi-Marketplace Studio Engine
 * Munajat International Commercial Edition
 */

document.addEventListener("DOMContentLoaded", () => {
  // ---------------- Application State ----------------
  const state = {
    activeTool: "video",
    activeMarketplace: "universal",
    viewLayout: localStorage.getItem("mtk_view_layout") || "grid",
    activeTheme: localStorage.getItem("mtk_theme") || "dark_studio",
    video: { file: null, videoUrl: null, pollTimer: null, currentJobId: null, probeData: null },
    image: { file: null, imageUrl: null, pollTimer: null, currentJobId: null, probeData: null },
    psd:   { file: null, imageUrl: null, pollTimer: null, currentJobId: null, probeData: null },
    session: null,
    agenciesConfig: {},
  };

  // Check URL parameters for Unified SSO and Theme Synchronization with StockMeta Pro
  const urlParams = new URLSearchParams(window.location.search);
  const ssoUser = urlParams.get("sso_user");
  const ssoToken = urlParams.get("sso_token");
  const urlTheme = urlParams.get("theme");

  if (urlTheme && ["dark_studio", "obsidian_oled", "cyber_neon", "titanium_light"].includes(urlTheme)) {
    state.activeTheme = urlTheme;
    localStorage.setItem("mtk_theme", urlTheme);
    localStorage.setItem("stockmeta_theme", urlTheme);
  }

  // Apply initial theme
  document.documentElement.setAttribute("data-theme", state.activeTheme);

  // Dynamic StockMeta Pro link generator with current active theme & SSO session
  function updateStockMetaLink() {
    const navStockMeta = document.getElementById("nav-stockmeta-pro");
    if (!navStockMeta) return;
    const currentTheme = state.activeTheme || localStorage.getItem("mtk_theme") || "dark_studio";
    const params = new URLSearchParams();
    params.set("theme", currentTheme);
    if (state.session && state.session.logged_in && state.session.user_email) {
      params.set("sso_user", state.session.user_email);
      params.set("sso_token", btoa(state.session.user_email + ":" + Date.now()));
    }
    navStockMeta.href = `https://stockmeta-pro.onrender.com/?${params.toString()}`;
  }

  // If SSO credentials provided from StockMeta Pro, auto-login immediately
  if (ssoUser) {
    fetch("/api/auth/sso-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sso_user: ssoUser, sso_token: ssoToken || "" })
    }).then(res => res.json()).then(data => {
      if (data.success) {
        refreshSession();
        showToast(`Unified Login Active: ${ssoUser}`, "success");
        // Clean URL query parameters cleanly
        const cleanUrl = window.location.protocol + "//" + window.location.host + window.location.pathname;
        window.history.replaceState({ path: cleanUrl }, "", cleanUrl);
      }
    }).catch(() => {});
  }

  // Cross-Tab Theme Synchronization via Storage Event
  window.addEventListener("storage", (e) => {
    if (e.key === "mtk_theme" || e.key === "stockmeta_theme") {
      const syncedTheme = e.newValue;
      if (syncedTheme && ["dark_studio", "obsidian_oled", "cyber_neon", "titanium_light"].includes(syncedTheme)) {
        state.activeTheme = syncedTheme;
        document.documentElement.setAttribute("data-theme", syncedTheme);
        document.querySelectorAll(".theme-card").forEach(c => c.classList.toggle("active", c.dataset.theme === syncedTheme));
        updateStockMetaLink();
      }
    }
  });

  // ---------------- UI Toast System ----------------
  function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    const icon = type === "success" ? "âœ“" : type === "error" ? "âš ï¸" : "â„¹ï¸";
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(10px)";
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  // ---------------- Layout View Switcher (Grid vs List) ----------------
  function applyViewLayout(layout) {
    state.viewLayout = layout;
    localStorage.setItem("mtk_view_layout", layout);

    // Update containers
    ["video", "image", "psd"].forEach(tool => {
      const container = document.getElementById(`media-container-${tool}`);
      if (container) {
        container.classList.remove("layout-grid", "layout-list");
        container.classList.add(`layout-${layout}`);
      }
    });

    // Update toggle buttons in sidebar
    document.querySelectorAll(".view-toggle-btn").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.layout === layout);
    });

    // Update in-panel view buttons
    document.querySelectorAll(".view-pill-btn").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.view === layout);
    });
  }

  // Bind Sidebar view toggles
  document.querySelectorAll(".view-toggle-btn").forEach(btn => {
    btn.addEventListener("click", () => applyViewLayout(btn.dataset.layout));
  });

  // Bind In-panel view toggles
  document.querySelectorAll(".view-pill-btn").forEach(btn => {
    btn.addEventListener("click", () => applyViewLayout(btn.dataset.view));
  });

  // Initial layout apply
  applyViewLayout(state.viewLayout);

  // ---------------- Tool Pipeline Switching ----------------
  const toolTitles = {
    video: "🎬 4K Stock Video Master Upscaler",
    image: "🖼️ Image Upscaler (4K & 8K)",
    psd:   "📄 PNG to Layered PSD Generator",
    toolkit: "🛠️ Stock Contributor Toolkit Pro",
  };

  const tabBtns = document.querySelectorAll(".tab-btn");
  const toolPanels = document.querySelectorAll(".tool-panel");

  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const tool = btn.dataset.tool;
      state.activeTool = tool;

      tabBtns.forEach(b => b.classList.remove("active"));
      toolPanels.forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const activePanel = document.getElementById(`panel-${tool}`);
      if (activePanel) activePanel.classList.add("active");

      // Update topbar breadcrumb
      const topTitle = document.getElementById("topbar-tool-title");
      const crumbPrefix = document.getElementById("topbar-crumb-prefix");
      const marketPill = document.getElementById("topbar-market-pill");

      if (tool === "toolkit") {
        if (crumbPrefix) crumbPrefix.style.display = "none";
        if (marketPill) marketPill.style.display = "none";
        if (topTitle) topTitle.textContent = "🛠️ Stock Contributor Toolkit Pro";
      } else {
        if (crumbPrefix) crumbPrefix.style.display = "";
        if (marketPill) marketPill.style.display = "";
        if (topTitle && toolTitles[tool]) {
          topTitle.textContent = toolTitles[tool];
        }
      }
    });
  });

  // ---------------- Target Marketplace Switcher ----------------
  const marketplaceBtns = document.querySelectorAll(".m-btn");
  marketplaceBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      marketplaceBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.activeMarketplace = btn.dataset.marketplace;

      const badgeName = btn.querySelector(".market-name") ? btn.querySelector(".market-name").textContent.trim() : btn.textContent.trim();
      
      document.querySelectorAll(".active-market-badge").forEach(el => {
        el.textContent = badgeName;
      });

      const topMarketPill = document.getElementById("topbar-market-pill");
      if (topMarketPill) {
        topMarketPill.textContent = badgeName;
      }

      // Re-run preflight checks if files are currently loaded
      ["video", "image"].forEach(tool => {
        if (state[tool].file) {
          runPreflight(tool, state[tool].file);
        }
      });

      showToast(`Active Target Marketplace: ${badgeName}`, "info");
    });
  });

  // ---------------- Target Marketplace Accordion / Minimize Toggle ----------------
  const marketplaceMenu = document.getElementById("marketplaces-menu");
  const marketplaceHeader = document.getElementById("marketplace-accordion-header");
  const btnToggleMarketplaces = document.getElementById("btn-toggle-marketplaces");
  const marketArrow = document.getElementById("market-accordion-arrow");
  const marketSymbol = document.getElementById("market-toggle-symbol");

  function toggleMarketplacesMenu(e) {
    if (e) e.stopPropagation();
    if (!marketplaceMenu) return;
    const isCollapsed = marketplaceMenu.classList.toggle("collapsed");
    if (marketArrow) marketArrow.classList.toggle("collapsed", isCollapsed);
    if (marketSymbol) marketSymbol.textContent = isCollapsed ? "+" : "âˆ’";
  }

  if (btnToggleMarketplaces) {
    btnToggleMarketplaces.addEventListener("click", toggleMarketplacesMenu);
  }
  if (marketplaceHeader) {
    marketplaceHeader.addEventListener("click", toggleMarketplacesMenu);
  }

  // ---------------- Mobile Sidebar Toggle ----------------
  const sidebar = document.getElementById("sidebar");
  const sidebarToggle = document.getElementById("sidebar-toggle");
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", () => {
      sidebar.classList.toggle("open");
    });
  }

  // ---------------- File Drop & Selection Handlers ----------------
  ["video", "image", "psd"].forEach(tool => {
    const dropZone = document.getElementById(`drop-${tool}`);
    const fileInput = document.getElementById(`file-${tool}`);
    const actionBtn = document.getElementById(`btn-${tool}`);
    const removeBtn = document.getElementById(`btn-remove-${tool}`);

    if (!dropZone || !fileInput) return;

    dropZone.addEventListener("click", () => fileInput.click());

    ["dragenter", "dragover"].forEach(eName => {
      dropZone.addEventListener(eName, e => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach(eName => {
      dropZone.addEventListener(eName, e => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove("dragover");
      });
    });

    dropZone.addEventListener("drop", e => {
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleFileSelect(tool, e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener("change", () => {
      if (fileInput.files && fileInput.files.length > 0) {
        handleFileSelect(tool, fileInput.files[0]);
      }
    });

    if (actionBtn) {
      actionBtn.addEventListener("click", () => submitJob(tool));
    }

    if (removeBtn) {
      removeBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        clearFile(tool);
      });
    }
  });

  function clearFile(tool) {
    state[tool].file = null;
    state[tool].probeData = null;
    const previewCard = document.getElementById(`preview-${tool}`);
    const preflightCard = document.getElementById(`preflight-${tool}`);
    const actionBtn = document.getElementById(`btn-${tool}`);
    const fileInput = document.getElementById(`file-${tool}`);

    if (previewCard) previewCard.classList.remove("show");
    if (preflightCard) preflightCard.classList.remove("show");
    if (actionBtn) actionBtn.disabled = true;
    if (fileInput) fileInput.value = "";

    hideElement(`progress-${tool}`);
    hideElement(`result-${tool}`);
    hideElement(`error-${tool}`);
  }

  // ---------------- Video File Handling & Instant Thumbnail Generation ----------------
  function handleFileSelect(tool, file) {
    state[tool].file = file;

    // Reset results & progress
    hideElement(`error-${tool}`);
    hideElement(`progress-${tool}`);
    hideElement(`result-${tool}`);

    const previewCard = document.getElementById(`preview-${tool}`);
    const previewName = document.getElementById(`preview-name-${tool}`);
    const previewFormat = document.getElementById(`preview-format-${tool}`);
    const actionBtn = document.getElementById(`btn-${tool}`);

    const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
    const ext = file.name.split('.').pop().toUpperCase();

    if (previewName) previewName.textContent = file.name;
    if (previewFormat) previewFormat.textContent = ext;

    // Video Specific Thumbnail & Inspector
    if (tool === "video") {
      const sizeEl = document.getElementById("tech-size-video");
      if (sizeEl) sizeEl.textContent = `${sizeMb} MB`;

      // Revoke older URL
      if (state.video.videoUrl) URL.revokeObjectURL(state.video.videoUrl);
      state.video.videoUrl = URL.createObjectURL(file);

      // Generate instant client-side thumbnail via canvas
      generateVideoThumbnail(file, state.video.videoUrl);

      // Enable play preview
      const playBtn = document.getElementById("btn-play-video-preview");
      const inspectBtn = document.getElementById("btn-inspect-video");
      const openPlayer = () => openVideoPlayerModal(file.name, state.video.videoUrl);

      if (playBtn) playBtn.onclick = openPlayer;
      if (inspectBtn) inspectBtn.onclick = openPlayer;
    }

    // Image & PSD previews
    if (tool === "image" || tool === "psd") {
      const previewImg = document.getElementById(`preview-img-${tool}`);
      const sizeEl = document.getElementById(`tech-size-${tool}`);
      if (sizeEl) sizeEl.textContent = `${sizeMb} MB`;

      if (file.type.startsWith("image/") || /\.(png|jpg|jpeg|webp|bmp|tif|tiff)$/i.test(file.name)) {
        if (state[tool].imageUrl) URL.revokeObjectURL(state[tool].imageUrl);
        state[tool].imageUrl = URL.createObjectURL(file);
        if (previewImg) {
          previewImg.src = state[tool].imageUrl;
          previewImg.onload = () => {
            const w = previewImg.naturalWidth;
            const h = previewImg.naturalHeight;
            const mp = ((w * h) / 1000000).toFixed(2);
            
            const resEl = document.getElementById(`tech-res-${tool}`);
            if (resEl) resEl.textContent = `${w} Ã— ${h} px`;

            const mpEl = document.getElementById(`tech-mp-${tool}`);
            if (mpEl) mpEl.textContent = `${mp} MP`;

            const mpPill = document.getElementById(`image-mp-pill`);
            if (mpPill && tool === "image") mpPill.textContent = `${mp} MP`;
          };
        }
      }
    }

    if (previewCard) previewCard.classList.add("show");
    if (actionBtn) actionBtn.disabled = false;

    // Run Pre-Flight Inspection on file upload
    if (tool === "video" || tool === "image") {
      runPreflight(tool, file);
    }
  }

  // Generate instant client-side video thumbnail
  function generateVideoThumbnail(file, objectUrl) {
    const tempVideo = document.createElement("video");
    tempVideo.preload = "metadata";
    tempVideo.src = objectUrl;
    tempVideo.muted = true;
    tempVideo.playsInline = true;

    tempVideo.onloadedmetadata = () => {
      const dur = tempVideo.duration || 0;
      const w = tempVideo.videoWidth || 1920;
      const h = tempVideo.videoHeight || 1080;

      // Update pills
      const durEl = document.getElementById("video-duration-pill");
      if (durEl) {
        const mins = Math.floor(dur / 60);
        const secs = Math.floor(dur % 60);
        durEl.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
      }

      const resEl = document.getElementById("video-resolution-pill");
      if (resEl) {
        resEl.textContent = h >= 2160 ? "4K UHD" : h >= 1440 ? "2K QHD" : h >= 1080 ? "1080p FHD" : `${w}Ã—${h}`;
      }

      const techRes = document.getElementById("tech-res-video");
      if (techRes) techRes.textContent = `${w} Ã— ${h}`;

      // Seek to capture frame
      tempVideo.currentTime = Math.min(1.0, dur * 0.1);
    };

    tempVideo.onseeked = () => {
      try {
        const canvas = document.createElement("canvas");
        canvas.width = tempVideo.videoWidth || 640;
        canvas.height = tempVideo.videoHeight || 360;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(tempVideo, 0, 0, canvas.width, canvas.height);
        const thumbDataUrl = canvas.toDataURL("image/jpeg", 0.85);

        const thumbImg = document.getElementById("video-thumb-img");
        if (thumbImg) {
          thumbImg.src = thumbDataUrl;
        }
      } catch (err) {
        console.warn("Client canvas capture skipped:", err);
      }
    };
  }

  // ---------------- Video Player Preview Modal ----------------
  const playerModal = document.getElementById("modal-video-player");
  const playerEl = document.getElementById("preview-video-element");
  const closePlayerBtn = document.getElementById("close-player-btn");

  function openVideoPlayerModal(filename, videoSrc) {
    if (!playerModal || !playerEl) return;
    document.getElementById("player-modal-title").textContent = `Preview: ${filename}`;
    playerEl.src = videoSrc;
    playerModal.classList.add("open");
    playerEl.play().catch(() => {});
  }

  if (closePlayerBtn && playerModal && playerEl) {
    closePlayerBtn.addEventListener("click", () => {
      playerModal.classList.remove("open");
      playerEl.pause();
      playerEl.src = "";
    });
  }

  // ---------------- Pre-Flight Compliance Inspector ----------------
  async function runPreflight(tool, file) {
    const preflightCard = document.getElementById(`preflight-${tool}`);
    const preflightGrid = document.getElementById(`preflight-grid-${tool}`);
    const preflightMarket = document.getElementById(`preflight-market-${tool}`);

    if (!preflightCard || !preflightGrid) return;

    const fd = new FormData();
    fd.append("file", file);
    fd.append("marketplace", state.activeMarketplace);

    const endpoint = tool === "video" ? "/api/preflight/video" : "/api/preflight/image";

    try {
      const res = await fetch(endpoint, { method: "POST", body: fd });
      if (!res.ok) return;
      const data = await res.json();
      const report = data.report;
      const src = data.source;

      state[tool].probeData = src;

      // Update server-extracted technical details
      if (tool === "video" && src) {
        if (src.thumbnail) {
          const thumbImg = document.getElementById("video-thumb-img");
          if (thumbImg) thumbImg.src = src.thumbnail;
        }
        const fpsEl = document.getElementById("tech-fps-video");
        if (fpsEl) fpsEl.textContent = `${src.fps} fps`;

        const codecEl = document.getElementById("tech-codec-video");
        if (codecEl) codecEl.textContent = `${src.codec.toUpperCase()} (${src.profile || 'Main'})`;

        const audioEl = document.getElementById("tech-audio-video");
        if (audioEl) audioEl.textContent = src.has_audio ? `Present (${src.audio_codec || 'AAC'})` : "Muted (No Audio)";

        const bitEl = document.getElementById("tech-bitrate-video");
        if (bitEl) bitEl.textContent = src.bitrate_kbps ? `${(src.bitrate_kbps / 1000).toFixed(1)} Mbps` : "~60 Mbps";
      }

      if (preflightMarket) preflightMarket.textContent = `${report.marketplace} Pre-Flight Check`;

      let gridHtml = "";
      report.checks.forEach(c => {
        let badgeClass = "badge-status-pass";
        let statusLabel = "PASS";
        if (c.status === "FAIL") {
          badgeClass = "badge-status-fail";
          statusLabel = "ACTION REQ";
        } else if (c.status === "WARNING") {
          badgeClass = "badge-status-warn";
          statusLabel = "WARNING";
        } else if (c.status === "READY" || c.status === "UPSCALING_REQUIRED" || c.status === "CONFORM") {
          badgeClass = "badge-status-info";
          statusLabel = c.status;
        }

        gridHtml += `
          <div class="check-item">
            <span class="check-param">${c.param}</span>
            <div class="check-val">
              <span>${c.value}</span>
              <span class="${badgeClass}">${statusLabel}</span>
            </div>
            <span class="check-msg">${c.message}</span>
          </div>
        `;
      });

      preflightGrid.innerHTML = gridHtml;
      preflightCard.classList.add("show");
    } catch (err) {
      console.warn("Pre-flight check error:", err);
    }
  }

  // ---------------- Segmented Controls ----------------
  document.querySelectorAll(".segmented-control").forEach(control => {
    const inputTargetId = control.dataset.for;
    const hiddenInput = document.getElementById(inputTargetId);
    const options = control.querySelectorAll(".segmented-option");

    options.forEach(opt => {
      opt.addEventListener("click", () => {
        options.forEach(o => o.classList.remove("selected"));
        opt.classList.add("selected");
        if (hiddenInput) {
          hiddenInput.value = opt.dataset.val;
          hiddenInput.dispatchEvent(new Event("change"));
        }
      });
    });
  });

  // ---------------- Job Submission & Processing ----------------
  async function submitJob(tool) {
    const file = state[tool].file;
    if (!file) return;

    const actionBtn = document.getElementById(`btn-${tool}`);
    const progressCard = document.getElementById(`progress-${tool}`);
    const progressFill = document.getElementById(`progress-fill-${tool}`);
    const progressStatus = document.getElementById(`progress-status-${tool}`);
    const progressPct = document.getElementById(`progress-pct-${tool}`);
    const errorBanner = document.getElementById(`error-${tool}`);
    const resultCard = document.getElementById(`result-${tool}`);

    // UI state
    actionBtn.disabled = true;
    hideElement(`error-${tool}`);
    hideElement(`result-${tool}`);
    if (progressCard) progressCard.style.display = "block";
    if (progressFill) progressFill.style.width = "0%";
    if (progressPct) progressPct.textContent = "0%";
    if (progressStatus) progressStatus.textContent = "Uploading asset to studio engineâ€¦";

    const fd = new FormData();
    fd.append("file", file);
    fd.append("marketplace", state.activeMarketplace);

    let endpoint = "";

    if (tool === "video") {
      endpoint = "/api/jobs";
      fd.append("target", document.getElementById("video-target").value);
      fd.append("codec", document.getElementById("video-codec").value);
      fd.append("quality", document.getElementById("video-quality").value);
      fd.append("keep_audio", document.getElementById("video-keep-audio").checked ? "true" : "false");
    } else if (tool === "image") {
      endpoint = "/api/jobs/image";
      fd.append("scale", document.getElementById("image-scale").value);
      fd.append("out_format", document.getElementById("image-format").value);
      fd.append("quality", document.getElementById("image-quality").value);
      fd.append("dpi", document.getElementById("image-dpi").value);
      fd.append("auto_denoise", document.getElementById("image-auto-denoise").checked ? "true" : "false");
    } else if (tool === "psd") {
      endpoint = "/api/psd-jobs";
      fd.append("layer_name", document.getElementById("psd-layer-name")?.value || "Artwork Layer");
      fd.append("canvas_size", document.getElementById("psd-canvas-size")?.value || "original");
      fd.append("custom_w", document.getElementById("psd-custom-w")?.value || "4000");
      fd.append("custom_h", document.getElementById("psd-custom-h")?.value || "4000");
      fd.append("auto_trim", document.getElementById("psd-auto-trim")?.checked ? "true" : "false");
      fd.append("isolate_bg", document.getElementById("psd-isolate-bg")?.value || "none");
      fd.append("layer_structure", document.getElementById("psd-layer-structure")?.value || "dual_white");
      fd.append("add_shadow", document.getElementById("psd-add-shadow")?.checked ? "true" : "false");
      fd.append("defringe", document.getElementById("psd-defringe")?.checked ? "true" : "false");
      fd.append("dpi", document.getElementById("psd-dpi")?.value || "300");
    }

    try {
      const res = await fetch(endpoint, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to create studio job.");

      state[tool].currentJobId = data.id;
      pollJobProgress(tool, data.id);
    } catch (err) {
      if (progressCard) progressCard.style.display = "none";
      if (errorBanner) {
        errorBanner.textContent = `Error: ${err.message}`;
        errorBanner.style.display = "block";
      }
      actionBtn.disabled = false;
      showToast(err.message, "error");
    }
  }

  function pollJobProgress(tool, jobId) {
    if (state[tool].pollTimer) clearInterval(state[tool].pollTimer);

    const progressFill = document.getElementById(`progress-fill-${tool}`);
    const progressPct = document.getElementById(`progress-pct-${tool}`);
    const progressStatus = document.getElementById(`progress-status-${tool}`);
    const actionBtn = document.getElementById(`btn-${tool}`);
    const errorBanner = document.getElementById(`error-${tool}`);
    const progressCard = document.getElementById(`progress-${tool}`);

    state[tool].pollTimer = setInterval(async () => {
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        if (!res.ok) return;
        const job = await res.json();

        const pct = job.progress || 0;
        if (progressFill) progressFill.style.width = `${pct}%`;
        if (progressPct) progressPct.textContent = `${pct.toFixed(0)}%`;

        if (job.state === "running") {
          if (progressStatus) {
            progressStatus.textContent = tool === "video" 
              ? `Encoding 4K Master (${pct.toFixed(0)}% complete)â€¦`
              : `Upscaling high-density pixels (${pct.toFixed(0)}%)â€¦`;
          }
        } else if (job.state === "done") {
          clearInterval(state[tool].pollTimer);
          if (progressCard) progressCard.style.display = "none";
          renderJobResults(tool, job);
          actionBtn.disabled = false;
          showToast(`Master export ready for ${state[tool].file.name}!`, "success");
        } else if (job.state === "error") {
          clearInterval(state[tool].pollTimer);
          if (progressCard) progressCard.style.display = "none";
          if (errorBanner) {
            errorBanner.textContent = `Processing failed: ${job.error}`;
            errorBanner.style.display = "block";
          }
          actionBtn.disabled = false;
          showToast("Export failed: " + job.error, "error");
        }
      } catch (err) {
        console.warn("Polling error:", err);
      }
    }, 800);
  }

  function renderJobResults(tool, job) {
    const resultCard = document.getElementById(`result-${tool}`);
    const tableBody = document.getElementById(`table-${tool}`);
    const dlBtn = document.getElementById(`dl-btn-${tool}`);

    if (!resultCard || !tableBody || !dlBtn) return;

    dlBtn.href = `/api/download/${job.id}`;

    const src = job.source || (job.meta && job.meta.source) || {};
    const meta = (job.meta && job.meta.output) ? job.meta.output : (job.meta || {});

    let rows = "";

    if (tool === "video") {
      rows += `
        <tr><td>Resolution</td><td>${src.width}Ã—${src.height}</td><td><b>${meta.width}Ã—${meta.height} (4K)</b></td><td><span class="badge-status-pass">PASS</span></td></tr>
        <tr><td>Frame Rate</td><td>${src.fps} fps</td><td><b>${meta.fps} fps (CFR Lock)</b></td><td><span class="badge-status-pass">PASS</span></td></tr>
        <tr><td>Codec Container</td><td>${(src.codec||'').toUpperCase()}</td><td><b>${meta.codec.toUpperCase()} (${meta.container})</b></td><td><span class="badge-status-pass">STOCK READY</span></td></tr>
        <tr><td>Bitrate Quality</td><td>${src.bitrate_kbps || 'Dynamic'} kbps</td><td><b>${meta.bitrate}</b></td><td><span class="badge-status-pass">PASS</span></td></tr>
        <tr><td>Audio Track</td><td>${src.has_audio ? 'Detected' : 'None'}</td><td><b>${meta.audio_retained ? 'Kept' : 'Muted (Zero Rejection)'}</b></td><td><span class="badge-status-pass">COMPLIANT</span></td></tr>
        <tr><td>File Size</td><td>${src.size_mb} MB</td><td><b>${meta.size_mb} MB</b></td><td><span class="badge-status-pass">OPTIMIZED</span></td></tr>
      `;
    } else if (tool === "image") {
      rows += `
        <tr><td>Resolution</td><td>${src.width}Ã—${src.height}</td><td><b>${meta.width}Ã—${meta.height} px</b></td><td><span class="badge-status-pass">UHD ENLARGED</span></td></tr>
        <tr><td>Megapixels</td><td>${src.megapixels} MP</td><td><b>${meta.megapixels} MP (Stock Rule â‰¥ 4.0 MP)</b></td><td><span class="badge-status-pass">PASS</span></td></tr>
        <tr><td>Print Resolution</td><td>Standard</td><td><b>${meta.dpi} DPI Commercial Print</b></td><td><span class="badge-status-pass">EMBEDDED</span></td></tr>
        <tr><td>Format / Denoise</td><td>${src.format}</td><td><b>${meta.format} (Denoised: ${meta.auto_denoise ? 'Yes' : 'No'})</b></td><td><span class="badge-status-pass">CLEAN</span></td></tr>
      `;
    } else if (tool === "psd") {
      rows += `
        <tr><td>Dimensions & Canvas</td><td>${src.width}Ã—${src.height} (${src.size_mb} MB)</td><td><b>${meta.width}Ã—${meta.height} px (${meta.megapixels} MP)</b></td><td><span class="badge-status-pass">CALIBRATED</span></td></tr>
        <tr><td>Photoshop Layers</td><td>Single Layer</td><td><b>${meta.layers} Layers (${meta.layer_name})</b></td><td><span class="badge-status-pass">PASS</span></td></tr>
        <tr><td>Layer Structure & Alpha</td><td>Raw Bitmap</td><td><b>${meta.background} Â· 100% Alpha Intact</b></td><td><span class="badge-status-pass">FREEPIK READY</span></td></tr>
        <tr><td>Print Resolution</td><td>Standard</td><td><b>${meta.dpi} Commercial Print Headers</b></td><td><span class="badge-status-pass">EMBEDDED</span></td></tr>
      `;

      const pngBtn = document.getElementById("dl-btn-psd-png");
      if (pngBtn) {
        if (meta.companion_png) {
          pngBtn.href = `/api/download/png/${job.id}`;
          pngBtn.style.display = "inline-flex";
        } else {
          pngBtn.style.display = "none";
        }
      }
    }

    tableBody.innerHTML = rows;
    resultCard.style.display = "block";
  }

  // ---------------- MODAL MANAGEMENT ----------------
  function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add("open");
  }

  function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove("open");
  }

  // Close buttons bindings
  document.querySelectorAll(".modal-backdrop").forEach(backdrop => {
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) backdrop.classList.remove("open");
    });
  });

  // Top header button triggers
  async function loadUpscalerSettings() {
    try {
      const res = await fetch("/api/settings/studio");
      if (res.ok) {
        const s = await res.json();
        if (s.video_resolution && document.getElementById("setting-video-res")) document.getElementById("setting-video-res").value = s.video_resolution;
        if (s.video_codec && document.getElementById("setting-video-codec")) document.getElementById("setting-video-codec").value = s.video_codec;
        if (s.video_fps && document.getElementById("setting-video-fps")) document.getElementById("setting-video-fps").value = s.video_fps;
        if (s.video_crf && document.getElementById("setting-video-crf")) document.getElementById("setting-video-crf").value = s.video_crf;
        if (s.image_scale && document.getElementById("setting-image-scale")) document.getElementById("setting-image-scale").value = s.image_scale;
        if (s.image_resampling && document.getElementById("setting-image-resampling")) document.getElementById("setting-image-resampling").value = s.image_resampling;
        if (s.image_dpi && document.getElementById("setting-image-dpi")) document.getElementById("setting-image-dpi").value = s.image_dpi;
        if (s.image_quality && document.getElementById("setting-image-quality")) document.getElementById("setting-image-quality").value = s.image_quality;
      }
    } catch (e) {
      console.warn("Could not load upscaler settings", e);
    }
  }

  const openSettingsBtn = document.getElementById("open-settings-btn");
  if (openSettingsBtn) openSettingsBtn.addEventListener("click", () => {
    loadUpscalerSettings();
    openModal("modal-settings");
  });

  const closeSettingsBtn = document.getElementById("close-settings-btn");
  if (closeSettingsBtn) closeSettingsBtn.addEventListener("click", () => closeModal("modal-settings"));
  const cancelSettingsBtn = document.getElementById("cancel-settings-btn");
  if (cancelSettingsBtn) cancelSettingsBtn.addEventListener("click", () => closeModal("modal-settings"));

  const openAdminBtn = document.getElementById("open-admin-btn");
  if (openAdminBtn) openAdminBtn.addEventListener("click", () => {
    loadAdminData();
    openModal("modal-admin");
  });

  const closeAdminBtn = document.getElementById("close-admin-btn");
  if (closeAdminBtn) closeAdminBtn.addEventListener("click", () => closeModal("modal-admin"));

  const openActivateBtn = document.getElementById("open-activate-btn");
  if (openActivateBtn) openActivateBtn.addEventListener("click", () => openModal("modal-activate"));
  const closeActivateBtn = document.getElementById("close-activate-btn");
  if (closeActivateBtn) closeActivateBtn.addEventListener("click", () => closeModal("modal-activate"));
  const cancelActivateBtn = document.getElementById("cancel-activate-btn");
  if (cancelActivateBtn) cancelActivateBtn.addEventListener("click", () => closeModal("modal-activate"));

  // ---------------- AUTH & SESSION (Strict Per-User Browser Isolation) ----------------

  async function refreshSession() {
    try {
      const res = await fetch("/api/auth/session");
      if (!res.ok) return;
      const sess = await res.json();
      state.session = sess;

      const userEmailEl = document.getElementById("chip-user-email");
      const userTierEl = document.getElementById("chip-user-tier");
      const logoutBtn = document.getElementById("auth-logout-btn");

      // STRICT ADMIN VISIBILITY: Only show Admin Panel button if is_admin is true and role is Master Admin
      if (openAdminBtn) {
        if (sess.logged_in && sess.is_admin && sess.role === "Master Admin") {
          openAdminBtn.style.display = "inline-flex";
        } else {
          openAdminBtn.style.display = "none";
        }
      }

      if (sess.logged_in) {
        if (userEmailEl) userEmailEl.textContent = sess.user_email;
        if (userTierEl) userTierEl.textContent = `â­ ${sess.role} (${sess.license_tier || 'Pro'})`;
        if (logoutBtn) logoutBtn.textContent = "Logout";
      } else {
        if (userEmailEl) userEmailEl.textContent = "Guest Contributor";
        if (userTierEl) userTierEl.textContent = "Unregistered Â· 7-Day Free Trial Available";
        if (logoutBtn) logoutBtn.textContent = "Sign In / Register";
      }
      updateStockMetaLink();
    } catch (err) {
      console.warn("Session check error:", err);
    }
  }
  refreshSession();

  // Auth Logout/Login toggle
  const authBtn = document.getElementById("auth-logout-btn");
  if (authBtn) {
    authBtn.addEventListener("click", async () => {
      if (state.session && state.session.logged_in) {
        await fetch("/api/auth/logout", { method: "POST" });
        if (openAdminBtn) openAdminBtn.style.display = "none";
        showToast("Logged out successfully.", "info");
        refreshSession();
      } else {
        openModal("modal-login");
      }
    });
  }

  // Footer navigation links
  const footerReadmeLink = document.getElementById("footer-link-readme");
  if (footerReadmeLink) {
    footerReadmeLink.addEventListener("click", () => {
      openModal("modal-settings");
      const readmePill = document.querySelector('.s-pill-btn[data-panel="readme"]');
      if (readmePill) readmePill.click();
    });
  }

  const footerSettingsLink = document.getElementById("footer-link-settings");
  if (footerSettingsLink) {
    footerSettingsLink.addEventListener("click", () => {
      openModal("modal-settings");
    });
  }

  const closeLoginBtn = document.getElementById("close-login-btn");
  if (closeLoginBtn) closeLoginBtn.addEventListener("click", () => closeModal("modal-login"));
  const cancelLoginBtn = document.getElementById("cancel-login-btn");
  if (cancelLoginBtn) cancelLoginBtn.addEventListener("click", () => closeModal("modal-login"));

  // Auth Tab Switcher (Sign In vs Register)
  const tabBtnSignIn = document.getElementById("tab-btn-signin");
  const tabBtnRegister = document.getElementById("tab-btn-register");
  const authPaneSignIn = document.getElementById("auth-pane-signin");
  const authPaneRegister = document.getElementById("auth-pane-register");
  const authTitle = document.getElementById("auth-modal-title");
  const authSubtitle = document.getElementById("auth-modal-subtitle");
  const doLoginBtn = document.getElementById("do-login-btn");
  const doRegisterBtn = document.getElementById("do-register-btn");

  if (tabBtnSignIn && tabBtnRegister) {
    tabBtnSignIn.addEventListener("click", () => {
      tabBtnSignIn.classList.add("active");
      tabBtnRegister.classList.remove("active");
      if (authPaneSignIn) authPaneSignIn.style.display = "block";
      if (authPaneRegister) authPaneRegister.style.display = "none";
      if (doLoginBtn) doLoginBtn.style.display = "inline-block";
      if (doRegisterBtn) doRegisterBtn.style.display = "none";
      if (authTitle) authTitle.textContent = "Contributor Access";
      if (authSubtitle) authSubtitle.textContent = "Sign in with your registered email";
      const statusMsg = document.getElementById("login-status-msg");
      if (statusMsg) statusMsg.style.display = "none";
    });

    tabBtnRegister.addEventListener("click", () => {
      tabBtnRegister.classList.add("active");
      tabBtnSignIn.classList.remove("active");
      if (authPaneSignIn) authPaneSignIn.style.display = "none";
      if (authPaneRegister) authPaneRegister.style.display = "block";
      if (doLoginBtn) doLoginBtn.style.display = "none";
      if (doRegisterBtn) doRegisterBtn.style.display = "inline-block";
      if (authTitle) authTitle.textContent = "Register Contributor";
      if (authSubtitle) authSubtitle.textContent = "Instant 7-Day Free Trial (15 files/day)";
      const statusMsg = document.getElementById("login-status-msg");
      if (statusMsg) statusMsg.style.display = "none";
    });
  }

  if (doLoginBtn) {
    doLoginBtn.addEventListener("click", async () => {
      const email = document.getElementById("login-email").value.trim();
      const pass = document.getElementById("login-password").value.trim();
      const statusMsg = document.getElementById("login-status-msg");

      try {
        const res = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, identifier: email, username: email, password: pass }),
        });
        const data = await res.json();
        if (data.success) {
          statusMsg.className = "activate-status-msg success";
          statusMsg.textContent = "Sign in successful!";
          statusMsg.style.display = "block";
          setTimeout(() => {
            closeModal("modal-login");
            refreshSession();
            showToast(`Welcome back, ${email}!`, "success");
          }, 800);
        } else {
          statusMsg.className = "activate-status-msg error";
          statusMsg.textContent = data.message || "Invalid login credentials.";
          statusMsg.style.display = "block";
        }
      } catch (err) {
        statusMsg.className = "activate-status-msg error";
        statusMsg.textContent = "Connection error. Please try again.";
        statusMsg.style.display = "block";
      }
    });
  }

  if (doRegisterBtn) {
    doRegisterBtn.addEventListener("click", async () => {
      const email = document.getElementById("register-email").value.trim();
      const password = document.getElementById("register-password").value.trim();
      const name = document.getElementById("register-name").value.trim();
      const statusMsg = document.getElementById("login-status-msg");

      if (!email || !email.includes("@")) {
        statusMsg.className = "activate-status-msg error";
        statusMsg.textContent = "Please enter a valid email address.";
        statusMsg.style.display = "block";
        return;
      }
      if (!password || password.length < 4) {
        statusMsg.className = "activate-status-msg error";
        statusMsg.textContent = "Please enter a password with at least 4 characters.";
        statusMsg.style.display = "block";
        return;
      }

      try {
        const res = await fetch("/api/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password, name }),
        });
        const data = await res.json();
        if (res.ok && data.success) {
          statusMsg.className = "activate-status-msg success";
          statusMsg.textContent = "ðŸŽ‰ Registration successful! 7-Day Free Trial activated.";
          statusMsg.style.display = "block";
          setTimeout(() => {
            closeModal("modal-login");
            refreshSession();
            showToast(`Welcome! 7-Day Free Trial active for ${email}`, "success");
          }, 1200);
        } else {
          statusMsg.className = "activate-status-msg error";
          statusMsg.textContent = data.error || data.message || "Registration failed.";
          statusMsg.style.display = "block";
        }
      } catch (err) {
        statusMsg.className = "activate-status-msg error";
        statusMsg.textContent = "Connection error. Please try again.";
        statusMsg.style.display = "block";
      }
    });
  }

  // ---------------- LICENSE ACTIVATION ----------------
  const doActivateBtn = document.getElementById("do-activate-btn");
  if (doActivateBtn) {
    doActivateBtn.addEventListener("click", async () => {
      const email = document.getElementById("activate-email").value.trim();
      const key = document.getElementById("activate-key").value.trim();
      const statusMsg = document.getElementById("activate-status-msg");

      if (!email || !key) {
        statusMsg.className = "activate-status-msg error";
        statusMsg.textContent = "Please provide both email address and license key.";
        statusMsg.style.display = "block";
        return;
      }

      try {
        const res = await fetch("/api/license/activate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, key, hwid: "WIN-STATION-HWID" }),
        });
        const data = await res.json();
        if (data.success) {
          statusMsg.className = "activate-status-msg success";
          statusMsg.textContent = data.message;
          statusMsg.style.display = "block";
          showToast("Pro Studio License Activated!", "success");
          setTimeout(() => {
            closeModal("modal-activate");
            refreshSession();
          }, 1200);
        } else {
          statusMsg.className = "activate-status-msg error";
          statusMsg.textContent = data.message;
          statusMsg.style.display = "block";
        }
      } catch (err) {
        statusMsg.className = "activate-status-msg error";
        statusMsg.textContent = "Activation request error.";
        statusMsg.style.display = "block";
      }
    });
  }

  // ---------------- SETTINGS DATA & SWITCHING (Upscaler Parameters) ----------------
  // Settings Panel Switcher
  const settingsNavBtns = document.querySelectorAll(".s-nav-btn[data-target]");
  const settingsPanels = document.querySelectorAll(".settings-panel-view");

  function switchSettingsPanel(target) {
    settingsNavBtns.forEach(btn => {
      btn.classList.toggle("active", btn.dataset.target === target);
    });
    document.querySelectorAll(".s-pill-btn[data-panel]").forEach(pill => {
      pill.classList.toggle("active", pill.dataset.panel === target);
    });
    settingsPanels.forEach(p => {
      p.style.display = (p.id === `panel-${target}`) ? "block" : "none";
    });
  }

  settingsNavBtns.forEach(btn => {
    btn.addEventListener("click", () => switchSettingsPanel(btn.dataset.target));
  });

  document.querySelectorAll(".s-pill-btn[data-panel]").forEach(pill => {
    pill.addEventListener("click", () => switchSettingsPanel(pill.dataset.panel));
  });

  // Readme English / Bengali Language Switcher
  document.querySelectorAll(".lang-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".lang-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const lang = btn.dataset.lang;
      const enEl = document.getElementById("readme-en");
      const bnEl = document.getElementById("readme-bn");
      if (enEl) enEl.style.display = lang === "en" ? "block" : "none";
      if (bnEl) bnEl.style.display = lang === "bn" ? "block" : "none";
    });
  });

  // Theme Picker Switcher
  document.querySelectorAll(".theme-card").forEach(card => {
    card.addEventListener("click", () => {
      document.querySelectorAll(".theme-card").forEach(c => c.classList.remove("active"));
      card.classList.add("active");
      const theme = card.dataset.theme;
      state.activeTheme = theme;
      document.documentElement.setAttribute("data-theme", theme);
      localStorage.setItem("mtk_theme", theme);
      localStorage.setItem("stockmeta_theme", theme);
      updateStockMetaLink();
      fetch("/api/user/theme", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ theme })
      }).catch(() => {});
      showToast(`Visual Theme: ${card.querySelector("span").textContent} (Synced with StockMeta Pro)`, "info");
    });
  });

  // Save Settings
  const saveSettingsBtn = document.getElementById("save-settings-btn");
  if (saveSettingsBtn) {
    saveSettingsBtn.addEventListener("click", async () => {
      const upscalerSettings = {
        video_resolution: document.getElementById("setting-video-res")?.value || "4k",
        video_codec: document.getElementById("setting-video-codec")?.value || "h264",
        video_fps: document.getElementById("setting-video-fps")?.value || "30",
        video_crf: document.getElementById("setting-video-crf")?.value || "18",
        video_mute: document.getElementById("setting-video-mute")?.checked ?? true,
        image_scale: document.getElementById("setting-image-scale")?.value || "4",
        image_resampling: document.getElementById("setting-image-resampling")?.value || "lanczos",
        image_dpi: document.getElementById("setting-image-dpi")?.value || "300",
        image_quality: document.getElementById("setting-image-quality")?.value || "95",
        psd_depth: document.getElementById("setting-psd-depth")?.value || "8",
        psd_layer_name: document.getElementById("setting-psd-layer-name")?.value || "Artwork Layer",
        hw_accel: document.getElementById("setting-hw-accel")?.value || "auto",
      };

      try {
        await fetch("/api/settings/studio", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(upscalerSettings),
        });
        localStorage.setItem("mtk_upscaler_settings", JSON.stringify(upscalerSettings));
        showToast("Studio Upscaler Settings saved and applied!", "success");
        closeModal("modal-settings");
      } catch (err) {
        showToast("Settings applied locally.", "info");
        closeModal("modal-settings");
      }
    });
  }

  const resetSettingsBtn = document.getElementById("reset-settings-btn");
  if (resetSettingsBtn) {
    resetSettingsBtn.addEventListener("click", () => {
      if (document.getElementById("setting-video-res")) document.getElementById("setting-video-res").value = "4k";
      if (document.getElementById("setting-video-codec")) document.getElementById("setting-video-codec").value = "h264";
      if (document.getElementById("setting-video-fps")) document.getElementById("setting-video-fps").value = "30";
      if (document.getElementById("setting-video-crf")) document.getElementById("setting-video-crf").value = "18";
      if (document.getElementById("setting-video-mute")) document.getElementById("setting-video-mute").checked = true;
      if (document.getElementById("setting-image-scale")) document.getElementById("setting-image-scale").value = "4";
      if (document.getElementById("setting-image-resampling")) document.getElementById("setting-image-resampling").value = "lanczos";
      if (document.getElementById("setting-image-dpi")) document.getElementById("setting-image-dpi").value = "300";
      if (document.getElementById("setting-image-quality")) document.getElementById("setting-image-quality").value = "95";
      showToast("Reset all parameters to factory defaults.", "info");
    });
  }

  // ---------------- ADMINISTRATOR CONTROL PANEL (Image 5) ----------------
  const adminTabBtns = document.querySelectorAll(".admin-tab-btn");
  const adminPanes = document.querySelectorAll(".admin-tab-pane");

  adminTabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab;
      adminTabBtns.forEach(b => b.classList.remove("active"));
      adminPanes.forEach(p => p.style.display = "none");

      btn.classList.add("active");
      const targetPane = document.getElementById(`pane-admin-${tab}`);
      if (targetPane) targetPane.style.display = "block";
    });
  });

  async function loadAdminData() {
    loadAdminKeys();
    loadAdminUsers();
    loadAdminPolicies();
    loadStorageStats();
  }

  // Refresh admin button
  const adminRefreshBtn = document.getElementById("admin-refresh-btn");
  if (adminRefreshBtn) adminRefreshBtn.addEventListener("click", () => {
    loadAdminData();
    showToast("Database refreshed.", "info");
  });

  // Pick registered email
  const pickEmailBtn = document.getElementById("quick-pick-email");
  if (pickEmailBtn) {
    pickEmailBtn.addEventListener("click", () => {
      document.getElementById("gen-email").value = pickEmailBtn.textContent.trim();
    });
  }

  // Period pills
  document.querySelectorAll("#pills-period .pill-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#pills-period .pill-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("gen-period").value = btn.dataset.val;
    });
  });

  // Limit pills
  document.querySelectorAll("#pills-limit .pill-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#pills-limit .pill-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("gen-limit").value = btn.dataset.val;
    });
  });

  // Generate Key action
  const doGenKeyBtn = document.getElementById("btn-do-generate-key");
  if (doGenKeyBtn) {
    doGenKeyBtn.addEventListener("click", async () => {
      const email = document.getElementById("gen-email").value.trim();
      const period = document.getElementById("gen-period").value.trim();
      const limit = document.getElementById("gen-limit").value.trim();
      const note = document.getElementById("gen-note").value.trim();

      if (!email) {
        showToast("Please enter user email address.", "error");
        return;
      }

      try {
        const res = await fetch("/api/admin/keys/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, period, daily_limit: limit, note }),
        });
        const data = await res.json();
        if (data.success) {
          showToast(`License Key Generated: ${data.key.key}`, "success");
          loadAdminKeys();
          loadAdminUsers();
        } else {
          showToast(data.error || "Failed to generate key", "error");
        }
      } catch (err) {
        showToast("Network error: " + err.message, "error");
      }
    });
  }

  // Load Admin Keys List
  let currentKeyFilter = "All";
  async function loadAdminKeys() {
    const searchVal = document.getElementById("search-keys-input") ? document.getElementById("search-keys-input").value.trim() : "";
    try {
      const res = await fetch(`/api/admin/keys?status=${currentKeyFilter}&search=${encodeURIComponent(searchVal)}`);
      if (!res.ok) return;
      const data = await res.json();
      const keys = data.keys || [];

      document.getElementById("admin-keys-count").textContent = data.total;
      document.getElementById("table-keys-count").textContent = data.total;

      const activeUnclaimed = keys.filter(k => k.status === "Active").length;
      document.getElementById("unclaimed-keys-pill").textContent = `${activeUnclaimed} Active Unclaimed Keys`;

      const tbody = document.getElementById("keys-table-body");
      if (!tbody) return;

      if (keys.length === 0) {
        tbody.innerHTML = `
          <tr class="empty-row">
            <td colspan="8">No license keys match your filter. Generate one above!</td>
          </tr>
        `;
        return;
      }

      let rows = "";
      keys.forEach(k => {
        let statusBadge = "badge-status-pass";
        if (k.status === "Used") statusBadge = "badge-status-info";
        if (k.status === "Revoked") statusBadge = "badge-status-fail";

        rows += `
          <tr>
            <td>
              <span class="key-code-pill">${k.key}</span>
            </td>
            <td><b>${k.assigned_email}</b></td>
            <td>${k.period_days} Days</td>
            <td>${k.daily_limit}</td>
            <td><span class="${statusBadge}">${k.status}</span></td>
            <td>${k.created_date}</td>
            <td>${k.activated_at ? `${k.activated_at} (${k.activated_hwid || 'Locked'})` : 'Unclaimed'}</td>
            <td>
              <button class="btn-table-action" onclick="copyKeyText('${k.key}')">ðŸ“‹ Copy</button>
              <button class="btn-table-action" onclick="toggleRevokeKey('${k.key}')">${k.status === 'Revoked' ? 'Restore' : 'Revoke'}</button>
              <button class="btn-table-action" onclick="deleteKey('${k.key}')" style="color:var(--danger)">ðŸ—‘ï¸</button>
            </td>
          </tr>
        `;
      });
      tbody.innerHTML = rows;
    } catch (err) {
      console.warn("Failed to load keys:", err);
    }
  }

  // Status filter pills
  document.querySelectorAll("#keys-filter-pills .status-filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#keys-filter-pills .status-filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentKeyFilter = btn.dataset.filter;
      loadAdminKeys();
    });
  });

  const searchKeysInput = document.getElementById("search-keys-input");
  if (searchKeysInput) {
    searchKeysInput.addEventListener("input", () => loadAdminKeys());
  }

  // Global window functions for table action buttons
  window.copyKeyText = (text) => {
    navigator.clipboard.writeText(text);
    showToast(`Key copied to clipboard: ${text}`, "success");
  };

  window.toggleRevokeKey = async (key) => {
    try {
      await fetch("/api/admin/keys/revoke", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key }),
      });
      showToast("License key status updated.", "info");
      loadAdminKeys();
    } catch (err) {
      showToast("Failed to update key", "error");
    }
  };

  window.deleteKey = async (key) => {
    if (!confirm(`Are you sure you want to delete key ${key}?`)) return;
    try {
      await fetch("/api/admin/keys/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key }),
      });
      showToast("License key deleted.", "info");
      loadAdminKeys();
    } catch (err) {
      showToast("Failed to delete key", "error");
    }
  };

  // Load Registered Users
  let cachedUsers = [];
  async function loadAdminUsers() {
    try {
      const res = await fetch("/api/admin/users");
      if (!res.ok) return;
      const data = await res.json();
      cachedUsers = data.users || [];

      document.getElementById("admin-users-count").textContent = data.total;

      const totalUsersEl = document.getElementById("stat-total-users");
      if (totalUsersEl) totalUsersEl.textContent = data.total;

      const activeUsersEl = document.getElementById("stat-active-users");
      if (activeUsersEl) activeUsersEl.textContent = cachedUsers.filter(u => u.status === "Active").length;

      renderUsersTable(cachedUsers);
    } catch (err) {
      console.warn("Failed to load users:", err);
    }
  }

  function renderUsersTable(users) {
    const tbody = document.getElementById("users-table-body");
    if (!tbody) return;

    const filterVal = document.getElementById("search-users-input") ? document.getElementById("search-users-input").value.trim().toLowerCase() : "";
    const filtered = filterVal ? users.filter(u => u.email.toLowerCase().includes(filterVal) || (u.name||'').toLowerCase().includes(filterVal)) : users;

    if (filtered.length === 0) {
      tbody.innerHTML = `<tr class="empty-row"><td colspan="7">No registered contributors match your search.</td></tr>`;
      return;
    }

    let rows = "";
    filtered.forEach(u => {
      const isSuspended = u.status === "Suspended";
      rows += `
        <tr>
          <td><b>${u.email}</b></td>
          <td>${u.name} <span class="badge-status-info" style="margin-left:6px;">${u.role}</span></td>
          <td>${u.license_period_days} Days (${u.license_key ? u.license_key.substring(0, 12) + 'â€¦' : 'Pending'})</td>
          <td>${u.used_today || 0} / ${u.daily_limit}</td>
          <td><code>${u.hwid || 'Unlocked'}</code></td>
          <td><span class="${isSuspended ? 'badge-status-fail' : 'badge-status-pass'}">${u.status}</span></td>
          <td>
            <button class="btn-table-action" onclick="openEditUserModal('${u.id}')">âœï¸ Edit</button>
            <button class="btn-table-action" onclick="resetUserHwid('${u.id}')">Reset HWID</button>
            <button class="btn-table-action" onclick="toggleUserSuspend('${u.id}', '${isSuspended ? 'Active' : 'Suspended'}')">${isSuspended ? 'Activate' : 'Suspend'}</button>
            <button class="btn-table-action" onclick="deleteUserAccount('${u.id}')" style="color:var(--danger)">ðŸ—‘ï¸</button>
          </td>
        </tr>
      `;
    });
    tbody.innerHTML = rows;
  }

  const searchUsersInput = document.getElementById("search-users-input");
  if (searchUsersInput) {
    searchUsersInput.addEventListener("input", () => renderUsersTable(cachedUsers));
  }

  // Add User Modal
  const btnOpenAddUser = document.getElementById("btn-open-add-user");
  const closeAddUserBtn = document.getElementById("close-add-user-btn");
  const cancelAddUserBtn = document.getElementById("cancel-add-user-btn");
  const doAddUserBtn = document.getElementById("do-add-user-btn");

  if (btnOpenAddUser) btnOpenAddUser.addEventListener("click", () => openModal("modal-add-user"));
  if (closeAddUserBtn) closeAddUserBtn.addEventListener("click", () => closeModal("modal-add-user"));
  if (cancelAddUserBtn) cancelAddUserBtn.addEventListener("click", () => closeModal("modal-add-user"));

  if (doAddUserBtn) {
    doAddUserBtn.addEventListener("click", async () => {
      const email = document.getElementById("new-user-email").value.trim();
      const name = document.getElementById("new-user-name").value.trim();
      const role = document.getElementById("new-user-role").value;
      const limit = document.getElementById("new-user-limit").value;

      if (!email) {
        showToast("Email address is required.", "error");
        return;
      }

      try {
        const res = await fetch("/api/admin/users/add", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, name, role, daily_limit: limit }),
        });
        const data = await res.json();
        if (data.success) {
          showToast(`Contributor ${email} registered!`, "success");
          closeModal("modal-add-user");
          loadAdminUsers();
        } else {
          showToast(data.error || "Failed to add user", "error");
        }
      } catch (err) {
        showToast("Error: " + err.message, "error");
      }
    });
  }

  // Edit User Modal
  window.openEditUserModal = (userId) => {
    const user = cachedUsers.find(u => u.id === userId || u.email === userId);
    if (!user) return;

    document.getElementById("edit-user-id").value = user.id;
    document.getElementById("edit-user-email").value = user.email;
    document.getElementById("edit-user-name").value = user.name || "";
    document.getElementById("edit-user-days").value = user.license_period_days || 30;
    document.getElementById("edit-user-limit").value = user.daily_limit || 50;
    document.getElementById("edit-user-status").value = user.status || "Active";

    openModal("modal-edit-user");
  };

  const closeEditUserBtn = document.getElementById("close-edit-user-btn");
  const cancelEditUserBtn = document.getElementById("cancel-edit-user-btn");
  const doSaveEditUserBtn = document.getElementById("do-save-edit-user-btn");

  if (closeEditUserBtn) closeEditUserBtn.addEventListener("click", () => closeModal("modal-edit-user"));
  if (cancelEditUserBtn) cancelEditUserBtn.addEventListener("click", () => closeModal("modal-edit-user"));

  if (doSaveEditUserBtn) {
    doSaveEditUserBtn.addEventListener("click", async () => {
      const userId = document.getElementById("edit-user-id").value;
      const updates = {
        user_id: userId,
        name: document.getElementById("edit-user-name").value.trim(),
        license_period_days: document.getElementById("edit-user-days").value,
        daily_limit: document.getElementById("edit-user-limit").value,
        status: document.getElementById("edit-user-status").value,
      };

      try {
        const res = await fetch("/api/admin/users/edit", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(updates),
        });
        const data = await res.json();
        if (data.success) {
          showToast("User details updated!", "success");
          closeModal("modal-edit-user");
          loadAdminUsers();
        } else {
          showToast(data.error || "Failed to update", "error");
        }
      } catch (err) {
        showToast("Error: " + err.message, "error");
      }
    });
  }

  window.toggleUserSuspend = async (userId, newStatus) => {
    try {
      await fetch("/api/admin/users/status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, status: newStatus }),
      });
      showToast(`User status set to ${newStatus}.`, "info");
      loadAdminUsers();
    } catch (err) {
      showToast("Error updating user status", "error");
    }
  };

  window.deleteUserAccount = async (userId) => {
    if (!confirm("Are you sure you want to delete this contributor account?")) return;
    try {
      await fetch("/api/admin/users/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId }),
      });
      showToast("User removed from database.", "info");
      loadAdminUsers();
    } catch (err) {
      showToast("Error deleting user", "error");
    }
  };

  // Storage Stats & Cache Hygiene
  async function loadStorageStats() {
    try {
      const res = await fetch("/api/admin/stats");
      if (!res.ok) return;
      const stats = await res.json();

      const upMb = document.getElementById("disk-uploads-mb");
      if (upMb) upMb.textContent = `${stats.uploads_size_mb} MB (${stats.uploads_count} files)`;

      const outMb = document.getElementById("disk-outputs-mb");
      if (outMb) outMb.textContent = `${stats.outputs_size_mb} MB (${stats.outputs_count} files)`;

      const totalKeysEl = document.getElementById("disk-total-keys");
      if (totalKeysEl) totalKeysEl.textContent = stats.total_keys;

      const diskMb = document.getElementById("stat-disk-mb");
      if (diskMb) diskMb.textContent = `${stats.total_disk_mb} MB`;

      const unclaimedEl = document.getElementById("stat-unclaimed-keys");
      if (unclaimedEl) unclaimedEl.textContent = stats.active_unclaimed_keys;
    } catch (err) {
      console.warn("Storage stats error:", err);
    }
  }

  const btnPurgeCache = document.getElementById("btn-purge-cache");
  if (btnPurgeCache) {
    btnPurgeCache.addEventListener("click", async () => {
      if (!confirm("Purge temporary uploads and outputs to reclaim disk space?")) return;
      try {
        const res = await fetch("/api/admin/purge-cache", { method: "POST" });
        const data = await res.json();
        showToast(`Cache purged: ${data.files_removed} files removed.`, "success");
        loadStorageStats();
      } catch (err) {
        showToast("Failed to purge cache", "error");
      }
    });
  }

  const btnFactoryReset = document.getElementById("btn-factory-reset");
  if (btnFactoryReset) {
    btnFactoryReset.addEventListener("click", async () => {
      const pin = prompt("DANGER: Factory reset will reset all license keys and contributors. Type 'RESET' to confirm:");
      if (pin !== "RESET") return;
      try {
        await fetch("/api/admin/factory-reset", { method: "POST" });
        showToast("System store reset to factory clean state.", "info");
        loadAdminData();
      } catch (err) {
        showToast("Reset failed: " + err.message, "error");
      }
    });
  }

  // Admin Guide Sub Navigation
  document.querySelectorAll(".guide-nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".guide-nav-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".guide-card-section").forEach(s => s.classList.remove("active"));

      btn.classList.add("active");
      const targetSec = document.getElementById(`guide-sec-${btn.dataset.guide}`);
      if (targetSec) targetSec.classList.add("active");
    });
  });

  // Open in Windows Explorer Button
  ["video", "image", "psd"].forEach(tool => {
    const folderBtn = document.getElementById(`btn-open-folder-${tool}`);
    if (folderBtn) {
      folderBtn.addEventListener("click", async () => {
        const jobId = state[tool].currentJobId;
        if (!jobId) return;
        try {
          const res = await fetch(`/api/open-folder/${jobId}`, { method: "POST" });
          if (res.ok) {
            showToast("Opening folder in Windows Explorerâ€¦", "success");
          } else {
            showToast("Could not open folder directly.", "info");
          }
        } catch (err) {
          showToast("Explorer request error", "error");
        }
      });
    }
  });

  window.resetUserHwid = async (userId) => {
    try {
      await fetch("/api/admin/users/reset-hwid", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId }),
      });
      showToast("Hardware lock reset for contributor.", "success");
      loadAdminUsers();
    } catch (err) {
      showToast("Failed to reset HWID", "error");
    }
  };

  // Policies
  async function loadAdminPolicies() {
    try {
      const res = await fetch("/api/admin/policies");
      if (!res.ok) return;
      const pol = await res.json();
      document.getElementById("policy-default-days").value = pol.default_access_period_days || 30;
      document.getElementById("policy-default-limit").value = pol.default_daily_limit || 50;
      document.getElementById("policy-max-duration").value = pol.max_video_duration_sec || 120;
      document.getElementById("policy-admin-email").value = pol.master_admin_email || "bulbulworka1@gmail.com";
      document.getElementById("policy-enforce-hwid").checked = pol.enforce_single_device !== false;
      document.getElementById("policy-allow-offline").checked = pol.allow_offline_validation !== false;
    } catch (err) {
      console.warn("Failed to load policies:", err);
    }
  }

  const savePoliciesBtn = document.getElementById("btn-save-policies");
  if (savePoliciesBtn) {
    savePoliciesBtn.addEventListener("click", async () => {
      const pol = {
        default_access_period_days: parseInt(document.getElementById("policy-default-days").value) || 30,
        default_daily_limit: parseInt(document.getElementById("policy-default-limit").value) || 50,
        max_video_duration_sec: parseInt(document.getElementById("policy-max-duration").value) || 120,
        master_admin_email: document.getElementById("policy-admin-email").value,
        enforce_single_device: document.getElementById("policy-enforce-hwid").checked,
        allow_offline_validation: document.getElementById("policy-allow-offline").checked,
      };

      try {
        await fetch("/api/admin/policies", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(pol),
        });
        showToast("System policies successfully saved!", "success");
      } catch (err) {
        showToast("Failed to save policies: " + err.message, "error");
      }
    });
  }

  // Backup & Restore
  const restoreTriggerBtn = document.getElementById("btn-trigger-restore");
  const backupFileInput = document.getElementById("backup-file-input");
  if (restoreTriggerBtn && backupFileInput) {
    restoreTriggerBtn.addEventListener("click", () => backupFileInput.click());
    backupFileInput.addEventListener("change", async () => {
      if (!backupFileInput.files || backupFileInput.files.length === 0) return;
      const file = backupFileInput.files[0];
      const fd = new FormData();
      fd.append("backup_file", file);

      try {
        const res = await fetch("/api/admin/restore", { method: "POST", body: fd });
        const data = await res.json();
        if (data.success) {
          showToast("Database restored successfully!", "success");
          loadAdminData();
        } else {
          showToast("Restore failed: " + data.error, "error");
        }
      } catch (err) {
        showToast("Error uploading backup: " + err.message, "error");
      }
    });
  }

  // Utility helper to hide elements
  function hideElement(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = "none";
  }
});

  // PSD Canvas Size Custom Toggle
  const psdCanvasSelect = document.getElementById("psd-canvas-size");
  const psdCustomDimRow = document.getElementById("psd-custom-dim-row");
  if (psdCanvasSelect && psdCustomDimRow) {
    psdCanvasSelect.addEventListener("change", () => {
      psdCustomDimRow.style.display = (psdCanvasSelect.value === "custom") ? "flex" : "none";
    
  // -----------------------------------------------------------------------------
  // AI Stock Rejection Inspector Logic
  // -----------------------------------------------------------------------------
  async function loadAiConfig() {
    try {
      const res = await fetch("/api/ai/config");
      if (res.ok) {
        const data = await res.json();
        const geminiInput = document.getElementById("setting-gemini-key");
        const grokInput = document.getElementById("setting-grok-key");
        const modelSelect = document.getElementById("setting-ai-model");
        const providerSelect = document.getElementById("setting-ai-provider");
        const statusPill = document.getElementById("ai-key-status-pill");

        if (geminiInput && data.gemini_masked) {
          geminiInput.placeholder = `Saved: ${data.gemini_masked}`;
        }
        if (grokInput && data.grok_masked) {
          grokInput.placeholder = `Saved: ${data.grok_masked}`;
        }
        if (modelSelect && data.model) modelSelect.value = data.model;
        if (providerSelect && data.provider) providerSelect.value = data.provider;

        const chkTrademarks = document.getElementById("setting-check-trademarks");
        const chkModel = document.getElementById("setting-check-model-release");
        const chkProperty = document.getElementById("setting-check-property-release");

        if (chkTrademarks && data.check_trademarks !== undefined) chkTrademarks.checked = data.check_trademarks;
        if (chkModel && data.check_model_release !== undefined) chkModel.checked = data.check_model_release;
        if (chkProperty && data.check_property_release !== undefined) chkProperty.checked = data.check_property_release;

        if (statusPill) {
          if (data.has_gemini) {
            statusPill.textContent = "âœ“ Gemini Connected";
            statusPill.style.background = "rgba(16, 185, 129, 0.2)";
            statusPill.style.color = "#10b981";
          } else {
            statusPill.textContent = "Key Needed";
            statusPill.style.background = "rgba(245, 158, 11, 0.2)";
            statusPill.style.color = "#f59e0b";
          }
        }
      }
    } catch (e) {
      console.warn("Could not load AI configuration", e);
    }
  }

  const btnSaveAiSettings = document.getElementById("btn-save-ai-settings");
  if (btnSaveAiSettings) {
    btnSaveAiSettings.addEventListener("click", async () => {
      const msgEl = document.getElementById("ai-settings-msg");
      if (msgEl) msgEl.textContent = "Saving AI settings...";

      const payload = {
        gemini_api_key: (document.getElementById("setting-gemini-key")?.value || "").trim(),
        grok_api_key: (document.getElementById("setting-grok-key")?.value || "").trim(),
        model: document.getElementById("setting-ai-model")?.value || "gemini-1.5-flash",
        provider: document.getElementById("setting-ai-provider")?.value || "gemini",
        check_trademarks: document.getElementById("setting-check-trademarks")?.checked ?? true,
        check_model_release: document.getElementById("setting-check-model-release")?.checked ?? true,
        check_property_release: document.getElementById("setting-check-property-release")?.checked ?? true
      };

      try {
        const res = await fetch("/api/ai/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
          if (msgEl) {
            msgEl.textContent = "âœ“ Settings saved successfully!";
            msgEl.style.color = "#10b981";
          }
          await loadAiConfig();
        } else {
          if (msgEl) {
            msgEl.textContent = data.error || "Failed to save AI settings.";
            msgEl.style.color = "#ef4444";
          }
        }
      } catch (err) {
        if (msgEl) {
          msgEl.textContent = "Network error saving AI settings.";
          msgEl.style.color = "#ef4444";
        }
      }
    });
  }

  // AI Inspector Runner
  async function runAiInspection(tool) {
    const fileInput = document.getElementById(`file-${tool}`);
    const file = fileInput && fileInput.files && fileInput.files[0];
    if (!file) {
      alert("Please choose or upload a media file first before running the AI Inspector.");
      return;
    }

    openModal("modal-ai-inspector");
    const loadingEl = document.getElementById("ai-inspector-loading");
    const promptEl = document.getElementById("ai-config-prompt");
    const reportEl = document.getElementById("ai-inspector-report");
    const modalBadge = document.getElementById("ai-modal-status-badge");

    if (loadingEl) loadingEl.style.display = "block";
    if (promptEl) promptEl.style.display = "none";
    if (reportEl) reportEl.style.display = "none";
    if (modalBadge) modalBadge.textContent = "Analyzing Assetâ€¦";

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/ai/inspect", {
        method: "POST",
        body: formData
      });
      const data = await res.json();

      if (loadingEl) loadingEl.style.display = "none";

      if (data.is_config_needed) {
        if (promptEl) promptEl.style.display = "block";
        if (modalBadge) modalBadge.textContent = "API Key Required";
        return;
      }

      if (!data.success) {
        alert("AI Inspection Notice: " + (data.error || "Unable to analyze media."));
        closeModal("modal-ai-inspector");
        return;
      }

      // Render Inspection Report
      if (reportEl) reportEl.style.display = "block";
      if (modalBadge) modalBadge.textContent = `${data.provider || "Gemini"} Verified`;

      // Verdict Banner
      const verdictBanner = document.getElementById("ai-verdict-banner");
      const verdictIcon = document.getElementById("ai-verdict-icon");
      const verdictStatus = document.getElementById("ai-verdict-status");
      const verdictSummary = document.getElementById("ai-verdict-summary");

      const verdict = (data.verdict || "PASS").toUpperCase();
      if (verdictBanner) {
        verdictBanner.className = "ai-verdict-banner " + 
          (verdict === "PASS" ? "verdict-pass" : (verdict === "CAUTION" ? "verdict-caution" : "verdict-reject"));
      }
      if (verdictIcon) {
        verdictIcon.textContent = verdict === "PASS" ? "âœ“" : (verdict === "CAUTION" ? "âš ï¸" : "âœ•");
      }
      if (verdictStatus) {
        verdictStatus.textContent = verdict === "PASS" ? "COMMERCIAL PASS" : (verdict === "CAUTION" ? "CAUTION: REVIEW NEEDED" : "REJECT HAZARD DETECTED");
      }
      if (verdictSummary) {
        verdictSummary.textContent = data.summary || "No critical stock rejection hazards found.";
      }

      // Pillar 1: Trademarks
      const badgeTrademarks = document.getElementById("badge-pillar-trademarks");
      const bodyTrademarks = document.getElementById("body-pillar-trademarks");
      const trademarks = data.trademarks || [];
      if (badgeTrademarks) {
        badgeTrademarks.textContent = trademarks.length > 0 ? `${trademarks.length} LOGOS` : "PASS";
        badgeTrademarks.className = "pillar-badge " + (trademarks.length > 0 ? "badge-hazard" : "");
      }
      if (bodyTrademarks) {
        if (trademarks.length > 0) {
          bodyTrademarks.innerHTML = trademarks.map(t => `
            <div style="margin-bottom:8px; padding-bottom:6px; border-bottom:1px solid rgba(255,255,255,0.05);">
              <b style="color:#ef4444;">${t.name}</b> (${t.location || "visible"})<br>
              <span style="font-size:0.75rem; color:var(--text-dim);">${t.fix || "Clone stamp or remove"}</span>
            </div>
          `).join("");
        } else {
          bodyTrademarks.innerHTML = '<span class="pillar-empty">âœ“ No commercial brand logos or trademarks detected.</span>';
        }
      }

      // Pillar 2: Model Release
      const badgeModel = document.getElementById("badge-pillar-model");
      const bodyModel = document.getElementById("body-pillar-model");
      const faces = data.faces_detected || [];
      const modelNeeded = data.model_release_needed;
      if (badgeModel) {
        badgeModel.textContent = modelNeeded ? "RELEASE REQ" : "NONE";
        badgeModel.className = "pillar-badge " + (modelNeeded ? "badge-warn" : "");
      }
      if (bodyModel) {
        if (faces.length > 0) {
          bodyModel.innerHTML = faces.map(f => `
            <div style="margin-bottom:6px;">
              <b>${f.description || "Identifiable person"}</b><br>
              <span style="font-size:0.75rem; color:var(--text-dim);">${f.requires_release ? "Requires signed Model Release" : "Feature obscured / no release needed"}</span>
            </div>
          `).join("");
        } else {
          bodyModel.innerHTML = '<span class="pillar-empty">âœ“ No recognizable human faces or people detected.</span>';
        }
      }

      // Pillar 3: Property Release
      const badgeProperty = document.getElementById("badge-pillar-property");
      const bodyProperty = document.getElementById("body-pillar-property");
      const properties = data.properties_detected || [];
      const propNeeded = data.property_release_needed;
      if (badgeProperty) {
        badgeProperty.textContent = propNeeded ? "RELEASE REQ" : "NONE";
        badgeProperty.className = "pillar-badge " + (propNeeded ? "badge-warn" : "");
      }
      if (bodyProperty) {
        if (properties.length > 0) {
          bodyProperty.innerHTML = properties.map(p => `
            <div style="margin-bottom:6px;">
              <b>${p.description || "Architectural property"}</b><br>
              <span style="font-size:0.75rem; color:var(--text-dim);">${p.reason || "Requires Property Release"}</span>
            </div>
          `).join("");
        } else {
          bodyProperty.innerHTML = '<span class="pillar-empty">âœ“ No copyrighted modern architecture or sculptures detected.</span>';
        }
      }

      // Recommendations List
      const recList = document.getElementById("ai-recommendations-list");
      if (recList) {
        const recs = data.recommendations || [];
        if (recs.length > 0) {
          recList.innerHTML = recs.map(r => `<li>${r}</li>`).join("");
        } else {
          recList.innerHTML = '<li>Asset is clean and complies with Adobe Stock & Freepik guidelines.</li>';
        }
      }

    } catch (err) {
      if (loadingEl) loadingEl.style.display = "none";
      alert("Error executing AI inspection: " + err.message);
    }
  }

  // Wire AI Inspect Trigger Buttons
  const btnAiInspectVideo = document.getElementById("btn-ai-inspect-video");
  if (btnAiInspectVideo) btnAiInspectVideo.addEventListener("click", () => runAiInspection("video"));

  const btnAiInspectImg = document.getElementById("btn-ai-inspect-image");
  if (btnAiInspectImg) btnAiInspectImg.addEventListener("click", () => runAiInspection("image"));

  const btnAiInspectPsd = document.getElementById("btn-ai-inspect-psd");
  if (btnAiInspectPsd) btnAiInspectPsd.addEventListener("click", () => runAiInspection("psd"));

  // Wire modal close & modal settings jump
  const closeAiInspectorBtn = document.getElementById("close-ai-inspector-btn");
  if (closeAiInspectorBtn) closeAiInspectorBtn.addEventListener("click", () => closeModal("modal-ai-inspector"));

  const btnOpenAiFromModal = document.getElementById("btn-open-ai-settings-from-modal");
  if (btnOpenAiFromModal) {
    btnOpenAiFromModal.addEventListener("click", () => {
      closeModal("modal-ai-inspector");
      openModal("modal-settings");
      switchSettingsPanel("ai_settings");
      loadAiConfig();
    });
  }

  // When settings modal opens, also load AI config
  if (openSettingsBtn) {
    openSettingsBtn.addEventListener("click", () => {
      loadAiConfig();
    });
  }


  // -----------------------------------------------------------------------
  // Stock Contributor Toolkit Panel — iFrame loader
  // -----------------------------------------------------------------------
  let toolkitLoaded = false;

  function loadToolkitPanel() {
    const iframe = document.getElementById("toolkit-iframe");
    const loader = document.getElementById("toolkit-iframe-loading");
    const banner = document.getElementById("toolkit-not-running-banner");
    if (!iframe) return;

    if (banner) banner.style.display = "none";

    if (!iframe.src || iframe.src.endsWith("about:blank") || iframe.src.endsWith("/")) {
      if (!iframe.src.includes("/toolkit/")) {
        iframe.src = "/toolkit/";
      }
    }

    // Dismiss loader smoothly within 1.5s max
    setTimeout(() => {
      if (loader) {
        loader.classList.add("hidden");
        loader.style.display = "none";
      }
    }, 1500);
  }

  // Hide loading spinner when iframe finishes loading
  const toolkitIframe = document.getElementById("toolkit-iframe");
  if (toolkitIframe) {
    toolkitIframe.addEventListener("load", () => {
      const loader = document.getElementById("toolkit-iframe-loading");
      if (loader && toolkitIframe.src && !toolkitIframe.src.endsWith("about:blank")) {
        loader.classList.add("hidden");
        loader.style.display = "none";
        toolkitLoaded = true;
      }
    });
  }

  // Wire the toolkit tab button
  const toolkitTabBtn = document.querySelector('.tab-btn[data-tool="toolkit"]');
  if (toolkitTabBtn) {
    toolkitTabBtn.addEventListener("click", () => {
      loadToolkitPanel();
    });
  }
});
  }
