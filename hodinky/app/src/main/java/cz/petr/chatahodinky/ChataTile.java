package cz.petr.chatahodinky;

import androidx.annotation.NonNull;
import androidx.concurrent.futures.CallbackToFutureAdapter;
import androidx.wear.protolayout.ActionBuilders;
import androidx.wear.protolayout.ColorBuilders;
import androidx.wear.protolayout.DimensionBuilders;
import androidx.wear.protolayout.LayoutElementBuilders;
import androidx.wear.protolayout.ModifiersBuilders;
import androidx.wear.protolayout.ResourceBuilders;
import androidx.wear.protolayout.TimelineBuilders;
import androidx.wear.tiles.RequestBuilders;
import androidx.wear.tiles.TileBuilders;
import androidx.wear.tiles.TileService;

import com.google.common.util.concurrent.Futures;
import com.google.common.util.concurrent.ListenableFuture;

import org.json.JSONObject;

/** Dlaždice: napětí, nabití #, panely, odběr chaty, předpověď. Ťuknutím se změří hned (přes Flip) a obnoví. */
public class ChataTile extends TileService {
    private static final String RES_VER = "1";
    private static final int GREY = 0xFFAAAAAA, WHITE = 0xFFFFFFFF;

    @NonNull
    @Override
    protected ListenableFuture<TileBuilders.Tile> onTileRequest(@NonNull RequestBuilders.TileRequest req) {
        return CallbackToFutureAdapter.getFuture(completer -> {
            new Thread(() -> {
                try {
                    // ťuknutí na dlaždici = změřit hned (Flip změří a spustí hlídače), dlaždice se pak obnovuje po minutě
                    if ("refresh".equals(req.getCurrentState().getLastClickableId())) Data.wake(this);
                    completer.set(tile(Data.fresh(this)));
                } catch (Exception e) {
                    completer.setException(e);
                }
            }).start();
            return "chata-tile";
        });
    }

    @NonNull
    @Override
    protected ListenableFuture<ResourceBuilders.Resources> onTileResourcesRequest(@NonNull RequestBuilders.ResourcesRequest req) {
        return Futures.immediateFuture(new ResourceBuilders.Resources.Builder().setVersion(RES_VER).build());
    }

