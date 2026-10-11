# Hlídač chaty

Každých 10 minut (GitHub Actions) načte data solárního regulátoru EPEVER XTRA-N z cloudu Solar Guardian,
uloží je do zašifrované historie a:

**posílá upozornění do aplikace ntfy v telefonu**
- 🔋 baterie na 100 % (fáze Float) – můžeš zapojit náročnější spotřebič
- 🌥 panely nevyrábí, i když je den (východ/západ slunce + rezerva)
- ⚠️ napětí pod 12,2 V (~50 %)
- 🛑 napětí pod 12,0 V – alarm regulátoru, odpojit spotřebiče
- 🔌 napětí na úrovni ochranného odpojení regulátoru (11,6 V)
- 🔄 River skoro vybitá – vyměnit; ⛽ River nabitá generátorem – vypnout generátor
- 📡 regulátor neposílá data déle než 2 h
- 📊 večerní souhrn po 20:00

**aktualizuje webový přehled** na https://kptdundee.github.io/chata-hlidac/
(aktuální stav, grafy napětí a výkonu za 24 h – 14 dní, výroba po dnech).

Data na webu jsou zašifrovaná (AES-GCM, klíč z hesla `DATA_KEY`); bez hesla je nikdo nepřečte.
Kód v repozitáři žádná hesla neobsahuje – ta jsou jen v GitHub Secrets.

Podmínky a hranice se mění v souboru **`nastaveni.txt`** (jde upravit i z telefonu v aplikaci GitHub). Ruční spuštění: **Actions → Hlídač chaty → Run workflow**
(zaškrtnutím „test“ přijde zkušební upozornění).

Potřebné Secrets (Settings → Secrets and variables → Actions):
`SG_ACCOUNT`, `SG_PASSWORD`, `NTFY_TOPIC`, `DATA_KEY`;
volitelně `ECOFLOW_ACCESS_KEY`, `ECOFLOW_SECRET_KEY` (z developer-eu.ecoflow.com).
