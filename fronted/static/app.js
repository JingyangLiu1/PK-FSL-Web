const $ = (id) => document.getElementById(id);

const appState = {
  files: { prior: "", exp: "", test: "" },
  sheets: { prior: [], exp: [], test: [] },
  prior: { columns: [], target: "", base: [] },
  exp: { columns: [], target: "", base: [], aux: [] },
};

const progressTimers = new Map();
const appLocale = String(window.__APP_LOCALE__ || "en").toLowerCase();
const isChineseUI = appLocale.startsWith("zh");

const zhText = new Map([
  ["PK-FSL Framework-Based Process Optimization Platform", "\u57fa\u4e8ePK-FSL\u6846\u67b6\u7684\u5de5\u827a\u4f18\u5316\u5e73\u53f0"],
  ["Prior Knowledge Guided Workflow", "\u5148\u9a8c\u77e5\u8bc6\u9a71\u52a8\u5de5\u4f5c\u6d41"],
  ["Session And Samples", "\u4f1a\u8bdd\u4e0e\u793a\u4f8b\u6570\u636e"],
  ["Create a session first, then load sample files or upload your own files in each module.", "\u5148\u521b\u5efa\u4f1a\u8bdd\uff0c\u518d\u5728\u5bf9\u5e94\u6a21\u5757\u4e2d\u8f7d\u5165\u793a\u4f8b\u6587\u4ef6\u6216\u4e0a\u4f20\u81ea\u5df1\u7684\u6587\u4ef6\u3002"],
  ["Session", "\u4f1a\u8bdd"],
  ["Create Session", "\u521b\u5efa\u4f1a\u8bdd"],
  ["Load Teacher Sample", "\u8f7d\u5165\u6559\u5e08\u793a\u4f8b"],
  ["Load Experiment Sample", "\u8f7d\u5165\u5b9e\u9a8c\u793a\u4f8b"],
  ["Load Test Sample", "\u8f7d\u5165\u6d4b\u8bd5\u793a\u4f8b"],
  ["Waiting for a session.", "\u7b49\u5f85\u521b\u5efa\u4f1a\u8bdd\u3002"],
  ["Teacher Model", "\u6559\u5e08\u6a21\u578b"],
  ["Upload prior data, choose a sheet, select target and base features, then train the teacher model.", "\u4e0a\u4f20\u5148\u9a8c\u6570\u636e\u540e\uff0c\u9009\u62e9\u5de5\u4f5c\u8868\u3001\u76ee\u6807\u53d8\u91cf\u548c\u57fa\u7840\u7279\u5f81\uff0c\u518d\u8bad\u7ec3\u6559\u5e08\u6a21\u578b\u3002"],
  ["Prior data", "\u5148\u9a8c\u6570\u636e"],
  ["Upload And Read", "\u6570\u636e\u4e0a\u4f20\u4e0e\u8bfb\u53d6"],
  ["Upload File", "\u4e0a\u4f20\u6587\u4ef6"],
  ["Choose File", "\u9009\u62e9\u6587\u4ef6"],
  ["No file chosen", "\u672a\u9009\u62e9\u6587\u4ef6"],
  ["Sheet picker", "\u5de5\u4f5c\u8868\u9009\u62e9"],
  ["Click after upload", "\u4e0a\u4f20\u540e\u70b9\u51fb"],
  ["sheet", "\u5de5\u4f5c\u8868"],
  ["auto after upload", "\u4e0a\u4f20\u540e\u81ea\u52a8\u586b\u5165"],
  ["blank", "\u7559\u7a7a"],
  ["missing", "\u7f3a\u5931\u503c"],
  ["keep", "\u4fdd\u7559"],
  ["drop rows", "\u5220\u9664\u884c"],
  ["mean fill", "\u5747\u503c\u586b\u8865"],
  ["median fill", "\u4e2d\u4f4d\u6570\u586b\u8865"],
  ["outlier", "\u5f02\u5e38\u503c"],
  ["Read Columns", "\u8bfb\u53d6\u53d8\u91cf"],
  ["Save Teacher Data", "\u4fdd\u5b58\u6559\u5e08\u6570\u636e"],
  ["Save Teacher Features", "\u4fdd\u5b58\u6559\u5e08\u7279\u5f81"],
  ["Waiting for teacher data.", "\u7b49\u5f85\u6559\u5e08\u6570\u636e\u3002"],
  ["Feature Selection", "\u7279\u5f81\u9009\u62e9"],
  ["No columns loaded yet.", "\u5c1a\u672a\u8bfb\u53d6\u53d8\u91cf\u3002"],
  ["Load data first.", "\u8bf7\u5148\u8bfb\u53d6\u6570\u636e\u3002"],
  ["Upload Excel to list sheets.", "\u4e0a\u4f20 Excel \u540e\u4f1a\u5728\u8fd9\u91cc\u5217\u51fa\u5de5\u4f5c\u8868\u3002"],
  ["CSV does not need a sheet.", "CSV \u6587\u4ef6\u65e0\u9700\u9009\u62e9\u5de5\u4f5c\u8868\u3002"],
  ["Teacher variables are not ready.", "\u6559\u5e08\u6a21\u578b\u53d8\u91cf\u5c1a\u672a\u5c31\u7eea\u3002"],
  ["Experiment variables are not ready.", "\u5b9e\u9a8c\u6a21\u578b\u53d8\u91cf\u5c1a\u672a\u5c31\u7eea\u3002"],
  ["No data.", "\u6682\u65e0\u6570\u636e\u3002"],
  ["Target", "\u76ee\u6807\u53d8\u91cf"],
  ["single", "\u5355\u9009"],
  ["Base features", "\u57fa\u7840\u7279\u5f81"],
  ["multi", "\u591a\u9009"],
  ["Choose teacher variables first.", "\u8bf7\u5148\u9009\u62e9\u6559\u5e08\u6a21\u578b\u53d8\u91cf\u3002"],
  ["Teacher Model Comparison", "\u6559\u5e08\u6a21\u578b\u6bd4\u8f83"],
  ["Partial Dependence", "\u90e8\u5206\u4f9d\u8d56\u56fe"],
  ["Train Teacher Model", "\u8bad\u7ec3\u6559\u5e08\u6a21\u578b"],
  ["Teacher model not trained yet.", "\u6559\u5e08\u6a21\u578b\u5c1a\u672a\u8bad\u7ec3\u3002"],
  ["Experiment Data", "\u57fa\u672c\u5b9e\u9a8c\u6570\u636e"],
  ["Upload experiment data, choose target, base features, and aux features, then compare models.", "\u4e0a\u4f20\u5b9e\u9a8c\u6570\u636e\u540e\uff0c\u9009\u62e9\u76ee\u6807\u53d8\u91cf\u3001\u57fa\u7840\u7279\u5f81\u548c\u8f85\u52a9\u7279\u5f81\uff0c\u518d\u8fdb\u884c\u6a21\u578b\u5bf9\u6bd4\u3002"],
  ["Experiment data", "\u5b9e\u9a8c\u6570\u636e"],
  ["Save Experiment Data", "\u4fdd\u5b58\u5b9e\u9a8c\u6570\u636e"],
  ["Save Experiment Features", "\u4fdd\u5b58\u5b9e\u9a8c\u7279\u5f81"],
  ["Waiting for experiment data.", "\u7b49\u5f85\u5b9e\u9a8c\u6570\u636e\u3002"],
  ["Aux features", "\u8f85\u52a9\u7279\u5f81"],
  ["Choose experiment variables first.", "\u8bf7\u5148\u9009\u62e9\u5b9e\u9a8c\u6a21\u578b\u53d8\u91cf\u3002"],
  ["Base Model Comparison", "\u57fa\u7840\u5b9e\u9a8c\u6a21\u578b\u5bf9\u6bd4"],
  ["Aux Feature Importance", "\u8f85\u52a9\u7279\u5f81\u91cd\u8981\u6027"],
  ["seed", "\u968f\u673a\u79cd\u5b50"],
  ["Save Current Experiment Features", "\u4fdd\u5b58\u5f53\u524d\u5b9e\u9a8c\u7279\u5f81"],
  ["Run Model Comparison", "\u8fd0\u884c\u6a21\u578b\u5bf9\u6bd4"],
  ["Run Feature Selection", "\u8fd0\u884c\u7279\u5f81\u7b5b\u9009"],
  ["Model comparison not started yet.", "\u6a21\u578b\u5bf9\u6bd4\u5c1a\u672a\u5f00\u59cb\u3002"],
  ["Feature selection not started yet.", "\u7279\u5f81\u7b5b\u9009\u5c1a\u672a\u5f00\u59cb\u3002"],
  ["GAN Augmentation", "GAN \u6570\u636e\u589e\u5f3a"],
  ["Run GAN", "\u8fd0\u884c GAN"],
  ["Target Distribution", "\u76ee\u6807\u53d8\u91cf\u5206\u5e03"],
  ["GAN Loss Curves", "GAN \u635f\u5931\u66f2\u7ebf"],
  ["GAN not started yet.", "GAN \u5c1a\u672a\u5f00\u59cb\u3002"],
  ["GAN Screening", "GAN \u7b5b\u9009"],
  ["Run Screening", "\u8fd0\u884c\u7b5b\u9009"],
  ["Screening Error Distribution", "\u7b5b\u9009\u8bef\u5dee\u5206\u5e03"],
  ["GAN screening not started yet.", "GAN \u7b5b\u9009\u5c1a\u672a\u5f00\u59cb\u3002"],
  ["Distillation And Final Model", "\u77e5\u8bc6\u84b8\u998f\u4e0e\u6700\u7ec8\u6a21\u578b"],
  ["Train Final Model", "\u8bad\u7ec3\u6700\u7ec8\u6a21\u578b"],
  ["Final Model Comparison", "\u6700\u7ec8\u6a21\u578b\u6bd4\u8f83"],
  ["Final model not trained yet.", "\u6700\u7ec8\u6a21\u578b\u5c1a\u672a\u8bad\u7ec3\u3002"],
  ["Multi-Objective Optimization", "\u591a\u76ee\u6807\u4f18\u5316"],
  ["mode", "\u6a21\u5f0f"],
  ["cost_formula", "\u6210\u672c\u516c\u5f0f"],
  ["Example: 10**(lgO3TOC0+1.7)*1.2*0.477", "\u793a\u4f8b\uff1a10**(lgO3TOC0+1.7)*1.2*0.477"],
  ["Run Optimization", "\u8fd0\u884c\u4f18\u5316"],
  ["Pareto Plot", "Pareto \u56fe"],
  ["Optimization not started yet.", "\u4f18\u5316\u5c1a\u672a\u5f00\u59cb\u3002"],
  ["Test Validation", "\u6d4b\u8bd5\u96c6\u9a8c\u8bc1"],
  ["This module compares base models and the final model together, then shows metrics and prediction details.", "\u672c\u6a21\u5757\u4f1a\u540c\u65f6\u6bd4\u8f83\u57fa\u7840\u5b9e\u9a8c\u6a21\u578b\u548c\u6700\u7ec8\u6a21\u578b\uff0c\u5e76\u5c55\u793a\u6307\u6807\u6c47\u603b\u4e0e\u9884\u6d4b\u660e\u7ec6\u3002"],
  ["Test validation", "\u6d4b\u8bd5\u9a8c\u8bc1"],
  ["Upload Test Data", "\u4e0a\u4f20\u6d4b\u8bd5\u6570\u636e"],
  ["CSV does not need a sheet", "CSV \u65e0\u9700\u9009\u62e9\u5de5\u4f5c\u8868"],
  ["Run Validation", "\u5f00\u59cb\u9a8c\u8bc1"],
  ["Waiting for test data.", "\u7b49\u5f85\u6d4b\u8bd5\u6570\u636e\u3002"],
  ["Replace Experiment Dataset", "\u66ff\u6362\u5b9e\u9a8c\u6570\u636e\u96c6"],
  ["No", "\u5426"],
  ["Yes", "\u662f"],
  ["Merge Test Into Experiment", "\u5c06\u6d4b\u8bd5\u96c6\u5e76\u5165\u5b9e\u9a8c\u96c6"],
  ["By default, experiment data will not be replaced.", "\u9ed8\u8ba4\u4e0d\u66ff\u6362\u5b9e\u9a8c\u6570\u636e\u96c6\u3002"],
  ["Test Model Comparison", "\u6d4b\u8bd5\u96c6\u6a21\u578b\u5bf9\u6bd4"],
  ["All Model Metrics", "\u6240\u6709\u6a21\u578b\u6d4b\u8bd5\u7ed3\u679c"],
  ["Validation results will be shown here.", "\u9a8c\u8bc1\u5b8c\u6210\u540e\u5728\u6b64\u5c55\u793a\u6307\u6807\u3002"],
  ["Prediction Details", "\u9884\u6d4b\u503c\u4e0e\u6d4b\u8bd5\u503c\u660e\u7ec6"],
  ["Prediction details will be shown here.", "\u9a8c\u8bc1\u5b8c\u6210\u540e\u5728\u6b64\u5c55\u793a\u9884\u6d4b\u660e\u7ec6\u3002"],
  ["Run Logs", "\u8fd0\u884c\u65e5\u5fd7"],
  ["Refresh Logs", "\u5237\u65b0\u65e5\u5fd7"],
  ["Image Preview", "\u56fe\u7247\u9884\u89c8"],
  ["Close", "\u5173\u95ed"],
  ["Workflow order: teacher model, experiment data, downstream modules, test validation, logs.", "\u6d41\u7a0b\u987a\u5e8f\uff1a\u6559\u5e08\u6a21\u578b\u3001\u57fa\u672c\u5b9e\u9a8c\u6570\u636e\u3001\u540e\u7eed\u6a21\u5757\u3001\u6d4b\u8bd5\u96c6\u9a8c\u8bc1\u3001\u8fd0\u884c\u65e5\u5fd7\u3002"],
  ["Loaded teacher data columns: {count}.", "\u5df2\u8bfb\u53d6 {count} \u4e2a\u6559\u5e08\u6570\u636e\u53d8\u91cf\u3002"],
  ["Loaded experiment data columns: {count}.", "\u5df2\u8bfb\u53d6 {count} \u4e2a\u5b9e\u9a8c\u6570\u636e\u53d8\u91cf\u3002"],
  ["Teacher model: target {target}, base features {count}.", "\u6559\u5e08\u6a21\u578b\uff1a\u76ee\u6807\u53d8\u91cf {target}\uff0c\u57fa\u7840\u7279\u5f81 {count} \u4e2a\u3002"],
  ["Experiment model: target {target}, base features {baseCount}, aux features {auxCount}.", "\u5b9e\u9a8c\u6a21\u578b\uff1a\u76ee\u6807\u53d8\u91cf {target}\uff0c\u57fa\u7840\u7279\u5f81 {baseCount} \u4e2a\uff0c\u8f85\u52a9\u7279\u5f81 {auxCount} \u4e2a\u3002"],
  ["Please create a session first.", "\u8bf7\u5148\u521b\u5efa\u4f1a\u8bdd\u3002"],
  ["Please choose a file first.", "\u8bf7\u5148\u9009\u62e9\u6587\u4ef6\u3002"],
  ["Please upload or load a file first.", "\u8bf7\u5148\u4e0a\u4f20\u6216\u8f7d\u5165\u6587\u4ef6\u3002"],
  ["Please choose a sheet first.", "\u8bf7\u5148\u9009\u62e9\u5de5\u4f5c\u8868\u3002"],
  ["Teacher target and base features are required.", "\u6559\u5e08\u6a21\u578b\u9700\u8981\u76ee\u6807\u53d8\u91cf\u548c\u57fa\u7840\u7279\u5f81\u3002"],
  ["Experiment target and base features are required.", "\u5b9e\u9a8c\u6a21\u578b\u9700\u8981\u76ee\u6807\u53d8\u91cf\u548c\u57fa\u7840\u7279\u5f81\u3002"],
  ["Teacher features saved. target={target}.", "\u6559\u5e08\u7279\u5f81\u5df2\u4fdd\u5b58\uff0c\u76ee\u6807\u53d8\u91cf={target}\u3002"],
  ["Experiment features saved. target={target}.", "\u5b9e\u9a8c\u7279\u5f81\u5df2\u4fdd\u5b58\uff0c\u76ee\u6807\u53d8\u91cf={target}\u3002"],
  ["Merge skipped because option is set to No.", "\u5f53\u524d\u9009\u62e9\u4e3a\u201c\u5426\u201d\uff0c\u672a\u6267\u884c\u5408\u5e76\u3002"],
  ["Experiment dataset updated. iteration={iteration}, rows={rows}.", "\u5b9e\u9a8c\u6570\u636e\u96c6\u5df2\u66f4\u65b0\uff1aiteration={iteration}\uff0crows={rows}\u3002"],
  ["Experiment dataset now has {rows} rows.", "\u5f53\u524d\u5b9e\u9a8c\u6570\u636e\u96c6\u5171 {rows} \u884c\u3002"],
  ["Create session failed: ", "\u521b\u5efa\u4f1a\u8bdd\u5931\u8d25\uff1a"],
  ["Load teacher sample failed: ", "\u8f7d\u5165\u6559\u5e08\u793a\u4f8b\u5931\u8d25\uff1a"],
  ["Load experiment sample failed: ", "\u8f7d\u5165\u5b9e\u9a8c\u793a\u4f8b\u5931\u8d25\uff1a"],
  ["Load test sample failed: ", "\u8f7d\u5165\u6d4b\u8bd5\u793a\u4f8b\u5931\u8d25\uff1a"],
  ["Upload teacher file failed: ", "\u4e0a\u4f20\u6559\u5e08\u6587\u4ef6\u5931\u8d25\uff1a"],
  ["Upload experiment file failed: ", "\u4e0a\u4f20\u5b9e\u9a8c\u6587\u4ef6\u5931\u8d25\uff1a"],
  ["Upload test file failed: ", "\u4e0a\u4f20\u6d4b\u8bd5\u6587\u4ef6\u5931\u8d25\uff1a"],
  ["Read teacher columns failed: ", "\u8bfb\u53d6\u6559\u5e08\u53d8\u91cf\u5931\u8d25\uff1a"],
  ["Read experiment columns failed: ", "\u8bfb\u53d6\u5b9e\u9a8c\u53d8\u91cf\u5931\u8d25\uff1a"],
  ["Save teacher dataset failed: ", "\u4fdd\u5b58\u6559\u5e08\u6570\u636e\u5931\u8d25\uff1a"],
  ["Save experiment dataset failed: ", "\u4fdd\u5b58\u5b9e\u9a8c\u6570\u636e\u5931\u8d25\uff1a"],
  ["Save teacher features failed: ", "\u4fdd\u5b58\u6559\u5e08\u7279\u5f81\u5931\u8d25\uff1a"],
  ["Save experiment features failed: ", "\u4fdd\u5b58\u5b9e\u9a8c\u7279\u5f81\u5931\u8d25\uff1a"],
  ["Teacher training failed: ", "\u6559\u5e08\u6a21\u578b\u8bad\u7ec3\u5931\u8d25\uff1a"],
  ["Model comparison failed: ", "\u6a21\u578b\u5bf9\u6bd4\u5931\u8d25\uff1a"],
  ["Feature selection failed: ", "\u7279\u5f81\u7b5b\u9009\u5931\u8d25\uff1a"],
  ["GAN failed: ", "GAN \u8fd0\u884c\u5931\u8d25\uff1a"],
  ["Screening failed: ", "\u7b5b\u9009\u5931\u8d25\uff1a"],
  ["Final model failed: ", "\u6700\u7ec8\u6a21\u578b\u8bad\u7ec3\u5931\u8d25\uff1a"],
  ["Optimization failed: ", "\u4f18\u5316\u5931\u8d25\uff1a"],
  ["Test validation failed: ", "\u6d4b\u8bd5\u9a8c\u8bc1\u5931\u8d25\uff1a"],
  ["Merge test failed: ", "\u5408\u5e76\u6d4b\u8bd5\u96c6\u5931\u8d25\uff1a"],
  ["Refresh logs failed: ", "\u5237\u65b0\u65e5\u5fd7\u5931\u8d25\uff1a"],
]);

