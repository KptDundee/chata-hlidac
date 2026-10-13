package cz.petr.chatahodinky;

import android.Manifest;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationManager;
import android.os.RemoteException;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.wear.watchface.complications.data.ComplicationData;
import androidx.wear.watchface.complications.data.ComplicationText;
import androidx.wear.watchface.complications.data.ComplicationType;
import androidx.wear.watchface.complications.data.NoDataComplicationData;
import androidx.wear.watchface.complications.data.PlainComplicationText;
import androidx.wear.watchface.complications.data.RangedValueComplicationData;
import androidx.wear.watchface.complications.data.ShortTextComplicationData;
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceService;
import androidx.wear.watchface.complications.datasource.ComplicationRequest;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

/**
 * Komplikace: aktuální venkovní teplota (Open-Meteo, zdarma, bez klíče).
 * Poloha: poslední známá poloha hodinek (když je povolená), jinak poloha chaty z hlídače, jinak Praha.
 * Výsledek se drží 20 minut, aby se zbytečně nestahovalo.
 */
public class TempComplication extends ComplicationDataSourceService {

    static final float MIN = -20f, MAX = 40f;

    @Override
    public void onComplicationRequest(@NonNull ComplicationRequest request, @NonNull ComplicationRequestListener listener) {
        new Thread(() -> {
            Double t = temperature(this);
            ComplicationData out = t == null ? new NoDataComplicationData() : build(request.getComplicationType(), t);
            try {
                listener.onComplicationData(out);
            } catch (RemoteException ignored) { }
        }).start();
    }

    @Nullable
    @Override
    public ComplicationData getPreviewData(@NonNull ComplicationType type) {
        return build(type, 14.0);
    }

    private ComplicationData build(ComplicationType type, double t) {
        String s = Math.round(t) + "°";
        ComplicationText desc = txt("Venku " + s);
        PendingIntent tap = PendingIntent.getActivity(this, 2, new Intent(this, MainActivity.class),
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        switch (type) {
            case RANGED_VALUE:
                return new RangedValueComplicationData.Builder((float) Math.max(MIN, Math.min(MAX, t)), MIN, MAX, desc)
                        .setText(txt(s)).setTapAction(tap).build();
            case SHORT_TEXT:
                return new ShortTextComplicationData.Builder(txt(s), desc).setTapAction(tap).build();
            default:
                return null;
        }
    }

    /** Teplota ve °C; z mezipaměti, je-li mladší 20 min. Při chybě poslední známá (max. 3 h), jinak null. */
    static Double temperature(Context c) {
        android.content.SharedPreferences p = Data.prefs(c);
        long age = System.currentTimeMillis() - p.getLong("temp_t", 0);
        if (age < 20 * 60_000L && p.contains("temp")) return (double) p.getFloat("temp", 0);
        double[] ll = location(c);
        HttpURLConnection con = null;
        try {
            URL u = new URL(String.format(Locale.US,
                    "https://api.open-meteo.com/v1/forecast?latitude=%.3f&longitude=%.3f&current=temperature_2m", ll[0], ll[1]));
            con = (HttpURLConnection) u.openConnection();
            con.setConnectTimeout(8000);
            con.setReadTimeout(8000);
            StringBuilder sb = new StringBuilder();
            try (BufferedReader r = new BufferedReader(new InputStreamReader(con.getInputStream(), StandardCharsets.UTF_8))) {
                String ln;
                while ((ln = r.readLine()) != null) sb.append(ln);
            }
            double t = new JSONObject(sb.toString()).getJSONObject("current").getDouble("temperature_2m");
            p.edit().putFloat("temp", (float) t).putLong("temp_t", System.currentTimeMillis()).apply();
            return t;
        } catch (Exception e) {
            return age < 3 * 3600_000L && p.contains("temp") ? (double) p.getFloat("temp", 0) : null;
        } finally {
            if (con != null) con.disconnect();
        }
    }

    /** Poslední známá poloha hodinek (síť / GPS / pasivní), jinak chata, jinak Praha. */
    static double[] location(Context c) {
        if (c.checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
            try {
                LocationManager lm = (LocationManager) c.getSystemService(Context.LOCATION_SERVICE);
                Location best = null;
                for (String prov : lm.getProviders(true)) {
                    Location l = lm.getLastKnownLocation(prov);
                    if (l != null && (best == null || l.getTime() > best.getTime())) best = l;
                }
                if (best != null && System.currentTimeMillis() - best.getTime() < 24 * 3600_000L) {
                    return new double[]{best.getLatitude(), best.getLongitude()};
                }
            } catch (SecurityException ignored) { }
        }
        JSONObject d = Data.cached(c);
        if (d != null && d.has("lat") && d.has("lon")) return new double[]{d.optDouble("lat"), d.optDouble("lon")};
        return new double[]{50.08, 14.43};
    }

    private static ComplicationText txt(String s) {
        return new PlainComplicationText.Builder(s).build();
    }
}
