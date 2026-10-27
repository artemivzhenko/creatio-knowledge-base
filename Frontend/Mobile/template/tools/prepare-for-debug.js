import { readFileSync } from 'fs';
import { copyFile } from 'fs/promises';
import { resolve, dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';
import { updateExcludedModules } from './common.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

const config = JSON.parse(readFileSync(resolve(__dirname, '../creatio-mobile-config.json'), 'utf8'));

function injectDebugSdk() {
	try {
		execSync(`cpx "${config['mobileAppSrcFolder']}/ts/out/sdk.debug.js" "${config['mobileAppSrcFolder']}/flutter_creatio/assets/js" -v`, { stdio: 'inherit' });
		console.log(`Debug SDK injected successfully`);
	} catch (error) {
		console.error(`Error executing injection of debug SDK:`, error);
		process.exit(1);
	}
}

async function injectModule() {
	const sourcePath = join('./out/mobile', config['moduleName'], 'main.debug.js');
	const destPath = join(config['mobileAppSrcFolder'], 'flutter_creatio/assets/js', 'dev-module.js');

	try {
		await copyFile(sourcePath, destPath);
		console.log(`Successfully copied ${sourcePath} to ${destPath}`);
	} catch (error) {
		console.error('Error copying file:', error);
		process.exit(1);
	}
}

await injectModule();
injectDebugSdk();
updateExcludedModules(config['moduleName'], `${config['mobileAppSrcFolder']}/flutter_creatio/assets/js/excluded-modules.json`);
