package cz.petr.chatabrana;

import android.annotation.SuppressLint;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothManager;
import android.bluetooth.le.BluetoothLeScanner;
import android.bluetooth.le.ScanCallback;
import android.bluetooth.le.ScanFilter;
import android.bluetooth.le.ScanResult;
import android.bluetooth.le.ScanSettings;
import android.content.Context;
import android.os.ParcelUuid;
import android.os.SystemClock;


/**
 * Trvale (úsporně) poslouchá vysílání měniče Victron a sbírá průměr / maximum odběru
 * mezi dvěma odesláními.
 */
public final class BleListener {
    private final Context ctx;
    private BluetoothLeScanner scanner;
    private long startedAt;
    private byte[] key;
    private String mac;

    // nasbíráno od posledního odeslání
    private double sumVa;
    private int n;
    private int maxVa = -1;
    private VictronParser.Inverter last;
    private long lastSeen;
    private String lastError;
    private int victronAds;            // kolik vysílání Victron (jakéhokoli) jsme od posledního odeslání zachytili
    private String otherMac;           // jiné Victron zařízení, které vidíme (pro diagnostiku)

    // 1.5: teploměry Xiaomi (MiBeacon, service data 0xFE95) – MAC → [jméno, klíč] a poslední hodnoty
    private static final ParcelUuid MI_UUID = ParcelUuid.fromString("0000fe95-0000-1000-8000-00805f9b34fb");
    private final java.util.Map<String, Object[]> thCfg = new java.util.LinkedHashMap<>();
    private final java.util.Map<String, double[]> thVal = new java.util.HashMap<>();   // t, h, b, kdy (elapsedRealtime)
    private String thSig = "";

    public static final class Thermo { public String name, mac; public Double t, h; public Integer b; public long ageSec; public int seen, ok; }
    /** 1.7.7: diagnostika – kolik zpráv od teploměru Flip zachytil a kolik šlo přečíst (MAC → [zachyceno, přečteno]). */
    private final java.util.Map<String, int[]> thStat = new java.util.HashMap<>();

    /** Načte seznam teploměrů z nastavení (řádky „MAC KLÍČ jméno“). */
    private void loadThermo() {
        String raw = Prefs.s(ctx, Prefs.XIAOMI);
        if (raw.equals(thSig)) return;
        thSig = raw;
        thCfg.clear();
        for (String ln : raw.split("[\\n;]")) {                // 1.7.6: řádek nebo středník
            String[] w = ln.trim().split("\\s+", 3);
            if (w.length < 2) continue;
            String m = Prefs.normMac(w[0]), k = w[1].replaceAll("[^0-9a-fA-F]", "");
            if (!BluetoothAdapter.checkBluetoothAddress(m) || k.length() != 32) continue;
            thCfg.put(m, new Object[]{w.length > 2 ? w[2].trim() : m, XiaomiParser.hex(k)});
        }
    }

    /** Poslední hodnoty teploměrů (nemaže se – stáří v ageSec). */
    public synchronized java.util.List<Thermo> thermo() {
        java.util.List<Thermo> out = new java.util.ArrayList<>();
        for (java.util.Map.Entry<String, Object[]> e : thCfg.entrySet()) {
            double[] v = thVal.get(e.getKey());
            Thermo t = new Thermo();
            t.mac = e.getKey(); t.name = (String) e.getValue()[0];
            int[] stc = thStat.get(e.getKey());
            if (stc != null) { t.seen = stc[0]; t.ok = stc[1]; }
            if (v != null) {
                if (!Double.isNaN(v[0])) t.t = v[0];
                if (!Double.isNaN(v[1])) t.h = v[1];
                if (!Double.isNaN(v[2])) t.b = (int) v[2];
                t.ageSec = (SystemClock.elapsedRealtime() - (long) v[3]) / 1000;
            } else t.ageSec = -1;
            out.add(t);
        }
        return out;
    }

    public BleListener(Context ctx) { this.ctx = ctx.getApplicationContext(); }

    public static final class Snapshot {
        public Double avgVa;
        public Integer maxVa;
        public int samples;
        public VictronParser.Inverter last;
        public long ageSec = -1;
        public String error;
    }

    private final ScanCallback cb = new ScanCallback() {
        @Override public void onScanResult(int type, ScanResult r) { handle(r); }
        @Override public void onScanFailed(int code) { lastError = "Bluetooth sken selhal (" + code + ")"; scanner = null; }
    };

