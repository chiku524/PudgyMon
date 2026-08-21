using System.IO;
using UnityEngine;

namespace PudgyMon
{
    public static class RepoPaths
    {
        static string _root;

        public static string Root
        {
            get
            {
                if (!string.IsNullOrEmpty(_root))
                    return _root;

                var dir = new DirectoryInfo(Application.dataPath);
                while (dir != null)
                {
                    if (Directory.Exists(Path.Combine(dir.FullName, "assets", "models")) &&
                        Directory.Exists(Path.Combine(dir.FullName, "data")))
                    {
                        _root = dir.FullName;
                        return _root;
                    }

                    dir = dir.Parent;
                }

                _root = Path.GetFullPath(Path.Combine(Application.dataPath, "..", ".."));
                return _root;
            }
        }

        public static string ModelsRoot => Path.Combine(Root, "assets", "models");
        public static string DataRoot => Path.Combine(Root, "data");

        public static string DataFile(string relative) => Path.Combine(DataRoot, relative);

        public static string GlbPath(string assetId)
        {
            var path = Path.Combine(ModelsRoot, assetId, assetId + ".glb");
            return File.Exists(path) ? path : null;
        }
    }
}