function translateText(text) {
  if (!text) return text;
  if (!isChineseUI) return text;
  const trimmed = String(text).trim();
  return zhText.get(trimmed) || text;
}

function translateTemplate(template, params = {}) {
  const localized = translateText(template);
  return Object.entries(params).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, value),
    localized,
  );
}

function translateRuntimeText(text) {
  if (!text) return text;
  if (!isChineseUI) return text;
  const exact = translateText(text);
  if (exact !== text) return exact;
  return String(text)
    .replace(/^Session created: (.+)$/u, "\u4f1a\u8bdd\u5df2\u521b\u5efa\uff1a$1")
    .replace(/^(.+) is ready\.$/u, "$1 \u5df2\u51c6\u5907\u5c31\u7eea\u3002")
    .replace(/^(.+) uploaded successfully\.$/u, "$1 \u4e0a\u4f20\u6210\u529f\u3002")
    .replace(/^Loaded (.+) columns from sheet (.+)\.$/u, "\u5df2\u4ece\u5de5\u4f5c\u8868 $2 \u8bfb\u53d6 $1 \u4e2a\u53d8\u91cf\u3002")
    .replace(/^Saved (.+) dataset: (.+) rows, (.+) cols\.$/u, "\u5df2\u4fdd\u5b58 $1 \u6570\u636e\u96c6\uff1a$2 \u884c\uff0c$3 \u5217\u3002")
    .replace(/^Best teacher model: (.+)$/u, "\u6700\u4f73\u6559\u5e08\u6a21\u578b\uff1a$1")
    .replace(/^Best base model: (.+)$/u, "\u6700\u4f73\u57fa\u7840\u6a21\u578b\uff1a$1")
    .replace(/^Selected features: (.+)$/u, "\u5df2\u7b5b\u9009\u7279\u5f81\uff1a$1")
    .replace(/^GAN generated (.+) rows\.$/u, "GAN \u5df2\u751f\u6210 $1 \u884c\u6570\u636e\u3002")
    .replace(/^Screening kept (.+)$/u, "\u7b5b\u9009\u4fdd\u7559 $1")
    .replace(/^Final model: (.+)$/u, "\u6700\u7ec8\u6a21\u578b\uff1a$1")
    .replace(/^Optimization done\. pareto_rows=(.+)\.$/u, "\u4f18\u5316\u5b8c\u6210\uff1aPareto \u7ed3\u679c $1 \u884c\u3002")
    .replace(/^Validation done\. models=(.+)$/u, "\u9a8c\u8bc1\u5b8c\u6210\uff1a\u5171\u6bd4\u8f83 $1");
}

