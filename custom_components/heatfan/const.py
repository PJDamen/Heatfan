"""Constants for the Heatfan integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "heatfan"
MANUFACTURER: Final = "Heatfan B.V."

# Public Firebase web client configuration used by app.heatfan.eu.
FIREBASE_API_KEY: Final = "AIzaSyBEnl8h2IjV9_Gz_EBaq8Uj5wtMvOYCMYc"
FIREBASE_DB_URL: Final = (
    "https://heatfan-database-default-rtdb.europe-west1.firebasedatabase.app"
)
SIGN_IN_URL: Final = (
    "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
)
REFRESH_URL: Final = "https://securetoken.googleapis.com/v1/token"

ROOT_PATH: Final = "heatfan-controller-dc/live-data"

CONF_UID: Final = "uid"
CONF_REFRESH_TOKEN: Final = "refresh_token"

# Fallback poll in case the live stream silently stalls.
POLL_INTERVAL: Final = timedelta(minutes=5)
# A unit is reported offline when its status has not changed for this long.
OFFLINE_AFTER: Final = timedelta(minutes=90)

MODES: Final = [1, 2, 3, 4, 5, 6]

PARAM_START_TEMP: Final = "start-temp"
PARAM_MAX_TEMP: Final = "max-temp"
PARAM_START_SPEED: Final = "start-speed"
PARAM_MAX_SPEED: Final = "max-speed"

TEMP_MIN: Final = 1
TEMP_MAX: Final = 100
SPEED_MIN: Final = 1
SPEED_MAX: Final = 10
