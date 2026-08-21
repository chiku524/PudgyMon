using UnityEngine;

namespace PudgyMon
{
    public sealed class PartyAudio : MonoBehaviour
    {
        AudioSource _src;
        readonly System.Collections.Generic.Dictionary<int, AudioClip> _clips =
            new System.Collections.Generic.Dictionary<int, AudioClip>();

        public void Init()
        {
            _src = gameObject.AddComponent<AudioSource>();
            _src.playOnAwake = false;
            _src.spatialBlend = 0f;
            _src.ignoreListenerPause = false;
        }

        public void Pickup() => Blip(880f, 0.08f);
        public void Ko() => Blip(220f, 0.16f);
        public void Finish() => Blip(523f, 0.22f);
        public void Pad() => Blip(660f, 0.07f);

        void Blip(float hz, float dur)
        {
            if (_src == null) return;
            _src.PlayOneShot(Tone(hz, dur), 0.35f);
        }

        AudioClip Tone(float hz, float seconds)
        {
            var key = (Mathf.RoundToInt(hz) << 8) ^ Mathf.RoundToInt(seconds * 1000f);
            if (_clips.TryGetValue(key, out var cached) && cached != null)
                return cached;

            var sampleRate = 22050;
            var samples = Mathf.CeilToInt(sampleRate * seconds);
            var data = new float[samples];
            for (int i = 0; i < samples; i++)
            {
                var t = i / (float)sampleRate;
                var env = 1f - t / seconds;
                data[i] = Mathf.Sin(2f * Mathf.PI * hz * t) * env * 0.25f;
            }
            var clip = AudioClip.Create("tone", samples, 1, sampleRate, false);
            clip.SetData(data, 0);
            _clips[key] = clip;
            return clip;
        }
    }
}