function localizeStaticText(root = document.body) {
  if (!isChineseUI) return;
  document.title = zhText.get("PK-FSL Framework-Based Process Optimization Platform") || document.title;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  nodes.forEach((node) => {
    const value = node.nodeValue;
    const translated = translateText(value);
    if (translated !== value) node.nodeValue = value.replace(value.trim(), translated);
  });
  document.querySelectorAll("[placeholder], [aria-label], [data-image-title], img[alt]").forEach((el) => {
    ["placeholder", "aria-label", "data-image-title", "alt"].forEach((attr) => {
      const value = el.getAttribute(attr);
      const translated = translateText(value);
      if (translated !== value) el.setAttribute(attr, translated);
    });
  });
}

function api(path) {
  const base = (window.__API_BASE__ || "").replace(/\/+$/, "");
  return `${base}/api${path}`;
}

function getSessionId() {
  const sid = $("sessionId")?.textContent?.trim() || "";
  return sid && sid !== "NOT_CREATED" ? sid : "";
}

function mustSession() {
  const sid = getSessionId();
  if (!sid) setStatus("statusSession", "Please create a session first.", "warn");
  return sid;
}

function setSessionId(sessionId) {
  const node = $("sessionId");
  if (node) node.textContent = sessionId || "NOT_CREATED";
}

