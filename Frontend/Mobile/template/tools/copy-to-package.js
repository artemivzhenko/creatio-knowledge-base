/**
 * Copies the webpack output (main.js) into the Creatio package file content:
 *   <targetPackagePath>/Files/src/mobile/<moduleName>/main.js
 *
 * The folder name MUST equal the bootstrapped module name (see src/index.ts),
 * otherwise the mobile app will not pick the remote module up.
 */
import { copyFileSync, existsSync, mkdirSync, readFileSync } from 'fs';
import { dirname, join, resolve } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const config = JSON.parse(readFileSync(resolve(__dirname, '../creatio-mobile-config.json'), 'utf8'));

const moduleName = config.moduleName;
const source = join(__dirname, '..', 'out', 'mobile', moduleName, 'main.js');
const targetDir = resolve(__dirname, '..', config.targetPackagePath, 'Files', 'src', 'mobile', moduleName);
const target = join(targetDir, 'main.js');

if (!existsSync(source)) {
	console.error(`Build output not found: ${source}\nRun "npm run build" first.`);
	process.exit(1);
}

mkdirSync(targetDir, { recursive: true });
copyFileSync(source, target);
console.log(`Copied ${source}\n     -> ${target}`);
console.log('Next: load the package into the runtime (clio pkg-to-db / "Update packages from file system") and re-sync the mobile app.');
