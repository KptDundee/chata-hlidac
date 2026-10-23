package cz.petr.chatabrana;

import android.content.Context;
import android.util.Base64;

import org.json.JSONObject;

import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.NetworkInterface;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Najde zásuvky Tapo v místní síti bez ohledu na IP adresu (router je přiděluje, jak chce).
 * Zásuvka se pozná podle čísla v první závorce jejího jména v aplikaci Tapo: „(3) (R) River žlutý“ → 3.
 * Bez čísla v závorce se použije konec IP adresy (jako dřív).
 */
public final class TapoScan {
    private TapoScan() {}

    private static final Pattern ID = Pattern.compile("^\\s*\\((\\d{1,3})\\)");

    /** Číslo zásuvky z jména („(3) (R) …“ → "3"), jinak null. */
    public static String idFromName(String nick) {
        if (nick == null) return null;
        Matcher m = ID.matcher(nick);
        return m.find() ? String.valueOf(Integer.parseInt(m.group(1))) : null;
    }

    /** Prefixy podsítí k prohledání: vlastní Wi‑Fi telefonu + podsítě ručně zadaných adres. */
    public static List<String> subnets(Context c) {
        Set<String> out = new LinkedHashSet<>();
        try {
            for (NetworkInterface ni : Collections.list(NetworkInterface.getNetworkInterfaces())) {
                if (!ni.isUp() || ni.isLoopback()) continue;
                String n = ni.getName().toLowerCase();
                if (!(n.startsWith("wlan") || n.startsWith("eth") || n.startsWith("ap"))) continue;
                for (InetAddress a : Collections.list(ni.getInetAddresses())) {
                    if (a instanceof Inet4Address && a.isSiteLocalAddress()) {
                        String ip = a.getHostAddress();
                        out.add(ip.substring(0, ip.lastIndexOf('.') + 1));
                    }
                }
            }
        } catch (Exception ignored) { }
        for (String ip : Prefs.tapoIps(c)) out.add(ip.substring(0, ip.lastIndexOf('.') + 1));
        return new ArrayList<>(out);
    }

    /**
     * Prohledá podsítě: rychlý test portu 80, pak přihlášení KLAP a get_device_info.
     * @return mapa „číslo zásuvky“ → {ip, nick, model}
     */
    public static Map<String, JSONObject> scan(Context c, String email, String pass) { return scan(c, email, pass, false); }

    public static Map<String, JSONObject> scan(Context c, String email, String pass, boolean quiet) { return scan(c, email, pass, quiet, null); }

    /** Zásuvky, které odmítly přihlášení (401) – při rychlém hledání je hodinu nezkoušet znovu. */
    private static final Map<String, Long> refused = new java.util.concurrent.ConcurrentHashMap<>();

    /** @param skip adresy, na které se nepřihlašovat (fungující zásuvky z tohoto měření); null = plné hledání */
    public static Map<String, JSONObject> scan(Context c, String email, String pass, boolean quiet, java.util.Set<String> skip) {
        Map<String, JSONObject> found = Collections.synchronizedMap(new TreeMap<>());
        java.util.concurrent.atomic.AtomicInteger open = new java.util.concurrent.atomic.AtomicInteger();
        List<String> errs = Collections.synchronizedList(new ArrayList<>());
        List<String> nets = subnets(c);
        ExecutorService ex = Executors.newFixedThreadPool(32);
        for (String pre : nets) {
            for (int i = 2; i < 255; i++) {
                final String ip = pre + i;
                ex.submit(() -> {
                    try (Socket s = new Socket()) {
                        s.connect(new InetSocketAddress(ip, 80), 1200);
                    } catch (Exception e) {
                        return;
                    }
                    open.incrementAndGet();
                    if (skip != null && skip.contains(ip)) return;
                    Long rf = refused.get(ip);
                    if (skip != null && rf != null && System.currentTimeMillis() - rf < 3600_000L) return;
                    try {
                        TapoKlap t = new TapoKlap(ip, email, pass);
                        JSONObject info = new JSONObject(t.call("get_device_info")).optJSONObject("result");
                        if (info == null) return;
                        String nick = info.optString("nickname", "");
                        try { nick = new String(Base64.decode(nick, Base64.DEFAULT), StandardCharsets.UTF_8); } catch (Exception ignored) { }
                        String id = idFromName(nick);
                        boolean named = id != null;
                        if (id == null) id = ip.substring(ip.lastIndexOf('.') + 1);
                        JSONObject o = new JSONObject();
                        o.put("named", named);
                        o.put("ip", ip);
                        o.put("nick", nick);
                        o.put("model", info.optString("model", ""));
                        found.put(id, o);
                    } catch (Exception e) {
                        String m = String.valueOf(e.getMessage());
                        String oct = ip.substring(ip.lastIndexOf('.') + 1);
                        if (m.contains("401")) refused.put(ip, System.currentTimeMillis());
                        if (errs.size() < 3) errs.add(m.contains("401") ? "zásuvka na ." + oct + " odmítá přihlášení (401) – číslo nejde zjistit, v aplikaci Tapo zapni „Kompatibilita s třetími stranami“"
                                                                     : "." + oct + ": " + m);
                    }
                });
            }
        }
        ex.shutdown();
        try { ex.awaitTermination(90, TimeUnit.SECONDS); } catch (InterruptedException ignored) { }
        if (!quiet) Prefs.log(c, "Hledání zásuvek v " + nets + "*: odpovídá " + open.get() + " adres, zásuvek Tapo " + found.size()
                + (errs.isEmpty() ? "" : " · chyby: " + errs));
        return found;
    }
}
