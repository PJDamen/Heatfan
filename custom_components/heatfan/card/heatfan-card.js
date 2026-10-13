/*
 * Heatfan card for Home Assistant
 * One compact card per Heatfan unit. Works with the "heatfan" integration:
 * entities are looked up by device, so entity ids and language don't matter.
 *
 *   type: custom:heatfan-card
 *   device: <device id>        # required (pick it in the visual editor)
 *   name: Woonkamer            # optional, defaults to the device name
 *   color: "#6E56F0"           # optional accent, hex or [r, g, b]
 *   show_curve: true           # optional, show the fan-curve row
 *   language: auto             # optional: auto | nl | en | de
 */

const CARD_VERSION = "0.3.1";
const DEFAULT_COLOR = "#6E56F0";

const STRINGS = {
  nl: {
    idle: "Stil",
    speed: "Snelheid",
    speed_inline: "snelheid",
    temperature: "Temperatuur",
    start: "Start",
    max: "Max",
    curve_for: "Curve voor modus",
    offline: "Offline",
    rising: "stijgend",
    falling: "dalend",
    stable: "stabiel",
    mode: "Modus",
    no_device: "Kies een Heatfan in de kaartinstellingen.",
    not_found: "Geen Heatfan-entiteiten gevonden voor dit apparaat.",
    lower: "Lager",
    higher: "Hoger",
    edit_curve: "Ventilatorcurve aanpassen",
    f_device: "Heatfan",
    f_name: "Naam (optioneel)",
    f_color: "Accentkleur",
    f_show_curve: "Curve tonen",
    f_language: "Taal",
    lang_auto: "Automatisch (taal van Home Assistant)",
  },
  en: {
    idle: "Idle",
    speed: "Speed",
    speed_inline: "speed",
    temperature: "Temperature",
    start: "Start",
    max: "Max",
    curve_for: "Curve for mode",
    offline: "Offline",
    rising: "rising",
    falling: "falling",
    stable: "stable",
    mode: "Mode",
    no_device: "Pick a Heatfan in the card settings.",
    not_found: "No Heatfan entities found for this device.",
    lower: "Lower",
    higher: "Higher",
    edit_curve: "Adjust fan curve",
    f_device: "Heatfan",
    f_name: "Name (optional)",
    f_color: "Accent colour",
    f_show_curve: "Show curve",
    f_language: "Language",
    lang_auto: "Automatic (Home Assistant language)",
  },
  de: {
    idle: "Aus",
    speed: "Drehzahl",
    speed_inline: "Drehzahl",
    temperature: "Temperatur",
    start: "Start",
    max: "Max",
    curve_for: "Kurve für Modus",
    offline: "Offline",
    rising: "steigend",
    falling: "fallend",
    stable: "stabil",
    mode: "Modus",
    no_device: "Wähle einen Heatfan in den Karteneinstellungen.",
    not_found: "Keine Heatfan-Entitäten für dieses Gerät gefunden.",
    lower: "Niedriger",
    higher: "Höher",
    edit_curve: "Lüfterkurve anpassen",
    f_device: "Heatfan",
    f_name: "Name (optional)",
    f_color: "Akzentfarbe",
    f_show_curve: "Kurve anzeigen",
    f_language: "Sprache",
    lang_auto: "Automatisch (Sprache von Home Assistant)",
  },
};

const ICON = {
  rotor:
    '<g transform="scale(.42)">' +
    [0, 120, 240]
      .map(
        (a) =>
          `<path transform="rotate(${a})" d="M0 -14 C 26 -26 52 -64 26 -92 C 4 -114 -36 -96 -30 -58 C -26 -36 -14 -22 0 -14 Z"/>`
      )
      .join("") +
    '</g><circle r="7"/>',
  rising: '<path d="M6 17 17 6M9.5 6H17v7.5"/>',
  falling: '<path d="M6 7l11 11M17 10.5V18H9.5"/>',
  stable: '<path d="M4 12h15M14 7l5 5-5 5"/>',
  chevron: '<path d="M6 9l6 6 6-6"/>',
  minus: '<path d="M6 12h12"/>',
  plus: '<path d="M6 12h12M12 6v12"/>',
};

