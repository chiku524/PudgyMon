using System.IO;
using UnityEngine;

namespace PudgyMon
{
    public static class AppPaths
    {
        public static string DataDir
        {
            get
            {
                var dir = Path.Combine(
                    System.Environment.GetFolderPath(System.Environment.SpecialFolder.LocalApplicationData),
                    Brand.AppDataDir);
                Directory.CreateDirectory(dir);
                return dir;
            }
        }

        public static string MapsDir
        {
            get
            {
                var dir = Path.Combine(DataDir, "maps");
                Directory.CreateDirectory(dir);
                return dir;
            }
        }

        public static string SharesDir
        {
            get
            {
                var dir = Path.Combine(MapsDir, "shares");
                Directory.CreateDirectory(dir);
                return dir;
            }
        }

        public static string LogsDir
        {
            get
            {
                var dir = Path.Combine(DataDir, "logs");
                Directory.CreateDirectory(dir);
                return dir;
            }
        }

        public static string BundledMaps => Path.Combine(RepoPaths.Root, "data", "maps");
        public static string CompanionClaim => Path.Combine(RepoPaths.Root, "companion", "claim", "index.html");
        public static string CompanionMaps => Path.Combine(RepoPaths.Root, "companion", "maps", "index.html");
        public static string WebIndex => Path.Combine(RepoPaths.Root, "web", "index.html");

        public static void Open(string pathOrUrl)
        {
            if (string.IsNullOrEmpty(pathOrUrl))
                return;
            try
            {
                Application.OpenURL(pathOrUrl);
            }
            catch (System.Exception e)
            {
                Debug.LogWarning($"Open failed: {e.Message}");
            }
        }
    }
}
