const APP_URL = "http://localhost:8501";
const WRAPPER_ID = "ytd-studio-download-buttons";

function currentVideoUrl() {
  const url = new URL(window.location.href);
  const videoId = url.searchParams.get("v");
  if (!videoId) return "";
  return `https://www.youtube.com/watch?v=${encodeURIComponent(videoId)}`;
}

function openDownloader(mode) {
  const videoUrl = currentVideoUrl();
  if (!videoUrl) return;
  const target = new URL(APP_URL);
  target.searchParams.set("url", videoUrl);
  target.searchParams.set("quality", "720p");
  target.searchParams.set("mode", mode);
  target.searchParams.set("auto", "1");
  window.open(target.toString(), "_blank", "noopener,noreferrer");
}

function buttonStyle() {
  return [
    "align-items:center",
    "background:linear-gradient(135deg,#f472b6,#38bdf8)",
    "border:0",
    "border-radius:999px",
    "box-shadow:0 8px 22px rgba(244,114,182,.34)",
    "color:#ffffff",
    "cursor:pointer",
    "display:inline-flex",
    "font-family:'Segoe UI Emoji','Segoe UI Symbol',Roboto,Arial,sans-serif",
    "font-size:18px",
    "font-weight:800",
    "height:36px",
    "justify-content:center",
    "line-height:1",
    "padding:0",
    "width:38px"
  ].join(";");
}

function makeIconButton(label, title, mode) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.title = title;
  button.setAttribute("aria-label", title);
  button.addEventListener("click", () => openDownloader(mode));
  button.style.cssText = buttonStyle();
  return button;
}

function makeWrapper() {
  const wrapper = document.createElement("div");
  wrapper.id = WRAPPER_ID;
  wrapper.style.cssText = [
    "align-items:center",
    "display:inline-flex",
    "gap:6px",
    "margin-left:8px"
  ].join(";");
  wrapper.appendChild(makeIconButton("🎬", "Download 720p video", "video"));
  wrapper.appendChild(makeIconButton("🎵", "Download MP3 audio", "audio"));
  return wrapper;
}

function insertButtons() {
  if (!currentVideoUrl()) return;
  if (document.getElementById(WRAPPER_ID)) return;

  const owner =
    document.querySelector("#top-level-buttons-computed") ||
    document.querySelector("#actions-inner") ||
    document.querySelector("#menu-container");

  if (!owner) return;
  owner.appendChild(makeWrapper());
}

let lastHref = "";
function tick() {
  if (location.href !== lastHref) {
    lastHref = location.href;
    document.getElementById(WRAPPER_ID)?.remove();
  }
  insertButtons();
}

setInterval(tick, 1200);
tick();