    private TileBuilders.Tile tile(JSONObject d) {
        LayoutElementBuilders.Column.Builder col = new LayoutElementBuilders.Column.Builder()
                .setHorizontalAlignment(LayoutElementBuilders.HORIZONTAL_ALIGN_CENTER);
        col.addContent(text("⚡ CHATA", 12, GREY, false, 1));
        if (Data.topic(this).isEmpty()) {
            col.addContent(space(6));
            col.addContent(text("Otevři aplikaci Chata\na zadej téma ntfy", 14, WHITE, false, 3));
        } else if (d == null) {
            col.addContent(space(6));
            col.addContent(text("Zatím žádná data", 15, WHITE, false, 2));
            col.addContent(text("ťukni pro načtení", 12, GREY, false, 1));
        } else if (!d.isNull("rv") && d.optJSONObject("rv") != null) {
            // chata jede z River: jde o chatu – River (nabití, výdrž, odběr), solár jen malým řádkem
            JSONObject r = d.optJSONObject("rv");
            boolean old = Data.ageMin(d) > 60;
            boolean hasS = !r.isNull("s");
            int rc = !hasS ? WHITE : r.optInt("s") <= 15 ? Data.color(2) : r.has("ok") && !r.isNull("ok") && !r.optBoolean("ok") ? Data.color(1) : Data.color(0);
            col.addContent(text("🔋 " + r.optString("n", "River"), 13, WHITE, false, 1));
            int nowW = r.isNull("now") ? r.optInt("w") : r.optInt("now");
            col.addContent(text(hasS ? r.optInt("s") + " %" : nowW + " W", 34, old ? GREY : rc, true, 1));
            if (hasS && !r.isNull("u")) {
                String until = new java.text.SimpleDateFormat("HH:mm", Data.CS).format(new java.util.Date(r.optLong("u") * 1000));
                col.addContent(text("vydrží do ~" + until + (r.has("ok") && !r.isNull("ok") ? (r.optBoolean("ok") ? " ✓" : " ✗") : ""), 15, rc, false, 1));
            } else {
                col.addContent(text("% až z EcoFlow", 12, GREY, false, 1));
            }
            StringBuilder l3 = new StringBuilder("🏠 ").append(nowW).append(" W");
            if (!r.isNull("t0")) l3.append(" · od ").append(new java.text.SimpleDateFormat("HH:mm", Data.CS).format(new java.util.Date(r.optLong("t0") * 1000)));
            if (!r.isNull("wh")) l3.append(String.format(Data.CS, " · %.2f kWh", r.optDouble("wh") / 1000));
            col.addContent(text(l3.toString(), 13, WHITE, false, 1));
            col.addContent(space(4));
            col.addContent(text("☀ solár " + Data.volt(d.optDouble("v")) + " V" + (d.isNull("hq") ? "" : " · " + d.optInt("hq") + " #"), 12, GREY, false, 1));
            col.addContent(space(4));
            col.addContent(text(Data.waiting(this, d) ? "⏳ měří se…" : Data.ageText(d), 11, GREY, false, 1));
        } else {
            int lvl = d.optInt("lvl", 0);
            boolean old = Data.ageMin(d) > 60;
            col.addContent(text(Data.volt(d.optDouble("v")) + " V", 34, old ? GREY : Data.color(lvl), true, 1));
            if (!d.isNull("hq")) {                 // nabití # (z ampérhodin): výrazněji než ostatní, menší než napětí
                int hq = d.optInt("hq");
                col.addContent(text(hq + " #", 24, old ? GREY : hq < 30 ? Data.color(2) : hq < 50 ? Data.color(1) : WHITE, true, 1));
            }
            String l2 = (d.isNull("soc") ? "" : d.optInt("soc") + " %") + (d.optString("st").isEmpty() ? "" : (d.isNull("soc") ? "" : " · ") + d.optString("st"));
            if (!l2.isEmpty()) col.addContent(text(l2, 15, WHITE, false, 1));
            StringBuilder l3 = new StringBuilder();
            if (!d.isNull("pv")) l3.append("☀ ").append(d.optInt("pv")).append(" W");
            if (!d.isNull("w")) l3.append(l3.length() > 0 ? "  " : "").append("🏠 ").append(d.optInt("w")).append(" W");
            if (l3.length() > 0) col.addContent(text(l3.toString(), 15, WHITE, false, 1));
            if (d.optBoolean("ra")) col.addContent(text("🔌 nabíjí River", 12, 0xFF6EA8FF, false, 1));
            String fc = d.optString("fc");
            if (!fc.isEmpty()) {
                col.addContent(space(4));
                col.addContent(text(fc, 13, lvl >= 1 ? Data.color(lvl) : WHITE, false, 2));
            }
            col.addContent(space(4));
            col.addContent(text(Data.waiting(this, d) ? "⏳ měří se…" : Data.ageText(d), 11, GREY, false, 1));
        }
        LayoutElementBuilders.Box root = new LayoutElementBuilders.Box.Builder()
                .setWidth(DimensionBuilders.expand())
                .setHeight(DimensionBuilders.expand())
                .setHorizontalAlignment(LayoutElementBuilders.HORIZONTAL_ALIGN_CENTER)
                .setVerticalAlignment(LayoutElementBuilders.VERTICAL_ALIGN_CENTER)
                .setModifiers(new ModifiersBuilders.Modifiers.Builder()
                        .setClickable(new ModifiersBuilders.Clickable.Builder()
                                .setId("refresh")
                                .setOnClick(new ActionBuilders.LoadAction.Builder().build())
                                .build())
                        .build())
                .addContent(col.build())
                .build();
        return new TileBuilders.Tile.Builder()
                .setResourcesVersion(RES_VER)
                .setFreshnessIntervalMillis(Data.waiting(this, d) ? 60 * 1000L : 10 * 60 * 1000L)
                .setTileTimeline(TimelineBuilders.Timeline.fromLayoutElement(root))
                .build();
    }

    private static LayoutElementBuilders.LayoutElement text(String s, float sp, int color, boolean bold, int lines) {
        LayoutElementBuilders.FontStyle.Builder fs = new LayoutElementBuilders.FontStyle.Builder()
                .setSize(DimensionBuilders.sp(sp))
                .setColor(ColorBuilders.argb(color));
        if (bold) fs.setWeight(LayoutElementBuilders.FONT_WEIGHT_BOLD);
        return new LayoutElementBuilders.Text.Builder()
                .setText(s)
                .setFontStyle(fs.build())
                .setMaxLines(lines)
                .setMultilineAlignment(LayoutElementBuilders.TEXT_ALIGN_CENTER)
                .build();
    }

    private static LayoutElementBuilders.LayoutElement space(float dp) {
        return new LayoutElementBuilders.Spacer.Builder().setHeight(DimensionBuilders.dp(dp)).build();
    }
}
