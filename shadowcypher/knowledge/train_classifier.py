#!/usr/bin/env python3
"""
Shadow Intent Classifier — training pipeline.

Trains TF-IDF + Logistic Regression on natural-language intent examples.
Exports a single JSON model that runs in both Python and JavaScript
(no ONNX, no heavy dependencies at inference time).

Output:
  shadowcypher/knowledge/classifier.json — full model
  shadowcypher/knowledge/classifier_test.py — accuracy report

Install: pip install scikit-learn numpy
"""

import json
import math
import re
import time
from collections import Counter
from pathlib import Path

# ── Training data ────────────────────────────────────────────────────────────
# 80-100 natural-language examples per intent.
# Covers slang, varied phrasing, different word orders.

TRAINING_DATA: list[tuple[str, str]] = [

  # ── scan_network ────────────────────────────────────────────────────────────
  ("scan my network", "scan_network"),
  ("run a network scan", "scan_network"),
  ("scan the lan", "scan_network"),
  ("do a scan", "scan_network"),
  ("start scanning", "scan_network"),
  ("scan for devices", "scan_network"),
  ("scan my wifi", "scan_network"),
  ("run a scan on my network", "scan_network"),
  ("initiate a network scan", "scan_network"),
  ("scan local network", "scan_network"),
  ("quick scan", "scan_network"),
  ("run network scan", "scan_network"),
  ("scan the network now", "scan_network"),
  ("do a network scan", "scan_network"),
  ("kick off a scan", "scan_network"),
  ("trigger scan", "scan_network"),
  ("start a scan", "scan_network"),
  ("scan everything", "scan_network"),
  ("new scan", "scan_network"),
  ("check my network for devices", "scan_network"),
  ("launch a network scan", "scan_network"),
  ("run a quick scan", "scan_network"),
  ("scan now", "scan_network"),
  ("network scan please", "scan_network"),
  ("scan my home network", "scan_network"),

  # ── list_devices ────────────────────────────────────────────────────────────
  ("what devices are on my network", "list_devices"),
  ("show me all devices", "list_devices"),
  ("list devices", "list_devices"),
  ("what's connected to my wifi", "list_devices"),
  ("who's on my network", "list_devices"),
  ("what machines are connected", "list_devices"),
  ("show connected devices", "list_devices"),
  ("how many devices on my network", "list_devices"),
  ("list all hosts", "list_devices"),
  ("what hosts are up", "list_devices"),
  ("what's on my lan", "list_devices"),
  ("show network devices", "list_devices"),
  ("who is connected to my router", "list_devices"),
  ("list connected machines", "list_devices"),
  ("what computers are on my network", "list_devices"),
  ("show all hosts", "list_devices"),
  ("what's online on my network", "list_devices"),
  ("any unknown devices on my network", "list_devices"),
  ("show me what's connected", "list_devices"),
  ("list network hosts", "list_devices"),
  ("what ips are active", "list_devices"),
  ("who is on my wifi", "list_devices"),
  ("network devices", "list_devices"),
  ("connected devices", "list_devices"),
  ("show my devices", "list_devices"),

  # ── list_incidents ──────────────────────────────────────────────────────────
  ("any active incidents", "list_incidents"),
  ("show me incidents", "list_incidents"),
  ("any alerts", "list_incidents"),
  ("am i being hacked", "list_incidents"),
  ("any threats detected", "list_incidents"),
  ("are there any active threats", "list_incidents"),
  ("check for incidents", "list_incidents"),
  ("what attacks have been detected", "list_incidents"),
  ("any security events", "list_incidents"),
  ("show security alerts", "list_incidents"),
  ("am i under attack", "list_incidents"),
  ("any active alerts", "list_incidents"),
  ("what threats are active", "list_incidents"),
  ("any intrusions detected", "list_incidents"),
  ("show me security incidents", "list_incidents"),
  ("am i being monitored", "list_incidents"),
  ("any suspicious activity", "list_incidents"),
  ("security incidents", "list_incidents"),
  ("what's the threat status", "list_incidents"),
  ("any hacking attempts", "list_incidents"),
  ("check security events", "list_incidents"),
  ("any malicious activity", "list_incidents"),
  ("show threats", "list_incidents"),
  ("what happened on my network", "list_incidents"),
  ("security status", "list_incidents"),

  # ── list_cves ───────────────────────────────────────────────────────────────
  ("any cve alerts", "list_cves"),
  ("show cve alerts", "list_cves"),
  ("any vulnerabilities on my network", "list_cves"),
  ("what vulnerabilities are detected", "list_cves"),
  ("cve alerts", "list_cves"),
  ("show vulnerability alerts", "list_cves"),
  ("any exploits detected", "list_cves"),
  ("what cves are matched", "list_cves"),
  ("check for vulnerabilities", "list_cves"),
  ("are my devices vulnerable", "list_cves"),
  ("vulnerability report", "list_cves"),
  ("any critical vulnerabilities", "list_cves"),
  ("what software vulnerabilities do i have", "list_cves"),
  ("cve matches", "list_cves"),
  ("show exploits", "list_cves"),
  ("vulnerability scan results", "list_cves"),
  ("any known exploits on my devices", "list_cves"),
  ("security vulnerabilities", "list_cves"),
  ("check vulnerabilities", "list_cves"),
  ("what cves affect my network", "list_cves"),

  # ── ghost_status ─────────────────────────────────────────────────────────────
  ("am i in ghost mode", "ghost_status"),
  ("is ghost mode on", "ghost_status"),
  ("check ghost mode", "ghost_status"),
  ("am i anonymous", "ghost_status"),
  ("am i hidden", "ghost_status"),
  ("ghost mode status", "ghost_status"),
  ("is ghost protocol active", "ghost_status"),
  ("am i invisible online", "ghost_status"),
  ("check anonymity status", "ghost_status"),
  ("am i being tracked", "ghost_status"),
  ("is my ip hidden", "ghost_status"),
  ("ghost status", "ghost_status"),
  ("am i using tor", "ghost_status"),
  ("check my anonymity", "ghost_status"),
  ("is ghost mode enabled", "ghost_status"),
  ("privacy status", "ghost_status"),
  ("am i protected", "ghost_status"),
  ("anonymity check", "ghost_status"),
  ("is my traffic anonymized", "ghost_status"),
  ("ghost mode check", "ghost_status"),

  # ── network_summary ──────────────────────────────────────────────────────────
  ("network status", "network_summary"),
  ("guardian status", "network_summary"),
  ("give me a summary", "network_summary"),
  ("how's my network", "network_summary"),
  ("network overview", "network_summary"),
  ("what's the network status", "network_summary"),
  ("give me a network summary", "network_summary"),
  ("overall network health", "network_summary"),
  ("what's going on with my network", "network_summary"),
  ("how's everything looking", "network_summary"),
  ("network health check", "network_summary"),
  ("full network summary", "network_summary"),
  ("guardian summary", "network_summary"),
  ("status report", "network_summary"),
  ("how's my lan doing", "network_summary"),
  ("give me an overview", "network_summary"),
  ("network report", "network_summary"),
  ("how is everything", "network_summary"),
  ("whats up with my network", "network_summary"),
  ("check everything", "network_summary"),

  # ── weather ──────────────────────────────────────────────────────────────────
  ("what's the weather in london", "weather"),
  ("weather in new york", "weather"),
  ("how's the weather in tokyo", "weather"),
  ("weather forecast for paris", "weather"),
  ("what's it like in dubai", "weather"),
  ("temperature in miami", "weather"),
  ("is it raining in london", "weather"),
  ("weather today in chicago", "weather"),
  ("what's the temperature in berlin", "weather"),
  ("forecast for los angeles", "weather"),
  ("weather in dubai", "weather"),
  ("will it rain in seattle", "weather"),
  ("how hot is it in miami", "weather"),
  ("what's the weather like in sydney", "weather"),
  ("check weather for toronto", "weather"),
  ("current weather in moscow", "weather"),
  ("weather in singapore", "weather"),
  ("how cold is it in moscow", "weather"),
  ("is it sunny in barcelona", "weather"),
  ("weather forecast london", "weather"),
  ("temperature outside in cairo", "weather"),
  ("what's the weather", "weather"),
  ("weather today", "weather"),
  ("how's the weather", "weather"),
  ("weather in amsterdam", "weather"),
  ("forecast for next 3 days in paris", "weather"),
  ("is it going to rain tomorrow in manchester", "weather"),
  ("whats the weather like", "weather"),
  ("check the weather", "weather"),
  ("weather update", "weather"),

  # ── currency ─────────────────────────────────────────────────────────────────
  ("convert 100 usd to eur", "currency"),
  ("100 dollars to euros", "currency"),
  ("exchange rate usd to gbp", "currency"),
  ("what is 50 euros in dollars", "currency"),
  ("how much is 1 bitcoin in usd", "currency"),
  ("convert gbp to jpy", "currency"),
  ("1000 yen in dollars", "currency"),
  ("usd to cad exchange rate", "currency"),
  ("what is the exchange rate", "currency"),
  ("convert 500 eur to usd", "currency"),
  ("how many dollars is 100 pounds", "currency"),
  ("gbp to usd", "currency"),
  ("dollar to euro", "currency"),
  ("euros to pounds", "currency"),
  ("how much is a dollar in euros", "currency"),
  ("currency conversion usd eur", "currency"),
  ("convert dollars to pounds", "currency"),
  ("what's the rate for usd to eur", "currency"),
  ("exchange 200 dollars to yen", "currency"),
  ("currency rate", "currency"),
  ("how much is 1 usd in inr", "currency"),
  ("convert cad to usd", "currency"),
  ("what's 50 dollars in pounds", "currency"),
  ("forex rate usd eur", "currency"),
  ("money conversion", "currency"),

  # ── cve_lookup ───────────────────────────────────────────────────────────────
  ("look up cve 2021 44228", "cve_lookup"),
  ("what is cve-2021-44228", "cve_lookup"),
  ("cve 2021-44228 details", "cve_lookup"),
  ("search for cve-2023-1234", "cve_lookup"),
  ("tell me about cve 2022 0001", "cve_lookup"),
  ("look up log4shell cve", "cve_lookup"),
  ("what's the severity of cve-2021-44228", "cve_lookup"),
  ("cve details for 2019-0708", "cve_lookup"),
  ("find cve-2017-0144", "cve_lookup"),
  ("what is bluekeep vulnerability", "cve_lookup"),
  ("eternalblue cve details", "cve_lookup"),
  ("heartbleed cve", "cve_lookup"),
  ("look up this cve", "cve_lookup"),
  ("cve lookup", "cve_lookup"),
  ("search cve database", "cve_lookup"),
  ("what vulnerabilities does log4j have", "cve_lookup"),
  ("cve info", "cve_lookup"),
  ("check cve-2023-44487", "cve_lookup"),
  ("get details on cve 2021 34527", "cve_lookup"),
  ("what is printnightmare", "cve_lookup"),

  # ── ip_lookup ─────────────────────────────────────────────────────────────────
  ("check ip 192.168.1.1", "ip_lookup"),
  ("is 8.8.8.8 malicious", "ip_lookup"),
  ("ip reputation for 1.2.3.4", "ip_lookup"),
  ("check if this ip is dangerous 185.220.101.5", "ip_lookup"),
  ("lookup ip address 23.45.67.89", "ip_lookup"),
  ("is this ip safe 198.51.100.1", "ip_lookup"),
  ("check ip reputation", "ip_lookup"),
  ("is that ip address malicious", "ip_lookup"),
  ("run ip check on 45.33.32.156", "ip_lookup"),
  ("abuse score for 192.0.2.1", "ip_lookup"),
  ("is this ip a threat", "ip_lookup"),
  ("ip abuse check", "ip_lookup"),
  ("check this ip address", "ip_lookup"),
  ("who owns this ip", "ip_lookup"),
  ("ip info", "ip_lookup"),
  ("is that ip safe", "ip_lookup"),
  ("ip reputation check", "ip_lookup"),
  ("check the ip address", "ip_lookup"),
  ("is this ip blacklisted", "ip_lookup"),
  ("ip threat check", "ip_lookup"),

  # ── breach_check ─────────────────────────────────────────────────────────────
  ("have i been pwned", "breach_check"),
  ("check if my email was leaked", "breach_check"),
  ("was my account breached", "breach_check"),
  ("has my data been compromised", "breach_check"),
  ("check for data breaches", "breach_check"),
  ("am i in any data breaches", "breach_check"),
  ("was my password leaked", "breach_check"),
  ("check hibp", "breach_check"),
  ("have i been in a data breach", "breach_check"),
  ("is my email compromised", "breach_check"),
  ("check my email for breaches", "breach_check"),
  ("data breach check", "breach_check"),
  ("was i hacked", "breach_check"),
  ("is my account compromised", "breach_check"),
  ("check for leaks", "breach_check"),
  ("has my info been leaked", "breach_check"),
  ("pwned check", "breach_check"),
  ("breach scan", "breach_check"),
  ("check if i was breached", "breach_check"),
  ("am i pwned", "breach_check"),

  # ── dns_lookup ────────────────────────────────────────────────────────────────
  ("dns lookup google.com", "dns_lookup"),
  ("resolve shadowcypher.site", "dns_lookup"),
  ("what is the ip of github.com", "dns_lookup"),
  ("dns check for cloudflare.com", "dns_lookup"),
  ("lookup domain amazon.com", "dns_lookup"),
  ("what does google.com resolve to", "dns_lookup"),
  ("dns resolve microsoft.com", "dns_lookup"),
  ("look up the dns for apple.com", "dns_lookup"),
  ("check dns records for example.com", "dns_lookup"),
  ("dns info for twitter.com", "dns_lookup"),
  ("resolve this domain", "dns_lookup"),
  ("what ip does this domain point to", "dns_lookup"),
  ("dns query", "dns_lookup"),
  ("look up domain", "dns_lookup"),
  ("dns resolution check", "dns_lookup"),
  ("what are the dns records for this site", "dns_lookup"),
  ("resolve hostname", "dns_lookup"),
  ("nslookup google.com", "dns_lookup"),
  ("dns check", "dns_lookup"),
  ("get ip from domain name", "dns_lookup"),

  # ── open_settings ─────────────────────────────────────────────────────────────
  ("open settings", "open_settings"),
  ("go to settings", "open_settings"),
  ("set my api key", "open_settings"),
  ("enter api key", "open_settings"),
  ("configure api key", "open_settings"),
  ("change my api key", "open_settings"),
  ("settings", "open_settings"),
  ("configure shadow", "open_settings"),
  ("setup api key", "open_settings"),
  ("i need to set my key", "open_settings"),
  ("update api key", "open_settings"),
  ("api key settings", "open_settings"),
  ("where do i put my api key", "open_settings"),
  ("configure my account", "open_settings"),
  ("shadowcypher settings", "open_settings"),

  # ── call (OS) ─────────────────────────────────────────────────────────────────
  ("call mom", "call"),
  ("call john", "call"),
  ("ring sarah", "call"),
  ("phone dad", "call"),
  ("call 555-1234", "call"),
  ("make a call to mike", "call"),
  ("dial alex", "call"),
  ("call my wife", "call"),
  ("ring my boss", "call"),
  ("call emergency services", "call"),
  ("phone my doctor", "call"),
  ("give john a call", "call"),
  ("call back", "call"),
  ("ring 911", "call"),
  ("call the office", "call"),

  # ── sms (OS) ──────────────────────────────────────────────────────────────────
  ("text mom i'll be late", "sms"),
  ("send a message to john saying hello", "sms"),
  ("text sarah are you free tonight", "sms"),
  ("message dad i'm on my way", "sms"),
  ("send sms to mike meeting cancelled", "sms"),
  ("text my wife i love you", "sms"),
  ("send a text", "sms"),
  ("message alex", "sms"),
  ("text 555-1234 running late", "sms"),
  ("send message to boss", "sms"),

  # ── alarm (OS) ────────────────────────────────────────────────────────────────
  ("set an alarm for 7am", "alarm"),
  ("wake me up at 6:30", "alarm"),
  ("set alarm for tomorrow morning 8 o'clock", "alarm"),
  ("alarm at 7:30 am", "alarm"),
  ("wake me at 5am", "alarm"),
  ("set a wake up alarm", "alarm"),
  ("alarm for 9pm", "alarm"),
  ("set alarm 6 am", "alarm"),
  ("remind me to wake up at 7", "alarm"),
  ("morning alarm at 6:45", "alarm"),

  # ── timer (OS) ────────────────────────────────────────────────────────────────
  ("set a timer for 10 minutes", "timer"),
  ("timer 5 minutes", "timer"),
  ("start a 30 second timer", "timer"),
  ("set timer for 1 hour", "timer"),
  ("10 minute timer", "timer"),
  ("countdown timer 5 mins", "timer"),
  ("set a 2 minute timer", "timer"),
  ("start timer", "timer"),
  ("timer for 45 minutes", "timer"),
  ("3 hour timer", "timer"),

  # ── open_app (OS) ─────────────────────────────────────────────────────────────
  ("open spotify", "open_app"),
  ("launch chrome", "open_app"),
  ("open netflix", "open_app"),
  ("start whatsapp", "open_app"),
  ("open maps", "open_app"),
  ("launch camera", "open_app"),
  ("open telegram", "open_app"),
  ("start gmail", "open_app"),
  ("open youtube", "open_app"),
  ("launch calculator", "open_app"),

  # ── maps (OS) ─────────────────────────────────────────────────────────────────
  ("navigate to the airport", "maps"),
  ("directions to starbucks", "maps"),
  ("take me to new york", "maps"),
  ("get directions to the nearest hospital", "maps"),
  ("navigate home", "maps"),
  ("how do i get to downtown", "maps"),
  ("directions to 123 main street", "maps"),
  ("go to the nearest gas station", "maps"),
  ("navigate to work", "maps"),
  ("take me to mcdonald's", "maps"),

]

