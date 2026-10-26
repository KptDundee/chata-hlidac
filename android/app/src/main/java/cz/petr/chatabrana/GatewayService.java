package cz.petr.chatabrana;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;
import android.os.SystemClock;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Služba v popředí: drží Bluetooth poslech měniče a každých 10 minut
 * (budík AlarmManager) spustí sběr a odeslání.
 */
public class GatewayService extends Service {
    public static final String ACTION_TICK = "cz.petr.chatabrana.TICK";
    public static final String ACTION_STOP = "cz.petr.chatabrana.STOP";
    static final long INTERVAL_MS = 10 * 60_000L;
    static final long FAST_MS = 2 * 60_000L;
    private static final String CHANNEL = "brana";
    private static final int NOTIF_ID = 1;

    private BleListener ble;
    private Collector collector;
    private final ExecutorService exec = Executors.newSingleThreadExecutor();
    private long namesAt;
    private volatile Thread wakeThread;
    private volatile long lastWake;

    public static void start(Context c) { start(c, false); }

    /** @param restart true = restartovat Bluetooth poslech (po změně nastavení) */
    public static void start(Context c, boolean restart) {
        Intent i = new Intent(c, GatewayService.class).setAction(ACTION_TICK).putExtra("restart", restart);
        if (Build.VERSION.SDK_INT >= 26) c.startForegroundService(i); else c.startService(i);
    }

    /** Z otevřené aplikace: obnovit službu s polohou (bez měření). */
    public static void refreshForeground(Context c) {
        Intent i = new Intent(c, GatewayService.class).setAction("fg");
        if (Build.VERSION.SDK_INT >= 26) c.startForegroundService(i); else c.startService(i);
    }

    public static void stop(Context c) {
        c.startService(new Intent(c, GatewayService.class).setAction(ACTION_STOP));
    }

