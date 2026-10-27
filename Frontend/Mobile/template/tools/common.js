import { existsSync, readFileSync, writeFileSync } from 'fs';

export function updateExcludedModules(moduleName, excludedModulesPath) {
	let excludedModules = {};

	if (existsSync(excludedModulesPath)) {
		excludedModules = JSON.parse(readFileSync(excludedModulesPath, 'utf8'));
	}

	if (!excludedModules[moduleName]) {
		excludedModules[moduleName] = ['main.js', 'main.debug.js'];
		writeFileSync(excludedModulesPath, JSON.stringify(excludedModules, null, 2));
		console.log(`Updated excluded-modules.json with ${moduleName}`);
	} else {
		console.log(`${moduleName} already exists in excluded-modules.json, skip`);
	}
}
