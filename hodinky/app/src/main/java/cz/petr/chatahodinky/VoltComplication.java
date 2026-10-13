package cz.petr.chatahodinky;

import android.app.PendingIntent;
import android.content.Intent;
import android.os.RemoteException;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.wear.watchface.complications.data.ComplicationData;
import androidx.wear.watchface.complications.data.ComplicationText;
import androidx.wear.watchface.complications.data.ComplicationType;
import androidx.wear.watchface.complications.data.LongTextComplicationData;
import androidx.wear.watchface.complications.data.NoDataComplicationData;
import androidx.wear.watchface.complications.data.PlainComplicationText;
import androidx.wear.watchface.complications.data.RangedValueComplicationData;
import androidx.wear.watchface.complications.data.ShortTextComplicationData;
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceService;
import androidx.wear.watchface.complications.datasource.ComplicationRequest;

import org.json.JSONObject;

/** Komplikace na ciferník: napětí solární baterie (krátký text, ukazatel 11,6–13,0 V, dlouhý text). */
public class VoltComplication extends ComplicationDataSourceService {

    @Override
    public void onComplicationRequest(@NonNull ComplicationRequest request, @NonNull ComplicationRequestListener listener) {
        new Thread(() -> {
            ComplicationData out = build(request.getComplicationType(), Data.fresh(this));
            try {
                listener.onComplicationData(out);
            } catch (RemoteException ignored) { }
        }).start();
    }

    @Nullable
    @Override
    public ComplicationData getPreviewData(@NonNull ComplicationType type) {
        try {
            JSONObject d = new JSONObject("{\"v\":12.64,\"soc\":72,\"pv\":180,\"lvl\":0,\"t\":" + System.currentTimeMillis() / 1000 + "}");
            return build(type, d);
        } catch (Exception e) {
            return null;
        }
    }

    private ComplicationData build(ComplicationType type, JSONObject d) {
        if (d == null || !d.has("v")) return new NoDataComplicationData();
        double v = d.optDouble("v");
        boolean old = Data.ageMin(d) > 60;
        String vs = Data.volt(v);
        ComplicationText desc = txt("Baterie chaty " + vs + " V" + (old ? ", " + Data.ageText(d) : ""));
        PendingIntent tap = PendingIntent.getActivity(this, 0, new Intent(this, MainActivity.class),
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        String title = old ? "V?" : (d.optInt("lvl", 0) >= 2 ? "V!" : "V");
        switch (type) {
            case SHORT_TEXT:
                return new ShortTextComplicationData.Builder(txt(vs), desc)
                        .setTitle(txt(title)).setTapAction(tap).build();
            case RANGED_VALUE: {
                float min = (float) d.optDouble("vmin", 11.6), max = 13.0f;
                float val = (float) Math.max(min, Math.min(max, v));
                return new RangedValueComplicationData.Builder(val, min, max, desc)
                        .setText(txt(String.format(Data.CS, "%.1f", v)))   // na ciferníku stačí 1 desetinné místo
                        .setTitle(txt(title)).setTapAction(tap).build();
            }
            case LONG_TEXT: {
                StringBuilder s = new StringBuilder(vs).append(" V");
                if (!d.isNull("soc")) s.append(" · ").append(d.optInt("soc")).append(" %");
                if (!d.isNull("pv")) s.append(" · ☀ ").append(d.optInt("pv")).append(" W");
                return new LongTextComplicationData.Builder(txt(s.toString()), desc)
                        .setTitle(txt("Chata" + (old ? " (" + Data.ageText(d) + ")" : ""))).setTapAction(tap).build();
            }
            default:
                return null;
        }
    }

    private static ComplicationText txt(String s) {
        return new PlainComplicationText.Builder(s).build();
    }
}
