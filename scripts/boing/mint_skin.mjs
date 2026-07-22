#!/usr/bin/env node
/**
 * Lazy-mint a PudgyMon skin NFT to a recipient AccountId.
 *
 * Usage:
 *   node scripts/boing/mint_skin.mjs --to 0x… --token-id 1001
 *
 * Env (scripts/boing/.env or process):
 *   BOING_RPC_URL, BOING_SECRET_HEX (collection admin / deployer)
 *   BOING_SDK_PATH (optional)
 *
 * Prints one JSON line to stdout:
 *   { "ok": true, "token_id": 1001, "tx_hash": "...", "recipient": "0x..." }
 */

import { readFileSync, existsSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { pathToFileURL } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, "../..");

function loadDotEnv(path) {
  if (!existsSync(path)) return;
  for (const line of readFileSync(path, "utf8").split(/\r?\n/)) {
    const t = line.trim();
    if (!t || t.startsWith("#") || !t.includes("=")) continue;
    const i = t.indexOf("=");
    const k = t.slice(0, i).trim();
    let v = t.slice(i + 1).trim();
    if (
      (v.startsWith('"') && v.endsWith('"')) ||
      (v.startsWith("'") && v.endsWith("'"))
    ) {
      v = v.slice(1, -1);
    }
    if (!(k in process.env)) process.env[k] = v;
  }
}

loadDotEnv(resolve(__dirname, ".env"));

function parseArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--to" || a === "--recipient") {
      out.to = argv[++i];
    } else if (a === "--token-id" || a === "--token") {
      out.tokenId = argv[++i];
    } else if (a === "--rpc") {
      out.rpc = argv[++i];
    } else if (a === "--collection") {
      out.collection = argv[++i];
    } else if (a === "--help" || a === "-h") {
      out.help = true;
    }
  }
  return out;
}

function hexToBytes(hex) {
  const h = hex.startsWith("0x") ? hex.slice(2) : hex;
  if (h.length % 2) throw new Error("odd hex length");
  const out = new Uint8Array(h.length / 2);
  for (let i = 0; i < out.length; i++) {
    out[i] = parseInt(h.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
}

function resolveSdkEntry() {
  const candidates = [
    process.env.BOING_SDK_PATH,
    resolve(
      "C:/Users/chiku/Desktop/vibe-code/boing.network/boing-sdk/dist/index.js"
    ),
    resolve(repoRoot, "../boing.network/boing-sdk/dist/index.js"),
    resolve(repoRoot, "../../Desktop/vibe-code/boing.network/boing-sdk/dist/index.js"),
  ].filter(Boolean);
  for (const p of candidates) {
    if (existsSync(p)) return p;
  }
  try {
    const req = createRequire(import.meta.url);
    return req.resolve("boing-sdk");
  } catch {
    return null;
  }
}

function loadContracts() {
  const path = resolve(repoRoot, "data/boing/contracts.json");
  if (!existsSync(path)) return {};
  return JSON.parse(readFileSync(path, "utf8"));
}

function fail(msg) {
  console.log(JSON.stringify({ ok: false, error: msg }));
  process.exit(1);
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help) {
    console.error(
      "Usage: node mint_skin.mjs --to 0x…64hex --token-id <u64> [--rpc URL] [--collection 0x…]"
    );
    process.exit(0);
  }

  const contracts = loadContracts();
  const rpc =
    args.rpc ||
    process.env.BOING_RPC_URL ||
    contracts.rpc_url ||
    "http://127.0.0.1:8545";
  const secretHex = (process.env.BOING_SECRET_HEX || "").trim();
  const collection =
    args.collection ||
    contracts.nft_collection ||
    process.env.BOING_NFT_COLLECTION ||
    "";
  const to = (args.to || "").trim();
  const tokenIdRaw = args.tokenId;

  if (!secretHex || !/^0x[0-9a-fA-F]{64}$/.test(secretHex)) {
    fail("Set BOING_SECRET_HEX=0x…64 hex (collection admin / deployer seed)");
  }
  if (!to || !/^0x[0-9a-fA-F]{64}$/.test(to)) {
    fail("--to must be a Boing AccountId (0x + 64 hex)");
  }
  if (tokenIdRaw == null || tokenIdRaw === "") {
    fail("--token-id is required");
  }
  const tokenId = BigInt(tokenIdRaw);
  if (tokenId < 0n) fail("token-id must be >= 0");
  if (!collection || !/^0x[0-9a-fA-F]{64}$/.test(collection)) {
    fail("nft_collection missing (contracts.json or --collection)");
  }

  const sdkPath = resolveSdkEntry();
  if (!sdkPath) {
    fail("boing-sdk not found. Set BOING_SDK_PATH to boing-sdk/dist/index.js");
  }

  const sdk = await import(pathToFileURL(sdkPath).href);
  const {
    createClient,
    senderHexFromSecretKey,
    submitContractCallWithSimulationRetry,
    encodeReferenceTransferNftCalldata,
    referenceNftTokenIdWordFromU64,
    hexToBytes: sdkHexToBytes,
    explainBoingRpcError,
  } = sdk;

  const toBytes = sdkHexToBytes || hexToBytes;
  const secretKey32 = toBytes(secretHex);
  const client = createClient(rpc);
  const senderHex = await senderHexFromSecretKey(secretKey32);
  const tokenIdWord = referenceNftTokenIdWordFromU64(tokenId);
  const calldata = encodeReferenceTransferNftCalldata(to, tokenIdWord);

  try {
    const result = await submitContractCallWithSimulationRetry({
      client,
      secretKey32,
      senderHex,
      contractHex: collection,
      calldata,
    });
    console.log(
      JSON.stringify({
        ok: true,
        token_id: Number(tokenId),
        tx_hash: result.tx_hash,
        recipient: to,
        collection,
        admin: senderHex,
        attempts: result.attempts,
      })
    );
  } catch (e) {
    const msg = explainBoingRpcError?.(e) || e?.message || String(e);
    fail(msg);
  }
}

main().catch((e) => fail(e?.stack || String(e)));
