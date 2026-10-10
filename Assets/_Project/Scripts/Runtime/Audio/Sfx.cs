using UnityEngine;

namespace DeadCells.Audio
{
    /// <summary>One-shot sound effects by event id (see Tools/Audio/sfx.py).</summary>
    public static class Sfx
    {
        /// <summary>World sound: panned and faded by its distance from the camera.</summary>
        public static void Play(string id, Vector3 at, float volume = 1f, float pitch = 1f) =>
            AudioManager.Instance?.Play(id, at, volume, pitch);

        /// <summary>Interface / non-positional sound.</summary>
        public static void Play(string id, float volume = 1f, float pitch = 1f) =>
            AudioManager.Instance?.Play(id, null, volume, pitch);
    }

    /// <summary>Cross-faded music and ambience beds.</summary>
    public static class Music
    {
        public static void Play(string id, float fade = 1.5f) => AudioManager.Instance?.PlayBed(true, id, fade);

        public static void Stop(float fade = 1.5f) => AudioManager.Instance?.PlayBed(true, null, fade);

        public static void Ambience(string id, float fade = 2f) => AudioManager.Instance?.PlayBed(false, id, fade);

        public static string Current => AudioManager.Instance?.CurrentMusic;

        /// <summary>Music and ambience for an area (BiomeDef.id).</summary>
        public static void ForBiome(string biomeId, float fade = 2f)
        {
            string track, bed;
            switch (biomeId)
            {
                case "Oubliette": track = "music.oubliette"; bed = "amb.dungeon"; break;
                case "Promenade": track = "music.promenade"; bed = "amb.wind"; break;
                case "Ossuary": track = "music.ossuary"; bed = "amb.ossuary"; break;
                case "StiltVillage": track = "music.stilt"; bed = "amb.sea"; break;
                case "ClockLung": track = "music.lung"; bed = "amb.clock"; break;
                case "ToxicSewers": track = "music.oubliette"; bed = "amb.dungeon"; break;
                case "Ramparts": track = "music.promenade"; bed = "amb.wind"; break;
                default: track = "music.passage"; bed = "amb.passage"; break;
            }
            Play(track, fade);
            Ambience(bed, fade);
        }
    }
}
