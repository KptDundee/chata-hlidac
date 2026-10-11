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
import android.os.SystemClock;

import java.util.Collections;

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
        if (r.getScanRecord() == null || key == null) return;
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
    public synchronized void ensureRunning() {
        String m = Prefs.normMac(Prefs.s(ctx, Prefs.VICTRON_MAC));
        String k = Prefs.s(ctx, Prefs.VICTRON_KEY).replaceAll("[^0-9a-fA-F]", "");
        if (k.length() < 32) { stop(); lastError = "Chybí šifrovací klíč měniče (32 znaků)"; return; }
        if (!m.equals(mac) || key == null) { stop(); mac = m; key = VictronParser.hex(k); }
        if (scanner != null && SystemClock.elapsedRealtime() - startedAt < 25 * 60_000L) return;
        stop();
        BluetoothManager bm = (BluetoothManager) ctx.getSystemService(Context.BLUETOOTH_SERVICE);
        BluetoothAdapter a = bm == null ? null : bm.getAdapter();
        if (a == null || !a.isEnabled()) { lastError = "Bluetooth je vypnutý"; return; }
        scanner = a.getBluetoothLeScanner();
        if (scanner == null) { lastError = "Bluetooth sken není dostupný"; return; }
        // filtr podle výrobce Victron (0x02E1) a typu „Instant readout“ (0x10) – nezávisle na typu MAC adresy
        ScanFilter f = new ScanFilter.Builder()
                .setManufacturerData(VictronParser.MANUFACTURER_ID, new byte[]{0x10}, new byte[]{(byte) 0xFF})
                .build();
        ScanSettings s = new ScanSettings.Builder()
                .setScanMode(ScanSettings.SCAN_MODE_LOW_POWER)
                .build();
        try {
            scanner.startScan(Collections.singletonList(f), s, cb);
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
