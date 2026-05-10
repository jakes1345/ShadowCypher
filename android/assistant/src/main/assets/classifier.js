/**
 * Shadow Intent Classifier — JS runtime.
 * Loads classifier.json (trained by train_classifier.py).
 * Runs in <0.5ms per query. No dependencies.
 */

const ShadowClassifier = (() => {
  let model = null;

  async function load() {
    try {
      const resp = await fetch('classifier.json');
      if (!resp.ok) return false;
      model = await resp.json();
      console.log(`[Classifier] Loaded. ${model.classes.length} intents, vocab ${Object.keys(model.vocabulary).length}`);
      return true;
    } catch (e) {
      console.warn('[Classifier] Failed to load:', e);
      return false;
    }
  }

  function tokenize(text) {
    let t = text.toLowerCase();
    t = t.replace(/cve[- ](\d{4})[- ](\d+)/g, 'cve-$1-$2');
    t = t.replace(/\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, 'IP_ADDR');
    t = t.replace(/'(s|ll|re|ve|m|d|t)\b/g, '');
    const tokens = (t.match(/\b[a-z][a-z0-9\-\.]{0,}\b/g) || []);
    const bigrams = [];
    for (let i = 0; i < tokens.length - 1; i++) {
      bigrams.push(`${tokens[i]}_${tokens[i+1]}`);
    }
    return tokens.concat(bigrams);
  }

  function vectorize(tokens) {
    const vocab = model.vocabulary;
    const idf = model.idf;
    const nFeatures = model.n_features;
    const vec = new Float32Array(nFeatures);
    const tf = {};
    for (const tok of tokens) tf[tok] = (tf[tok] || 0) + 1;
    const len = Math.max(tokens.length, 1);
    for (const [tok, count] of Object.entries(tf)) {
      const idx = vocab[tok];
      if (idx !== undefined) {
        vec[idx] = (count / len) * idf[idx];
      }
    }
    // L2 normalize
    let norm = 0;
    for (let i = 0; i < nFeatures; i++) norm += vec[i] * vec[i];
    norm = Math.sqrt(norm);
    if (norm > 0) for (let i = 0; i < nFeatures; i++) vec[i] /= norm;
    return vec;
  }

  function softmax(logits) {
    const max = Math.max(...logits);
    const exp = logits.map(l => Math.exp(l - max));
    const sum = exp.reduce((a, b) => a + b, 0);
    return exp.map(e => e / sum);
  }

  function classify(text) {
    if (!model) return { intent: null, confidence: 0 };

    const tokens = tokenize(text);
    const vec = vectorize(tokens);
    const nClasses = model.classes.length;
    const bias = model.bias;
    const weights = model.weights;

    const logits = new Array(nClasses);
    for (let c = 0; c < nClasses; c++) {
      let sum = bias[c];
      const w = weights[c];
      for (const [i, v] of Object.entries(w)) {
        sum += v * vec[parseInt(i)];
      }
      logits[c] = sum;
    }

    const probs = softmax(logits);
    const bestIdx = probs.indexOf(Math.max(...probs));
    const confidence = probs[bestIdx];

    if (confidence < model.threshold) {
      return { intent: 'unknown', confidence };
    }

    return {
      intent: model.classes[bestIdx],
      confidence,
      all: model.classes.map((c, i) => ({ intent: c, prob: probs[i] }))
        .sort((a, b) => b.prob - a.prob).slice(0, 3),
    };
  }

  function isReady() { return model !== null; }

  return { load, classify, isReady };
})();
