# Chata – hodinky (Wear OS)

Komplikace na ciferník (napětí solární baterie) a dlaždice se základními údaji.
Data posílá hlídač každých 10 minut do ntfy kanálu `<téma>-hodinky`; hodinky si je jen přečtou (nepotřebují heslo ani telefon).

## Instalace (Android Studio)
1. Složku `hodinky` z ZIPu zkopíruj vedle projektu pro Flip (např. `C:\Android\chata-hodinky`) a v Android Studiu **File → Open** → vyber složku `hodinky`.
2. Na hodinkách: **Nastavení → Systém → Informace** → 7× ťukni na **Číslo sestavení** (zapnou se Možnosti pro vývojáře).
3. **Nastavení → Možnosti pro vývojáře** → zapni **Ladění ADB** a **Bezdrátové ladění** (hodinky a počítač na stejné Wi-Fi).
4. V Android Studiu: **Device Manager → Pair Devices Using Wi-Fi** → na hodinkách *Bezdrátové ladění → Spárovat nové zařízení* a opiš kód.
5. Nahoře vyber hodinky a dej ▶ **Run**.
6. Na hodinkách se otevře aplikace **Chata** → zadej **téma ntfy** (stejné jako v aplikaci ntfy) → *Uložit a načíst*.

## Dlaždice
Přejeď z ciferníku do strany → na konci *+ Přidat dlaždici* → **Chata**. Ťuknutím na dlaždici se obnoví.

## Komplikace
Dlouze podrž ciferník → *Upravit / Přizpůsobit* → vyber místo pro komplikaci → **Chata – napětí baterie**.
Krátká verze ukáže „12,64 V“, kruhová ukazuje napětí mezi vypnutím měniče (11,6 V) a 13 V.
Pozn.: některé ciferníky od Xiaomi cizí komplikace nepodporují – pak zkus jiný ciferník (např. z Google / Play).

## Ciferník Chata (modul `cifernik`)
Analogový ciferník ve formátu **Watch Face Format** – kreslí ho systém, nemá vlastní kód, takže šetří baterii.
1. V Android Studiu nahoře v seznamu konfigurací vyber **cifernik** (vedle **app**).
   Pokud tam není: *Run → Edit Configurations → + → Android App*, Module **ChataHodinky.cifernik**, **Launch: Nothing**.
2. Hodinky vybrané nahoře → ▶ **Run**. (Nejdřív nainstaluj i **app** – kvůli komplikacím Chata a slunce.)
3. Na hodinkách dlouze podrž ciferník → přejeď na konec → **+** → **Chata – ciferník**.
4. Když se v subdialu CHATA nic neukazuje: podrž ciferník → **Upravit** → levý subdial → **Chata – napětí baterie**; nahoře → **Chata – východ / západ slunce**. Hodinky se můžou zeptat na povolení dat – potvrď.

Grafika: `cifernik/grafika/generuj.py` (Python + pycairo) vykreslí PNG do `cifernik/src/main/res/drawable-nodpi`.
Písmo Saira Expanded (statická instance Saira, wdth 125 / wght 600; SIL Open Font License, viz grafika/Saira-OFL.txt).
