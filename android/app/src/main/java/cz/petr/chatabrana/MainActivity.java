package cz.petr.chatabrana;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.provider.Settings;
import android.text.InputType;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

/** Jednoduchá obrazovka: nastavení, start/stop, stav a log. */
public class MainActivity extends Activity {
    private EditText topic, ghtok, mac, key, email, pass, ips;
    private TextView status, log;
    private final Handler h = new Handler(Looper.getMainLooper());

    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        int pad = dp(16);
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        l.setPadding(pad, pad, pad, pad);

        TextView title = new TextView(this);
        title.setText("Chata brána " + Collector.appVersion(this));
        title.setTextSize(24);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        l.addView(title);
        status = new TextView(this);
        status.setPadding(0, dp(4), 0, dp(12));
        l.addView(status);

        section(l, "Hlídač (ntfy)");
        topic = field(l, "ntfy téma (stejné jako NTFY_TOPIC na GitHubu)", Prefs.NTFY_TOPIC, false);
        ghtok = field(l, "GitHub token (stejný jako na webu u ⚡ Načíst) – Flip pak po každém měření spustí hlídače", Prefs.GH_TOKEN, true);
        section(l, "Měnič Victron (Bluetooth)");
        mac = field(l, "MAC adresa, např. AA:BB:CC:DD:EE:FF", Prefs.VICTRON_MAC, false);
        key = field(l, "Šifrovací klíč (32 znaků z VictronConnect)", Prefs.VICTRON_KEY, true);
        section(l, "Zásuvky Tapo (místní Wi-Fi)");
        email = field(l, "E-mail účtu Tapo", Prefs.TAPO_EMAIL, false);
        pass = field(l, "Heslo účtu Tapo", Prefs.TAPO_PASSWORD, true);
        ips = field(l, "IP adresy oddělené čárkou (stačí konec: 185, 106, …)", Prefs.TAPO_IPS, false);

        Button save = button(l, "Uložit a spustit");
        save.setOnClickListener(v -> { save(); askPermissionsThenStart(); });
        Button now = button(l, "Odeslat teď");
        now.setOnClickListener(v -> { save(); GatewayService.start(this, true); toast("Odesílám… (do 30 s)"); });
        Button batt = button(l, "Povolit běh na pozadí (baterie: Neomezeno)");
        batt.setOnClickListener(v -> askBatteryExemption());
        Button test = button(l, "Test Bluetooth (15 s)");
        test.setOnClickListener(v -> {
            save();
            test.setEnabled(false);
            test.setText("Testuji… (15 s)");
            BleTest.run(this, () -> { test.setEnabled(true); test.setText("Test Bluetooth (15 s)"); refresh(); });
        });
        Button stop = button(l, "Zastavit");
        stop.setOnClickListener(v -> { GatewayService.stop(this); toast("Zastaveno"); refresh(); });

        section(l, "Záznam");
        log = new TextView(this);
        log.setTextSize(12);
        log.setTypeface(Typeface.MONOSPACE);
        l.addView(log);

        ScrollView sv = new ScrollView(this);
        sv.setFitsSystemWindows(true);
        sv.addView(l);
        setContentView(sv);
    }

    @Override protected void onResume() {
        super.onResume();
        refresh();
        h.postDelayed(tickUi, 5000);
    }

    @Override protected void onPause() {
        super.onPause();
        h.removeCallbacks(tickUi);
    }

    private final Runnable tickUi = new Runnable() {
        @Override public void run() { refresh(); h.postDelayed(this, 5000); }
    };

    private void refresh() {
        SharedPreferences p = Prefs.get(this);
        long last = p.getLong(Prefs.LAST_SENT, 0);
        boolean run = p.getBoolean(Prefs.RUNNING, false);
        PowerManager pm = getSystemService(PowerManager.class);
        boolean exempt = pm.isIgnoringBatteryOptimizations(getPackageName());
        status.setText((run ? "▶ Běží" : "■ Zastaveno")
                + (last > 0 ? " · naposledy odesláno " + new SimpleDateFormat("d.M. HH:mm", Locale.getDefault()).format(new Date(last)) : "")
                + (exempt ? "" : "\n⚠ Běh na pozadí není povolený – klepni na tlačítko níže"));
        log.setText(Prefs.log(this));
    }

    private void save() {
        Prefs.get(this).edit()
                .putString(Prefs.NTFY_TOPIC, topic.getText().toString().trim())
                .putString(Prefs.GH_TOKEN, ghtok.getText().toString().trim())
                .putString(Prefs.VICTRON_MAC, Prefs.normMac(mac.getText().toString()))
                .putString(Prefs.VICTRON_KEY, key.getText().toString().trim())
                .putString(Prefs.TAPO_EMAIL, email.getText().toString().trim())
                .putString(Prefs.TAPO_PASSWORD, pass.getText().toString())
                .putString(Prefs.TAPO_IPS, ips.getText().toString().trim())
                .apply();
        mac.setText(Prefs.s(this, Prefs.VICTRON_MAC));   // ukáže upravený tvar
    }

    private void askPermissionsThenStart() {
        List<String> need = new ArrayList<>();
        for (String perm : new String[]{Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.POST_NOTIFICATIONS}) {
            if (checkSelfPermission(perm) != PackageManager.PERMISSION_GRANTED) need.add(perm);
        }
        if (need.isEmpty()) { startGateway(); return; }
        requestPermissions(need.toArray(new String[0]), 1);
    }

    @Override public void onRequestPermissionsResult(int req, String[] perms, int[] res) {
        super.onRequestPermissionsResult(req, perms, res);
        if (checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN) != PackageManager.PERMISSION_GRANTED) {
            toast("Bez oprávnění „Zařízení v okolí“ nejde číst měnič");
        }
        startGateway();
    }

    private void startGateway() {
        Prefs.get(this).edit().putLong(Prefs.LAST_SENT, 0).apply();
        GatewayService.start(this, true);
        toast("Spuštěno – první data za ~30 s");
        if (!getSystemService(PowerManager.class).isIgnoringBatteryOptimizations(getPackageName())) askBatteryExemption();
        refresh();
    }

    private void askBatteryExemption() {
        try {
            startActivity(new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:" + getPackageName())));
        } catch (Exception e) {
            startActivity(new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS));
        }
    }

    private void section(LinearLayout l, String text) {
        TextView t = new TextView(this);
        t.setText(text);
        t.setTypeface(Typeface.DEFAULT_BOLD);
        t.setPadding(0, dp(16), 0, dp(4));
        l.addView(t);
    }

    private EditText field(LinearLayout l, String hint, String prefKey, boolean secret) {
        EditText e = new EditText(this);
        e.setHint(hint);
        e.setSingleLine(true);
        e.setText(Prefs.s(this, prefKey));
        e.setInputType(InputType.TYPE_CLASS_TEXT | (secret ? InputType.TYPE_TEXT_VARIATION_PASSWORD : InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS));
        l.addView(e);
        return e;
    }

    private Button button(LinearLayout l, String text) {
        Button b = new Button(this);
        b.setText(text);
        b.setAllCaps(false);
        l.addView(b);
        return b;
    }

    private void toast(String s) { Toast.makeText(this, s, Toast.LENGTH_SHORT).show(); }

    private int dp(int v) { return Math.round(v * getResources().getDisplayMetrics().density); }

}