function setStatus(id, text, tone = "ok") {
  const el = $(id);
  if (!el) return;
  el.textContent = translateRuntimeText(text) || "";
  el.dataset.tone = tone;
}

function formatValue(value, digits = 4) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return "-";
    return Number.isInteger(value) ? String(value) : value.toFixed(digits);
  }
  if (Array.isArray(value)) return value.join(", ");
  return String(value);
}

function metricText(metrics = {}) {
  const parts = [];
  if (metrics.r2 !== undefined && metrics.r2 !== null) parts.push(`R2=${formatValue(metrics.r2)}`);
  if (metrics.rmse !== undefined && metrics.rmse !== null) parts.push(`RMSE=${formatValue(metrics.rmse)}`);
  if (metrics.mae !== undefined && metrics.mae !== null) parts.push(`MAE=${formatValue(metrics.mae)}`);
  return parts.join(", ");
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, options);
  const text = await res.text();
  if (!res.ok) {
    let detail = text || `HTTP ${res.status}`;
    try {
      const parsed = JSON.parse(text);
      detail = parsed.detail || detail;
    } catch {}
    throw new Error(detail);
  }
  return text ? JSON.parse(text) : {};
}

function createFormData(fields) {
  const fd = new FormData();
  Object.entries(fields).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    fd.append(key, value);
  });
  return fd;
}

async function postForm(url, fields) {
  return fetchJson(url, { method: "POST", body: createFormData(fields) });
}

async function postFile(url, file) {
  const fd = new FormData();
  fd.append("file", file);
  return fetchJson(url, { method: "POST", body: fd });
}

function setRoleFile(role, fileName) {
  appState.files[role] = fileName || "";
  const meta = $(`${role}FileMeta`);
  if (meta) meta.textContent = fileName || "NONE";
  const fileNameEl = $(`${role}FileName`);
  if (fileNameEl) fileNameEl.textContent = fileName || translateText("No file chosen");
}

function setRoleSheets(role, sheets) {
  appState.sheets[role] = Array.isArray(sheets) ? sheets : [];
  renderSheetChoices(role);
}

function roleSheetInput(role) {
  return $(`${role}Sheet`);
}

function setSelectedSheet(role, sheetName) {
  const input = roleSheetInput(role);
  if (input) input.value = sheetName || "";
}

function syncSelectedFileName(role) {
  const input = $(`${role}FileInput`);
  const label = $(`${role}FileName`);
  if (!label) return;
  const fileName = input?.files?.[0]?.name || appState.files[role] || "";
  label.textContent = fileName || translateText("No file chosen");
}

function autoPickSheet(role, sheets) {
  if (!Array.isArray(sheets) || !sheets.length) return "";
  const items = sheets.map((raw) => ({ raw, value: String(raw).toLowerCase() }));
  const keys =
    role === "prior"
      ? ["teacher", "prior", "all_prior", "knowledge"]
      : role === "exp"
        ? ["exp", "experiment", "all_exp", "sheet1"]
        : ["test", "valid", "sheet1"];
  for (const key of keys) {
    const match = items.find((item) => item.value.includes(key));
    if (match) return match.raw;
  }
  return sheets[0];
}

