# Hlídač chaty

Každých 10 minut (GitHub Actions) načte data solárního regulátoru EPEVER XTRA-N z cloudu Solar Guardian,
uloží je do zašifrované historie a:

**posílá upozornění do aplikace ntfy v telefonu**
- ☀️ solární baterie nabitá (fáze Float) – můžeš ji připojit
- ⚠️ napětí pod 12,2 V (~50 %)
- 🛑 napětí pod 12,0 V – odpojit, nevybíjet dál
- 📡 regulátor neposílá data déle než 2 h
- 📊 večerní souhrn po 20:00

**aktualizuje webový přehled** na https://kptdundee.github.io/chata-hlidac/
(aktuální stav, grafy napětí a výkonu za 24 h – 14 dní, výroba po dnech).

Data na webu jsou zašifrovaná (AES-GCM, klíč z hesla `DATA_KEY`); bez hesla je nikdo nepřečte.
Kód v repozitáři žádná hesla neobsahuje – ta jsou jen v GitHub Secrets.

Hranice se mění nahoře v `hlidac.py`. Ruční spuštění: **Actions → Hlídač chaty → Run workflow**
(zaškrtnutím „test“ přijde zkušební upozornění).

Potřebné Secrets (Settings → Secrets and variables → Actions):
`SG_ACCOUNT`, `SG_PASSWORD`, `NTFY_TOPIC`, `DATA_KEY`.
