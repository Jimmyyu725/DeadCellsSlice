using System.Collections.Generic;
using System.IO;
using DeadCells.Audio;
using UnityEditor;
using UnityEngine;

namespace DeadCells.EditorTools
{
    public static partial class DCContentBuilder
    {
        const string AudioDir = "Assets/_Project/Audio";

        [System.Serializable]
        class BankJson
        {
            public SfxJson[] sfx;
            public TrackJson[] music;
            public TrackJson[] ambience;
        }

        [System.Serializable]
        class SfxJson
        {
            public string id;
            public string[] files;
            public float volume = 1f;
            public float[] pitch;
            public float cooldown = 0.03f;
            public int voices = 4;
            public bool spatial = true;
        }

        [System.Serializable]
        class TrackJson
        {
            public string id;
            public string file;
            public float volume = 0.75f;
            public bool loop = true;
        }

        /// <summary>Resources/SoundBank from Tools/Audio/make_audio.py's audio_bank.json.</summary>
        public static void BuildSoundBank()
        {
            string json = $"{AudioDir}/audio_bank.json";
            if (!File.Exists(json))
            {
                Debug.LogError($"[DC] missing {json}: run Tools/Audio/make_audio.py");
                return;
            }
            AssetDatabase.ImportAsset(AudioDir, ImportAssetOptions.ImportRecursive);
            var data = JsonUtility.FromJson<BankJson>(File.ReadAllText(json));
            var bank = Asset<SoundBank>($"{ResourcesDir}/SoundBank.asset");
            bank.sfx = new List<SoundEvent>();
            int missing = 0;
            foreach (var e in data.sfx)
            {
                var clips = new List<AudioClip>();
                foreach (var f in e.files)
                {
                    var clip = AssetDatabase.LoadAssetAtPath<AudioClip>(f);
                    if (clip != null)
                        clips.Add(clip);
                    else
                        missing++;
                }
                bank.sfx.Add(new SoundEvent
                {
                    id = e.id,
                    clips = clips.ToArray(),
                    volume = e.volume,
                    pitch = e.pitch != null && e.pitch.Length == 2 ? new Vector2(e.pitch[0], e.pitch[1]) : Vector2.one,
                    cooldown = e.cooldown,
                    voices = Mathf.Max(1, e.voices),
                    spatial = e.spatial,
                });
            }
            bank.music = Tracks(data.music, ref missing);
            bank.ambience = Tracks(data.ambience, ref missing);
            EditorUtility.SetDirty(bank);
            Debug.Log($"[DC] sound bank: {bank.sfx.Count} effects, {bank.music.Count} music, {bank.ambience.Count} ambience, missing clips={missing}");
        }

        static List<MusicTrack> Tracks(TrackJson[] list, ref int missing)
        {
            var result = new List<MusicTrack>();
            if (list == null)
                return result;
            foreach (var t in list)
            {
                var clip = AssetDatabase.LoadAssetAtPath<AudioClip>(t.file);
                if (clip == null)
                    missing++;
                result.Add(new MusicTrack { id = t.id, clip = clip, volume = t.volume, loop = t.loop });
            }
            return result;
        }
    }
}
