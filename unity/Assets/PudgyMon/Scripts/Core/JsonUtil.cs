using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;

namespace PudgyMon
{
    /// <summary>Minimal JSON DOM so map files with nested number arrays load without extra packages.</summary>
    public abstract class JNode
    {
        public virtual string AsString() => ToString();
        public virtual double AsNumber() => 0;
        public virtual bool AsBool() => false;
        public virtual JObject AsObject() => null;
        public virtual JArray AsArray() => null;
        public float AsFloat() => (float)AsNumber();
        public int AsInt() => (int)AsNumber();

        public static JNode Parse(string json) => new Parser(json).ParseValue();

        public static JNode LoadFile(string path) =>
            File.Exists(path) ? Parse(File.ReadAllText(path)) : null;
    }

    public sealed class JNull : JNode
    {
        public override string ToString() => "null";
    }

    public sealed class JBool : JNode
    {
        public readonly bool Value;
        public JBool(bool v) => Value = v;
        public override bool AsBool() => Value;
        public override double AsNumber() => Value ? 1 : 0;
        public override string ToString() => Value ? "true" : "false";
    }

    public sealed class JNumber : JNode
    {
        public readonly double Value;
        public JNumber(double v) => Value = v;
        public override double AsNumber() => Value;
        public override string AsString() => Value.ToString(CultureInfo.InvariantCulture);
        public override string ToString() => AsString();
    }

    public sealed class JString : JNode
    {
        public readonly string Value;
        public JString(string v) => Value = v ?? "";
        public override string AsString() => Value;
        public override string ToString() => Value;
    }

    public sealed class JArray : JNode
    {
        public readonly List<JNode> Items = new List<JNode>();
        public override JArray AsArray() => this;
        public int Count => Items.Count;
        public JNode this[int i] => i >= 0 && i < Items.Count ? Items[i] : new JNull();

        public float[] Float3(int i)
        {
            var a = this[i].AsArray();
            if (a == null || a.Count < 3)
                return new[] { 0f, 0f, 0f };
            return new[] { a[0].AsFloat(), a[1].AsFloat(), a[2].AsFloat() };
        }

        public List<float[]> Float3List()
        {
            var list = new List<float[]>();
            for (int i = 0; i < Count; i++)
                list.Add(Float3(i));
            return list;
        }
    }

    public sealed class JObject : JNode
    {
        public readonly Dictionary<string, JNode> Fields = new Dictionary<string, JNode>();
        public override JObject AsObject() => this;
        public JNode this[string key] => Fields.TryGetValue(key, out var n) ? n : new JNull();
        public string Str(string key, string fallback = "") =>
            Fields.TryGetValue(key, out var n) && (n is JString || n is JNumber) ? n.AsString() : fallback;
        public float Num(string key, float fallback = 0f) =>
            Fields.TryGetValue(key, out var n) && n is JNumber ? n.AsFloat() : fallback;
        public int Int(string key, int fallback = 0) =>
            Fields.TryGetValue(key, out var n) && n is JNumber ? n.AsInt() : fallback;
        public JArray Arr(string key) => this[key].AsArray() ?? new JArray();
        public JObject Obj(string key) => this[key].AsObject();
        public bool Has(string key) => Fields.ContainsKey(key);
    }

    sealed class Parser
    {
        readonly string _s;
        int _i;
        public Parser(string s) => _s = s ?? "";

        public JNode ParseValue()
        {
            Skip();
            if (_i >= _s.Length)
                return new JNull();
            var c = _s[_i];
            if (c == '{') return ParseObject();
            if (c == '[') return ParseArray();
            if (c == '"') return new JString(ParseString());
            if (c == 't' || c == 'f') return ParseBool();
            if (c == 'n') { Expect("null"); return new JNull(); }
            return ParseNumber();
        }

        JObject ParseObject()
        {
            _i++;
            var o = new JObject();
            Skip();
            if (Peek() == '}') { _i++; return o; }
            while (_i < _s.Length)
            {
                Skip();
                var key = ParseString();
                Skip();
                ExpectChar(':');
                o.Fields[key] = ParseValue();
                Skip();
                if (Peek() == ',') { _i++; continue; }
                if (Peek() == '}') { _i++; break; }
                break;
            }
            return o;
        }

        JArray ParseArray()
        {
            _i++;
            var a = new JArray();
            Skip();
            if (Peek() == ']') { _i++; return a; }
            while (_i < _s.Length)
            {
                a.Items.Add(ParseValue());
                Skip();
                if (Peek() == ',') { _i++; continue; }
                if (Peek() == ']') { _i++; break; }
                break;
            }
            return a;
        }

        string ParseString()
        {
            ExpectChar('"');
            var sb = new StringBuilder();
            while (_i < _s.Length)
            {
                var c = _s[_i++];
                if (c == '"') break;
                if (c == '\\' && _i < _s.Length)
                {
                    var e = _s[_i++];
                    sb.Append(e switch
                    {
                        'n' => '\n',
                        't' => '\t',
                        'r' => '\r',
                        '"' => '"',
                        '\\' => '\\',
                        _ => e
                    });
                }
                else sb.Append(c);
            }
            return sb.ToString();
        }

        JNumber ParseNumber()
        {
            var start = _i;
            if (Peek() == '-') _i++;
            while (_i < _s.Length && (char.IsDigit(_s[_i]) || _s[_i] == '.' || _s[_i] == 'e' || _s[_i] == 'E' || _s[_i] == '+' || _s[_i] == '-'))
                _i++;
            var slice = _s.Substring(start, _i - start);
            double.TryParse(slice, NumberStyles.Float, CultureInfo.InvariantCulture, out var n);
            return new JNumber(n);
        }

        JBool ParseBool()
        {
            if (Peek() == 't') { Expect("true"); return new JBool(true); }
            Expect("false");
            return new JBool(false);
        }

        void Skip()
        {
            while (_i < _s.Length && char.IsWhiteSpace(_s[_i])) _i++;
        }

        char Peek() => _i < _s.Length ? _s[_i] : '\0';

        void Expect(string token)
        {
            foreach (var c in token)
            {
                if (Peek() == c) _i++;
            }
        }

        void ExpectChar(char c)
        {
            Skip();
            if (Peek() == c) _i++;
        }
    }

    public static class JsonWrite
    {
        public static string Pretty(JNode node, int indent = 0)
        {
            var pad = new string(' ', indent);
            switch (node)
            {
                case JObject o:
                    if (o.Fields.Count == 0) return "{}";
                    var sb = new StringBuilder();
                    sb.Append("{\n");
                    var i = 0;
                    foreach (var kv in o.Fields)
                    {
                        sb.Append(pad).Append("  \"").Append(Escape(kv.Key)).Append("\": ");
                        sb.Append(Pretty(kv.Value, indent + 2));
                        sb.Append(++i < o.Fields.Count ? ",\n" : "\n");
                    }
                    sb.Append(pad).Append('}');
                    return sb.ToString();
                case JArray a:
                    var items = new List<string>();
                    foreach (var it in a.Items) items.Add(Pretty(it, indent + 2));
                    return "[" + string.Join(", ", items) + "]";
                case JString s: return "\"" + Escape(s.Value) + "\"";
                case JNumber n: return n.AsString();
                case JBool b: return b.Value ? "true" : "false";
                default: return "null";
            }
        }

        static string Escape(string s) =>
            s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n");
    }
}
