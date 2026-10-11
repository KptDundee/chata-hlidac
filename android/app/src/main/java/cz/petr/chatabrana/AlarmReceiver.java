package cz.petr.chatabrana;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** Budík každých 10 minut (a po restartu telefonu) – probudí službu. */
public class AlarmReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context c, Intent i) {
        if (!Prefs.get(c).getBoolean(Prefs.RUNNING, false)) return;
        try {
            GatewayService.start(c);
        } catch (Exception e) {
            // Android někdy nedovolí spustit službu z pozadí – zkusíme to při dalším budíku
            Prefs.log(c, "Nejde spustit službu: " + e.getMessage());
            GatewayService.scheduleAlarm(c);
        }
    }
}
