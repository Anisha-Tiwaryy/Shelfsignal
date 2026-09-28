const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType,
  AlignmentType, BorderStyle, ShadingType, ExternalHyperlink, LevelFormat,
} = require("docx");

const FONT = "Calibri";
const A = "/home/claude/shelfsignal/analysis/";
const t = (text, o = {}) => new TextRun({ text, font: FONT, size: o.size || 21, bold: o.bold, italics: o.italics, color: o.color });
const p = (runs, o = {}) => new Paragraph({ children: typeof runs === "string" ? [t(runs)] : runs, spacing: { after: o.after ?? 100, before: o.before ?? 0, line: 276 }, alignment: o.align });
const h = (text) => new Paragraph({ children: [t(text, { bold: true, size: 26, color: "111827" })], spacing: { before: 220, after: 90 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "D1D5DB", space: 2 } } });
const b = (runs) => new Paragraph({ numbering: { reference: "dots", level: 0 }, spacing: { after: 60, line: 264 }, children: typeof runs === "string" ? [t(runs)] : runs });
const link = (text, url) => new ExternalHyperlink({ link: url, children: [new TextRun({ text, font: FONT, size: 21, color: "1D4ED8", underline: {} })] });
const img = (file, w, hgt) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
  children: [new ImageRun({ type: "png", data: fs.readFileSync(A + file), transformation: { width: w, height: hgt } })] });
const cap = (text) => p([t(text, { italics: true, size: 18, color: "6B7280" })], { align: AlignmentType.CENTER, after: 140 });

const border = { style: BorderStyle.SINGLE, size: 4, color: "D1D5DB" };
function table(header, rows, widths) {
  const total = widths.reduce((a, c) => a + c, 0);
  const cell = (text, head) => new TableCell({
    width: { size: text.w, type: WidthType.DXA },
    borders: { top: border, bottom: border, left: border, right: border },
    shading: head ? { type: ShadingType.CLEAR, fill: "F3F4F6", color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: [t(text.s, { bold: head, size: 19 })] })],
  });
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [header, ...rows].map((r, i) => new TableRow({ children: r.map((s, j) => cell({ s, w: widths[j] }, i === 0)) })),
  });
}
const callout = (runs) => new Table({
  width: { size: 9360, type: WidthType.DXA }, columnWidths: [9360],
  rows: [new TableRow({ children: [new TableCell({
    width: { size: 9360, type: WidthType.DXA },
    borders: { top: border, bottom: border, right: border, left: { style: BorderStyle.SINGLE, size: 24, color: "DC2626" } },
    shading: { type: ShadingType.CLEAR, fill: "FEF2F2", color: "auto" },
    margins: { top: 120, bottom: 120, left: 200, right: 200 },
    children: [new Paragraph({ children: runs, spacing: { line: 276 } })],
  })] })],
});

