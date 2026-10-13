<p align="center"><img src="custom_components/heatfan/brand/logo.png" alt="Heatfan" width="200"></p>

# Heatfan for Home Assistant

Unofficial integration for [Heatfan](https://heatfan.nl) radiator fans with the Heatfan Wi-Fi Controller. It talks to the same cloud backend as [app.heatfan.eu](https://app.heatfan.eu) (Firebase Realtime Database) and receives changes live via its event stream — no polling delay.

> Not affiliated with Heatfan B.V. The cloud structure is undocumented and can change without notice.

## Installation (HACS)

1. HACS → ⋮ → *Custom repositories* → add this repo as type **Integration**.
2. Install **Heatfan**, restart Home Assistant.
3. *Settings → Devices & services → Add integration → Heatfan*, log in with your app.heatfan.eu account.

Only a Firebase refresh token is stored, not your password. If it ever stops working, Home Assistant asks you to log in again.

## Entities per unit

| Entity | Type | Notes |
|---|---|---|
| Radiator temperature | sensor | `temp_ext`, the probe on the radiator, rounded to 0.1 °C |
| Fan speed | sensor | 0–10 |
| Temperature trend | sensor | rising / falling |
| Mode | select | Mode 1–6, same as the app |
| Start/max temperature, start/max speed | number | Fan curve of the **active** mode |
| Connectivity | binary_sensor | Off when the unit hasn't reported for 90 min |
| Wi-Fi signal | sensor | diagnostic |
| Last update | sensor | diagnostic, disabled by default (changes every minute) |
| Board / MCU temperature | sensor | diagnostic, disabled by default |

The rooms from the app are not assigned to areas automatically; put each device in an area yourself.

## Recorder

The units report about once a minute. Temperatures are rounded to 0.1 °C so tiny fluctuations don't create history rows. *Last update* changes every minute by definition, so it is disabled by default. An integration cannot exclude its own entities from the recorder; if you enable *Last update* and don't want its history, add this to `configuration.yaml`:

```yaml
recorder:
  exclude:
    entity_globs:
      - sensor.*_last_update
      - sensor.*_laatste_update
```

## Service `heatfan.set_drive_params`

Change the curve of any mode (the active mode if `mode` is omitted). Useful because the cloud has no "set speed now" command — speed always follows the curve.

```yaml
action: heatfan.set_drive_params
data:
  device_id: <device id>
  mode: 4
  start_temp: 23
  max_temp: 40
  start_speed: 2
  max_speed: 9
```

## Icon

The integration ships its own icon and logo in `custom_components/heatfan/brand/` (shown from Home Assistant 2026.3).

## How it works

- Auth: Firebase `accounts:signInWithPassword` → ID token (1 h) + refresh token.
- Data: `heatfan-controller-dc/live-data/<uid>/room/<room>/<MAC>` in the Realtime Database, read via REST and followed via Server-Sent Events.
- Writes use the same paths as the web app: `…/user` `{mode}` and `…/user/drive-params/mode-N`.
- History lives under `heatfan-controller-dc/history-data/…` (not used; Home Assistant records its own history).

## Changelog

**0.2.0**
- Temperatures rounded to 0.1 °C (fewer recorder writes).
- *Last update* sensor disabled by default.
- Own icon and logo (Home Assistant 2026.3+).
- MIT license.

**0.1.0** — first release.

## License

MIT, see [LICENSE](LICENSE).
