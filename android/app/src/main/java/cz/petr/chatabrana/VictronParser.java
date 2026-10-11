package cz.petr.chatabrana;

import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

/**
 * Dekódování Victron „Instant readout“ (Bluetooth advertisement, výrobce 0x02E1).
 * Formát podle knihovny victron-ble: [prefix 2B][model 2B LE][typ 1B][iv 2B LE][kontrolní bajt klíče][šifrovaná data]
 * AES-128-CTR, počítadlo = iv jako little-endian 128bit číslo.
 */
public final class VictronParser {
    public static final int MANUFACTURER_ID = 0x02E1;
    public static final int TYPE_INVERTER = 0x03;

    public static final class Inverter {
        public int state = -1;          // 9 = INVERTING, 0 = OFF, 1 = LOW_POWER, 2 = FAULT
        public int alarm;               // bitová maska AlarmReason
        public Double batteryV;         // V
        public Integer acVa;            // VA
        public Double acV;              // V
        public Double acA;              // A

        public String stateName() { return VictronParser.stateName(state); }
        public String alarmName() { return VictronParser.alarmName(alarm); }
    }

    private VictronParser() {}

    public static byte[] hex(String s) {
        s = s.replaceAll("[^0-9a-fA-F]", "");
        byte[] b = new byte[s.length() / 2];
        for (int i = 0; i < b.length; i++) b[i] = (byte) Integer.parseInt(s.substring(2 * i, 2 * i + 2), 16);
        return b;
    }

    /** @param data manufacturer data BEZ id výrobce (tak je vrací Android ScanRecord.getManufacturerSpecificData). */
    public static Inverter parse(byte[] data, byte[] key) throws Exception {
        if (data == null || data.length < 9 || (data[0] & 0xFF) != 0x10) throw new IllegalArgumentException("Není Victron readout");
        int type = data[4] & 0xFF;
        if (type != TYPE_INVERTER) throw new IllegalArgumentException("Typ záznamu " + type + " není měnič");
        if (data[7] != key[0]) throw new IllegalArgumentException("Špatný klíč (kontrolní bajt nesedí)");
        byte[] iv = new byte[16];
        iv[0] = data[5];
        iv[1] = data[6];
        int n = data.length - 8;
        byte[] enc = new byte[16];                      // stačí jeden blok, záznam má < 16 B
        System.arraycopy(data, 8, enc, 0, Math.min(n, 16));
        Cipher c = Cipher.getInstance("AES/CTR/NoPadding");
        c.init(Cipher.DECRYPT_MODE, new SecretKeySpec(key, "AES"), new IvParameterSpec(iv));
        byte[] d = c.doFinal(enc);

        Bits r = new Bits(d);
        Inverter inv = new Inverter();
        int st = r.u(8);
        inv.state = st == 0xFF ? -1 : st;
        inv.alarm = r.u(16);
        int bv = r.s(16);
        inv.batteryV = bv == 0x7FFF ? null : bv / 100.0;
        int va = r.u(16);
        inv.acVa = va == 0xFFFF ? null : va;
        int av = r.u(15);
        inv.acV = av == 0x7FFF ? null : av / 100.0;
        int aa = r.u(11);
        inv.acA = aa == 0x7FF ? null : aa / 10.0;
        return inv;
    }

    /** Čte bitová pole od nejnižšího bitu (LSB first), stejně jako victron-ble BitReader. */
    static final class Bits {
        private final byte[] d;
        private int i;
        Bits(byte[] d) { this.d = d; }
        int u(int n) {
            int v = 0;
            for (int p = 0; p < n; p++, i++) v |= ((d[i >> 3] >> (i & 7)) & 1) << p;
            return v;
        }
        int s(int n) {
            int v = u(n);
            return (v & (1 << (n - 1))) != 0 ? v - (1 << n) : v;
        }
    }

    public static String stateName(int s) {
        switch (s) {
            case 0: return "OFF";
            case 1: return "LOW_POWER";
            case 2: return "FAULT";
            case 9: return "INVERTING";
            case 11: return "POWER_SUPPLY";
            case 248: return "BATTERY_SAFE";
            case -1: return "";
            default: return "STATE_" + s;
        }
    }

    public static String alarmName(int a) {
        if (a == 0) return "";
        String[] names = {"LOW_VOLTAGE", "HIGH_VOLTAGE", "LOW_SOC", "LOW_STARTER_VOLTAGE", "HIGH_STARTER_VOLTAGE",
                "LOW_TEMPERATURE", "HIGH_TEMPERATURE", "MID_VOLTAGE", "OVERLOAD", "DC_RIPPLE", "LOW_V_AC_OUT",
                "HIGH_V_AC_OUT", "SHORT_CIRCUIT", "BMS_LOCKOUT"};
        StringBuilder sb = new StringBuilder();
        for (int b = 0; b < names.length; b++) if ((a & (1 << b)) != 0) sb.append(sb.length() > 0 ? "," : "").append(names[b]);
        return sb.length() > 0 ? sb.toString() : "ALARM_" + a;
    }
}
