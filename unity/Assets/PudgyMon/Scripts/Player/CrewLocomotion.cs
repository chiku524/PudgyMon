using System;
using UnityEngine;

namespace PudgyMon
{
    /// <summary>
    /// Plays GLB idle / walk / run / jump on the attached crew mesh.
    /// Core studio bodies ship those clips; dense Tripo meshes stay in bind pose.
    /// </summary>
    public sealed class CrewLocomotion : MonoBehaviour
    {
        public PlayerMotor Motor;

        Animation _anim;
        string _playing;
        string _idle;
        string _walk;
        string _run;
        string _jump;

        public void Bind(GameObject meshRoot)
        {
            _anim = meshRoot != null ? meshRoot.GetComponentInChildren<Animation>(true) : null;
            _playing = null;
            _idle = _walk = _run = _jump = null;
            if (_anim == null)
                return;

            _anim.playAutomatically = false;
            _anim.cullingType = AnimationCullingType.BasedOnRenderers;
            foreach (AnimationState state in _anim)
            {
                if (state.clip == null)
                    continue;
                var name = state.clip.name;
                if (Matches(name, "idle"))
                    _idle = state.name;
                else if (Matches(name, "walk"))
                    _walk = state.name;
                else if (Matches(name, "run"))
                    _run = state.name;
                else if (Matches(name, "jump"))
                    _jump = state.name;

                state.wrapMode = Matches(name, "jump") ? WrapMode.Once : WrapMode.Loop;
            }

            Play(_idle ?? _walk, 0f);
        }

        void LateUpdate()
        {
            if (_anim == null || Motor == null)
                return;

            string want;
            if (!Motor.Grounded && Motor.VerticalVelocity > 1.5f && _jump != null
                && (_playing != _jump || _anim.IsPlaying(_jump)))
                want = _jump;
            else if (Motor.Speed > 0.2f)
                want = Motor.Sprint ? (_run ?? _walk ?? _idle) : (_walk ?? _run ?? _idle);
            else
                want = _idle ?? _walk;

            Play(want, 0.12f);
        }

        void Play(string clip, float fade)
        {
            if (string.IsNullOrEmpty(clip) || clip == _playing || !_anim)
                return;
            if (fade > 0f && _playing != null)
                _anim.CrossFade(clip, fade);
            else
                _anim.Play(clip);
            _playing = clip;
        }

        static bool Matches(string clipName, string token)
        {
            return !string.IsNullOrEmpty(clipName)
                   && clipName.IndexOf(token, StringComparison.OrdinalIgnoreCase) >= 0;
        }
    }
}
