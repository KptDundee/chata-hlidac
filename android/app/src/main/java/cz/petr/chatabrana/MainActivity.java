package cz.petr.chatabrana;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.provider.Settings;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
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

/**
 * 1.7: obrazovka jako aplikace – karty (stav, ovládání, nastavení, oprávnění, záznam).
 * Nastavení je normálně jen ke čtení (nejde omylem přepsat), upravuje se po „Upravit“.
 * U každého tlačítka „?“ s vysvětlením.
 */
public class MainActivity extends Activity {
    private static final int BG = 0xFF121212, CARD = 0xFF1E1E1E, TXT = 0xFFEEEEEE, SUB = 0xFF9E9E9E,
            GOOD = 0xFF43A047, WARN = 0xFFFFB300, BAD = 0xFFE53935, ACC = 0xFF2A78D6, LINE = 0xFF333333;

    private EditText topic, ghtok, mac, key, email, pass, ips, xiaomi, rpass;
    private TextView stTitle, stSub, log, sumBox;
    private LinearLayout warnBox, editBox, permBox;
    private Button startBtn, editBtn, logBtn;
    private final Handler h = new Handler(Looper.getMainLooper());

    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        l.setPadding(dp(14), dp(14), dp(14), dp(24));
        l.setBackgroundColor(BG);

        TextView title = text(l, "⚡ Chata brána", 24, TXT, true);
        title.setPadding(dp(4), dp(6), 0, 0);
        TextView ver = text(l, "verze " + Collector.appVersion(this) + " · brána u měniče na chatě", 13, SUB, false);
        ver.setPadding(dp(4), 0, 0, dp(12));

        // ---- stav ----
        LinearLayout st = card(l);
        stTitle = text(st, "", 20, TXT, true);
        stSub = text(st, "", 14, SUB, false);
        stSub.setPadding(0, dp(4), 0, 0);
        warnBox = new LinearLayout(this);
        warnBox.setOrientation(LinearLayout.VERTICAL);
        st.addView(warnBox);

        // ---- ovládání ----
        LinearLayout ctl = card(l);
        header(ctl, "Ovládání");
        startBtn = action(ctl, "▶  Spustit bránu", ACC,
                "Spustí měření na pozadí: každých 10 minut přečte měnič Victron (Bluetooth), zásuvky Tapo, teploměry a baterii telefonu a pošle to hlídači. Běží i se zhasnutým displejem a po restartu telefonu se spustí sama. Když brána běží, tlačítko ji zastaví.",
                v -> {
                    if (Prefs.get(this).getBoolean(Prefs.RUNNING, false)) { GatewayService.stop(this); toast("Zastaveno"); refresh(); }
                    else askPermissionsThenStart();
                });
        action(ctl, "📤  Odeslat teď", CARD_BTN(),
                "Změří a pošle data hned, nečeká na dalších 10 minut. Hodí se po změně nastavení nebo když chceš na webu vidět čerstvý stav.",
                v -> { GatewayService.start(this, true); toast("Odesílám… (do 30 s)"); });
        Button test = action(ctl, "📶  Test Bluetooth (15 s)", CARD_BTN(),
                "15 sekund poslouchá Bluetooth a do záznamu zapíše, jestli vidí měnič Victron (a s jakým klíčem). Použij, když web píše „Victron neposílá“.",
                null);
        test.setOnClickListener(v -> {
            test.setEnabled(false);
            test.setText("Testuji… (15 s)");
            BleTest.run(this, () -> { test.setEnabled(true); test.setText("📶  Test Bluetooth (15 s)"); refresh(); });
        });