function renderChoiceGroup(container, items, selected, onPick, emptyText = "Load data first.") {
  if (!container) return;
  container.innerHTML = "";
  if (!items.length) {
    container.innerHTML = `<div class="muted">${translateText(emptyText)}</div>`;
    return;
  }
  const selectedSet = new Set(Array.isArray(selected) ? selected : selected ? [selected] : []);
  items.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `chip${selectedSet.has(item) ? " is-active" : ""}`;
    button.textContent = item;
    button.title = item;
    button.addEventListener("click", () => onPick(item));
    container.appendChild(button);
  });
}

function renderSheetChoices(role) {
  const container = $(`${role}SheetList`);
  if (!container) return;
  const sheets = appState.sheets[role] || [];
  const selected = roleSheetInput(role)?.value?.trim() || "";
  if (!sheets.length) {
    const hint = role === "test" ? "CSV does not need a sheet." : "Upload Excel to list sheets.";
    container.innerHTML = `<div class="muted">${translateText(hint)}</div>`;
    return;
  }
  renderChoiceGroup(container, sheets, selected, (sheetName) => {
    setSelectedSheet(role, sheetName);
    renderSheetChoices(role);
  });
}

function renderTeacherSelectors() {
  renderChoiceGroup($("priorTargetList"), appState.prior.columns, appState.prior.target, (column) => {
    appState.prior.target = column;
    appState.prior.base = appState.prior.base.filter((item) => item !== column);
    renderTeacherSelectors();
    renderFeatureSummary();
  });

  renderChoiceGroup(
    $("priorBaseList"),
    appState.prior.columns.filter((column) => column !== appState.prior.target),
    appState.prior.base,
    (column) => {
      const index = appState.prior.base.indexOf(column);
      if (index >= 0) appState.prior.base.splice(index, 1);
      else appState.prior.base.push(column);
      renderTeacherSelectors();
      renderFeatureSummary();
    },
  );

  const meta = $("priorColumnsMeta");
  if (meta) {
    meta.textContent = appState.prior.columns.length
      ? translateTemplate("Loaded teacher data columns: {count}.", { count: appState.prior.columns.length })
      : translateText("No columns loaded yet.");
  }
}

function renderExpSelectors() {
  renderChoiceGroup($("expTargetList"), appState.exp.columns, appState.exp.target, (column) => {
    appState.exp.target = column;
    appState.exp.base = appState.exp.base.filter((item) => item !== column);
    appState.exp.aux = appState.exp.aux.filter((item) => item !== column);
    renderExpSelectors();
    renderFeatureSummary();
  });

  const baseCandidates = appState.exp.columns.filter((column) => column !== appState.exp.target);

  renderChoiceGroup($("expBaseList"), baseCandidates, appState.exp.base, (column) => {
    const index = appState.exp.base.indexOf(column);
    if (index >= 0) appState.exp.base.splice(index, 1);
    else appState.exp.base.push(column);
    appState.exp.aux = appState.exp.aux.filter((item) => item !== column);
    renderExpSelectors();
    renderFeatureSummary();
  });

  renderChoiceGroup(
    $("expAuxList"),
    baseCandidates.filter((column) => !appState.exp.base.includes(column)),
    appState.exp.aux,
    (column) => {
      const index = appState.exp.aux.indexOf(column);
      if (index >= 0) appState.exp.aux.splice(index, 1);
      else appState.exp.aux.push(column);
      renderExpSelectors();
      renderFeatureSummary();
    },
  );

  const meta = $("expColumnsMeta");
  if (meta) {
    meta.textContent = appState.exp.columns.length
      ? translateTemplate("Loaded experiment data columns: {count}.", { count: appState.exp.columns.length })
      : translateText("No columns loaded yet.");
  }
}

function renderFeatureSummary() {
  setStatus(
    "statusTeacherFeatures",
    appState.prior.target
      ? translateTemplate("Teacher model: target {target}, base features {count}.", {
          target: appState.prior.target,
          count: appState.prior.base.length,
        })
      : translateText("Teacher variables are not ready."),
    appState.prior.target && appState.prior.base.length ? "ok" : "warn",
  );

  setStatus(
    "statusExpFeatures",
    appState.exp.target
      ? translateTemplate("Experiment model: target {target}, base features {baseCount}, aux features {auxCount}.", {
          target: appState.exp.target,
          baseCount: appState.exp.base.length,
          auxCount: appState.exp.aux.length,
        })
      : translateText("Experiment variables are not ready."),
    appState.exp.target && appState.exp.base.length ? "ok" : "warn",
  );
}

function seedExperimentSelectionFromTeacher() {
  if (!appState.exp.target && appState.prior.target) appState.exp.target = appState.prior.target;
  if (!appState.exp.base.length && appState.prior.base.length) appState.exp.base = [...appState.prior.base];
}

function stopProgress(progressId) {
  const timer = progressTimers.get(progressId);
  if (timer) {
    clearInterval(timer);
    progressTimers.delete(progressId);
  }
}

function setProgress(progressId, value) {
  const root = $(progressId);
  const bar = root?.querySelector(".progress__bar");
  if (!root || !bar) return;
  const clamped = Math.max(0, Math.min(100, Number(value) || 0));
  bar.style.width = `${clamped}%`;
  root.dataset.state = clamped >= 100 ? "done" : clamped > 0 ? "running" : "idle";
}

function resetProgress(progressId) {
  stopProgress(progressId);
  setProgress(progressId, 0);
}

function startProgress(progressId) {
  stopProgress(progressId);
  let current = 8;
  setProgress(progressId, current);
  const timer = window.setInterval(() => {
    current = Math.min(92, current + Math.max(1, (92 - current) * 0.18));
    setProgress(progressId, current);
  }, 180);
  progressTimers.set(progressId, timer);
}

async function runWithProgress(progressId, task) {
  startProgress(progressId);
  try {
    const result = await task();
    stopProgress(progressId);
    setProgress(progressId, 100);
    window.setTimeout(() => resetProgress(progressId), 600);
    return result;
  } catch (error) {
    stopProgress(progressId);
    setProgress(progressId, 0);
    throw error;
  }
}

function setArtifactLink(el, sid, name, label) {
  if (!el) return;
  if (!sid || !name) {
    el.textContent = "";
    el.removeAttribute("href");
    return;
  }
  el.textContent = translateRuntimeText(label || name);
  el.href = api(`/sessions/${sid}/download/${encodeURIComponent(name)}`);
}

function setImg(el, sid, name) {
  if (!el) return;
  if (!sid || !name) {
    el.removeAttribute("src");
    el.dataset.loaded = "false";
    return;
  }
  el.src = `${api(`/sessions/${sid}/download/${encodeURIComponent(name)}`)}?t=${Date.now()}`;
  el.dataset.loaded = "true";
}

