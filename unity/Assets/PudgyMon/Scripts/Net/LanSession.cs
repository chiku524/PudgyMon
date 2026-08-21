using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using UnityEngine;

namespace PudgyMon
{
    /// <summary>
    /// Lightweight LAN listen-server. Host is authority; joiners send input, receive poses.
    /// Start with --host/--join on the command line, or H / J in the pause menu.
    /// </summary>
    public sealed class LanSession
    {
        public bool Hosting { get; private set; }
        public bool Joining { get; private set; }
        public string Status = "Offline";
        public int Port = 7777;
        public string JoinAddress = "127.0.0.1";

        UdpClient _udp;
        IPEndPoint _hostEp;
        readonly Dictionary<string, int> _slots = new Dictionary<string, int>();
        readonly Dictionary<int, Vector3> _remotePos = new Dictionary<int, Vector3>();
        float _sendAcc;
        int _nextSlot = 1;

        public void TryParseCommandLine()
        {
            var args = System.Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length; i++)
            {
                if (args[i] == "--port" && i + 1 < args.Length && int.TryParse(args[i + 1], out var p))
                    Port = p;
                if (args[i] == "--address" && i + 1 < args.Length)
                    JoinAddress = args[i + 1];
                if (args[i] == "host" || args[i] == "--host")
                    StartHost();
                if (args[i] == "join" || args[i] == "--join")
                    StartJoin(JoinAddress);
            }
        }

        public void StartHost()
        {
            Stop();
            _udp = new UdpClient(Port);
            _udp.Client.Blocking = false;
            Hosting = true;
            Status = $"Hosting :{Port}";
            Debug.Log(Status);
        }

        public void StartJoin(string address)
        {
            Stop();
            JoinAddress = address;
            _udp = new UdpClient(0);
            _udp.Client.Blocking = false;
            _hostEp = new IPEndPoint(IPAddress.Parse(address), Port);
            Joining = true;
            Status = $"Joining {address}:{Port}";
            Debug.Log(Status);
        }

        public void Stop()
        {
            Hosting = false;
            Joining = false;
            _udp?.Close();
            _udp = null;
            _slots.Clear();
            _remotePos.Clear();
            Status = "Offline";
        }

        public void TickHost(float dt, IReadOnlyList<PlayerMotor> players, PartyDirector director)
        {
            if (!Hosting || _udp == null) return;
            DrainHost();
            _sendAcc += dt;
            if (_sendAcc < 0.05f) return;
            _sendAcc = 0f;
            var sb = new StringBuilder();
            sb.Append((int)director.Phase).Append('|').Append(director.PhaseTimer.ToString("0.00")).Append('|')
                .Append(director.Announcer.Replace('|', '/')).Append('|').Append(director.MatchPoints[0]);
            foreach (var p in players)
            {
                var t = p.transform.position;
                sb.Append('|').Append(p.Slot).Append(',').Append(t.x.ToString("0.00")).Append(',')
                    .Append(t.y.ToString("0.00")).Append(',').Append(t.z.ToString("0.00"));
            }
            var bytes = Encoding.UTF8.GetBytes("S|" + sb);
            foreach (var kv in _slots)
            {
                try
                {
                    var parts = kv.Key.Split(':');
                    _udp.Send(bytes, bytes.Length, parts[0], int.Parse(parts[1]));
                }
                catch { /* ignore send fail */ }
            }
        }

        public void TickJoin(float dt, PlayerMotor local, PartyDirector director)
        {
            if (!Joining || _udp == null || _hostEp == null) return;
            _sendAcc += dt;
            if (_sendAcc >= 0.05f)
            {
                _sendAcc = 0f;
                var t = local.transform.position;
                var msg = Encoding.UTF8.GetBytes($"I|{t.x:0.00},{t.y:0.00},{t.z:0.00}");
                _udp.Send(msg, msg.Length, _hostEp);
            }

            while (_udp.Available > 0)
            {
                try
                {
                    IPEndPoint ep = null;
                    var data = _udp.Receive(ref ep);
                    ApplySnapshot(Encoding.UTF8.GetString(data), director);
                }
                catch { break; }
            }
        }

        public void ApplyRemotes(IReadOnlyList<PlayerMotor> players)
        {
            foreach (var p in players)
            {
                if (p.IsLocal) continue;
                if (_remotePos.TryGetValue(p.Slot, out var pos))
                    p.transform.position = pos;
            }
        }

        void DrainHost()
        {
            while (_udp.Available > 0)
            {
                try
                {
                    IPEndPoint ep = null;
                    var data = _udp.Receive(ref ep);
                    var key = ep.Address + ":" + ep.Port;
                    if (!_slots.ContainsKey(key))
                    {
                        _slots[key] = _nextSlot++;
                        Status = $"Hosting :{Port} · {_slots.Count} joiner(s)";
                    }
                    var text = Encoding.UTF8.GetString(data);
                    if (text.StartsWith("I|"))
                    {
                        var xyz = text.Substring(2).Split(',');
                        if (xyz.Length >= 3)
                            _remotePos[_slots[key]] = new Vector3(float.Parse(xyz[0]), float.Parse(xyz[1]), float.Parse(xyz[2]));
                    }
                }
                catch { break; }
            }
        }

        void ApplySnapshot(string text, PartyDirector director)
        {
            if (!text.StartsWith("S|")) return;
            var parts = text.Substring(2).Split('|');
            if (parts.Length < 4) return;
            if (int.TryParse(parts[0], out var ph))
                director.Phase = (PartyPhase)ph;
            float.TryParse(parts[1], out director.PhaseTimer);
            director.Announcer = parts[2];
            if (uint.TryParse(parts[3], out var pts))
                director.MatchPoints[0] = pts;
            for (int i = 4; i < parts.Length; i++)
            {
                var b = parts[i].Split(',');
                if (b.Length < 4) continue;
                if (int.TryParse(b[0], out var slot))
                    _remotePos[slot] = new Vector3(float.Parse(b[1]), float.Parse(b[2]), float.Parse(b[3]));
            }
        }
    }
}