        // ---- nastavení ----
        LinearLayout set = card(l);
        header(set, "Nastavení");
        sumBox = text(set, "", 14, TXT, false);
        sumBox.setLineSpacing(0, 1.25f);
        editBtn = action(set, "✏️  Upravit nastavení", CARD_BTN(),
                "Nastavení je zamčené, aby se omylem nepřepsalo. Po „Upravit“ jde měnit, pak „Uložit“ (nebo „Zrušit“ – nic se nezmění).",
                v -> showEdit(true));
        editBox = new LinearLayout(this);
        editBox.setOrientation(LinearLayout.VERTICAL);
        editBox.setVisibility(View.GONE);
        set.addView(editBox);
        sub(editBox, "Hlídač");
        topic = field(editBox, "ntfy téma (stejné jako NTFY_TOPIC na GitHubu)", Prefs.NTFY_TOPIC, false);
        ghtok = field(editBox, "GitHub token (Actions: Read and write)", Prefs.GH_TOKEN, true);
        sub(editBox, "Měnič Victron (Bluetooth)");
        mac = field(editBox, "MAC adresa, např. AA:BB:CC:DD:EE:FF", Prefs.VICTRON_MAC, false);
        key = field(editBox, "Šifrovací klíč (32 znaků z VictronConnect)", Prefs.VICTRON_KEY, true);
        sub(editBox, "Zásuvky Tapo (místní Wi-Fi)");
        email = field(editBox, "E-mail účtu Tapo", Prefs.TAPO_EMAIL, false);
        pass = field(editBox, "Heslo účtu Tapo", Prefs.TAPO_PASSWORD, true);
        ips = field(editBox, "IP adresy (jen když hledání nenajde, např. 185, 106)", Prefs.TAPO_IPS, false);
        sub(editBox, "Teploměry Xiaomi (Bluetooth)");
        xiaomi = field(editBox, "Každý na řádek: MAC  BLE-KLÍČ  jméno", Prefs.XIAOMI, false);
        xiaomi.setSingleLine(false);
        xiaomi.setMinLines(3);
        xiaomi.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        sub(editBox, "Router M7000 (čtení baterie)");
        rpass = field(editBox, "Heslo správce routeru (prázdné = nečíst)", Prefs.ROUTER_PASS, true);
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, dp(10), 0, 0);
        editBox.addView(row);
        Button save = btn(row, "💾  Uložit", GOOD);
        Button cancel = btn(row, "Zrušit", CARD_BTN());
        ((LinearLayout.LayoutParams) save.getLayoutParams()).rightMargin = dp(8);
        save.setOnClickListener(v -> {
            save();
            showEdit(false);
            if (Prefs.get(this).getBoolean(Prefs.RUNNING, false)) GatewayService.start(this, true);
            toast("Uloženo");
            refresh();
        });
        cancel.setOnClickListener(v -> { loadFields(); showEdit(false); });

        // ---- oprávnění ----
        LinearLayout perm = card(l);
        header(perm, "Oprávnění a běh na pozadí");
        permBox = new LinearLayout(this);
        permBox.setOrientation(LinearLayout.VERTICAL);
        perm.addView(permBox);
        action(perm, "🔋  Baterie: Neomezeno", CARD_BTN(),
                "Android jinak aplikaci na pozadí uspává a data přestanou chodit. Nastav pro Chata brána „Bez omezení“.",
                v -> askBatteryExemption());
        action(perm, "📍  Poloha: Povolit vždy", CARD_BTN(),
                "Bluetooth (Victron, teploměry) se zhasnutým displejem Android pustí jen s polohou „Povolit vždy“. Otevře nastavení aplikace → Oprávnění → Poloha.",
                v -> startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", getPackageName(), null))));

        // ---- záznam ----
        LinearLayout lg = card(l);
        LinearLayout lh = new LinearLayout(this);
        lh.setOrientation(LinearLayout.HORIZONTAL);
        lh.setGravity(Gravity.CENTER_VERTICAL);
        lg.addView(lh);
        TextView lt = text(lh, "Záznam", 17, TXT, true);
        lt.setLayoutParams(new LinearLayout.LayoutParams(0, -2, 1));
        logBtn = btn(lh, "Zobrazit", CARD_BTN());
        log = text(lg, "", 12, SUB, false);
        log.setTypeface(Typeface.MONOSPACE);
        log.setVisibility(View.GONE);
        logBtn.setOnClickListener(v -> {
            boolean show = log.getVisibility() != View.VISIBLE;
            log.setVisibility(show ? View.VISIBLE : View.GONE);
            logBtn.setText(show ? "Skrýt" : "Zobrazit");
        });

        ScrollView sv = new ScrollView(this);
        sv.setFitsSystemWindows(true);
        sv.setBackgroundColor(BG);
        sv.addView(l);
        setContentView(sv);
        showEdit(false);
    }

    @Override protected void onResume() {
        super.onResume();
        if (Prefs.get(this).getBoolean(Prefs.RUNNING, false)) {
            try { GatewayService.refreshForeground(this); } catch (Exception ignored) { }
        }
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
        stTitle.setText(run ? "● Běží" : "● Zastaveno");
        stTitle.setTextColor(run ? GOOD : BAD);
        String ago = last > 0 ? new SimpleDateFormat("d. M. HH:mm", Locale.getDefault()).format(new Date(last))
                + " (před " + Math.max(0, (System.currentTimeMillis() - last) / 60000) + " min)" : "zatím nic";
        stSub.setText("Naposledy odesláno: " + ago);
        startBtn.setText(run ? "⏹  Zastavit bránu" : "▶  Spustit bránu");
        tint(startBtn, run ? CARD_BTN() : ACC);   // 1.7.1: „Zastavit“ neutrálně – červená vypadala jako chyba

        // varování
        warnBox.removeAllViews();
        PowerManager pm = getSystemService(PowerManager.class);
        boolean exempt = pm.isIgnoringBatteryOptimizations(getPackageName());
        if (run && last > 0 && System.currentTimeMillis() - last > 25 * 60_000L) warn(warnBox, "Přes 25 minut nic neodešlo – podívej se do záznamu.", BAD);
        if (!exempt) warn(warnBox, "Běh na pozadí není povolený (baterie) – níže „Baterie: Neomezeno“.", WARN);
        if (!bgLoc()) warn(warnBox, "Poloha není „Povolit vždy“ – Victron se zhasnutým displejem nemusí jít.", WARN);

        // oprávnění
        permBox.removeAllViews();
        permLine(permBox, "Běh na pozadí bez omezení", exempt);
        permLine(permBox, "Poloha vždy (Bluetooth na pozadí)", bgLoc());
        permLine(permBox, "Zařízení v okolí (Bluetooth)", checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN) == PackageManager.PERMISSION_GRANTED);

        // přehled nastavení (jen ke čtení)
        int nTh = 0;
        for (String ln : Prefs.s(this, Prefs.XIAOMI).split("\n")) if (ln.trim().split("\\s+").length >= 2) nTh++;
        String tp = Prefs.s(this, Prefs.NTFY_TOPIC);
        sumBox.setText("ntfy téma: " + (tp.isEmpty() ? "–" : tp.substring(0, Math.min(5, tp.length())) + "…") + "\n"
                + "GitHub token: " + ok(Prefs.GH_TOKEN) + "\n"
                + "Victron: " + (Prefs.s(this, Prefs.VICTRON_MAC).isEmpty() ? "–" : Prefs.s(this, Prefs.VICTRON_MAC)) + " · klíč " + ok(Prefs.VICTRON_KEY) + "\n"
                + "Tapo: " + (Prefs.s(this, Prefs.TAPO_EMAIL).isEmpty() ? "–" : Prefs.s(this, Prefs.TAPO_EMAIL)) + " · heslo " + ok(Prefs.TAPO_PASSWORD) + "\n"
                + "Teploměry Xiaomi: " + (nTh == 0 ? "žádné" : nTh) + "\n"
                + "Router M7000: " + (Prefs.get(this).getString(Prefs.ROUTER_PASS, "").isEmpty() ? "nečte se" : "heslo ✓ (čte baterii)"));
        log.setText(Prefs.log(this));
    }

    private String ok(String k) { return Prefs.s(this, k).isEmpty() ? "chybí" : "✓"; }

    private boolean bgLoc() {
        return checkSelfPermission(Manifest.permission.ACCESS_BACKGROUND_LOCATION) == PackageManager.PERMISSION_GRANTED;
    }

    private void showEdit(boolean on) {
        editBox.setVisibility(on ? View.VISIBLE : View.GONE);
        ((View) editBtn.getParent()).setVisibility(on ? View.GONE : View.VISIBLE);   // řádek s tlačítkem i „?“
        ((View) editBtn.getTag()).setVisibility(View.GONE);
        if (on) loadFields();
    }

    private void loadFields() {
        topic.setText(Prefs.s(this, Prefs.NTFY_TOPIC));
        ghtok.setText(Prefs.s(this, Prefs.GH_TOKEN));
        mac.setText(Prefs.s(this, Prefs.VICTRON_MAC));
        key.setText(Prefs.s(this, Prefs.VICTRON_KEY));
        email.setText(Prefs.s(this, Prefs.TAPO_EMAIL));
        pass.setText(Prefs.get(this).getString(Prefs.TAPO_PASSWORD, ""));
        ips.setText(Prefs.s(this, Prefs.TAPO_IPS));
        xiaomi.setText(Prefs.s(this, Prefs.XIAOMI));
        rpass.setText(Prefs.get(this).getString(Prefs.ROUTER_PASS, ""));
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
                .putString(Prefs.XIAOMI, xiaomi.getText().toString().trim())
                .putString(Prefs.ROUTER_PASS, rpass.getText().toString())
                .apply();
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

    // ---------- stavební kameny vzhledu ----------

    private static int CARD_BTN() { return 0xFF2C2C2C; }

    private LinearLayout card(LinearLayout parent) {
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setPadding(dp(16), dp(14), dp(16), dp(14));
        GradientDrawable g = new GradientDrawable();
        g.setColor(CARD);
        g.setCornerRadius(dp(16));
        g.setStroke(1, LINE);
        c.setBackground(g);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
        lp.bottomMargin = dp(12);
        parent.addView(c, lp);
        return c;
    }

    private TextView text(LinearLayout parent, String s, int sp, int color, boolean bold) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(sp);
        t.setTextColor(color);
        if (bold) t.setTypeface(Typeface.DEFAULT_BOLD);
        parent.addView(t);
        return t;
    }

    private void header(LinearLayout parent, String s) {
        TextView t = text(parent, s, 17, TXT, true);
        t.setPadding(0, 0, 0, dp(8));
    }

    private void sub(LinearLayout parent, String s) {
        TextView t = text(parent, s, 13, SUB, true);
        t.setPadding(0, dp(12), 0, dp(2));
    }

    private void warn(LinearLayout parent, String s, int color) {
        TextView t = text(parent, "⚠ " + s, 14, color, false);
        t.setPadding(0, dp(8), 0, 0);
    }

    private void permLine(LinearLayout parent, String s, boolean okv) {
        TextView t = text(parent, (okv ? "✓  " : "⚠  ") + s, 14, okv ? GOOD : WARN, false);
        t.setPadding(0, 0, 0, dp(4));
    }

    private Button btn(LinearLayout parent, String s, int color) {
        Button b = new Button(this);
        b.setText(s);
        b.setAllCaps(false);
        b.setTextColor(TXT);
        b.setTextSize(15);
        tint(b, color);
        LinearLayout.LayoutParams lp = parent.getOrientation() == LinearLayout.HORIZONTAL
                ? new LinearLayout.LayoutParams(0, dp(48), 1) : new LinearLayout.LayoutParams(-1, dp(48));
        parent.addView(b, lp);
        return b;
    }

    private void tint(Button b, int color) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(color);
        g.setCornerRadius(dp(12));
        b.setBackground(g);
        b.setStateListAnimator(null);
    }

    /** Tlačítko + „?“ vpravo; po ťuknutí na „?“ se pod ním rozbalí vysvětlení. */
    private Button action(LinearLayout parent, String label, int color, String help, View.OnClickListener click) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout.LayoutParams rp = new LinearLayout.LayoutParams(-1, -2);
        rp.topMargin = dp(6);
        parent.addView(row, rp);
        Button b = btn(row, label, color);
        b.setGravity(Gravity.CENTER_VERTICAL | Gravity.START);
        b.setPadding(dp(16), 0, dp(12), 0);
        if (click != null) b.setOnClickListener(click);
        TextView q = new TextView(this);
        q.setText("?");
        q.setTextSize(16);
        q.setTypeface(Typeface.DEFAULT_BOLD);
        q.setTextColor(SUB);
        q.setGravity(Gravity.CENTER);
        GradientDrawable g = new GradientDrawable();
        g.setShape(GradientDrawable.OVAL);
        g.setStroke(dp(1), SUB);
        q.setBackground(g);
        LinearLayout.LayoutParams qp = new LinearLayout.LayoutParams(dp(32), dp(32));
        qp.leftMargin = dp(10);
        row.addView(q, qp);
        TextView d = text(parent, help, 13, SUB, false);
        d.setPadding(dp(4), dp(6), dp(4), dp(4));
        d.setLineSpacing(0, 1.2f);
        d.setVisibility(View.GONE);
        q.setOnClickListener(v -> d.setVisibility(d.getVisibility() == View.VISIBLE ? View.GONE : View.VISIBLE));
        b.setTag(d);
        return b;
    }

    private EditText field(LinearLayout l, String hint, String prefKey, boolean secret) {
        EditText e = new EditText(this);
        e.setHint(hint);
        e.setHintTextColor(0xFF6E6E6E);
        e.setTextColor(TXT);
        e.setSingleLine(true);
        e.setText(Prefs.s(this, prefKey));
        e.setInputType(InputType.TYPE_CLASS_TEXT | (secret ? InputType.TYPE_TEXT_VARIATION_PASSWORD : InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS));
        l.addView(e);
        return e;
    }

    private void toast(String s) { Toast.makeText(this, s, Toast.LENGTH_SHORT).show(); }

    private int dp(int v) { return Math.round(v * getResources().getDisplayMetrics().density); }
}