function renderTable(containerId, rows) {
  const container = $(containerId);
  if (!container) return;
  if (!Array.isArray(rows) || !rows.length) {
    container.className = "table-wrap empty-hint";
    container.textContent = translateText("No data.");
    return;
  }

  const columns = Array.from(
    rows.reduce((set, row) => {
      Object.keys(row || {}).forEach((key) => set.add(key));
      return set;
    }, new Set()),
  );

  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const tbody = document.createElement("tbody");
  const trHead = document.createElement("tr");
  columns.forEach((column) => {
    const th = document.createElement("th");
    th.textContent = column;
    trHead.appendChild(th);
  });
  thead.appendChild(trHead);

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    columns.forEach((column) => {
      const td = document.createElement("td");
      td.textContent = formatValue(row?.[column]);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  table.appendChild(thead);
  table.appendChild(tbody);
  container.innerHTML = "";
  container.className = "table-wrap";
  container.appendChild(table);
}

function parseIndexValue(value) {
  const text = String(value || "").trim();
  return text === "" ? null : Number(text);
}

function showError(statusId, prefix, error) {
  const message = error?.message || String(error);
  setStatus(statusId, `${prefix}${message}`, "danger");
}

async function createSession() {
  const data = await runWithProgress("progress-session", () => fetchJson(api("/sessions"), { method: "POST" }));
  setSessionId(data.session_id);
  setStatus("statusSession", `Session created: ${data.session_id}`, "ok");
  await refreshLogs();
}

async function useSample(role) {
  const sid = mustSession();
  if (!sid) return;
  const data = await postForm(api(`/sessions/${sid}/use_sample`), { sample_name: "All_Data.xlsx" });
  setRoleFile(role, data.file_name);
  setRoleSheets(role, data.sheets || []);
  const picked = autoPickSheet(role, data.sheets || []);
  if (picked) setSelectedSheet(role, picked);
  renderSheetChoices(role);
  setStatus(role === "prior" ? "statusPrior" : role === "exp" ? "statusExp" : "statusTest", `${data.file_name} is ready.`, "ok");
}

async function uploadRole(role) {
  const sid = mustSession();
  if (!sid) return;
  const file = $(`${role}FileInput`)?.files?.[0];
  if (!file) {
    setStatus(role === "prior" ? "statusPrior" : role === "exp" ? "statusExp" : "statusTest", "Please choose a file first.", "warn");
    return;
  }
  const data = await postFile(api(`/sessions/${sid}/upload`), file);
  setRoleFile(role, data.file_name);
  setRoleSheets(role, data.sheets || []);
  const picked = autoPickSheet(role, data.sheets || []);
  if (picked) setSelectedSheet(role, picked);
  renderSheetChoices(role);
  setStatus(role === "prior" ? "statusPrior" : role === "exp" ? "statusExp" : "statusTest", `${data.file_name} uploaded successfully.`, "ok");
}

async function previewRole(role) {
  const sid = mustSession();
  if (!sid) return;
  if (!appState.files[role]) {
    setStatus(role === "prior" ? "statusPrior" : "statusExp", "Please upload or load a file first.", "warn");
    return;
  }
  const sheet = roleSheetInput(role)?.value?.trim() || "";
  if (!sheet) {
    setStatus(role === "prior" ? "statusPrior" : "statusExp", "Please choose a sheet first.", "warn");
    return;
  }
  const data = await runWithProgress(`progress-${role}`, () =>
    postForm(api(`/sessions/${sid}/load_sheet`), {
      file_name: appState.files[role],
      sheet_name: sheet,
      header_row: $(`${role}Header`)?.value || 0,
      index_col: parseIndexValue($(`${role}Index`)?.value),
    }),
  );
  const columns = Array.isArray(data.columns) ? data.columns.map(String) : [];
  appState[role].columns = columns;
  if (role === "prior") {
    if (!columns.includes(appState.prior.target)) appState.prior.target = "";
    appState.prior.base = appState.prior.base.filter((item) => columns.includes(item));
    renderTeacherSelectors();
  } else {
    if (!columns.includes(appState.exp.target)) appState.exp.target = "";
    appState.exp.base = appState.exp.base.filter((item) => columns.includes(item));
    appState.exp.aux = appState.exp.aux.filter((item) => columns.includes(item));
    seedExperimentSelectionFromTeacher();
    renderExpSelectors();
  }
  renderFeatureSummary();
  setStatus(role === "prior" ? "statusPrior" : "statusExp", `Loaded ${columns.length} columns from sheet ${sheet}.`, "ok");
}

async function setDataset(role) {
  const sid = mustSession();
  if (!sid) return;
  if (!appState.files[role]) {
    setStatus(role === "prior" ? "statusPrior" : "statusExp", "Please upload or load a file first.", "warn");
    return;
  }
  const sheet = roleSheetInput(role)?.value?.trim() || "";
  if (!sheet) {
    setStatus(role === "prior" ? "statusPrior" : "statusExp", "Please choose a sheet first.", "warn");
    return;
  }
  const data = await runWithProgress(`progress-${role}`, () =>
    postForm(api(`/sessions/${sid}/set_dataset`), {
      dataset_role: role,
      file_name: appState.files[role],
      sheet_name: sheet,
      header_row: $(`${role}Header`)?.value || 0,
      index_col: parseIndexValue($(`${role}Index`)?.value),
      na_strategy: $(`${role}NA`)?.value || "keep",
      outlier_strategy: $(`${role}Out`)?.value || "keep",
    }),
  );
  setStatus(role === "prior" ? "statusPrior" : "statusExp", `Saved ${role} dataset: ${formatValue(data.rows)} rows, ${formatValue(data.cols)} cols.`, "ok");
}

async function saveTeacherSelection() {
  const sid = mustSession();
  if (!sid) return;
  if (!appState.prior.target || !appState.prior.base.length) {
    setStatus("statusTeacherFeatures", "Teacher target and base features are required.", "warn");
    return;
  }
  await postForm(api(`/sessions/${sid}/set_features`), {
    target: appState.prior.target,
    base_features: appState.prior.base.join(","),
    aux_features: "",
    random_seed: $("seed")?.value || 42,
  });
  setStatus(
    "statusTeacherFeatures",
    translateTemplate("Teacher features saved. target={target}.", { target: appState.prior.target }),
    "ok",
  );
}

async function saveExperimentSelection() {
  const sid = mustSession();
  if (!sid) return;
  if (!appState.exp.target || !appState.exp.base.length) {
    setStatus("statusExpFeatures", "Experiment target and base features are required.", "warn");
    return;
  }
  await postForm(api(`/sessions/${sid}/set_features`), {
    target: appState.exp.target,
    base_features: appState.exp.base.join(","),
    aux_features: appState.exp.aux.join(","),
    random_seed: $("seed")?.value || 42,
  });
  setStatus(
    "statusExpFeatures",
    translateTemplate("Experiment features saved. target={target}.", { target: appState.exp.target }),
    "ok",
  );
}

async function runTeacher() {
  const sid = mustSession();
  if (!sid) return;
  const data = await runWithProgress("progress-prior", () =>
    postForm(api(`/sessions/${sid}/step3_teacher`), {
      cv_folds: $("teacherCv")?.value || 5,
      n_iter: $("teacherIter")?.value || 30,
    }),
  );
  setImg($("teacherComparePng"), sid, data.compare_png_artifact);
  setImg($("teacherPdp"), sid, data.pdp_png_artifact);
  setArtifactLink($("teacherCsvLink"), sid, data.compare_csv_artifact, "teacher metrics csv");
  setArtifactLink($("teacherCompareCsvLink"), sid, data.compare_csv_artifact, "teacher compare csv");
  setArtifactLink($("teacherModelLink"), sid, data.teacher_model_artifact, "teacher model");
  setStatus("statusTeacher", `Best teacher model: ${data.best_model || "-"}. ${metricText(data.metrics)}`, "ok");
}

async function runCompare() {
  const sid = mustSession();
  if (!sid) return;
  const data = await runWithProgress("progress-compare", () =>
    postForm(api(`/sessions/${sid}/step4_compare_models`), {
      n_iter: $("compareIter")?.value || 30,
    }),
  );
  setImg($("comparePng"), sid, data.png_artifact);
  setArtifactLink($("compareCsvLink"), sid, data.csv_artifact, "base model csv");
  setStatus("statusCompare", `Best base model: ${data.best_model || "-"}. features=${formatValue(data.best_features)}. ${metricText(data.best_row || {})}`, "ok");
}

async function runFeatureSelection() {
  const sid = mustSession();
  if (!sid) return;
  const data = await runWithProgress("progress-compare", () =>
    postForm(api(`/sessions/${sid}/step5_feature_selection`), {
      top_k: $("topK")?.value || 5,
    }),
  );
  setImg($("featSelPng"), sid, data.png_artifact);
  setArtifactLink($("featSelCsvLink"), sid, data.csv_artifact, "feature importance csv");
  setStatus("statusFeatSel", `Selected features: ${formatValue(data.selected_features)}`, "ok");
}

async function runGan() {
  const sid = mustSession();
  if (!sid) return;
  const data = await runWithProgress("progress-gan", () =>
    postForm(api(`/sessions/${sid}/step6_gan`), {
      epochs: $("ganEpochs")?.value || 500,
      n_generate: $("ganN")?.value || 200,
      latent_dim: $("ganLatent")?.value || 32,
      batch_size: $("ganBatch")?.value || 32,
    }),
  );
  setImg($("ganViolin"), sid, data.target_violin_png_artifact);
  setImg($("ganLossPng"), sid, data.loss_png_artifact);
  setArtifactLink($("ganCsvLink"), sid, data.gan_csv_artifact, "gan data csv");
  setArtifactLink($("ganLossCsvLink"), sid, data.loss_csv_artifact, "gan loss csv");
  setStatus("statusGan", `GAN generated ${formatValue(data.rows_generated)} rows.`, "ok");
}

async function runScreen() {
  const sid = mustSession();
  if (!sid) return;
  const data = await runWithProgress("progress-screen", () =>
    postForm(api(`/sessions/${sid}/step7_screen`), {
      pred_abs_tol: $("screenTol")?.value || 0.05,
      max_keep: $("screenKeep")?.value || 200,
    }),
  );
  setImg($("screenPng"), sid, data.png_artifact);
  setArtifactLink($("screenCsvLink"), sid, data.csv_artifact, "screened gan csv");
  setStatus("statusScreen", `Screening kept ${formatValue(data.rows_kept)} rows. mean_abs_err=${formatValue(data.stats?.abs_err_mean)}.`, "ok");
}

async function runFinal() {
  const sid = mustSession();
  if (!sid) return;
  const data = await runWithProgress("progress-final", () =>
    postForm(api(`/sessions/${sid}/step8_final`), {
      alpha: $("alpha")?.value || 0.3,
      method: $("distillMethod")?.value || "soft_label",
    }),
  );
  setImg($("finalComparePng"), sid, data.compare_png_artifact);
  setArtifactLink($("finalModelLink"), sid, data.final_model_artifact, "final model");
  setArtifactLink($("finalCsvLink"), sid, data.compare_csv_artifact, "final compare csv");
  setStatus("statusFinal", `Final model: ${data.best_model || data.final_model || "-"}. ${metricText(data.best_metrics || data.best_row || {})}`, "ok");
}

async function runOptimize() {
  const sid = mustSession();
  if (!sid) return;
  const data = await runWithProgress("progress-opt", () =>
    postForm(api(`/sessions/${sid}/step9_optimize`), {
      n_samples: $("optN")?.value || 3000,
      objective_mode: $("optMode")?.value || "maximize_target_minimize_l2",
      cost_formula: $("costFormula")?.value || "",
    }),
  );
  setImg($("optPng"), sid, data.pareto_png_artifact);
  setArtifactLink($("optParetoCsvLink"), sid, data.pareto_csv_artifact, "pareto csv");
  setArtifactLink($("optAllCsvLink"), sid, data.all_csv_artifact, "all samples csv");
  setStatus("statusOpt", `Optimization done. pareto_rows=${formatValue(data.pareto_rows)}.`, "ok");
}

async function runTest() {
  const sid = mustSession();
  if (!sid) return;
  if (!appState.files.test) {
    setStatus("statusTest", "Please upload or load a test file first.", "warn");
    return;
  }
  const payload = { file_name: appState.files.test };
  const sheet = $("testSheet")?.value?.trim() || "";
  if (sheet) payload.sheet_name = sheet;
  const data = await runWithProgress("progress-test", () => postForm(api(`/sessions/${sid}/step10_test`), payload));
  setImg($("testComparePng"), sid, data.summary_png_artifact);
  setArtifactLink($("testPredCsvLink"), sid, data.prediction_csv_artifact, "prediction csv");
  setArtifactLink($("testSummaryCsvLink"), sid, data.summary_csv_artifact, "summary csv");
  renderTable("testSummaryTable", data.summary_preview);
  renderTable("testPredictionTable", data.prediction_preview);
  const bestName = [data.best_model?.feature_set, data.best_model?.model].filter(Boolean).join(" / ");
  setStatus("statusTest", `Validation done. models=${formatValue(data.models)}. best=${bestName}. ${metricText(data.metrics || {})}`, "ok");
}

async function mergeTestIntoExperiment() {
  const sid = mustSession();
  if (!sid) return;
  const choice = document.querySelector('input[name="mergeTest"]:checked')?.value || "no";
  if (choice !== "yes") {
    setStatus("statusMergeTest", "Merge skipped because option is set to No.", "warn");
    return;
  }
  const data = await postForm(api(`/sessions/${sid}/step11_next_iter`), {});
  setStatus(
    "statusMergeTest",
    translateTemplate("Experiment dataset updated. iteration={iteration}, rows={rows}.", {
      iteration: formatValue(data.iteration),
      rows: formatValue(data.exp_rows),
    }),
    "ok",
  );
  setStatus(
    "statusExp",
    translateTemplate("Experiment dataset now has {rows} rows.", {
      rows: formatValue(data.exp_rows),
    }),
    "ok",
  );
}

async function refreshLogs() {
  const sid = mustSession();
  if (!sid) return;
  const data = await fetchJson(api(`/sessions/${sid}/logs`));
  if ($("outLogs")) $("outLogs").textContent = data.text || "";
}

function openLightboxFor(targetId, titleText) {
  const source = $(targetId);
  if (!source?.src) return;
  if ($("lightboxImage")) $("lightboxImage").src = source.src;
  if ($("lightboxTitle")) $("lightboxTitle").textContent = titleText || "Image Preview";
  if ($("imageLightbox")) $("imageLightbox").hidden = false;
  document.body.style.overflow = "hidden";
}

function closeLightbox() {
  if ($("imageLightbox")) $("imageLightbox").hidden = true;
  if ($("lightboxImage")) $("lightboxImage").removeAttribute("src");
  document.body.style.overflow = "";
}

function bindLightbox() {
  document.querySelectorAll(".image-button").forEach((button) => {
    button.addEventListener("click", () => openLightboxFor(button.dataset.imageTarget, button.dataset.imageTitle));
  });
  $("lightboxClose")?.addEventListener("click", closeLightbox);
  $("lightboxCloseButton")?.addEventListener("click", closeLightbox);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeLightbox();
  });
}

