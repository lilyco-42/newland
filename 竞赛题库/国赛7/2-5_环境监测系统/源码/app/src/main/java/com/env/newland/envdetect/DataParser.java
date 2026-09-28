package com.env.newland.envdetect;

import java.util.HashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class DataParser {

    public static Map<String, Double> parse(String line) {
        if (line == null || line.trim().isEmpty()) {
            return null;
        }
        Map<String, Double> result = new HashMap<>();
        String s = line.trim();

        if (parseTemper(s, result) && parseHumidity(s, result) && parseCo2(s, result) && parseLight(s, result)) {
            return result;
        }

        return result.isEmpty() ? null : result;
    }

    private static boolean parseTemper(String s, Map<String, Double> result) {
        String[] keys = {"温度", "temper", "temp", "temperature", "t"};
        for (String key : keys) {
            Double val = extractValue(s, key);
            if (val != null) {
                result.put("temper", val);
                return true;
            }
        }
        return false;
    }

    private static boolean parseHumidity(String s, Map<String, Double> result) {
        String[] keys = {"湿度", "humidity", "humi", "h"};
        for (String key : keys) {
            Double val = extractValue(s, key);
            if (val != null) {
                result.put("humidity", val);
                return true;
            }
        }
        return false;
    }

    private static boolean parseCo2(String s, Map<String, Double> result) {
        String[] keys = {"二氧化碳", "co2", "c"};
        for (String key : keys) {
            Double val = extractValue(s, key);
            if (val != null) {
                result.put("co2", val);
                return true;
            }
        }
        return false;
    }

    private static boolean parseLight(String s, Map<String, Double> result) {
        String[] keys = {"光照", "light", "lux", "l"};
        for (String key : keys) {
            Double val = extractValue(s, key);
            if (val != null) {
                result.put("light", val);
                return true;
            }
        }
        return false;
    }

    private static Double extractValue(String line, String key) {
        String pat = Pattern.quote(key) + "\\s*[:=]\\s*(-?\\d+\\.?\\d*)";
        Pattern p = Pattern.compile(pat, Pattern.CASE_INSENSITIVE);
        Matcher m = p.matcher(line);
        if (m.find()) {
            try {
                return Double.parseDouble(m.group(1));
            } catch (NumberFormatException e) {
                // skip
            }
        }
        return null;
    }
}
