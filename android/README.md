# Chata brána (Android)

Aplikace pro telefon, který zůstane na chatě u měniče. Každých 10 minut pošle hlídači:

- odběr z měniče **Victron Phoenix** (Bluetooth „Instant readout“): průměr a špičku za 10 min, napětí, stav, alarmy,
- spotřebu **zásuvek Tapo** (přímo po místní Wi-Fi, bez cloudu),
- **baterii telefonu** (%, nabíjí / nenabíjí, teplota).

Data jdou do ntfy tématu `<NTFY_TOPIC>-menic`, odkud si je bere hlídač na GitHubu.
Hlídač pak upozorní, když baterie telefonu klesne pod 15 %, nebo když telefon přestane posílat.

## Sestavení

1. Android Studio → **File → Open** → složka `android` z tohoto repozitáře.
2. Počkej na synchronizaci Gradle (poprvé stahuje pár minut).
3. Telefon připoj USB kabelem (zapnuté *Ladění USB*) → zelená šipka **Run**.

## Nastavení v aplikaci

| Pole | Kde to najdeš |
|---|---|
| ntfy téma | stejné jako GitHub Secret `NTFY_TOPIC` (téma, které máš v aplikaci ntfy) |
| MAC adresa měniče | VictronConnect → měnič → ⋮ → Product info → *Instant readout via Bluetooth: Enabled* → **Show encryption data** |
| Šifrovací klíč | tamtéž (32 znaků) |
| Tapo e-mail + heslo | tvůj účet v aplikaci Tapo – zůstane jen v telefonu |
| IP adresy zásuvek | např. `185, 106, 165, 172, 115, 190, 157` (stačí konec adresy, doplní se `192.168.0.`) |

Pak **Uložit a spustit**, povol *Zařízení v okolí*, *Poloha* a *Oznámení*, a nakonec **Povolit běh na pozadí** (baterie: Neomezeno).

## Telefon (Samsung)

- *Péče o baterii → Baterie → Ochrana baterie → Maximální (80 %)* → může být trvale na nabíječce.
- Wi-Fi a Bluetooth zapnuté, poloha zapnutá (stačí přesnost „nízká“ – Android ji vyžaduje pro Bluetooth sken).
- Mobilní data, NFC, Always On Display, synchronizace účtů: vypnout.
- Ostatní aplikace: *Limity používání na pozadí → Aplikace v hlubokém spánku*.
