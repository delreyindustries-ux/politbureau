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
mkdirSync(out, { recursive: true });
let n = 0;
for (const f of readdirSync(dir)) {
  if (!f.endsWith(".svg")) continue;
  const svg = readFileSync(join(dir, f));
  const png = new Resvg(svg, { fitTo: { mode: "width", value: 960 } }).render().asPng();
  writeFileSync(join(out, f.replace(".svg", ".png")), png);
  n++;
}
console.log(`${n} banderes -> ${out}`);
