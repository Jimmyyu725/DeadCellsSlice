using System.Collections.Generic;
using DeadCells.Core;
using DeadCells.Meta;
using UnityEngine;

namespace DeadCells.Audio
{
    /// <summary>
    /// Plays the sound bank: a pool of voices panned and attenuated by their
    /// distance from the camera (the game is 2D, so no 3D spatialiser), plus
    /// cross-faded music and ambience beds. Survives scene loads and owns the
    /// only AudioListener.
    /// </summary>
    public class AudioManager : MonoBehaviour
    {
        const int VoiceCount = 32;
        const float FullRange = 14f;    // metres from the camera centre at full volume
        const float SilentRange = 30f;  // inaudible beyond this
        const float PanRange = 16f;

        static AudioManager instance;
        static bool quitting;

        public static AudioManager Instance
        {
            get
            {
                if (instance == null && Application.isPlaying && !quitting)
                {
                    var go = new GameObject("AudioManager");
                    DontDestroyOnLoad(go);
                    instance = go.AddComponent<AudioManager>();
                }
                return instance;
            }
        }

        class Voice
        {
            public AudioSource src;
            public string id;
            public float baseVolume;
            public bool spatial;
            public Vector3 position;
            public float started;
        }

        class Bed
        {
            public readonly AudioSource[] src = new AudioSource[2];
            public readonly MusicTrack[] track = new MusicTrack[2];
            public int active;
            public float fade = 1.5f;
            public string Current => track[active] != null && src[active].isPlaying ? track[active].id : null;
        }

        readonly Dictionary<string, SoundEvent> events = new Dictionary<string, SoundEvent>();
        readonly Dictionary<string, MusicTrack> tracks = new Dictionary<string, MusicTrack>();
        readonly Dictionary<string, float> lastPlayed = new Dictionary<string, float>();
        readonly HashSet<string> warned = new HashSet<string>();
        readonly Bed music = new Bed();
        readonly Bed ambience = new Bed();
        Voice[] voices;

        static float SfxVolume => SaveSystem.Data.settings.sfxVolume;
        static float MusicVolume => SaveSystem.Data.settings.musicVolume;

        /// <summary>Effects started this session (test statistics).</summary>
        public static int PlayedCount { get; private set; }
        public static readonly HashSet<string> PlayedIds = new HashSet<string>();

        void Awake()
        {
            instance = this;
            gameObject.AddComponent<AudioListener>();
            // Test-bot runs stay silent: the machine they run on is in use.
            if (System.Array.IndexOf(System.Environment.GetCommandLineArgs(), "-autoplay") >= 0)
                AudioListener.volume = 0f;
            var bank = Resources.Load<SoundBank>("SoundBank");
            if (bank == null)
                Debug.LogWarning("[DC] audio: Resources/SoundBank missing");
            else
            {
                foreach (var e in bank.sfx)
                    events[e.id] = e;
                foreach (var t in bank.music)
                    tracks[t.id] = t;
                foreach (var t in bank.ambience)
                    tracks[t.id] = t;
                Debug.Log($"[DC] audio: {events.Count} effects, {bank.music.Count} music, {bank.ambience.Count} ambience");
            }
            voices = new Voice[VoiceCount];
            for (int i = 0; i < VoiceCount; i++)
                voices[i] = new Voice { src = NewSource(false) };
            for (int i = 0; i < 2; i++)
            {
                music.src[i] = NewSource(true);
                ambience.src[i] = NewSource(true);
            }
        }

        AudioSource NewSource(bool bed)
        {
            var s = gameObject.AddComponent<AudioSource>();
            s.playOnAwake = false;
            s.spatialBlend = 0f;
            s.loop = bed;
            s.priority = bed ? 0 : 128;
            s.ignoreListenerPause = true;
            return s;
        }

        void OnApplicationQuit() => quitting = true;

        // ------------------------------------------------------------- effects

