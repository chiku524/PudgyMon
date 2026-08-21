using System.IO;
using UnityEngine;

namespace PudgyMon
{
    public sealed class BoingBridge
    {
        public string RpcUrl = "http://127.0.0.1:8545";
        public string LinkedAccount;
        public string Note = "Boing offline";
        public string SkinId = "skin_starter";
        public uint SeasonPoints;

        public static BoingBridge Load()
        {
            var b = new BoingBridge();
            var node = JNode.LoadFile(RepoPaths.DataFile("boing/contracts.json"))?.AsObject();
            if (node != null)
                b.RpcUrl = node.Str("rpc_url", b.RpcUrl);
            var env = System.Environment.GetEnvironmentVariable("BOING_RPC_URL");
            if (!string.IsNullOrEmpty(env)) b.RpcUrl = env;
            var acc = System.Environment.GetEnvironmentVariable("BOING_ACCOUNT");
            if (!string.IsNullOrEmpty(acc)) b.LinkedAccount = acc;
            return b;
        }

        public string LinkFromEnv()
        {
            var acc = System.Environment.GetEnvironmentVariable("BOING_ACCOUNT");
            if (!string.IsNullOrEmpty(acc) && acc.StartsWith("0x") && acc.Length == 66)
            {
                LinkedAccount = acc;
                Note = "Wallet linked from BOING_ACCOUNT";
                return Note;
            }
            Note = string.IsNullOrEmpty(acc)
                ? "Set BOING_ACCOUNT=0x… then Ctrl+V"
                : "BOING_ACCOUNT looks invalid (want 0x + 64 hex)";
            return Note;
        }

        public string PrepareClaim(SeasonLedger season, string skinId)
        {
            if (string.IsNullOrEmpty(LinkedAccount))
            {
                Note = "Link wallet first: set BOING_ACCOUNT=0x… and Ctrl+V";
                return Note;
            }
            SkinId = skinId;
            SeasonPoints = season.points;
            Note = $"Claim voucher ready for '{SkinId}' ({SeasonPoints} pts). Ctrl+O opens companion.";
            var o = new JObject();
            o.Fields["skin_id"] = new JString(SkinId);
            o.Fields["account"] = new JString(LinkedAccount);
            o.Fields["season_points"] = new JNumber(SeasonPoints);
            o.Fields["note"] = new JString(Note);
            File.WriteAllText(Path.Combine(AppPaths.LogsDir, "claim_voucher.json"), JsonWrite.Pretty(o));
            return Note;
        }

        public string OpenCompanion()
        {
            var path = AppPaths.CompanionClaim;
            if (!File.Exists(path))
            {
                Note = "Claim companion missing (companion/claim/index.html)";
                return Note;
            }
            AppPaths.Open(path);
            Note = "Opened claim companion";
            return Note;
        }
    }

    public sealed class AccountSession
    {
        public string UserId;
        public string Email;
        public string DisplayName;
        public string BoingWallet;
        public string Note = "Not signed in";
        public string ApiBase = "http://127.0.0.1:8788";

        public bool SignedIn => !string.IsNullOrEmpty(UserId);

        public static AccountSession Load()
        {
            var a = new AccountSession();
            var env = System.Environment.GetEnvironmentVariable("PUDGYMON_ACCOUNTS_URL");
            if (!string.IsNullOrEmpty(env)) a.ApiBase = env;
            var path = Path.Combine(AppPaths.DataDir, "account_session.json");
            var node = JNode.LoadFile(path)?.AsObject();
            if (node == null) return a;
            a.UserId = node.Str("user_id");
            a.Email = node.Str("email");
            a.DisplayName = node.Str("display_name");
            a.BoingWallet = node.Str("boing_wallet");
            if (node.Has("api_base") && !string.IsNullOrEmpty(node.Str("api_base")))
                a.ApiBase = node.Str("api_base");
            a.Note = a.SignedIn ? $"Signed in as {a.DisplayName}" : "Not signed in";
            return a;
        }

        public void OpenWebsite()
        {
            var web = System.Environment.GetEnvironmentVariable("PUDGYMON_WEB_URL");
            AppPaths.Open(!string.IsNullOrEmpty(web) ? web : AppPaths.WebIndex);
            Note = "Opened accounts website";
        }
    }
}
