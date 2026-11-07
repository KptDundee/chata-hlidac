# Nápady na později

## Optimalizace nabíjení z generátoru (16. 10. 2026)
Podmínka: vývojářský přístup EcoFlow (data + ovládání nabíjecího výkonu River). Hlídač pošle připomínku, jakmile EcoFlow data poprvé dorazí.

- Ovládání nabíjení jednotlivých River z aplikace.
- Cíl **není** co nejmenší výkon generátoru (měrná spotřeba paliva na kWh je při malém zatížení nejhorší).
- Cíl je **čas**: nastavit nabíjecí výkon každé River podle toho, kolik jí chybí, aby všechny dobily ve stejnou chvíli a generátor běžel co nejkratší dobu (= co nejvyšší celkové zatížení v jeho rozumném pásmu).
- Neplatí vždy – když jedné chybí málo a druhé hodně, vyrovnávat nemá smysl.
- Potřeba zjistit: max. výstup generátoru a jeho spotřeba paliva při různém zatížení (v ideálním případě změřit: palivo / kWh ze zásuvky 7 při různých výkonech).
