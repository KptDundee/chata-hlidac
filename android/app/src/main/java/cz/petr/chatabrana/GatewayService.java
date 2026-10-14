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
    private static final String CHANNEL = "brana";
    private static final int NOTIF_ID = 1;

    private BleListener ble;
    private Collector collector;
    private final ExecutorService exec = Executors.newSingleThreadExecutor();
    private long namesAt;

    public static void start(Context c) { start(c, false); }

    /** @param restart true = restartovat Bluetooth poslech (po změně nastavení) */
    public static void start(Context c, boolean restart) {
        Intent i = new Intent(c, GatewayService.class).setAction(ACTION_TICK).putExtra("restart", restart);
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
        // každých 30 s: objevila se / zmizela zásuvka (generátor)? → poslat hned (Flip je na nabíječce, nespí)
        Thread w = new Thread(() -> {
            while (!exec.isShutdown()) {
                SystemClock.sleep(30_000);
                if (!Prefs.get(this).getBoolean(Prefs.RUNNING, false)) continue;
                try { exec.execute(() -> { if (collector.watch()) tick(); }); } catch (Exception ignored) { }
            }
        }, "zasuvky-watch");
        w.setDaemon(true);
        w.start();
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            Prefs.get(this).edit().putBoolean(Prefs.RUNNING, false).apply();
            cancelAlarm(this);
            ble.stop();
            stopForeground(STOP_FOREGROUND_REMOVE);
            stopSelf();
            return START_NOT_STICKY;
        }
        Prefs.get(this).edit().putBoolean(Prefs.RUNNING, true).apply();
        Notification n = notification("Spouštím…");
        if (Build.VERSION.SDK_INT >= 29) startForeground(NOTIF_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE);
        else startForeground(NOTIF_ID, n);
        ble.ensureRunning(intent != null && intent.getBooleanExtra("restart", false));
        scheduleAlarm(this);
        tick();
        return START_STICKY;
    }

    private void tick() {
        PowerManager pm = getSystemService(PowerManager.class);
        PowerManager.WakeLock wl = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "chatabrana:tick");
        wl.acquire(2 * 60_000L);
        exec.execute(() -> {
            try {
                if (SystemClock.elapsedRealtime() - namesAt > 3600_000L) { collector.forgetNames(); namesAt = SystemClock.elapsedRealtime(); }
                // první běh po startu: chvíli počkat, ať se stihne chytit měnič
                if (Prefs.get(this).getLong(Prefs.LAST_SENT, 0) == 0) SystemClock.sleep(20_000);
                String res = collector.runOnce();
                String time = new SimpleDateFormat("HH:mm", Locale.getDefault()).format(new Date());
                getSystemService(NotificationManager.class).notify(NOTIF_ID, notification(time + " · " + res));
                ble.ensureRunning();
            } finally {
                if (wl.isHeld()) wl.release();
            }
        });
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
        long at = SystemClock.elapsedRealtime() + INTERVAL_MS;
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
