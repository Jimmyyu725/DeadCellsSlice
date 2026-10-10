using System.Collections.Generic;
using System.Text;
using UnityEngine;

namespace DeadCells.Meta
{
    /// <summary>
    /// In-game update log, read from Resources/Changelog/{zh,en}.txt (newest
    /// first). Format per version:
    ///   # 0.4 | 2026-10-10 | Title
    ///   - change
    ///   - change
    /// </summary>
    public static class Changelog
    {
        public class Entry
        {
            public string version;
            public string date;
            public string title;
            public string notes;
        }

        public static List<Entry> Entries()
        {
            var list = new List<Entry>();
            var asset = Resources.Load<TextAsset>(Loc.Current == Language.Chinese ? "Changelog/zh" : "Changelog/en");
            if (asset == null)
                return list;
            Entry cur = null;
            var notes = new StringBuilder();
            foreach (var raw in asset.text.Split('\n'))
            {
                string line = raw.TrimEnd('\r');
                if (line.StartsWith("# "))
                {
                    Close(cur, notes, list);
                    var parts = line.Substring(2).Split('|');
                    cur = new Entry
                    {
                        version = parts[0].Trim(),
                        date = parts.Length > 1 ? parts[1].Trim() : "",
                        title = parts.Length > 2 ? parts[2].Trim() : "",
                    };
                    notes.Clear();
                }
                else if (cur != null && line.Trim().Length > 0)
                {
                    string t = line.Trim();
                    notes.Append(t.StartsWith("- ") ? "· " + t.Substring(2) : t).Append('\n');
                }
            }
            Close(cur, notes, list);
            return list;
        }

        static void Close(Entry cur, StringBuilder notes, List<Entry> list)
        {
            if (cur == null)
                return;
            cur.notes = notes.ToString().TrimEnd('\n');
            list.Add(cur);
        }

        /// <summary>Newest version number, e.g. "0.4".</summary>
        public static string Latest
        {
            get
            {
                var e = Entries();
                return e.Count > 0 ? e[0].version : "";
            }
        }
    }
}