    private synchronized void handle(ScanResult r) {
        if (r.getScanRecord() == null) return;
        if (!thCfg.isEmpty() && r.getDevice() != null) {                 // 1.5: teploměr Xiaomi?
            Object[] c = thCfg.get(r.getDevice().getAddress().toUpperCase(java.util.Locale.ROOT));
            byte[] sd = c == null ? null : r.getScanRecord().getServiceData(MI_UUID);
            if (sd != null) {
                int[] stc = thStat.get(r.getDevice().getAddress().toUpperCase(java.util.Locale.ROOT));
                if (stc == null) { stc = new int[2]; thStat.put(r.getDevice().getAddress().toUpperCase(java.util.Locale.ROOT), stc); }
                boolean hasObj = sd.length >= 2 && ((sd[0] & 0x40) != 0);
                if (hasObj) stc[0]++;
                try {
                    XiaomiParser.Reading x = XiaomiParser.parse(sd, r.getDevice().getAddress(), (byte[]) c[1]);
                    if (x != null) {
                        stc[1]++;
                        double[] v = thVal.get(r.getDevice().getAddress().toUpperCase(java.util.Locale.ROOT));
                        if (v == null) v = new double[]{Double.NaN, Double.NaN, Double.NaN, 0};
                        if (x.temp != null) v[0] = x.temp;
                        if (x.hum != null) v[1] = x.hum;
                        if (x.batt != null) v[2] = x.batt;
                        v[3] = SystemClock.elapsedRealtime();
                        thVal.put(r.getDevice().getAddress().toUpperCase(java.util.Locale.ROOT), v);
                    }
                } catch (Exception ignored) { }
                return;
            }
        }
        if (key == null) return;
        byte[] d = r.getScanRecord().getManufacturerSpecificData(VictronParser.MANUFACTURER_ID);
        if (d == null) return;
        victronAds++;
        String addr = r.getDevice() == null ? "" : r.getDevice().getAddress();
        boolean macOk = addr.equalsIgnoreCase(mac);
        try {
            // rozhoduje hlavně šifrovací klíč: měnič poznáme podle toho, že jde dešifrovat
            VictronParser.Inverter inv = VictronParser.parse(d, key);
            last = inv;
            lastSeen = SystemClock.elapsedRealtime();
            lastError = null;
            if (inv.acVa != null) {
                sumVa += inv.acVa;
                n++;
                maxVa = Math.max(maxVa, inv.acVa);
            }
        } catch (Exception e) {
            if (macOk) lastError = e.getMessage(); else otherMac = addr;
        }
    }

    /** Spustí (nebo po 25 min restartuje) sken. Android po 30 min nepřetržitého skenu omezí výsledky. */
    @SuppressLint("MissingPermission")
    public void ensureRunning() { ensureRunning(false); }

    /**
     * Filtry pro sken na pozadí (se zhasnutým displejem Android pustí jen filtrovaný sken):
     * výrobce Victron + první bajt 0x10 (každá zpráva Instant Readout jím začíná) a navíc konkrétní MAC.
     * Prázdná data ve filtru (verze 1.1) Samsung nepřijal – nic neprošlo.
     */
    private java.util.List<ScanFilter> filters() {
        java.util.List<ScanFilter> fl = new java.util.ArrayList<>();
        fl.add(new ScanFilter.Builder().setManufacturerData(VictronParser.MANUFACTURER_ID,
                new byte[]{0x10}, new byte[]{(byte) 0xFF}).build());
        if (mac != null && BluetoothAdapter.checkBluetoothAddress(mac)) {
            fl.add(new ScanFilter.Builder().setDeviceAddress(mac).build());
        }
        for (String m : thCfg.keySet()) fl.add(new ScanFilter.Builder().setDeviceAddress(m).build());   // 1.5: teploměry
        return fl;
    }

    /** Krátké intenzivní hledání (když trvalý poslech nic nechytil). Volat mimo hlavní vlákno. */
    @SuppressLint("MissingPermission")
    public void burst(long ms) {
        BluetoothLeScanner sc;
        synchronized (this) {
            stop();
            BluetoothManager bm = (BluetoothManager) ctx.getSystemService(Context.BLUETOOTH_SERVICE);
            BluetoothAdapter a = bm == null ? null : bm.getAdapter();
            if (a == null || !a.isEnabled() || key == null) return;
            sc = a.getBluetoothLeScanner();
            if (sc == null) return;
            try {
                sc.startScan(filters(), new ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build(), cb);
            } catch (Exception e) { lastError = "Nejde spustit sken: " + e.getMessage(); return; }
        }
        SystemClock.sleep(ms);
        synchronized (this) { try { sc.stopScan(cb); } catch (Exception ignored) {} }
        ensureRunning(true);
    }

