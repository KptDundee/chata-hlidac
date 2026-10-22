package cz.petr.chatabrana;

import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;

/**
 * Teploměr Xiaomi (Mi Temperature and Humidity Monitor 2 / LYWSD03MMC) s originálním firmwarem:
 * vysílá „MiBeacon“ v service data 0xFE95, hodnoty šifrované AES-CCM klíčem „BLE KEY“ (bindkey z účtu Xiaomi).
 * Bez Androidu (jen javax.crypto), aby šel otestovat i mimo telefon.
 */
public final class XiaomiParser {
    private XiaomiParser() {}

    /** Výsledek jedné zprávy – teploměr posílá střídavě teplotu, vlhkost, baterii (co chybí, je null). */
    public static final class Reading {
        public Double temp, hum;
        public Integer batt;
    }

    /**
     * @param sd    service data 0xFE95
     * @param mac   MAC adresa zařízení „AA:BB:CC:DD:EE:FF“ (kdyby ji zpráva neobsahovala)
     * @param key   16 bajtů BLE KEY
     * @return hodnoty, nebo null (nešifrovaná / jiná zpráva, špatný klíč)
     */
    public static Reading parse(byte[] sd, String mac, byte[] key) throws Exception {
        if (sd == null || sd.length < 5 || key == null || key.length != 16) return null;
        int fc = (sd[0] & 0xFF) | (sd[1] & 0xFF) << 8;
        boolean enc = (fc & 0x0008) != 0, hasMac = (fc & 0x0010) != 0, hasCap = (fc & 0x0020) != 0, hasObj = (fc & 0x0040) != 0;
        int ver = (fc >> 12) & 0x0F;
        if (!hasObj) return null;
        int i = 5;
        byte[] macRev = new byte[6];
        if (hasMac) {
            if (sd.length < i + 6) return null;
            System.arraycopy(sd, i, macRev, 0, 6);
            i += 6;
        } else {
            String h = mac.replaceAll("[^0-9a-fA-F]", "");
            if (h.length() != 12) return null;
            for (int k = 0; k < 6; k++) macRev[5 - k] = (byte) Integer.parseInt(h.substring(k * 2, k * 2 + 2), 16);
        }
        if (hasCap) {
            int cap = sd[i] & 0xFF;
            i += 1;
            if (ver >= 5 && (cap & 0x20) != 0) i += 2;          // IO capability
        }
        byte[] obj;
        if (enc) {
            if (ver < 4 || sd.length < i + 7 + 3) return null;   // ext. čítač 3 B + MIC 4 B
            int clen = sd.length - i - 7;
            byte[] ct = new byte[clen];
            System.arraycopy(sd, i, ct, 0, clen);
            byte[] ext = {sd[sd.length - 7], sd[sd.length - 6], sd[sd.length - 5]};
            byte[] mic = {sd[sd.length - 4], sd[sd.length - 3], sd[sd.length - 2], sd[sd.length - 1]};
            byte[] nonce = new byte[12];
            System.arraycopy(macRev, 0, nonce, 0, 6);
            nonce[6] = sd[2]; nonce[7] = sd[3]; nonce[8] = sd[4];
            System.arraycopy(ext, 0, nonce, 9, 3);
            obj = ccmDecrypt(key, nonce, ct, mic, new byte[]{0x11});
            if (obj == null) return null;                          // špatný klíč
        } else {
            obj = new byte[sd.length - i];
            System.arraycopy(sd, i, obj, 0, obj.length);
        }
        Reading r = new Reading();
        int p = 0;
        while (p + 3 <= obj.length) {
            int type = (obj[p] & 0xFF) | (obj[p + 1] & 0xFF) << 8, len = obj[p + 2] & 0xFF;
            p += 3;
            if (p + len > obj.length) break;
            if (type == 0x1004 && len >= 2) r.temp = s16(obj, p) / 10.0;
            else if (type == 0x1006 && len >= 2) r.hum = u16(obj, p) / 10.0;
            else if (type == 0x100A && len >= 1) r.batt = obj[p] & 0xFF;
            else if (type == 0x100D && len >= 4) { r.temp = s16(obj, p) / 10.0; r.hum = u16(obj, p + 2) / 10.0; }
            p += len;
        }
        return r.temp == null && r.hum == null && r.batt == null ? null : r;
    }

    private static int s16(byte[] b, int p) { return (short) ((b[p] & 0xFF) | (b[p + 1] & 0xFF) << 8); }
    private static int u16(byte[] b, int p) { return (b[p] & 0xFF) | (b[p + 1] & 0xFF) << 8; }

    /** AES-CCM (nonce 12 B → L = 3, tag 4 B) – Android nemá CCM ve standardních knihovnách, proto ručně přes AES/ECB. */
    static byte[] ccmDecrypt(byte[] key, byte[] nonce, byte[] ct, byte[] tag, byte[] aad) throws Exception {
        Cipher aes = Cipher.getInstance("AES/ECB/NoPadding");
        aes.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"));
        int L = 15 - nonce.length, M = tag.length;
        byte[] a = new byte[16];
        a[0] = (byte) (L - 1);
        System.arraycopy(nonce, 0, a, 1, nonce.length);
        // dešifrování (CTR od čítače 1)
        byte[] pt = new byte[ct.length];
        for (int blk = 0; blk * 16 < ct.length; blk++) {
            setCtr(a, blk + 1, L);
            byte[] s = aes.doFinal(a);
            for (int j = 0; j < 16 && blk * 16 + j < ct.length; j++) pt[blk * 16 + j] = (byte) (ct[blk * 16 + j] ^ s[j]);
        }
        // kontrola MIC (CBC-MAC)
        byte[] b0 = new byte[16];
        b0[0] = (byte) ((aad.length > 0 ? 0x40 : 0) | (((M - 2) / 2) << 3) | (L - 1));
        System.arraycopy(nonce, 0, b0, 1, nonce.length);
        for (int j = 0; j < L; j++) b0[15 - j] = (byte) (pt.length >> (8 * j));
        byte[] x = aes.doFinal(b0);
        if (aad.length > 0) {
            byte[] ab = new byte[((2 + aad.length + 15) / 16) * 16];
            ab[0] = (byte) (aad.length >> 8); ab[1] = (byte) aad.length;
            System.arraycopy(aad, 0, ab, 2, aad.length);
            x = cbc(aes, x, ab);
        }
        byte[] pb = new byte[((pt.length + 15) / 16) * 16];
        System.arraycopy(pt, 0, pb, 0, pt.length);
        x = cbc(aes, x, pb);
        setCtr(a, 0, L);
        byte[] s0 = aes.doFinal(a);
        for (int j = 0; j < M; j++) if ((byte) (x[j] ^ s0[j]) != tag[j]) return null;
        return pt;
    }

    private static byte[] cbc(Cipher aes, byte[] x, byte[] data) throws Exception {
        for (int o = 0; o < data.length; o += 16) {
            byte[] t = new byte[16];
            for (int j = 0; j < 16; j++) t[j] = (byte) (x[j] ^ data[o + j]);
            x = aes.doFinal(t);
        }
        return x;
    }

    private static void setCtr(byte[] a, int ctr, int L) {
        for (int j = 0; j < L; j++) a[15 - j] = (byte) (ctr >> (8 * j));
    }

    public static byte[] hex(String s) {
        String h = s.replaceAll("[^0-9a-fA-F]", "");
        byte[] b = new byte[h.length() / 2];
        for (int i = 0; i < b.length; i++) b[i] = (byte) Integer.parseInt(h.substring(i * 2, i * 2 + 2), 16);
        return b;
    }
}
