# Hlídač chaty

Každých 30 minut (GitHub Actions) načte data solárního regulátoru EPEVER XTRA-N z cloudu Solar Guardian
a posílá upozornění do aplikace **ntfy** v telefonu:

- ☀️ solární baterie nabitá (fáze Float) – můžeš ji připojit
- ⚠️ napětí pod 12,2 V (~50 %)
- 🛑 napětí pod 12,0 V – odpojit, nevybíjet dál
- 📡 regulátor neposílá data déle než 2 h
- 📊 večerní souhrn po 20:00

Hranice se mění nahoře v `hlidac.py`. Ruční test: záložka **Actions → Hlídač chaty → Run workflow**.

Potřebné Secrets (Settings → Secrets and variables → Actions): `SG_ACCOUNT`, `SG_PASSWORD`, `NTFY_TOPIC`.