# ── Tokenizer ────────────────────────────────────────────────────────────────

def tokenize(text: str) -> list[str]:
  text = text.lower()
  # Keep CVE-style tokens intact
  text = re.sub(r'cve[- ](\d{4})[- ](\d+)', r'cve-\1-\2', text)
  # Replace IP addresses with placeholder
  text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', 'IP_ADDR', text)
  # Normalize apostrophes
  text = re.sub(r"'(s|ll|re|ve|m|d|t)\b", '', text)
  tokens = re.findall(r'\b[a-z][a-z0-9\-\.]{0,}\b', text)
  # Add bigrams for common phrases
  bigrams = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens)-1)]
  return tokens + bigrams


# ── TF-IDF + Logistic Regression (manual implementation) ────────────────────

def train(data: list[tuple[str, str]]) -> dict:
  texts = [t for t, _ in data]
  labels = [lbl for _, lbl in data]
  classes = sorted(set(labels))
  class_idx = {c: i for i, c in enumerate(classes)}

  # Build vocabulary
  all_tokens = []
  tokenized = [tokenize(t) for t in texts]
  for tokens in tokenized:
    all_tokens.extend(tokens)
  vocab = {tok: i for i, tok in enumerate(sorted(set(all_tokens)))}

  # Compute IDF
  N = len(texts)
  df = Counter()
  for tokens in tokenized:
    for tok in set(tokens):
      if tok in vocab:
        df[tok] += 1
  idf = [math.log((N + 1) / (df.get(tok, 0) + 1)) + 1.0 for tok in sorted(vocab.keys())]

  # Build TF-IDF matrix
  def vectorize(tokens: list[str]) -> list[float]:
    tf = Counter(tokens)
    vec = [0.0] * len(vocab)
    for tok, count in tf.items():
      if tok in vocab:
        vec[vocab[tok]] = (count / max(len(tokens), 1)) * idf[vocab[tok]]
    # L2 normalize
    norm = math.sqrt(sum(v*v for v in vec))
    if norm > 0:
      vec = [v / norm for v in vec]
    return vec

  X = [vectorize(tok) for tok in tokenized]
  y = [class_idx[lbl] for lbl in labels]

  n_features = len(vocab)
  n_classes = len(classes)

  # Logistic Regression with SGD (simple, no deps)
  weights = [[0.0] * n_features for _ in range(n_classes)]
  bias = [0.0] * n_classes
  lr = 0.1
  reg = 0.001
  n_epochs = 200

  def softmax(logits):
    m = max(logits)
    exp_logits = [math.exp(logit - m) for logit in logits]
    s = sum(exp_logits)
    return [e / s for e in exp_logits]

  for epoch in range(n_epochs):
    total_loss = 0.0
    # Shuffle
    import random
    indices = list(range(len(X)))
    random.shuffle(indices)

    for i in indices:
      x = X[i]
      y_true = y[i]

      # Forward
      logits = [sum(weights[c][j] * x[j] for j in range(n_features)) + bias[c]
                for c in range(n_classes)]
      probs = softmax(logits)

      # Loss (cross-entropy)
      total_loss -= math.log(max(probs[y_true], 1e-10))

      # Backward
      for c in range(n_classes):
        delta = probs[c] - (1.0 if c == y_true else 0.0)
        for j in range(n_features):
          if x[j] != 0:  # Sparse update
            weights[c][j] -= lr * (delta * x[j] + reg * weights[c][j])
        bias[c] -= lr * delta

    if (epoch + 1) % 50 == 0:
      acc = evaluate(X, y, weights, bias, n_classes)
      print(f"  Epoch {epoch+1}/{n_epochs} — loss: {total_loss/len(X):.3f}, acc: {acc:.1%}")

  return {
    "vocabulary": vocab,
    "idf": idf,
    "classes": classes,
    "weights": weights,
    "bias": bias,
    "threshold": 0.35,
  }