    @Override public void onCreate() {
        super.onCreate();
        ble = new BleListener(this);
        collector = new Collector(this, ble);
        NotificationManager nm = getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel(CHANNEL, "Chata brána", NotificationManager.IMPORTANCE_LOW));
    }

    private int fgType = -1;

    /**
     * Služba typu „připojené zařízení“ + „poloha“. Výsledky Bluetooth skenu Android doručuje jen aplikaci,
     * která smí polohu – bez typu „poloha“ (a bez „Povolit vždy“) o ni služba přijde, jakmile se aplikace zavře:
     * proto po instalaci (aplikace otevřená) Victron jde a pak přestane. Z pozadí (budík) Android typ „poloha“
     * nemusí povolit → pak jen „připojené zařízení“ a záznam do Deníku.
     */
    private void startFg(Notification n) {
        int dev = ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE;
        int loc = checkSelfPermission(android.Manifest.permission.ACCESS_FINE_LOCATION) == android.content.pm.PackageManager.PERMISSION_GRANTED
                ? ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION : 0;
        int want = dev | loc;                       // vždy zkusit s polohou (když se dřív nepovedlo z pozadí, teď třeba z aplikace)
        try {
            startForeground(NOTIF_ID, n, want);
            fgType = want;
        } catch (Exception e) {
            if (want == dev) throw e;
            if (fgType != dev) Prefs.log(this, "Služba bez polohy (Android nedovolil z pozadí) – Victron půjde jen s polohou „Povolit vždy“ nebo po otevření aplikace");
            startForeground(NOTIF_ID, n, dev);
            fgType = dev;
        }
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            Prefs.get(this).edit().putBoolean(Prefs.RUNNING, false).apply();
            cancelAlarm(this);
            Thread w = wakeThread; wakeThread = null; if (w != null) w.interrupt();
            ble.stop();
            stopForeground(STOP_FOREGROUND_REMOVE);
            stopSelf();
            return START_NOT_STICKY;
        }
        if (intent != null && "fg".equals(intent.getAction()) && fgType >= 0) {
            // aplikace otevřená → teď Android dovolí službě typ „poloha“ (Victron i po zhasnutí displeje)
            if (Build.VERSION.SDK_INT >= 29) startFg(notification("Běží"));
            return START_STICKY;
        }
        Prefs.get(this).edit().putBoolean(Prefs.RUNNING, true).apply();
        Notification n = notification("Spouštím…");
        if (Build.VERSION.SDK_INT >= 29) startFg(n);
        else startForeground(NOTIF_ID, n);
        ble.ensureRunning(intent != null && intent.getBooleanExtra("restart", false));
        scheduleAlarm(this);
        startWakeListener();
        tick();
        return START_STICKY;
    }

    /**
     * Nouzové spuštění z aplikace: trvalé spojení na ntfy téma <topic>-wake. Když tam přijde zpráva
     * (tlačítko ⚡ Načíst na webu → hlídač ji pošle), Flip hned změří a odešle, nečeká na budík.
     */
    private void startWakeListener() {
        if (wakeThread != null && wakeThread.isAlive()) return;
        Thread t = new Thread(() -> {
            while (wakeThread == Thread.currentThread()) {
                String topic = Prefs.s(this, Prefs.NTFY_TOPIC);
                if (topic.isEmpty()) { SystemClock.sleep(60_000); continue; }
                java.net.HttpURLConnection c = null;
                try {
                    c = (java.net.HttpURLConnection) new java.net.URL("https://ntfy.sh/" + topic + "-wake/json").openConnection();
                    c.setConnectTimeout(20_000);
                    c.setReadTimeout(150_000);              // ntfy posílá „keepalive“ každých 45 s
                    java.io.BufferedReader r = new java.io.BufferedReader(new java.io.InputStreamReader(c.getInputStream(), "UTF-8"));
                    String ln;
                    while ((ln = r.readLine()) != null && wakeThread == Thread.currentThread()) {
                        if (!ln.contains("\"event\":\"message\"")) continue;
                        if (SystemClock.elapsedRealtime() - lastWake < 60_000) continue;
                        lastWake = SystemClock.elapsedRealtime();
                        boolean fromWatch = ln.contains("\"message\":\"hodinky\"");
                        Prefs.log(this, fromWatch ? "Probuzení z hodinek – měřím a spouštím hlídače" : "Probuzení z aplikace – měřím hned");
                        tick(fromWatch);                // z webu hlídače už spustil web, z hodinek ho spustí Flip
                    }
                } catch (Exception e) {
                    SystemClock.sleep(30_000);              // bez internetu: zkusit znovu za chvíli
                } finally {
                    if (c != null) c.disconnect();
                }
            }
        }, "wake");
        t.setDaemon(true);
        wakeThread = t;
        t.start();
    }

    private void tick() { tick(true); }

    private void tick(boolean dispatch) {
        PowerManager pm = getSystemService(PowerManager.class);
        PowerManager.WakeLock wl = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "chatabrana:tick");
        wl.acquire(4 * 60_000L);      // hledání zásuvek + historie + opakované odeslání se do 2 min nemusí vejít
        exec.execute(() -> {
            try {
                if (SystemClock.elapsedRealtime() - namesAt > 3600_000L) { collector.forgetNames(); namesAt = SystemClock.elapsedRealtime(); }
                // první běh po startu: chvíli počkat, ať se stihne chytit měnič
                if (Prefs.get(this).getLong(Prefs.LAST_SENT, 0) == 0) SystemClock.sleep(20_000);
                dailyRestart();                          // 1.9.11
                String res = collector.runOnce(dispatch);
                scheduleAlarm(this);                    // 1.7.3: generátor → další měření za 2 min (nebo zpět na 10 min)
                String time = new SimpleDateFormat("HH:mm", Locale.getDefault()).format(new Date());
                getSystemService(NotificationManager.class).notify(NOTIF_ID, notification(time + " · " + res));
                // 1.3.9: zpět jako do 1.3.6 – sken se restartuje jen po 25 min (restart po každém měření v 1.3.7
                // poslech na pozadí zhoršil: Android sken spuštěný se zhasnutým displejem nemusí rozběhnout)
                ble.ensureRunning();
            } finally {
                if (wl.isHeld()) wl.release();
            }
        });
    }


    /** 1.9.11: každý den v nastavený čas (výchozí 22:10, prázdné = vypnuto) restart Brány bez ukončení aplikace:
     *  Bluetooth sken znovu (se zrušením staré registrace), nová spojení se zásuvkami a prohledání sítě, znovu poslech
     *  probuzení. Aplikace se neukončuje – kdyby se po ukončení nespustila, Flip by z dálky nikdo nerozběhl. */
    private void dailyRestart() {
        android.content.SharedPreferences P = Prefs.get(this);
        String at = P.getString("rst_at", "22:10").trim();
        if (at.isEmpty() || !at.matches("\\d{1,2}:\\d{2}")) return;
        java.util.Calendar c = java.util.Calendar.getInstance();
        String day = new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(c.getTime());
        if (day.equals(P.getString("rst_day", ""))) return;
        String[] hm = at.split(":");
        java.util.Calendar t = (java.util.Calendar) c.clone();
        t.set(java.util.Calendar.HOUR_OF_DAY, Integer.parseInt(hm[0])); t.set(java.util.Calendar.MINUTE, Integer.parseInt(hm[1]));
        t.set(java.util.Calendar.SECOND, 0);
        long d = c.getTimeInMillis() - t.getTimeInMillis();
        if (d < 0 || d > 2 * 3600_000L) return;                       // jen v čase restartu (do 2 h, kdyby měření chybělo)
        Prefs.log(this, "Plánovaný restart Brány (Bluetooth, zásuvky, probuzení)");
        P.edit().putString("rst_day", day).putLong("rst_t", System.currentTimeMillis()).putBoolean("rst_sent", false).apply();
        try { collector.softReset(); } catch (Exception e) { Prefs.log(this, "Restart – zásuvky: " + e.getMessage()); }
        try { ble.stop(); ble.ensureRunning(true); } catch (Exception e) { Prefs.log(this, "Restart – Bluetooth: " + e.getMessage()); }
        Thread w = wakeThread; wakeThread = null; if (w != null) w.interrupt();
        startWakeListener();
        SystemClock.sleep(20_000);                                     // ať Bluetooth stihne chytit měnič a teploměry
    }

    private Notification notification(String text) {
        PendingIntent open = PendingIntent.getActivity(this, 0, new Intent(this, MainActivity.class),
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        return new Notification.Builder(this, CHANNEL)
                .setContentTitle("Chata brána")
                .setContentText(text)
                .setStyle(new Notification.BigTextStyle().bigText(text))
                .setSmallIcon(android.R.drawable.stat_sys_data_bluetooth)
                .setContentIntent(open)
                .setOngoing(true)
                .build();
    }

    static PendingIntent alarmIntent(Context c) {
        Intent i = new Intent(c, AlarmReceiver.class);
        return PendingIntent.getBroadcast(c, 1, i, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
    }

    static void scheduleAlarm(Context c) {
        AlarmManager am = c.getSystemService(AlarmManager.class);
        // 1.7.3: při nabíjení z generátoru každé 2 min, jinak 10 min
        boolean fast = System.currentTimeMillis() < Prefs.get(c).getLong("fast_until", 0);
        long at = SystemClock.elapsedRealtime() + (fast ? FAST_MS : INTERVAL_MS);
        // přesný budík i v úsporném režimu (jinak Android běh natahuje na 15–20 min)
        if (am.canScheduleExactAlarms()) {
            am.setExactAndAllowWhileIdle(AlarmManager.ELAPSED_REALTIME_WAKEUP, at, alarmIntent(c));
        } else {
            am.setAndAllowWhileIdle(AlarmManager.ELAPSED_REALTIME_WAKEUP, at, alarmIntent(c));
        }
    }

    static void cancelAlarm(Context c) {
        c.getSystemService(AlarmManager.class).cancel(alarmIntent(c));
    }

    @Override public void onDestroy() {
        ble.stop();
        exec.shutdownNow();
        super.onDestroy();
    }

    @Override public IBinder onBind(Intent intent) { return null; }
}