function bindFileInputs() {
  ["prior", "exp", "test"].forEach((role) => {
    const input = $(`${role}FileInput`);
    input?.addEventListener("change", () => syncSelectedFileName(role));
    syncSelectedFileName(role);
  });

  document.querySelectorAll("[data-file-trigger]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = $(button.dataset.fileTrigger);
      target?.click();
    });
  });
}

function bindActions() {
  $("btnNewSession")?.addEventListener("click", async () => {
    try { await createSession(); } catch (error) { showError("statusSession", "Create session failed: ", error); }
  });
  $("btnLoadPriorSample")?.addEventListener("click", async () => {
    try { await useSample("prior"); } catch (error) { showError("statusPrior", "Load teacher sample failed: ", error); }
  });
  $("btnLoadExpSample")?.addEventListener("click", async () => {
    try { await useSample("exp"); } catch (error) { showError("statusExp", "Load experiment sample failed: ", error); }
  });
  $("btnLoadTestSample")?.addEventListener("click", async () => {
    try { await useSample("test"); } catch (error) { showError("statusTest", "Load test sample failed: ", error); }
  });
  $("btnUploadPrior")?.addEventListener("click", async () => {
    try { await uploadRole("prior"); } catch (error) { showError("statusPrior", "Upload teacher file failed: ", error); }
  });
  $("btnUploadExp")?.addEventListener("click", async () => {
    try { await uploadRole("exp"); } catch (error) { showError("statusExp", "Upload experiment file failed: ", error); }
  });
  $("btnUploadTest")?.addEventListener("click", async () => {
    try { await uploadRole("test"); } catch (error) { showError("statusTest", "Upload test file failed: ", error); }
  });
  $("btnPreviewPrior")?.addEventListener("click", async () => {
    try { await previewRole("prior"); } catch (error) { showError("statusPrior", "Read teacher columns failed: ", error); }
  });
  $("btnPreviewExp")?.addEventListener("click", async () => {
    try { await previewRole("exp"); } catch (error) { showError("statusExp", "Read experiment columns failed: ", error); }
  });
  $("btnSetPrior")?.addEventListener("click", async () => {
    try { await setDataset("prior"); } catch (error) { showError("statusPrior", "Save teacher dataset failed: ", error); }
  });
  $("btnSetExp")?.addEventListener("click", async () => {
    try { await setDataset("exp"); } catch (error) { showError("statusExp", "Save experiment dataset failed: ", error); }
  });
  $("btnSaveTeacherSelection")?.addEventListener("click", async () => {
    try { await saveTeacherSelection(); } catch (error) { showError("statusTeacherFeatures", "Save teacher features failed: ", error); }
  });
  $("btnSaveExpSelection")?.addEventListener("click", async () => {
    try { await saveExperimentSelection(); } catch (error) { showError("statusExpFeatures", "Save experiment features failed: ", error); }
  });
  $("btnSetFeatures")?.addEventListener("click", async () => {
    try { await saveExperimentSelection(); } catch (error) { showError("statusExpFeatures", "Save experiment features failed: ", error); }
  });
  $("btnTeacher")?.addEventListener("click", async () => {
    try { await runTeacher(); await refreshLogs(); } catch (error) { showError("statusTeacher", "Teacher training failed: ", error); }
  });
  $("btnCompare")?.addEventListener("click", async () => {
    try { await runCompare(); await refreshLogs(); } catch (error) { showError("statusCompare", "Model comparison failed: ", error); }
  });
  $("btnFeatSel")?.addEventListener("click", async () => {
    try { await runFeatureSelection(); await refreshLogs(); } catch (error) { showError("statusFeatSel", "Feature selection failed: ", error); }
  });
  $("btnGan")?.addEventListener("click", async () => {
    try { await runGan(); await refreshLogs(); } catch (error) { showError("statusGan", "GAN failed: ", error); }
  });
  $("btnScreen")?.addEventListener("click", async () => {
    try { await runScreen(); await refreshLogs(); } catch (error) { showError("statusScreen", "Screening failed: ", error); }
  });
  $("btnFinal")?.addEventListener("click", async () => {
    try { await runFinal(); await refreshLogs(); } catch (error) { showError("statusFinal", "Final model failed: ", error); }
  });
  $("btnOpt")?.addEventListener("click", async () => {
    try { await runOptimize(); await refreshLogs(); } catch (error) { showError("statusOpt", "Optimization failed: ", error); }
  });
  $("btnTest")?.addEventListener("click", async () => {
    try { await runTest(); await refreshLogs(); } catch (error) { showError("statusTest", "Test validation failed: ", error); }
  });
  $("btnMergeTest")?.addEventListener("click", async () => {
    try { await mergeTestIntoExperiment(); await refreshLogs(); } catch (error) { showError("statusMergeTest", "Merge test failed: ", error); }
  });
  $("btnLogs")?.addEventListener("click", async () => {
    try { await refreshLogs(); } catch (error) { showError("statusSession", "Refresh logs failed: ", error); }
  });
}

function bootstrap() {
  localizeStaticText();
  renderSheetChoices("prior");
  renderSheetChoices("exp");
  renderSheetChoices("test");
  renderTeacherSelectors();
  renderExpSelectors();
  renderFeatureSummary();
  bindActions();
  bindLightbox();
  bindFileInputs();
}

document.addEventListener("DOMContentLoaded", bootstrap);