        public void Play(string id, Vector3? at, float volume, float pitch)
        {
            if (!events.TryGetValue(id, out var e) || e.clips == null || e.clips.Length == 0)
            {
                if (warned.Add(id))
                    Debug.LogWarning($"[DC] audio: no sound '{id}'");
                return;
            }
            float now = Time.unscaledTime;
            if (lastPlayed.TryGetValue(id, out float last) && now - last < e.cooldown)
                return;
            int playing = 0;
            foreach (var v in voices)
                if (v.id == id && v.src.isPlaying)
                    playing++;
            if (playing >= e.voices)
                return;
            bool spatial = e.spatial && at.HasValue;
            float att = 1f, pan = 0f;
            if (spatial)
            {
                Spatial(at.Value, out att, out pan);
                if (att <= 0.01f)
                    return;
            }
            var voice = FreeVoice();
            lastPlayed[id] = now;
            voice.id = id;
            voice.baseVolume = e.volume * volume;
            voice.spatial = spatial;
            voice.position = at ?? Vector3.zero;
            voice.started = now;
            var src = voice.src;
            src.clip = e.clips[Random.Range(0, e.clips.Length)];
            src.pitch = Random.Range(e.pitch.x, e.pitch.y) * pitch;
            src.panStereo = pan;
            src.volume = voice.baseVolume * att * SfxVolume;
            src.Play();
            PlayedCount++;
            PlayedIds.Add(id);
        }

        Voice FreeVoice()
        {
            Voice oldest = voices[0];
            foreach (var v in voices)
            {
                if (!v.src.isPlaying)
                    return v;
                if (v.started < oldest.started)
                    oldest = v;
            }
            oldest.src.Stop();
            return oldest;
        }

        static void Spatial(Vector3 at, out float attenuation, out float pan)
        {
            var cam = Camera.main;
            if (cam == null)
            {
                attenuation = 1f;
                pan = 0f;
                return;
            }
            Vector2 d = (Vector2)(at - cam.transform.position);
            attenuation = 1f - Mathf.InverseLerp(FullRange, SilentRange, d.magnitude);
            pan = Mathf.Clamp(d.x / PanRange, -1f, 1f) * 0.7f;
        }

        // ---------------------------------------------------------- music beds

        public void PlayBed(bool isMusic, string id, float fade)
        {
            var bed = isMusic ? music : ambience;
            MusicTrack t = null;
            if (!string.IsNullOrEmpty(id) && !tracks.TryGetValue(id, out t) && warned.Add(id))
                Debug.LogWarning($"[DC] audio: no track '{id}'");
            if (t != null && bed.Current == t.id)
                return;
            bed.fade = Mathf.Max(0.05f, fade);
            bed.active = 1 - bed.active;
            var src = bed.src[bed.active];
            bed.track[bed.active] = t;
            if (t == null || t.clip == null)
            {
                src.Stop();
                return;
            }
            src.clip = t.clip;
            src.loop = t.loop;
            src.volume = 0f;
            src.time = 0f;
            src.Play();
        }

        public string CurrentMusic => music.Current;

        void Update()
        {
            float dt = Time.unscaledDeltaTime;
            float duck = GamePause.Paused ? 0.45f : 1f;
            UpdateBed(music, MusicVolume * duck, dt);
            UpdateBed(ambience, SfxVolume * duck, dt);
            foreach (var v in voices)
            {
                if (!v.src.isPlaying)
                {
                    v.id = null;
                    continue;
                }
                float att = 1f;
                if (v.spatial)
                {
                    Spatial(v.position, out att, out float pan);
                    v.src.panStereo = pan;
                }
                v.src.volume = v.baseVolume * att * SfxVolume;
            }
        }

        static void UpdateBed(Bed bed, float master, float dt)
        {
            for (int i = 0; i < 2; i++)
            {
                var s = bed.src[i];
                if (!s.isPlaying)
                    continue;
                float target = i == bed.active && bed.track[i] != null ? bed.track[i].volume * master : 0f;
                s.volume = Mathf.MoveTowards(s.volume, target, dt / bed.fade);
                if (i != bed.active && s.volume <= 0.001f)
                    s.Stop();
            }
        }
    }
}
