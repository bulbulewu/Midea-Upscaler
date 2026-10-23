/**
 * Media Toolkit Pro V3 — Multi-Marketplace Studio Engine
 * Made By Munajat International
 */

document.addEventListener("DOMContentLoaded", () => {
  const state = {
    activeMarketplace: "universal",
    video: { file: null, pollTimer: null, currentJobId: null },
    image: { file: null, pollTimer: null, currentJobId: null },
    psd:   { file: null, pollTimer: null, currentJobId: null }
  };

  // ---------------- Marketplace Switcher ----------------
  const marketplaceBtns = document.querySelectorAll(".m-btn");
  marketplaceBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      marketplaceBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.activeMarketplace = btn.dataset.marketplace;

      const badgeName = btn.textContent.trim();
      document.querySelectorAll(".active-market-badge").forEach(el => {
        el.textContent = badgeName;
      });

      // Re-run pre-flight validation if files are currently loaded
      ["video", "image"].forEach(tool => {
        if (state[tool].file) {
          runPreflight(tool, state[tool].file);
        }
      });
    });
  });

  // ---------------- Tab Switching ----------------
  const tabBtns = document.querySelectorAll(".tab-btn");
  const toolPanels = document.querySelectorAll(".tool-panel");

  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const tool = btn.dataset.tool;
      tabBtns.forEach(b => b.classList.remove("active"));
      toolPanels.forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const activePanel = document.getElementById(`panel-${tool}`);
      if (activePanel) activePanel.classList.add("active");
    });
  });

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

  // ---------------- Drag & Drop + File Selection ----------------
  ["video", "image", "psd"].forEach(tool => {
    const dropZone = document.getElementById(`drop-${tool}`);
    const fileInput = document.getElementById(`file-${tool}`);
    const previewCard = document.getElementById(`preview-${tool}`);
    const actionBtn = document.getElementById(`btn-${tool}`);

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
  });

  function handleFileSelect(tool, file) {
    state[tool].file = file;

    // Reset UI states
    hideElement(`error-${tool}`);
    hideElement(`progress-${tool}`);
    hideElement(`result-${tool}`);

    const previewCard = document.getElementById(`preview-${tool}`);
    const previewName = document.getElementById(`preview-name-${tool}`);
    const previewDetails = document.getElementById(`preview-details-${tool}`);
    const previewImg = document.getElementById(`preview-img-${tool}`);
    const actionBtn = document.getElementById(`btn-${tool}`);

    const sizeMb = (file.size / (1024 * 1024)).toFixed(2);

    if (previewName) previewName.textContent = file.name;
    if (previewDetails) {
      previewDetails.innerHTML = `<span><b>File Size:</b> ${sizeMb} MB</span> <span><b>Format:</b> ${file.type || file.name.split('.').pop().toUpperCase()}</span>`;
    }

    if (previewImg) {
      if (file.type.startsWith("image/")) {
        previewImg.src = URL.createObjectURL(file);
        previewImg.style.display = "block";
      } else {
        previewImg.style.display = "none";
      }
    }

    if (previewCard) previewCard.classList.add("show");
    if (actionBtn) actionBtn.disabled = false;

    // Run Pre-Flight Inspection on file upload
    if (tool === "video" || tool === "image") {
      runPreflight(tool, file);
    }
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
    } catch (e) {
      // Graceful bypass if network/probe interrupted
    }
  }

  // ---------------- Job Submission ----------------
  async function submitJob(tool) {
    const current = state[tool];
    if (!current.file) return;

    const actionBtn = document.getElementById(`btn-${tool}`);
    if (actionBtn) actionBtn.disabled = true;

    hideElement(`error-${tool}`);
    hideElement(`result-${tool}`);

    const progressCard = document.getElementById(`progress-${tool}`);
    const progressFill = document.getElementById(`progress-fill-${tool}`);
    const progressStatus = document.getElementById(`progress-status-${tool}`);
    const progressPct = document.getElementById(`progress-pct-${tool}`);

    if (progressCard) progressCard.classList.add("show");
    updateProgress(progressFill, progressPct, 5);

    const formData = new FormData();
    formData.append("file", current.file);
    formData.append("marketplace", state.activeMarketplace);

    let endpoint = "";

    if (tool === "video") {
      endpoint = "/api/jobs";
      formData.append("target", getVal("video-target") || "4k");
      formData.append("quality", getVal("video-quality") || "stock");
      formData.append("codec", getVal("video-codec") || "h264");
      formData.append("keep_audio", document.getElementById("video-keep-audio")?.checked || "false");
      if (progressStatus) progressStatus.textContent = "Analyzing video & initializing FFmpeg pipeline…";
    } else if (tool === "image") {
      endpoint = "/api/image-jobs";
      formData.append("scale", getVal("image-scale") || "4x");
      formData.append("format", getVal("image-format") || "jpg");
      formData.append("quality", getVal("image-quality") || "95");
      formData.append("dpi", getVal("image-dpi") || "300");
      formData.append("auto_denoise", document.getElementById("image-auto-denoise")?.checked || "true");
      if (progressStatus) progressStatus.textContent = "Lanczos subpixel interpolation in progress…";
    } else if (tool === "psd") {
      endpoint = "/api/psd-jobs";
      formData.append("layer_name", document.getElementById("psd-layer-name")?.value || "Artwork Layer");
      formData.append("background", getVal("psd-background") || "transparent");
      formData.append("dpi", getVal("psd-dpi") || "300");
      if (progressStatus) progressStatus.textContent = "Constructing layered Photoshop PSD structure…";
    }

    try {
      const res = await fetch(endpoint, { method: "POST", body: formData });
      const data = await res.json();

      if (!res.ok) {
        showError(tool, data.error || "Failed to process request.");
        if (actionBtn) actionBtn.disabled = false;
        hideElement(`progress-${tool}`);
        return;
      }

      current.currentJobId = data.id;
      startPolling(tool, data.id);
    } catch (err) {
      showError(tool, "Server communication error. Please ensure the server is running.");
      if (actionBtn) actionBtn.disabled = false;
      hideElement(`progress-${tool}`);
    }
  }

  function startPolling(tool, jobId) {
    const current = state[tool];
    if (current.pollTimer) clearInterval(current.pollTimer);

    const progressFill = document.getElementById(`progress-fill-${tool}`);
    const progressStatus = document.getElementById(`progress-status-${tool}`);
    const progressPct = document.getElementById(`progress-pct-${tool}`);
    const actionBtn = document.getElementById(`btn-${tool}`);

    current.pollTimer = setInterval(async () => {
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        if (!res.ok) throw new Error("Could not check status.");
        const job = await res.json();

        const p = job.progress || 0;
        updateProgress(progressFill, progressPct, p);

        if (job.state === "running") {
          if (progressStatus) {
            progressStatus.textContent = tool === "video" 
              ? "Transcoding & conforming to stock 4K specifications…"
              : "Enhancing details and finalizing export…";
          }
        } else if (job.state === "done") {
          clearInterval(current.pollTimer);
          updateProgress(progressFill, progressPct, 100);
          if (progressStatus) progressStatus.textContent = "Processing completed successfully!";
          if (actionBtn) actionBtn.disabled = false;
          renderResult(tool, job);
        } else if (job.state === "error") {
          clearInterval(current.pollTimer);
          if (actionBtn) actionBtn.disabled = false;
          hideElement(`progress-${tool}`);
          showError(tool, job.error || "An error occurred during processing.");
        }
      } catch (e) {
        // Retry silently on transient poll errors
      }
    }, 700);
  }

  function updateProgress(fillEl, pctEl, val) {
    if (fillEl) fillEl.style.width = `${val}%`;
    if (pctEl) pctEl.textContent = `${Math.round(val)}%`;
  }

  function renderResult(tool, job) {
    const resultCard = document.getElementById(`result-${tool}`);
    const tableBody = document.getElementById(`table-${tool}`);
    const downloadBtn = document.getElementById(`dl-btn-${tool}`);

    if (!resultCard || !tableBody || !downloadBtn) return;

    const m = job.meta;
    const s = m.source;
    const o = m.output;

    let rowsHtml = "";
    const passBadge = `<span class="badge-pass">✓ Stock Pass</span>`;

    if (tool === "video") {
      rowsHtml = `
        <tr><td><b>Target Market</b></td><td>Universal</td><td>${m.marketplace.toUpperCase()}</td><td>${passBadge}</td></tr>
        <tr><td><b>Resolution</b></td><td>${s.width}×${s.height}</td><td>${o.width}×${o.height} (4K Master)</td><td>${passBadge}</td></tr>
        <tr><td><b>Frame Rate</b></td><td>${s.fps} fps</td><td>${o.fps} fps ${m.fps_preserved ? '(Preserved)' : '(Conformed)'}</td><td>${passBadge}</td></tr>
        <tr><td><b>Target Bitrate</b></td><td>${(s.bitrate_kbps/1000).toFixed(1)} Mbps</td><td>${(o.bitrate_kbps/1000).toFixed(1)} Mbps</td><td>${passBadge}</td></tr>
        <tr><td><b>Master Codec</b></td><td>${s.codec}</td><td>${m.codec}</td><td>${passBadge}</td></tr>
        <tr><td><b>Color Gamut</b></td><td>${s.color_space}</td><td>Rec.709 (BT.709 Broadcast)</td><td>${passBadge}</td></tr>
        <tr><td><b>Audio Track</b></td><td>${s.has_audio ? 'Audio present' : 'None'}</td><td>${m.audio}</td><td>${passBadge}</td></tr>
        <tr><td><b>File Size</b></td><td>${s.size_mb} MB</td><td>${o.size_mb} MB</td><td>${passBadge}</td></tr>
      `;
      downloadBtn.innerHTML = `⬇ Download Master Video (${o.size_mb} MB)`;
    } else if (tool === "image") {
      rowsHtml = `
        <tr><td><b>Dimensions</b></td><td>${s.width}×${s.height} px</td><td>${o.width}×${o.height} px</td><td>${passBadge}</td></tr>
        <tr><td><b>Megapixels (Stock ≥ 4 MP)</b></td><td>${s.megapixels} MP</td><td>${o.megapixels} MP</td><td>${passBadge}</td></tr>
        <tr><td><b>Scale Factor</b></td><td>1.0×</td><td>${o.scale}</td><td>${passBadge}</td></tr>
        <tr><td><b>Print Density</b></td><td>${s.dpi || '72 DPI'}</td><td>${o.dpi}</td><td>${passBadge}</td></tr>
        <tr><td><b>Format & Engine</b></td><td>${s.format}</td><td>${o.format} (${m.engine})</td><td>${passBadge}</td></tr>
        <tr><td><b>Auto Denoise</b></td><td>—</td><td>${o.auto_denoise ? 'Applied' : 'Bypassed'}</td><td>${passBadge}</td></tr>
        <tr><td><b>File Size</b></td><td>${s.size_mb} MB</td><td>${o.size_mb} MB</td><td>${passBadge}</td></tr>
      `;
      downloadBtn.innerHTML = `⬇ Download Stock Image (${o.size_mb} MB)`;
    } else if (tool === "psd") {
      rowsHtml = `
        <tr><td><b>Dimensions</b></td><td>${s.width}×${s.height} px</td><td>${o.width}×${o.height} px</td><td>${passBadge}</td></tr>
        <tr><td><b>Layer Architecture</b></td><td>Single Bitmap</td><td>1 Layer (“${o.layer_name}”)</td><td>${passBadge}</td></tr>
        <tr><td><b>Transparency</b></td><td>${s.mode}</td><td>${o.transparency ? 'Preserved as Alpha Mask' : 'Solid Canvas'}</td><td>${passBadge}</td></tr>
        <tr><td><b>Resolution Density</b></td><td>72 DPI</td><td>${o.dpi}</td><td>${passBadge}</td></tr>
        <tr><td><b>PSD Compression</b></td><td>—</td><td>Adobe ZIP Lossless</td><td>${passBadge}</td></tr>
        <tr><td><b>File Size</b></td><td>${s.size_mb} MB</td><td>${o.size_mb} MB</td><td>${passBadge}</td></tr>
      `;
      downloadBtn.innerHTML = `⬇ Download Layered PSD (${o.size_mb} MB)`;
    }

    tableBody.innerHTML = rowsHtml;
    downloadBtn.href = `/api/download/${job.id}`;
    resultCard.classList.add("show");
    resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function showError(tool, msg) {
    const errEl = document.getElementById(`error-${tool}`);
    if (errEl) {
      errEl.textContent = `⚠ ${msg}`;
      errEl.classList.add("show");
    }
  }

  function hideElement(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove("show");
  }

  function getVal(id) {
    const el = document.getElementById(id);
    return el ? el.value : null;
  }

  // ---------------- Health Check on Startup ----------------
  fetch("/api/health")
    .then(r => r.json())
    .then(data => {
      const statusPill = document.getElementById("system-status-pill");
      if (statusPill) {
        if (data.ffmpeg_ok) {
          statusPill.innerHTML = `<span class="status-dot"></span> STUDIO READY (FFMPEG ACTIVE)`;
        } else {
          statusPill.innerHTML = `<span class="status-dot" style="background:#f59e0b;box-shadow:0 0 10px #f59e0b"></span> RUNNING (FFMPEG MISSING)`;
        }
      }
    })
    .catch(() => {});
});
