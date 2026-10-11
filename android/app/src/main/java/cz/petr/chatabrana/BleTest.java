package cz.petr.chatabrana;

import android.Manifest;
import android.annotation.SuppressLint;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothManager;
import android.bluetooth.le.BluetoothLeScanner;
import android.bluetooth.le.ScanCallback;
import android.bluetooth.le.ScanResult;
import android.bluetooth.le.ScanSettings;
import android.content.Context;
import android.content.pm.PackageManager;
import android.location.LocationManager;
import android.os.Handler;
import android.os.Looper;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/** Diagnostika: 15 s poslouchá všechno na Bluetooth a zapíše do záznamu, co vidí. */
public final class BleTest {
    private BleTest() {}

    @SuppressLint("MissingPermission")
    public static void run(Context ctx, Runnable done) {
        Context c = ctx.getApplicationContext();
        StringBuilder sb = new StringBuilder("Test Bluetooth: ");
        boolean scanPerm = c.checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN) == PackageManager.PERMISSION_GRANTED;
        boolean locPerm = c.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED;
        LocationManager lm = (LocationManager) c.getSystemService(Context.LOCATION_SERVICE);
        boolean locOn = lm != null && lm.isLocationEnabled();
        sb.append("oprávnění Zařízení v okolí=").append(scanPerm ? "ANO" : "NE")
          .append(", Poloha=").append(locPerm ? "ANO" : "NE")
          .append(", poloha zapnutá=").append(locOn ? "ANO" : "NE");
        BluetoothManager bm = (BluetoothManager) c.getSystemService(Context.BLUETOOTH_SERVICE);
        BluetoothAdapter a = bm == null ? null : bm.getAdapter();
        if (a == null || !a.isEnabled()) { Prefs.log(c, sb + ", Bluetooth VYPNUTÝ"); done.run(); return; }
        BluetoothLeScanner sc = a.getBluetoothLeScanner();
        if (sc == null || !scanPerm) { Prefs.log(c, sb + ", sken nejde spustit"); done.run(); return; }

        Set<String> all = new HashSet<>();
        Map<String, String> victron = new HashMap<>();
        byte[] key = VictronParser.hex(Prefs.s(c, Prefs.VICTRON_KEY));
        ScanCallback cb = new ScanCallback() {
            @Override public void onScanResult(int t, ScanResult r) {
                String addr = r.getDevice().getAddress();
                all.add(addr);
                if (r.getScanRecord() == null) return;
                byte[] d = r.getScanRecord().getManufacturerSpecificData(VictronParser.MANUFACTURER_ID);
                if (d == null) return;
                String info;
                if (d.length < 8) info = "krátký záznam";
                else if ((d[0] & 0xFF) != 0x10) info = "není Instant readout (Instant readout vypnutý?)";
                else {
                    info = String.format(Locale.US, "typ %02X", d[4] & 0xFF);
                    if (key.length == 16) {
                        try {
                            VictronParser.Inverter i = VictronParser.parse(d, key);
                            info += String.format(Locale.US, " → OK %s V, %s VA, %s", i.batteryV, i.acVa, i.stateName());
                        } catch (Exception e) {
                            info += " → " + e.getMessage();
                        }
                    }
                }
                victron.put(addr, info);
            }
        };
        try {
            sc.startScan(null, new ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build(), cb);
        } catch (Exception e) {
            Prefs.log(c, sb + ", chyba: " + e.getMessage());
            done.run();
            return;
        }
        new Handler(Looper.getMainLooper()).postDelayed(() -> {
            try { sc.stopScan(cb); } catch (Exception ignored) {}
            sb.append(" | zařízení v okolí: ").append(all.size());
            if (victron.isEmpty()) sb.append(", Victron: žádný");
            for (Map.Entry<String, String> e : victron.entrySet()) sb.append(" | Victron ").append(e.getKey()).append(": ").append(e.getValue());
            Prefs.log(c, sb.toString());
            done.run();
        }, 15_000);
    }
}