const children = [
  p([t("CASE STUDY  |  Software Full Stack Development Intern application, Infilect", { size: 18, color: "6B7280", bold: true })], { after: 60 }),
  p([t("The Rs 10 Packet Problem", { bold: true, size: 44 })], { after: 40 }),
  p([t("ShelfSignal: a new data product hiding in shelf photos, built as a working prototype", { size: 24, color: "374151" })], { after: 60 }),
  p([t("Anisha Tiwary  |  Bengaluru  |  ", { size: 19, color: "6B7280" }), link("github.com/Anisha-Tiwaryy/shelfsignal", "https://github.com/Anisha-Tiwaryy/shelfsignal")], { after: 180 }),

  callout([t("The idea in one line: ", { bold: true }), t("every shelf photo Infilect processes already records a SKU, a shelf price and a pack weight. Put millions of those rows side by side across brands, stores and months, and they reveal things no single brand's dashboard shows: which products are quietly shrinking, how fast new launches really spread, and how much inflation is hiding inside smaller packs. Infilect already sells tools. This would be a data product.")]),

  h("1. What I noticed"),
  p("A Rs 10 packet of biscuits cannot get more expensive. The price is printed on the pack, shoppers know it by heart, and a Rs 11 packet would feel wrong. So when input costs rise, the price stays and the pack gets smaller. Indian business press has been reporting exactly this across FMCG in the last two years, with brands shrinking low-price packs to hold their price points."),
  p("That creates a blind spot. Anyone tracking shelf prices sees a flat line. The shopper is paying more per gram. The only record of the change is the weight printed on the pack, and the only people photographing that pack in thousands of stores every week are field teams using image recognition."),
  img("fig_rs10_pack.png", 560, 206),
  cap("One Rs 10 biscuit pack in one store (simulated): price never moves, the pack drops from 225g to 200g, price per gram rises 12.5%."),

  h("2. Three signals nobody is selling yet"),
  table(["Signal", "What it shows", "Who would pay for it (hypothesis)"], [
    ["Shrinkflation watch", "Which SKUs shrank while the shelf price held, where, since when, in what share of stores", "Competing brands' strategy teams; FMCG equity analysts; consumer-protection and media"],
    ["Launch velocity", "Days for a new product to reach 25% and 50% of stores, by city and channel", "Brand teams benchmarking their own launch against rivals; distributors"],
    ["Hidden inflation index", "Pack-price index vs price-per-gram index per city, plus sudden city price shocks", "Economists, investors, retailers planning price strategy"],
  ], [2200, 3900, 3260]),
  p([t("These are hypotheses to validate, not claims. The point is that the raw material already exists inside the image pipeline and is currently used to answer one client's questions about its own stores.", { italics: true, color: "4B5563", size: 19 })], { before: 80 }),

  h("3. What I built"),
  p("A full stack prototype in the same stack as the internship role, running on simulated shelf-audit data with known events planted in it, so every detector can be scored against the truth instead of eyeballed."),
  table(["Layer", "What it does"], [
    ["Data generator", "90 stores in 5 cities, 40 SKUs, 12 months, 78,028 shelf observations. Plants 6 shrinkflation events (2 on fixed Rs 10/20 packs), 2 proportional resizes, 1 upsize, 2 plain price hikes, 4 launches, 1 city price shock, and 1.5% OCR misreads of pack weight"],
    ["Django + DRF + PostgreSQL", "Models for stores, SKUs, observations and signals; 8 REST endpoints; token auth on writes; filters and pagination"],
    ["Celery + Redis", "POST /api/runs/ returns 202 and queues a background detector run; the dashboard polls its status. Full scan of 78,028 rows: about 1.5 seconds"],
    ["Detectors (pandas)", "Pack-change detection with a persistence filter that ignores one-off OCR misreads; launch adoption curves; Jevons price index on pack price and on price per gram; shock detection"],
    ["GenAI brief", "Sends only detector numbers (no images, no store names) to the Gemini API to write a weekly brief; falls back to a template when no key is set and says which one wrote it"],
    ["React + TypeScript", "Dashboard with KPIs, pack-change table, index chart and launch curves; typed API client"],
    ["Quality", "18 pytest tests (unit + API integration on Postgres), GitHub Actions CI with a Postgres service, stress-test script"],
  ], [2400, 6960]),
  p("", { after: 60 }),
  img("dashboard_crop.png", 520, 451),
  cap("The React dashboard running against the Django API after a background detector run."),

  h("4. Did it work?"),
  table(["Check against planted truth", "Result"], [
    ["Shrinkflation events found", "6 of 6, zero false positives"],
    ["Pack changes classified correctly (shrinkflation vs resize vs upsize)", "9 of 9"],
    ["Plain price hikes wrongly flagged as pack changes", "0 of 2"],
    ["City price shock (Kolkata, May 2026)", "Found, no false alarms in other cities"],
    ["Launch speed (days to reach 50% of stores)", "About 10 days late for 3 launches, 6 early for 1; lag comes from 14-day visit gaps"],
  ], [6000, 3360]),
  p("", { after: 60 }),
  img("fig_hidden_inflation.png", 560, 227),
  cap("Kolkata: what shoppers pay per gram (red) pulls away from what pack-price tracking sees (blue). Every city ends about 3 index points apart."),

  h("5. Where it breaks, and what the real version needs"),
  p("I stress-tested the detectors across 3 random seeds per setting instead of reporting only the clean run:"),
  table(["Setting", "Shrinkflation recall", "Precision", "False pack signals", "Launch error"], [
    ["10 to 90 stores", "1.0", "1.0", "0", "5 to 7 days"],
    ["OCR misreads 1.5% to 10%", "1.0", "1.0", "0", "7 to 8 days"],
    ["OCR misreads 20%", "1.0", "0.92", "1.7 per run", "5 days"],
    ["Visits every 28 days", "1.0", "0.95", "0", "16 days"],
  ], [2560, 1800, 1300, 1900, 1800]),
  p("", { after: 40 }),
  b([t("OCR quality is the ceiling. ", { bold: true }), t("At 20% misreads, repeated errors survive the persistence filter. In production the pack-weight read would come from Infilect's own vision models, so its confidence score should gate what reaches the detectors.")]),
  b([t("Data rights come first. ", { bold: true }), t("Images belong to client relationships. A product like this only works on aggregated signals, with minimum-store thresholds so no single client's data can be reverse engineered, and with client opt-in.")]),
  b([t("Coverage bias. ", { bold: true }), t("Stores visited for one brand are not a random sample of the market; indices need weighting by channel and city.")]),
  b([t("My own blind spot. ", { bold: true }), t("The detectors were scored on a world I designed. Real shelves will be messier: relabelled SKUs, regional pack variants, partial shelf photos.")]),

  h("6. What I would do as an intern at Infilect"),
  b([t("Week 1 to 4: ", { bold: true }), t("learn the Django/DRF codebase and ship small features and bug fixes with tests, the core of the role.")]),
  b([t("Reusable synthetic shelf fixtures. ", { bold: true }), t("The generator I wrote plants known events on purpose. The same idea gives engineering a realistic, labelled test dataset for API and pipeline integration tests without touching client data.")]),
  b([t("A pack-weight confidence check. ", { bold: true }), t("A small background job that flags SKUs whose recognised pack weight flips between visits, catching OCR drift before it reaches client reports.")]),
  b([t("A ShelfSignal pilot, if the team finds it worth exploring. ", { bold: true }), t("One category, aggregated data, one internal report, and an honest read on whether the signals hold up on real shelves.")]),

  h("Honest limits"),
  p("All data here is simulated and every brand and SKU name is invented. Figures describe how the prototype performs on that data, not facts about any real market. The Gemini path is wired but was not run (no API key in the build environment); the brief in the screenshot comes from the template fallback, which the app labels as such."),
  p([t("Code, tests and the stress test: ", { bold: true }), link("github.com/Anisha-Tiwaryy/shelfsignal", "https://github.com/Anisha-Tiwaryy/shelfsignal")]),
];

const doc = new Document({
  creator: "Anisha Tiwary", title: "The Rs 10 Packet Problem",
  styles: { default: { document: { run: { font: FONT, size: 21 } } } },
  numbering: { config: [{ reference: "dots", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 240 } } } }] }] },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, bottom: 1080, left: 1440, right: 1440 } } }, children }],
});
Packer.toBuffer(doc).then(buf => { fs.writeFileSync("/home/claude/shelfsignal/docs/Anisha_Tiwary_Infilect_Case_Study_ShelfSignal.docx", buf); console.log("ok"); });
