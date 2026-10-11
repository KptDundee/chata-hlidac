package cz.petr.chatabrana;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

/**
 * Místní komunikace se zásuvkou Tapo (protokol KLAP, jako python-kasa KlapTransportV2).
 * Žádný cloud – jen HTTP na IP adresu zásuvky v místní Wi-Fi.
 */
public final class TapoKlap {
    private final String host;
    private final byte[][] authHashes;   // zkouší se: tvoje údaje, prázdné, výchozí Tapo/Kasa
    private String cookie;
    private Session session;

    public TapoKlap(String host, String email, String password) {
        this.host = host;
        this.authHashes = new byte[][]{
                authHash(email, password),
                authHash("", ""),
                authHash("test@tp-link.net", "test"),
                authHash("kasa@tp-link.net", "kasaSetup"),
        };
    }

    static byte[] authHash(String user, String pass) {
        return sha256(concat(sha1(user.getBytes(StandardCharsets.UTF_8)), sha1(pass.getBytes(StandardCharsets.UTF_8))));
    }

    /** Zavolá metodu (např. get_device_info, get_energy_usage) a vrátí JSON odpovědi jako text. */
    public String call(String method) throws Exception {
        if (session == null) handshake();
        String req = "{\"method\":\"" + method + "\",\"request_time_milis\":" + System.currentTimeMillis() + "}";
        Session.Enc e = session.encrypt(req.getBytes(StandardCharsets.UTF_8));
        Resp r = post("/app/request?seq=" + e.seq, e.payload, cookie);
        if (r.code != 200) { session = null; throw new Exception("Tapo " + host + ": HTTP " + r.code); }
        return new String(session.decrypt(r.body, e.seq), StandardCharsets.UTF_8);
    }

    private void handshake() throws Exception {
        byte[] local = new byte[16];
        new SecureRandom().nextBytes(local);
        Resp r1 = post("/app/handshake1", local, null);
        if (r1.code != 200 || r1.body.length < 48) throw new Exception("Tapo " + host + ": handshake1 HTTP " + r1.code);
        cookie = r1.cookie;
        byte[] remote = Arrays.copyOfRange(r1.body, 0, 16);
        byte[] serverHash = Arrays.copyOfRange(r1.body, 16, 48);
        byte[] auth = null;
        for (byte[] a : authHashes) {
            if (Arrays.equals(sha256(concat(local, remote, a)), serverHash)) { auth = a; break; }
        }
        if (auth == null) throw new Exception("Tapo " + host + ": špatný e-mail nebo heslo k účtu Tapo");
        Resp r2 = post("/app/handshake2", sha256(concat(remote, local, auth)), cookie);
        if (r2.code != 200) throw new Exception("Tapo " + host + ": handshake2 HTTP " + r2.code);
        session = new Session(local, remote, auth);
    }

    static final class Session {
        final byte[] key, iv, sig;
        int seq;

        Session(byte[] local, byte[] remote, byte[] auth) {
            key = Arrays.copyOf(sha256(concat("lsk".getBytes(), local, remote, auth)), 16);
            byte[] full = sha256(concat("iv".getBytes(), local, remote, auth));
            iv = Arrays.copyOf(full, 12);
            seq = ByteBuffer.wrap(full, 28, 4).getInt();
            sig = Arrays.copyOf(sha256(concat("ldk".getBytes(), local, remote, auth)), 28);
        }

        static final class Enc { byte[] payload; int seq; }

        private byte[] ivSeq(int s) { return concat(iv, ByteBuffer.allocate(4).putInt(s).array()); }

        Enc encrypt(byte[] msg) throws Exception {
            seq++;
            Cipher c = Cipher.getInstance("AES/CBC/PKCS5Padding");
            c.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"), new IvParameterSpec(ivSeq(seq)));
            byte[] ct = c.doFinal(msg);
            byte[] signature = sha256(concat(sig, ByteBuffer.allocate(4).putInt(seq).array(), ct));
            Enc e = new Enc();
            e.payload = concat(signature, ct);
            e.seq = seq;
            return e;
        }

        byte[] decrypt(byte[] msg, int s) throws Exception {
            Cipher c = Cipher.getInstance("AES/CBC/PKCS5Padding");
            c.init(Cipher.DECRYPT_MODE, new SecretKeySpec(key, "AES"), new IvParameterSpec(ivSeq(s)));
            return c.doFinal(Arrays.copyOfRange(msg, 32, msg.length));
        }
    }

    static final class Resp { int code; byte[] body = new byte[0]; String cookie; }

    private Resp post(String path, byte[] body, String cookie) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL("http://" + host + path).openConnection();
        c.setConnectTimeout(5000);
        c.setReadTimeout(8000);
        c.setRequestMethod("POST");
        c.setDoOutput(true);
        c.setRequestProperty("Content-Type", "application/octet-stream");
        if (cookie != null) c.setRequestProperty("Cookie", cookie);
        try (OutputStream o = c.getOutputStream()) { o.write(body); }
        Resp r = new Resp();
        r.code = c.getResponseCode();
        Map<String, List<String>> h = c.getHeaderFields();
        for (Map.Entry<String, List<String>> en : h.entrySet()) {
            if (en.getKey() != null && en.getKey().equalsIgnoreCase("Set-Cookie")) {
                for (String v : en.getValue()) if (v.contains("TP_SESSIONID")) r.cookie = v.split(";", 2)[0];
            }
        }
        if (r.cookie == null) r.cookie = cookie;
        try (InputStream in = r.code < 400 ? c.getInputStream() : c.getErrorStream()) {
            if (in != null) {
                ByteArrayOutputStream bo = new ByteArrayOutputStream();
                byte[] buf = new byte[4096];
                int n;
                while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
                r.body = bo.toByteArray();
            }
        } finally {
            c.disconnect();
        }
        return r;
    }

    static byte[] sha256(byte[] b) { return digest("SHA-256", b); }
    static byte[] sha1(byte[] b) { return digest("SHA-1", b); }

    private static byte[] digest(String alg, byte[] b) {
        try { return MessageDigest.getInstance(alg).digest(b); } catch (Exception e) { throw new RuntimeException(e); }
    }

    static byte[] concat(byte[]... parts) {
        int n = 0;
        for (byte[] p : parts) n += p.length;
        byte[] out = new byte[n];
        int o = 0;
        for (byte[] p : parts) { System.arraycopy(p, 0, out, o, p.length); o += p.length; }
        return out;
    }
}