const KEYS = {
  mode: "mode",
  speed: "fan_speed",
  temp: "radiator_temperature",
  trend: "temperature_trend",
  start_temp: "start_temp",
  max_temp: "max_temp",
  start_speed: "start_speed",
  max_speed: "max_speed",
};

// Language of the HA interface (used for the editor itself).
function uiStrings() {
  const ha = document.querySelector("home-assistant");
  const lang = (ha?.hass?.locale?.language || document.documentElement.lang || "en").slice(0, 2);
  return STRINGS[lang] || STRINGS.en;
}

function toColor(value) {
  if (Array.isArray(value) && value.length === 3) return `rgb(${value.join(",")})`;
  if (typeof value === "string" && value.trim()) return value.trim();
  return DEFAULT_COLOR;
}

function rgbOf(cssColor) {
  const ctx = document.createElement("canvas").getContext("2d");
  ctx.fillStyle = "#000";
  ctx.fillStyle = cssColor;
  const v = ctx.fillStyle;
  if (v.startsWith("#")) {
    const n = parseInt(v.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  const m = v.match(/\d+(\.\d+)?/g);
  return m ? m.slice(0, 3).map(Number) : [110, 86, 240];
}

function onColorFor(cssColor) {
  const lin = rgbOf(cssColor).map((c) => {
    c /= 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  const L = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2];
  return L > 0.4 ? "#141414" : "#ffffff";
}

const STYLE = `
  :host { display: block; }
  [hidden] { display: none !important; }
  ha-card { overflow: hidden; }
  .card {
    --hf-soft: color-mix(in srgb, var(--hf-accent) 14%, transparent);
    --hf-track: color-mix(in srgb, var(--primary-text-color) 10%, transparent);
    padding: 12px 14px 12px;
    display: grid;
    gap: 10px;
    color: var(--primary-text-color);
    font-family: inherit;
  }
  button { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; }
  button:focus-visible { outline: 2px solid var(--hf-accent); outline-offset: 2px; border-radius: 8px; }
  svg { display: block; }

  .top { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 12px; align-items: center; }
  .head { display: flex; align-items: center; gap: 12px; min-width: 0; text-align: left; }
  .badge { flex: none; }
  .badge {
    width: 40px; height: 40px; border-radius: 50%;
    display: grid; place-items: center;
    background: var(--hf-soft); color: var(--hf-accent);
    transition: background .3s, color .3s;
  }
  .badge svg { width: 30px; height: 30px; fill: currentColor; }
  .running .badge { background: var(--hf-accent); color: var(--hf-on-accent); }
  .running .rotor { animation: spin var(--hf-spin, 2s) linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .running .rotor { animation: none; } }

  .title { min-width: 0; text-align: left; }
  .name { font-size: 15px; font-weight: 500; line-height: 1.25; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .sub { font-size: 12px; color: var(--secondary-text-color); display: flex; align-items: center; gap: 6px; line-height: 1.3; min-width: 0; }
  .sub span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--success-color, #43a047); flex: none; }
  .offline .dot { background: var(--error-color, #db4437); }

  .temp { display: flex; align-items: center; gap: 2px; font-variant-numeric: tabular-nums; }
  .tval { font-size: 22px; font-weight: 500; letter-spacing: -.01em; }
  .tunit { font-size: 13px; color: var(--secondary-text-color); align-self: flex-start; margin-top: 3px; }
  .trend { width: 18px; height: 18px; fill: none; stroke: var(--secondary-text-color); stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; margin-left: 2px; }

  .speed { display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: center; }
  .segs { display: grid; grid-template-columns: repeat(10, 1fr); gap: 3px; }
  .seg { height: 6px; border-radius: 3px; background: var(--hf-track); transition: background .3s; }
  .seg.on { background: var(--hf-accent); }
  .slabel { font-size: 12px; color: var(--secondary-text-color); font-variant-numeric: tabular-nums; min-width: 72px; text-align: right; }

  /* Mode selector drawn as the controller: OUT, knob, six numbered LEDs, IN */
  .modes {
    --hf-body: color-mix(in srgb, var(--primary-text-color) 7%, var(--ha-card-background, var(--card-background-color, #fff)));
    --hf-edge: color-mix(in srgb, var(--primary-text-color) 16%, var(--ha-card-background, var(--card-background-color, #fff)));
    --hf-emboss: color-mix(in srgb, var(--primary-text-color) 38%, transparent);
    display: grid; grid-template-columns: auto auto 1fr auto; align-items: center; gap: 10px;
    padding: 7px 12px 8px;
    border-radius: 10px;
    background: linear-gradient(180deg, color-mix(in srgb, #fff 35%, var(--hf-body)), var(--hf-body) 55%);
    box-shadow: inset 0 1px 0 color-mix(in srgb, #fff 40%, transparent), 0 3px 0 -1px var(--hf-edge), 0 4px 8px -4px rgba(0,0,0,.25);
    margin-bottom: 3px;
  }
  .port { font-size: 9px; font-weight: 700; letter-spacing: .1em; color: var(--hf-emboss); }
  .knob {
    width: 18px; height: 18px; border-radius: 50%;
    background: radial-gradient(circle at 35% 30%, color-mix(in srgb, #fff 70%, var(--hf-body)), var(--hf-body) 70%);
    box-shadow: 0 1px 2px rgba(0,0,0,.3), inset 0 -1px 1px rgba(0,0,0,.12);
  }
  .leds { display: grid; grid-template-columns: repeat(6, 1fr); gap: 2px; }
  .led { display: grid; justify-items: center; gap: 5px; padding: 2px 0; border-radius: 6px; }
  .led .num {
    width: 18px; height: 18px; display: grid; place-items: center;
    border-radius: 3px; border: 1px solid var(--hf-edge);
    font-size: 11px; font-weight: 600; color: var(--hf-emboss); font-variant-numeric: tabular-nums;
    box-shadow: inset 0 1px 1px rgba(0,0,0,.08);
    transition: color .2s, border-color .2s;
  }
  .led .lamp {
    width: 7px; height: 7px; border-radius: 50%;
    background: color-mix(in srgb, #000 70%, var(--hf-body));
    box-shadow: inset 0 1px 1px rgba(0,0,0,.5);
    transition: background .2s, box-shadow .2s;
  }
  .led:hover .num { border-color: var(--hf-accent); color: var(--hf-accent); }
  .led[aria-checked="true"] .num { color: var(--primary-text-color); border-color: color-mix(in srgb, var(--primary-text-color) 30%, transparent); }
  .led[aria-checked="true"] .lamp {
    background: var(--hf-accent);
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--hf-accent) 60%, transparent), 0 0 8px 2px color-mix(in srgb, var(--hf-accent) 70%, transparent);
  }
  .led:disabled { cursor: default; }

  .curve {
    display: flex; align-items: center; justify-content: space-between; gap: 8px;
    font-size: 12px; color: var(--secondary-text-color);
    padding-top: 8px; border-top: 1px solid var(--divider-color, var(--hf-track));
    font-variant-numeric: tabular-nums; width: 100%;
  }
  .curve svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; transition: transform .2s; flex: none; }
  .curve[aria-expanded="true"] svg { transform: rotate(180deg); }
  .curve b { color: var(--primary-text-color); font-weight: 500; }

  .editor { display: grid; grid-template-columns: auto 1fr 1fr; gap: 6px 10px; align-items: center; font-size: 12px; }
  .editor .h { color: var(--secondary-text-color); text-align: center; }
  .editor .rl { color: var(--secondary-text-color); }
  .editor .note { grid-column: 1 / -1; color: var(--secondary-text-color); }
  .step { display: grid; grid-template-columns: 28px 1fr 28px; align-items: center; background: var(--hf-track); border-radius: 15px; height: 30px; }
  .step button { height: 30px; display: grid; place-items: center; color: var(--hf-accent); }
  .step button:disabled { opacity: .3; cursor: default; }
  .step svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 2.2; stroke-linecap: round; }
  .step output { text-align: center; font-size: 13px; font-weight: 500; font-variant-numeric: tabular-nums; }
  .step.pending output { color: var(--hf-accent); }

  .offline .speed, .offline .modes, .offline .temp, .offline .curve { opacity: .45; }
  .offline .badge { background: var(--hf-track); color: var(--secondary-text-color); }
  .msg { padding: 16px; color: var(--secondary-text-color); font-size: 13px; }
`;

class HeatfanCard extends HTMLElement {
  static getConfigForm() {
    return {
      schema: [
        { name: "device", required: true, selector: { device: { filter: { integration: "heatfan" } } } },
        { name: "name", selector: { text: {} } },
        { name: "color", selector: { color_rgb: {} } },
        { name: "show_curve", default: true, selector: { boolean: {} } },
        {
          name: "language",
          selector: {
            select: {
              mode: "dropdown",
              options: [
                { value: "auto", label: uiStrings().lang_auto },
                { value: "nl", label: "Nederlands" },
                { value: "en", label: "English" },
                { value: "de", label: "Deutsch" },
              ],
            },
          },
        },
      ],
      computeLabel: (s) => uiStrings()[`f_${s.name}`],
    };
  }

  static getStubConfig(hass) {
    const entry = Object.values(hass.entities || {}).find((e) => e.platform === "heatfan" && e.device_id);
    return { device: entry ? entry.device_id : "" };
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._pending = {};
    this._timers = {};
    this._open = false;
  }

  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this._config = { show_curve: true, ...config };
    this._built = false;
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return this._config && this._config.show_curve === false ? 3 : 4;
  }

  getGridOptions() {
    return { columns: 6, min_columns: 4 };
  }

  get _lang() {
    const chosen = this._config?.language;
    if (chosen && chosen !== "auto" && STRINGS[chosen]) return chosen;
    const ha = ((this._hass && (this._hass.locale?.language || this._hass.language)) || "en").slice(0, 2);
    return STRINGS[ha] ? ha : "en";
  }

  get _t() {
    return STRINGS[this._lang];
  }

  _lookup() {
    const hass = this._hass;
    const deviceId = this._config.device || hass.entities?.[this._config.entity]?.device_id;
    const ids = {};
    if (!deviceId) return { deviceId, ids };
    for (const e of Object.values(hass.entities || {})) {
      if (e.device_id !== deviceId || e.platform !== "heatfan") continue;
      if (e.translation_key) ids[e.translation_key] = e.entity_id;
      else if (e.entity_id.startsWith("binary_sensor.")) ids.online = e.entity_id;
    }
    return { deviceId, ids };
  }

  _state(id) {
    return id ? this._hass.states[id] : undefined;
  }

  _num(id) {
    if (id && this._pending[id] !== undefined) return this._pending[id];
    const s = this._state(id);
    const n = s ? Number(s.state) : NaN;
    return Number.isFinite(n) ? n : null;
  }

  _build() {
    const t = this._t;
    const accent = toColor(this._config.color);
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <ha-card>
        <div class="card" style="--hf-accent:${accent};--hf-on-accent:${onColorFor(accent)}">
          <div class="top">
            <button class="head" data-more="temp">
              <span class="badge"><svg viewBox="-50 -50 100 100"><g class="rotor">${ICON.rotor}</g></svg></span>
              <span class="title"><div class="name"></div><div class="sub"><i class="dot"></i><span class="status"></span></div></span>
            </button>
            <div class="temp"><span class="tval">–</span><span class="tunit">°C</span><svg class="trend" viewBox="0 0 24 24"></svg></div>
          </div>
          <div class="speed">
            <div class="segs">${'<i class="seg"></i>'.repeat(10)}</div>
            <span class="slabel"></span>
          </div>
          <div class="modes">
            <span class="port">OUT</span>
            <span class="knob" aria-hidden="true"></span>
            <div class="leds" role="radiogroup" aria-label="${t.mode}">
              ${[1, 2, 3, 4, 5, 6].map((m) => `<button class="led" role="radio" data-mode="${m}" aria-checked="false" aria-label="${t.mode} ${m}"><span class="num">${m}</span><i class="lamp"></i></button>`).join("")}
            </div>
            <span class="port">IN</span>
          </div>
          <button class="curve" aria-expanded="false" title="${t.edit_curve}"><span class="ctext"></span><svg viewBox="0 0 24 24">${ICON.chevron}</svg></button>
          <div class="editor" hidden>
            <span></span><span class="h">${t.start}</span><span class="h">${t.max}</span>
            <span class="rl">${t.temperature}</span>${this._stepper("start_temp")}${this._stepper("max_temp")}
            <span class="rl">${t.speed}</span>${this._stepper("start_speed")}${this._stepper("max_speed")}
            <span class="note"></span>
          </div>
        </div>
      </ha-card>`;
    const root = this.shadowRoot;
    root.querySelector(".head").addEventListener("click", () => this._moreInfo());
    root.querySelectorAll(".led").forEach((b) => b.addEventListener("click", () => this._setMode(Number(b.dataset.mode))));
    root.querySelector(".curve").addEventListener("click", () => {
      this._open = !this._open;
      this._update();
    });
    root.querySelectorAll(".step button").forEach((b) =>
      b.addEventListener("click", () => this._step(b.closest(".step").dataset.key, Number(b.dataset.d)))
    );
    this._built = true;
  }

  _stepper(key) {
    const t = this._t;
    return `<div class="step" data-key="${key}">
      <button data-d="-1" aria-label="${t.lower}"><svg viewBox="0 0 24 24">${ICON.minus}</svg></button>
      <output></output>
      <button data-d="1" aria-label="${t.higher}"><svg viewBox="0 0 24 24">${ICON.plus}</svg></button>
    </div>`;
  }

  _render() {
    if (!this._hass || !this._config) return;
    const { deviceId, ids } = this._lookup();
    this._ids = ids;
    if (!deviceId || !ids.mode) {
      this._built = false;
      this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card><div class="msg">${deviceId ? this._t.not_found : this._t.no_device}</div></ha-card>`;
      return;
    }
    this._device = this._hass.devices?.[deviceId];
    if (!this._built) this._build();
    this._update();
  }

  _update() {
    const t = this._t;
    const ids = this._ids;
    const root = this.shadowRoot;
    const card = root.querySelector(".card");
    const lang = this._lang;

    const onlineState = this._state(ids.online);
    const offline = onlineState ? onlineState.state === "off" : false;
    const speed = offline ? 0 : this._num(ids[KEYS.speed]) ?? 0;
    const temp = this._num(ids[KEYS.temp]);
    const trend = this._state(ids[KEYS.trend])?.state;
    const modeState = this._state(ids[KEYS.mode])?.state || "";
    const mode = this._pending.mode ?? Number(modeState.replace("mode_", ""));

    card.classList.toggle("offline", offline);
    card.classList.toggle("running", !offline && speed > 0);
    card.style.setProperty("--hf-spin", `${(3.4 - speed * 0.27).toFixed(2)}s`);

    const area = this._hass.areas?.[this._device?.area_id]?.name;
    root.querySelector(".name").textContent =
      this._config.name || this._device?.name_by_user || this._device?.name || "Heatfan";
    let status;
    if (offline) {
      const since = onlineState?.last_changed ? new Date(onlineState.last_changed) : null;
      status = since ? `${t.offline} · ${this._relative(since, lang)}` : t.offline;
    } else {
      status = [area, trend && t[trend]].filter(Boolean).join(" · ");
    }
    root.querySelector(".status").textContent = status;

    root.querySelector(".tval").textContent =
      temp === null ? "–" : temp.toLocaleString(lang, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    root.querySelector(".trend").innerHTML = ICON[trend] || "";

    root.querySelectorAll(".seg").forEach((s, i) => s.classList.toggle("on", i < speed));
    root.querySelector(".slabel").textContent = offline ? "–" : speed > 0 ? `${t.speed} ${speed}` : t.idle;

    root.querySelectorAll(".led").forEach((b) => {
      b.setAttribute("aria-checked", String(Number(b.dataset.mode) === mode));
      b.disabled = offline;
    });

    const curveBtn = root.querySelector(".curve");
    const editor = root.querySelector(".editor");
    const show = this._config.show_curve !== false && ids.start_temp;
    curveBtn.hidden = !show;
    editor.hidden = !show || !this._open;
    curveBtn.setAttribute("aria-expanded", String(this._open));
    if (show) {
      const v = (k) => this._num(ids[k]) ?? "–";
      root.querySelector(".ctext").innerHTML =
        `<b>${v("start_temp")}° → ${v("max_temp")}°</b> &nbsp;·&nbsp; ${t.speed_inline} <b>${v("start_speed")} → ${v("max_speed")}</b>`;
      root.querySelectorAll(".step").forEach((el) => {
        const key = el.dataset.key;
        const id = ids[key];
        const val = this._num(id);
        el.querySelector("output").textContent = val === null ? "–" : key.endsWith("temp") ? `${val}°` : `${val}`;
        el.classList.toggle("pending", this._pending[id] !== undefined);
        const [lo, hi] = this._bounds(key);
        el.querySelector('[data-d="-1"]').disabled = offline || val === null || val <= lo;
        el.querySelector('[data-d="1"]').disabled = offline || val === null || val >= hi;
      });
      root.querySelector(".note").textContent = `${t.curve_for} ${mode || "–"}`;
    }
  }

  _bounds(key) {
    const ids = this._ids;
    const attrs = this._state(ids[key])?.attributes || {};
    let lo = attrs.min ?? 1;
    let hi = attrs.max ?? (key.endsWith("temp") ? 100 : 10);
    const pair = { start_temp: "max_temp", max_temp: "start_temp", start_speed: "max_speed", max_speed: "start_speed" }[key];
    const other = this._num(ids[pair]);
    if (other !== null) {
      if (key.startsWith("start")) hi = Math.min(hi, other);
      else lo = Math.max(lo, other);
    }
    return [lo, hi];
  }

  _step(key, delta) {
    const id = this._ids[key];
    const cur = this._num(id);
    if (cur === null) return;
    const [lo, hi] = this._bounds(key);
    const next = Math.min(hi, Math.max(lo, cur + delta));
    if (next === cur) return;
    this._pending[id] = next;
    this._update();
    clearTimeout(this._timers[id]);
    this._timers[id] = setTimeout(async () => {
      try {
        await this._hass.callService("number", "set_value", { entity_id: id, value: next });
      } finally {
        delete this._pending[id];
        this._update();
      }
    }, 800);
  }

  async _setMode(mode) {
    this._pending.mode = mode;
    this._update();
    try {
      await this._hass.callService("select", "select_option", { entity_id: this._ids.mode, option: `mode_${mode}` });
    } finally {
      delete this._pending.mode;
      this._update();
    }
  }

  _moreInfo() {
    const entityId = this._ids[KEYS.temp] || this._ids.mode;
    this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId }, bubbles: true, composed: true }));
  }

  _relative(date, lang) {
    const diff = (date.getTime() - Date.now()) / 1000;
    const rtf = new Intl.RelativeTimeFormat(lang, { numeric: "auto" });
    const steps = [["day", 86400], ["hour", 3600], ["minute", 60]];
    for (const [unit, sec] of steps) {
      if (Math.abs(diff) >= sec || unit === "minute") return rtf.format(Math.round(diff / sec), unit);
    }
    return "";
  }
}

if (!customElements.get("heatfan-card")) {
  customElements.define("heatfan-card", HeatfanCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "heatfan-card",
    name: "Heatfan",
    description: "Compact card for one Heatfan radiator fan unit.",
    preview: true,
    documentationURL: "https://github.com/PJDamen/heatfan",
  });
  console.info(`%c HEATFAN-CARD %c ${CARD_VERSION} `, "background:#6E56F0;color:#fff;border-radius:3px 0 0 3px", "background:#333;color:#fff;border-radius:0 3px 3px 0");
}