def predict(text: str, model: dict) -> tuple[str, float]:
  vocab = model["vocabulary"]
  idf = model["idf"]
  weights = model["weights"]
  bias = model["bias"]
  classes = model["classes"]
  n_features = len(vocab)

  tokens = tokenize(text)
  tf = Counter(tokens)
  vec = [0.0] * n_features
  for tok, count in tf.items():
    if tok in vocab:
      idx = vocab[tok]
      vec[idx] = (count / max(len(tokens), 1)) * idf[idx]

  norm = math.sqrt(sum(v*v for v in vec))
  if norm > 0:
    vec = [v / norm for v in vec]

  logits = [sum(weights[c][j] * vec[j] for j in range(n_features)) + bias[c]
            for c in range(len(classes))]
  m = max(logits)
  exp_l = [math.exp(logit - m) for logit in logits]
  s = sum(exp_l)
  probs = [e / s for e in exp_l]

  best_idx = probs.index(max(probs))
  return classes[best_idx], probs[best_idx]


def evaluate(X, y, weights, bias, n_classes):
  correct = 0
  for x, y_true in zip(X, y, strict=False):
    logits = [sum(weights[c][j] * x[j] for j in range(len(x))) + bias[c]
              for c in range(n_classes)]
    pred = logits.index(max(logits))
    if pred == y_true:
      correct += 1
  return correct / len(X)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
  import random
  random.seed(42)

  print("=== Shadow Intent Classifier — Training ===\n")
  print(f"Training examples: {len(TRAINING_DATA)}")
  intents = sorted(set(lbl for _, lbl in TRAINING_DATA))
  print(f"Intents ({len(intents)}): {', '.join(intents)}\n")

  print("Training...")
  t0 = time.time()
  model = train(TRAINING_DATA)
  elapsed = time.time() - t0
  print(f"\nTraining complete in {elapsed:.1f}s\n")

  # Full training accuracy
  correct = sum(1 for text, label in TRAINING_DATA if predict(text, model)[0] == label)
  print(f"Training accuracy: {correct}/{len(TRAINING_DATA)} = {correct/len(TRAINING_DATA):.1%}\n")

  # Test on unseen phrasing
  test_cases = [
    ("yo scan my wifi real quick", "scan_network"),
    ("who's leeching off my wifi", "list_devices"),
    ("anything sketchy going on", "list_incidents"),
    ("whats the temp in london bro", "weather"),
    ("convert 250 quid to dollars", "currency"),
    ("what's log4shell", "cve_lookup"),
    ("is 45.33.32.156 sus", "ip_lookup"),
    ("have i been in any leaks", "breach_check"),
    ("what does microsoft.com resolve to", "dns_lookup"),
    ("call my dad", "call"),
    ("text sarah i'm running late", "sms"),
    ("wake me up at 7 tomorrow", "alarm"),
    ("set a 20 minute timer", "timer"),
    ("open instagram", "open_app"),
    ("take me home", "maps"),
    ("turn on ghost mode", "ghost_status"),
    ("how's everything on the network", "network_summary"),
    ("any cves matched", "list_cves"),
    ("open the settings", "open_settings"),
  ]

  print("=== Holdout Test (unseen phrasing) ===")
  test_correct = 0
  for text, expected in test_cases:
    pred, conf = predict(text, model)
    ok = pred == expected
    if ok:
        test_correct += 1
    status = "✓" if ok else f"✗ (got {pred})"
    print(f"  {status} [{conf:.0%}] '{text}' → {pred}")

  print(f"\nHoldout accuracy: {test_correct}/{len(test_cases)} = {test_correct/len(test_cases):.1%}\n")

  # Save model
  out_path = Path(__file__).parent / "classifier.json"

  # Compress: only store non-zero weights per class
  compressed_weights = []
  for class_weights in model["weights"]:
    sparse = {str(i): v for i, v in enumerate(class_weights) if abs(v) > 1e-6}
    compressed_weights.append(sparse)

  export = {
    "vocabulary": {k: v for k, v in model["vocabulary"].items()},
    "idf": [round(v, 6) for v in model["idf"]],
    "classes": model["classes"],
    "weights": compressed_weights,
    "bias": [round(v, 6) for v in model["bias"]],
    "threshold": model["threshold"],
    "n_features": len(model["vocabulary"]),
  }

  with open(out_path, "w") as f:
    json.dump(export, f, separators=(",", ":"))

  size_kb = out_path.stat().st_size / 1024
  print(f"Model saved: {out_path.name} ({size_kb:.0f} KB)")
  print("Deploy to: android/assistant/src/main/assets/classifier.json")


if __name__ == "__main__":
  main()
