// Passa les banderes SVG de flag-icons (MIT, github.com/lipis/flag-icons) a PNG,
// per fer el mapamundi de banderes del globus (geo/world.py flags).
//   npm install flag-icons@7.2.3 @resvg/resvg-js@2.6.2   (en una carpeta a part)
//   node scripts/flags.mjs <carpeta amb node_modules> <carpeta de sortida>
import { readdirSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { createRequire } from "node:module";

const [mods, out] = process.argv.slice(2);
const require = createRequire(join(mods, "package.json"));
const { Resvg } = require("@resvg/resvg-js");
const dir = join(mods, "node_modules", "flag-icons", "flags", "4x3");

// La bandera dels EUA de flag-icons dibuixa les 50 estrelles amb <marker>, que
// resvg no pinta: el canto sortia tot blau (09/11/2026). Aqui es dibuixen una a
// una, amb les mides oficials (4 USC 1; Executive Order 10834) adaptades al 4:3.
function usFlag() {
  const W = 640, H = 480, s = H / 13;              // 13 franges
  const cw = 364.8, ch = 7 * s;                     // canto: 7 franges d'alt
  const G = cw / 12, E = ch / 10, r = (0.0616 * H) / 2;
  const star = (cx, cy) => {
    const pts = [];
    for (let i = 0; i < 10; i++) {
      const a = -Math.PI / 2 + (i * Math.PI) / 5;
      const k = i % 2 ? r * 0.382 : r;              // radi interior del pentagrama
      pts.push(`${(cx + k * Math.cos(a)).toFixed(2)},${(cy + k * Math.sin(a)).toFixed(2)}`);
    }
    return `<polygon points="${pts.join(" ")}"/>`;
  };
  let stars = "";
  for (let row = 1; row <= 9; row++) {
    const odd = row % 2 === 1;
    for (let k = 1; k <= (odd ? 6 : 5); k++) stars += star((odd ? 2 * k - 1 : 2 * k) * G, row * E);
  }
  let stripes = "";
  for (let i = 1; i < 13; i += 2) stripes += `<rect y="${(i * s).toFixed(2)}" width="${W}" height="${s.toFixed(2)}"/>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}">` +
    `<rect width="${W}" height="${H}" fill="#b22234"/><g fill="#fff">${stripes}</g>` +
    `<rect width="${cw}" height="${ch.toFixed(2)}" fill="#3c3b6e"/><g fill="#fff">${stars}</g></svg>`;
}
const OVERRIDE = { "us.svg": usFlag(), "um.svg": usFlag() };   // UM = mateixa bandera
mkdirSync(out, { recursive: true });
let n = 0;
for (const f of readdirSync(dir)) {
  if (!f.endsWith(".svg")) continue;
  const svg = OVERRIDE[f] ?? readFileSync(join(dir, f));
  const png = new Resvg(svg, { fitTo: { mode: "width", value: 960 } }).render().asPng();
  writeFileSync(join(out, f.replace(".svg", ".png")), png);
  n++;
}
console.log(`${n} banderes -> ${out}`);
