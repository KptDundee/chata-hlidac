package cz.petr.chatahodinky;

import android.app.PendingIntent;
import android.content.Intent;
import android.graphics.drawable.Icon;
import android.os.RemoteException;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.wear.watchface.complications.data.ComplicationData;
import androidx.wear.watchface.complications.data.ComplicationText;
import androidx.wear.watchface.complications.data.ComplicationType;
import androidx.wear.watchface.complications.data.LongTextComplicationData;
import androidx.wear.watchface.complications.data.MonochromaticImage;
import androidx.wear.watchface.complications.data.PlainComplicationText;
import androidx.wear.watchface.complications.data.ShortTextComplicationData;
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceService;
import androidx.wear.watchface.complications.datasource.ComplicationRequest;

import org.json.JSONObject;

import java.time.LocalDate;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;

/**
 * Komplikace: východ a západ slunce u chaty. Počítá se přímo v hodinkách (bez internetu)
 * z polohy chaty, kterou posílá hlídač; než první data dorazí, bere se Praha.
 * Ukazuje jen nejbližší událost: přes den západ („↓ 18:12“), v noci východ („↑ 6:58“).
 */
public class SunComplication extends ComplicationDataSourceService {

    private static final double LAT = 50.08, LON = 14.43;       // náhradní poloha (Praha)
    private static final DateTimeFormatter HM = DateTimeFormatter.ofPattern("H:mm");

    @Override
    public void onComplicationRequest(@NonNull ComplicationRequest request, @NonNull ComplicationRequestListener listener) {
        JSONObject d = Data.cached(this);
        double lat = d != null && d.has("lat") ? d.optDouble("lat", LAT) : LAT;
        double lon = d != null && d.has("lon") ? d.optDouble("lon", LON) : LON;
        try {
            listener.onComplicationData(build(request.getComplicationType(), lat, lon, ZonedDateTime.now()));
        } catch (RemoteException ignored) { }
    }

    @Nullable
    @Override
    public ComplicationData getPreviewData(@NonNull ComplicationType type) {
        return build(type, LAT, LON, ZonedDateTime.now());
    }

    private ComplicationData build(ComplicationType type, double lat, double lon, ZonedDateTime now) {
        ZoneId zone = now.getZone();
        LocalDate today = now.toLocalDate();
        ZonedDateTime rise = sun(today, lat, lon, true, zone), set = sun(today, lat, lon, false, zone);
        String r = rise == null ? "–" : rise.format(HM), s = set == null ? "–" : set.format(HM);
        ComplicationText desc = txt("Východ slunce " + r + ", západ " + s);
        PendingIntent tap = PendingIntent.getActivity(this, 1, new Intent(this, MainActivity.class),
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        // jen nejbližší událost: přes den západ, v noci východ
        String title, t;
        if (rise != null && now.isBefore(rise)) { title = "↑"; t = r; }
        else if (set != null && now.isBefore(set)) { title = "↓"; t = s; }
        else {
            ZonedDateTime r2 = sun(today.plusDays(1), lat, lon, true, zone);
            title = "↑"; t = r2 == null ? "–" : r2.format(HM);
        }
        // ikonka: slunce na obzoru + výrazná šipka (nahoru = východ, dolů = západ)
        MonochromaticImage img = new MonochromaticImage.Builder(
                Icon.createWithResource(this, "↑".equals(title) ? R.drawable.ic_sunrise : R.drawable.ic_sunset)).build();
        switch (type) {
            case LONG_TEXT:
                return new LongTextComplicationData.Builder(txt(t), desc)
                        .setMonochromaticImage(img).setTapAction(tap).build();
            case SHORT_TEXT:
                return new ShortTextComplicationData.Builder(txt(t), desc).setTitle(txt(title))
                        .setMonochromaticImage(img).setTapAction(tap).build();
            default:
                return null;
        }
    }

    /** Východ / západ slunce (algoritmus NOAA / Almanac for Computers, přesnost ~1 min). */
    static ZonedDateTime sun(LocalDate date, double lat, double lon, boolean rising, ZoneId zone) {
        double zenith = 90.833;
        int n = date.getDayOfYear();
        double lngHour = lon / 15.0;
        double t = n + ((rising ? 6 : 18) - lngHour) / 24.0;
        double m = 0.9856 * t - 3.289;
        double l = norm(m + 1.916 * sin(m) + 0.020 * sin(2 * m) + 282.634, 360);
        double ra = norm(Math.toDegrees(Math.atan(0.91764 * tan(l))), 360);
        ra += Math.floor(l / 90) * 90 - Math.floor(ra / 90) * 90;
        ra /= 15.0;
        double sinDec = 0.39782 * sin(l);
        double cosDec = Math.cos(Math.asin(sinDec));
        double cosH = (cos(zenith) - sinDec * sin(lat)) / (cosDec * cos(lat));
        if (cosH > 1 || cosH < -1) return null;               // polární den / noc
        double h = rising ? 360 - Math.toDegrees(Math.acos(cosH)) : Math.toDegrees(Math.acos(cosH));
        h /= 15.0;
        double localT = h + ra - 0.06571 * t - 6.622;
        double ut = norm(localT - lngHour, 24);
        long secs = Math.round(ut * 3600);
        ZonedDateTime utc = date.atStartOfDay(ZoneOffset.UTC).plusSeconds(secs);
        return utc.withZoneSameInstant(zone);
    }

    private static double sin(double deg) { return Math.sin(Math.toRadians(deg)); }
    private static double cos(double deg) { return Math.cos(Math.toRadians(deg)); }
    private static double tan(double deg) { return Math.tan(Math.toRadians(deg)); }
    private static double norm(double x, double m) { x %= m; return x < 0 ? x + m : x; }

    private static ComplicationText txt(String s) {
        return new PlainComplicationText.Builder(s).build();
    }
}
