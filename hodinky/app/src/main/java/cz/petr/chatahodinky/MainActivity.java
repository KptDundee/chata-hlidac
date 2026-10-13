package cz.petr.chatahodinky;

import android.app.Activity;
import android.graphics.Typeface;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONObject;

/** Nastavení (téma ntfy) a rychlý přehled. Na kulatém displeji vše na střed. */
public class MainActivity extends Activity {
    private TextView info;
    private EditText topic;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        int pad = dp(22);
        ScrollView sv = new ScrollView(this);
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        l.setGravity(Gravity.CENTER_HORIZONTAL);
        l.setPadding(pad, dp(28), pad, dp(40));
        sv.addView(l);

        TextView t = new TextView(this);
        t.setText("⚡ Chata");
        t.setTextSize(18);
        t.setTypeface(Typeface.DEFAULT_BOLD);
        t.setGravity(Gravity.CENTER);
        l.addView(t);

        info = new TextView(this);
        info.setGravity(Gravity.CENTER);
        info.setTextSize(14);
        info.setPadding(0, dp(6), 0, dp(10));
        l.addView(info);

        TextView h = new TextView(this);
        h.setText("Téma ntfy (stejné jako v aplikaci ntfy, bez -hodinky):");
        h.setTextSize(11);
        h.setGravity(Gravity.CENTER);
        l.addView(h);

        topic = new EditText(this);
        topic.setSingleLine(true);
        topic.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        topic.setTextSize(13);
        topic.setText(Data.topic(this));
        l.addView(topic);

        Button save = new Button(this);
        save.setText("Uložit a načíst");
        save.setOnClickListener(v -> {
            Data.setTopic(this, topic.getText().toString());
            load();
        });
        l.addView(save);

        setContentView(sv);
        show(Data.cached(this));
        load();
    }

    private void load() {
        info.setText(info.getText() + "\nnačítám…");
        new Thread(() -> {
            JSONObject d = Data.fetch(this);
            runOnUiThread(() -> {
                if (d != null) {
                    show(d);
                    Data.requestUpdates(this);
                } else {
                    show(Data.cached(this));
                    info.append(Data.topic(this).isEmpty() ? "" : "\n(nepodařilo se načíst)");
                }
            });
        }).start();
    }

    private void show(JSONObject d) {
        if (Data.topic(this).isEmpty()) {
            info.setText("Zadej téma ntfy a ulož.");
            return;
        }
        if (d == null) {
            info.setText("Zatím žádná data.");
            return;
        }
        StringBuilder s = new StringBuilder();
        s.append(Data.volt(d.optDouble("v"))).append(" V");
        if (!d.isNull("soc")) s.append(" · ").append(d.optInt("soc")).append(" %");
        if (!d.optString("st").isEmpty()) s.append("\n").append(d.optString("st"));
        if (!d.isNull("pv")) s.append("\n☀ panely ").append(d.optInt("pv")).append(" W");
        if (!d.isNull("w")) s.append("\n🏠 odběr ").append(d.optInt("w")).append(" W");
        if (!d.isNull("day")) s.append(String.format(Data.CS, "\nvyrobeno dnes %.2f kWh", d.optDouble("day")));
        if (d.optBoolean("ra")) s.append("\n🔌 nabíjí River");
        if (!d.optString("fc").isEmpty()) s.append("\n").append(d.optString("fc"));
        s.append("\n").append(Data.ageText(d));
        info.setText(s.toString());
        info.setTextColor(d.optInt("lvl", 0) >= 1 ? Data.color(d.optInt("lvl")) : 0xFFFFFFFF);
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }
}
