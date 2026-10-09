using System;
using System.Collections.Generic;
using UnityEngine;

namespace DeadCells.Meta
{
    public enum Language
    {
        English,
        Chinese,
    }

    /// <summary>
    /// String tables loaded from Resources/Localization/{en,zh}.txt.
    /// Format: one `key = value` per line, `#` comments, `\n` for line breaks.
    /// Missing keys fall back to English, then to the key itself.
    /// </summary>
    public static class Loc
    {
        static readonly Dictionary<Language, Dictionary<string, string>> Tables = new Dictionary<Language, Dictionary<string, string>>();
        static Language current = Language.Chinese;

        public static event Action Changed;

        public static Language Current
        {
            get => current;
            set
            {
                if (current == value)
                    return;
                current = value;
                Changed?.Invoke();
            }
        }

        public static bool IsChinese => current == Language.Chinese;

        static Dictionary<string, string> Table(Language lang)
        {
            if (Tables.TryGetValue(lang, out var t))
                return t;
            t = new Dictionary<string, string>();
            var asset = Resources.Load<TextAsset>(lang == Language.Chinese ? "Localization/zh" : "Localization/en");
            if (asset != null)
            {
                foreach (var raw in asset.text.Split('\n'))
                {
                    string line = raw.TrimEnd('\r');
                    if (line.Length == 0 || line.StartsWith("#"))
                        continue;
                    int eq = line.IndexOf(" = ", StringComparison.Ordinal);
                    if (eq <= 0)
                        continue;
                    t[line.Substring(0, eq).Trim()] = line.Substring(eq + 3).Replace("\\n", "\n");
                }
            }
            Tables[lang] = t;
            return t;
        }

        public static bool Has(string key) => Table(current).ContainsKey(key) || Table(Language.English).ContainsKey(key);

        public static string Get(string key)
        {
            if (string.IsNullOrEmpty(key))
                return "";
            if (Table(current).TryGetValue(key, out var v))
                return v;
            if (Table(Language.English).TryGetValue(key, out v))
                return v;
            return key;
        }

        public static string Get(string key, params object[] args)
        {
            string format = Get(key);
            try
            {
                return string.Format(format, args);
            }
            catch (FormatException)
            {
                return format;
            }
        }
    }
}