    public synchronized int samples() { return n; }

    private volatile int openSeen;
    private final ScanCallback openCb = new ScanCallback() {
        @Override public void onScanResult(int type, ScanResult r) { openSeen++; handle(r); }
    };

    /**
     * Záložní hledání BEZ filtru (jako tlačítko „Test Bluetooth“), když filtrovaný poslech nic nechytil.
     * @return krátký popis do Deníku: kolik vysílání bylo vidět, jestli Victron
     */
    @SuppressLint("MissingPermission")
    public String burstOpen(long ms) {
        BluetoothLeScanner sc;
        int before;
        synchronized (this) {
            stop();
            BluetoothManager bm = (BluetoothManager) ctx.getSystemService(Context.BLUETOOTH_SERVICE);
            BluetoothAdapter a = bm == null ? null : bm.getAdapter();
            if (a == null || !a.isEnabled() || key == null) return "Bluetooth nejde";
            sc = a.getBluetoothLeScanner();
            if (sc == null) return "sken nejde";
            openSeen = 0; before = n;
            try { sc.startScan(null, new ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build(), openCb); }
            catch (Exception e) { ensureRunning(true); return "nejde spustit: " + e.getMessage(); }
        }
        SystemClock.sleep(ms);
        synchronized (this) { try { sc.stopScan(openCb); } catch (Exception ignored) {} }
        ensureRunning(true);
        synchronized (this) { return "bez filtru: vysílání v okolí " + openSeen + ", Victron " + (n > before ? "ANO (" + (n - before) + "×)" : "ne"); }
    }

    public synchronized void ensureRunning(boolean force) {
        String sig0 = thSig;
        loadThermo();
        if (!sig0.equals(thSig)) force = true;                   // změnil se seznam teploměrů → nové filtry
        String m = Prefs.normMac(Prefs.s(ctx, Prefs.VICTRON_MAC));
        String k = Prefs.s(ctx, Prefs.VICTRON_KEY).replaceAll("[^0-9a-fA-F]", "");
        if (k.length() < 32) { stop(); lastError = "Chybí šifrovací klíč měniče (32 znaků)"; return; }
        if (!m.equals(mac) || key == null) { stop(); mac = m; key = VictronParser.hex(k); }
        if (!force && scanner != null && SystemClock.elapsedRealtime() - startedAt < 25 * 60_000L) return;
        stop();
        BluetoothManager bm = (BluetoothManager) ctx.getSystemService(Context.BLUETOOTH_SERVICE);
        BluetoothAdapter a = bm == null ? null : bm.getAdapter();
        if (a == null || !a.isEnabled()) { lastError = "Bluetooth je vypnutý"; return; }
        scanner = a.getBluetoothLeScanner();
        if (scanner == null) { lastError = "Bluetooth sken není dostupný"; return; }
        ScanSettings s = new ScanSettings.Builder()
                .setScanMode(ScanSettings.SCAN_MODE_BALANCED)
                .build();
        try {
            scanner.startScan(filters(), s, cb);
            startedAt = SystemClock.elapsedRealtime();
        } catch (Exception e) {
            lastError = "Nejde spustit sken: " + e.getMessage();
            scanner = null;
        }
    }

    @SuppressLint("MissingPermission")
    public synchronized void stop() {
        if (scanner != null) {
            try { scanner.stopScan(cb); } catch (Exception ignored) {}
            scanner = null;
        }
    }

    /** Vrátí nasbíraná data a začne sbírat znovu. */
    public synchronized Snapshot takeSnapshot() {
        Snapshot s = new Snapshot();
        if (n > 0) { s.avgVa = sumVa / n; s.maxVa = maxVa; }
        s.samples = n;
        s.last = last;
        s.ageSec = lastSeen == 0 ? -1 : (SystemClock.elapsedRealtime() - lastSeen) / 1000;
        s.error = lastError;
        if (n == 0 && s.error == null) {
            if (scanner == null) s.error = "Bluetooth sken neběží";
            else if (victronAds == 0) s.error = "žádné vysílání Victron (Instant readout zapnutý? VictronConnect zavřený? poloha zapnutá?)";
            else s.error = "vidím Victron " + otherMac + ", ale ne " + mac + " – zkontroluj MAC";
        }
        victronAds = 0;
        sumVa = 0; n = 0; maxVa = -1;
        return s;
    }
}
