/**
 * Prints the public surface of the installed @creatio/mobile-common typings.
 * Use it to confirm which SDK classes/enums are available in the version you
 * actually installed before writing handler code against them.
 *
 *   npm run sdk:surface              -- everything
 *   npm run sdk:surface -- barcode   -- only declarations matching /barcode/i
 */
import { readFileSync, existsSync } from 'fs';
import { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const filter = process.argv[2] ? new RegExp(process.argv[2], 'i') : null;

for (const pkg of ['@creatio/mobile-common', '@creatio/base']) {
	const dts = resolve(__dirname, '..', 'node_modules', pkg, 'index.d.ts');
	if (!existsSync(dts)) {
		console.log(`\n### ${pkg}: not installed (run npm install)`);
		continue;
	}
	const version = JSON.parse(readFileSync(resolve(__dirname, '..', 'node_modules', pkg, 'package.json'), 'utf8')).version;
	console.log(`\n### ${pkg}@${version}`);
	const decl = /^export declare (?:abstract )?(class|interface|enum|type|function|const) ([A-Za-zɵ_$][\w$]*)/;
	for (const line of readFileSync(dts, 'utf8').split(/\r?\n/)) {
		const m = decl.exec(line);
		if (!m) continue;
		const name = m[2].replace(/^ɵ/, '');
		if (filter && !filter.test(name)) continue;
		console.log(`  ${m[1].padEnd(9)} ${name}`);
	}
}
