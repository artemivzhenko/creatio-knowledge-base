// --- How to create a Mobile SDK remote module with custom request handlers ---
// A Creatio Mobile (8.2+) remote module is a TypeScript + webpack project whose
// bundle (main.js) is shipped inside a package as file content:
//   <Package>/Files/src/mobile/<ModuleName>/main.js
// The mobile app loads it on synchronization and registers the handlers declared
// in @CrtModule. This recipe is the whole project: split it at the
// "===== file:" markers - or copy the ready folder next to this file,
// Frontend/Mobile/template/ (the same content as real files, with a README),
// and rename UsrMobileModule. tsconfig.json and webpack.config.js are the
// official ts_sdk_template_module.zip from Academy, unchanged.
//
// Traps, in the order they bite:
// - Three names must be identical or the module silently never loads:
//   `moduleName` in creatio-mobile-config.json, the folder under Files/src/mobile/
//   and the first argument of bootstrapCrtModule(). Nothing reports the mismatch.
// - The `EnableMobileSDK` feature must be on for ALL users. The toggle on the
//   features page adds a rule for the current user only, which does not reach
//   the account the device logs in with.
// - `scopes` in @CrtRequestHandler are Freedom UI mobile page schema names
//   (`SchemaType: "MobileSchema"`, e.g. UsrMyEntity_MobileFormPage). An empty
//   array fires on every page of the app - never ship that. Classic mobile
//   schemas (`settingsType: "RecordPage"`, no viewConfigDiff) cannot host
//   handlers at all. What the platform really puts into request.scopes is
//   undocumented: confirm it once with UsrScopeProbeRequestHandler below.
// - The page attribute is NOT the column: the mobile designer generates a
//   suffix (`PDS_UsrField_a1b2c3d`). That generated name is what arrives in
//   request.attributeName and what $context.getAttribute() expects. Re-creating
//   the field changes the suffix.
// - Pass the request on with `return this.next?.handle(request)` unless you
//   fully replaced the platform behaviour. Calling next after handling a
//   platform request yourself runs the stock logic a second time.
// - `clicked.params` on mobile pages is undocumented: a handler must work when
//   the request arrives without parameters.
// - `@creatio/mobile-common` is a webpack external (`crtSdk`). Any other runtime
//   dependency has to fit inside main.js.
// - After `npm run build:deploy` and loading the package, re-synchronize the
//   app (Settings -> Synchronization), or the device keeps the old main.js.
//   Debug with `npm run build:inject-on-device` (adb) and chrome://inspect.
//   Logger.console() is the only logging that reaches the console.
// - No unit tests: the SDK only runs inside the mobile runtime. Verification is
//   a clean build plus a run on a device or emulator.

// ===== file: creatio-mobile-config.json =====
// {
//   "moduleName": "UsrMobileModule",
//   "mobileAppSrcFolder": "../",
//   "targetPackagePath": "../../packages/UsrPackage"
// }

// ===== file: package.json =====
// {
//   "name": "usr-mobile-module",
//   "version": "0.1.0",
//   "type": "module",
//   "private": true,
//   "scripts": {
//     "build": "webpack",
//     "deploy": "node ./tools/copy-to-package.js",
//     "build:deploy": "webpack && npm run deploy",
//     "inject-on-device": "node ./tools/inject-on-device.js",
//     "build:inject-on-device": "webpack && npm run inject-on-device"
//   },
//   "dependencies": {
//     "@creatio/mobile-common": "latest"
//   },
//   "devDependencies": {
//     "ts-loader": "^9.4.2",
//     "tslib": "^2.5.0",
//     "typescript": "^5.0.4",
//     "webpack": "^5.82.1",
//     "webpack-cli": "^5.1.1"
//   }
// }

// ===== file: tsconfig.json =====
// {
//   "compileOnSave": false,
//   "compilerOptions": {
//     "module": "ES2020",
//     "resolveJsonModule": true,
//     "esModuleInterop": true,
//     "target": "es2019",
//     "lib": ["es2020"],
//     "allowJs": true,
//     "moduleResolution": "node",
//     "sourceMap": true,
//     "sourceRoot": "src",
//     "outDir": "./out/",
//     "declaration": true,
//     "strict": true,
//     "experimentalDecorators": true,
//     "emitDecoratorMetadata": true
//   },
//   "include": ["src/**/*.ts"],
//   "exclude": ["node_modules", "out", "**/*.spec.ts", "**/*.test.ts"]
// }

// ===== file: webpack.config.js =====
// import path from "path";
// import { fileURLToPath } from 'url';
// import { readFileSync } from 'fs';
//
// const __filename = fileURLToPath(import.meta.url);
// const __dirname = path.dirname(__filename);
//
// const creatioMobileConfig = JSON.parse(
//   readFileSync(path.resolve(__dirname, 'creatio-mobile-config.json'), 'utf8')
// );
//
// const baseConfig = {
//     mode: 'development',
//     entry: './src/index.ts',
//     output: {
//         path: path.resolve('out/mobile', creatioMobileConfig.moduleName),
//         iife: true,
//         globalObject: 'this'
//     },
//     // The SDK lives in the app as the crtSdk global and never enters the bundle.
//     externals: {
//         "@creatio/mobile-common": "crtSdk",
//     },
//     resolve: {
//         conditionNames: ['es2015'],
//         extensions: [".ts", ".js"],
//     },
//     module: {
//         rules: [
//             { test: /\.ts$/, loader: "ts-loader", exclude: /node_modules/ }
//         ]
//     }
// };
//
// const inlineSourceMapConfig = {
//     ...baseConfig,
//     devtool: "inline-source-map",
//     output: { ...baseConfig.output, filename: "main.debug.js" }
// };
//
// const separateSourceMapConfig = {
//     ...baseConfig,
//     devtool: "source-map",
//     output: { ...baseConfig.output, filename: "main.js" }
// };
//
// export default [inlineSourceMapConfig, separateSourceMapConfig];

// ===== file: tools/copy-to-package.js =====
// /**
//  * Copies out/mobile/<moduleName>/main.js into the package file content:
//  *   <targetPackagePath>/Files/src/mobile/<moduleName>/main.js
//  * The folder name MUST equal the bootstrapped module name (src/index.ts).
//  */
// import { copyFileSync, existsSync, mkdirSync, readFileSync } from 'fs';
// import { dirname, join, resolve } from 'path';
// import { fileURLToPath } from 'url';
//
// const __dirname = dirname(fileURLToPath(import.meta.url));
// const config = JSON.parse(readFileSync(resolve(__dirname, '../creatio-mobile-config.json'), 'utf8'));
//
// const moduleName = config.moduleName;
// const source = join(__dirname, '..', 'out', 'mobile', moduleName, 'main.js');
// const targetDir = resolve(__dirname, '..', config.targetPackagePath, 'Files', 'src', 'mobile', moduleName);
// const target = join(targetDir, 'main.js');
//
// if (!existsSync(source)) {
// 	console.error(`Build output not found: ${source}. Run "npm run build" first.`);
// 	process.exit(1);
// }
//
// mkdirSync(targetDir, { recursive: true });
// copyFileSync(source, target);
// console.log(`Copied ${source} -> ${target}`);
// console.log('Next: load the package into the runtime and re-sync the mobile app.');

// ===== file: tools/common.js =====
// import { existsSync, readFileSync, writeFileSync } from 'fs';
//
// // Lists the module in excluded-modules.json so synchronization does not
// // overwrite the main.debug.js pushed to the device.
// export function updateExcludedModules(moduleName, excludedModulesPath) {
// 	let excludedModules = {};
// 	if (existsSync(excludedModulesPath)) {
// 		excludedModules = JSON.parse(readFileSync(excludedModulesPath, 'utf8'));
// 	}
// 	if (!excludedModules[moduleName]) {
// 		excludedModules[moduleName] = ['main.js', 'main.debug.js'];
// 		writeFileSync(excludedModulesPath, JSON.stringify(excludedModules, null, 2));
// 	}
// }

// ===== file: tools/inject-on-device.js =====
// // Pushes main.debug.js to an Android device over adb, bypassing Creatio.
// // Changes apply after an app restart; debug in chrome://inspect.
// import { execSync } from 'child_process';
// import { readFileSync } from 'fs';
// import { dirname, resolve, join } from 'path';
// import { fileURLToPath } from 'url';
// import { updateExcludedModules } from './common.js';
//
// const deviceDir = '/sdcard/Android/data/com.creatio.mobileapp/files/creatio/debugthis';
// const __dirname = dirname(fileURLToPath(import.meta.url));
// const config = JSON.parse(readFileSync(resolve(__dirname, '../creatio-mobile-config.json'), 'utf8'));
// const sourcePath = join(__dirname, '..', 'out', 'mobile', config.moduleName, 'main.debug.js');
// const excludedModulesPath = join(__dirname, '..', 'out', 'excluded-modules.json');
//
// const run = (command) => console.log(execSync(command, { encoding: 'utf8' }));
//
// updateExcludedModules(config.moduleName, excludedModulesPath);
// run(`adb push "${sourcePath}" /sdcard/main.debug.js`);
// run(`adb push "${excludedModulesPath}" /sdcard/excluded-modules.json`);
// run(`adb shell "mkdir -p ${deviceDir}/"`);
// run(`adb shell "mv /sdcard/main.debug.js ${deviceDir}/main.debug.js"`);
// run(`adb shell "mv /sdcard/excluded-modules.json ${deviceDir}/excluded-modules.json"`);
// console.log('Injected. Restart the app.');

// ===== file: src/index.ts =====
import { bootstrapCrtModule, CrtModule, DoBootstrap } from '@creatio/mobile-common';
import { UsrMyRequestHandler } from './handlers/my-request.handler';
import { UsrAttributeChangeRequestHandler } from './handlers/attribute-change.handler';

export * from './requests/my-request';
export * from './handlers/my-request.handler';
export * from './handlers/attribute-change.handler';

/**
 * Remote module entry point. The class name and the string passed to
 * bootstrapCrtModule() must equal `moduleName` in creatio-mobile-config.json.
 * UsrScopeProbeRequestHandler is intentionally NOT listed: register it only
 * while learning the scope value, then remove it again.
 */
@CrtModule({
	requestHandlers: [
		UsrMyRequestHandler,
		UsrAttributeChangeRequestHandler,
	],
})
export class UsrMobileModule implements DoBootstrap {
	public bootstrap(): void {
		bootstrapCrtModule('UsrMobileModule', UsrMobileModule);
	}
}

// ===== file: src/config/scopes.ts =====
/**
 * Freedom UI mobile pages the handlers run in. The value is assumed to be the
 * page schema name - confirm it with UsrScopeProbeRequestHandler. An empty
 * array means every page of the app.
 */
export const PAGE_SCOPES: string[] = ['UsrMyEntity_MobileFormPage'];

// ===== file: src/requests/my-request.ts =====
import { BaseRequest, CrtRequest } from '@creatio/mobile-common';

export const MY_REQUEST = 'usr.MyRequest';

/**
 * A custom request raised from a page button:
 *   "clicked": { "request": "usr.MyRequest", "params": { "attributeName": "PDS_UsrName_a1b2c3d" } }
 * Keep every parameter optional - params delivery on mobile pages is undocumented.
 */
@CrtRequest({
	type: MY_REQUEST,
})
export class UsrMyRequest extends BaseRequest {
	/** Page attribute to work with; falls back to a configured default when absent. */
	public attributeName?: string;
}

// ===== file: src/handlers/my-request.handler.ts =====
import { BaseRequestHandler, CrtRequestHandler, HandlerChainService, Logger } from '@creatio/mobile-common';
import { PAGE_SCOPES } from '../config/scopes';
import { MY_REQUEST, UsrMyRequest } from '../requests/my-request';

const DEFAULT_ATTRIBUTE = 'PDS_UsrName_a1b2c3d';

/**
 * Handles the custom request: reads an attribute, writes it back and runs a
 * stock request through HandlerChainService. Replace the body with real logic.
 */
@CrtRequestHandler({
	type: 'usr.MyRequestHandler',
	requestType: MY_REQUEST,
	scopes: PAGE_SCOPES,
})
export class UsrMyRequestHandler extends BaseRequestHandler<UsrMyRequest> {
	public async handle(request: UsrMyRequest): Promise<unknown> {
		const attributeName = request.attributeName ?? DEFAULT_ATTRIBUTE;
		const current = await request.$context.getAttribute(attributeName);
		Logger.console(`[UsrMobileModule] ${MY_REQUEST}: ${attributeName} = ${JSON.stringify(current)}`);

		await request.$context.setAttribute(attributeName, `${current ?? ''}`.trim());

		// Any stock request can be raised from a handler, e.g. a business process:
		await HandlerChainService.instance.process({
			type: 'crt.RunBusinessProcessRequest',
			$context: request.$context,
			processName: 'UsrMyProcess',
			processParameters: { RecordId: await request.$context.getAttribute('Id') },
			resultParameterNames: [],
			saveAtProcessStart: false,
			showNotification: false,
		} as never);

		// This request is ours alone, so there is no platform handler after us;
		// passing it on costs nothing and keeps other modules' handlers working.
		return this.next?.handle(request);
	}
}

// ===== file: src/handlers/attribute-change.handler.ts =====
import {
	BaseRequestHandler,
	CrtRequestHandler,
	HandleViewModelAttributeChangeRequest,
	Logger,
} from '@creatio/mobile-common';
import { PAGE_SCOPES } from '../config/scopes';

const WATCHED_ATTRIBUTE = 'PDS_UsrName_a1b2c3d';

/**
 * Intercepts a platform request - here the field-change event - and reacts to one
 * attribute only. Every other change passes through untouched. The same shape
 * intercepts any crt.* request (crt.SaveRecordRequest, crt.SetAttributeFromBarcodeRequest...).
 */
@CrtRequestHandler({
	type: 'usr.AttributeChangeRequestHandler',
	requestType: 'crt.HandleViewModelAttributeChangeRequest',
	scopes: PAGE_SCOPES,
})
export class UsrAttributeChangeRequestHandler extends BaseRequestHandler<HandleViewModelAttributeChangeRequest> {
	public async handle(request: HandleViewModelAttributeChangeRequest): Promise<unknown> {
		if (request.attributeName !== WATCHED_ATTRIBUTE) {
			return this.next?.handle(request);
		}
		Logger.console(`[UsrMobileModule] ${WATCHED_ATTRIBUTE}: ${request.oldValue} -> ${request.value}`);
		// React here, then let the platform finish its own processing of the change.
		return this.next?.handle(request);
	}
}

// ===== file: src/handlers/scope-probe.handler.ts =====
import { BaseRequest, BaseRequestHandler, CrtRequestHandler, Logger } from '@creatio/mobile-common';

/**
 * Diagnostic: prints the scopes the platform reports for the current page.
 * Register it in @CrtModule, build, inject on the device, open the page and read
 *   [UsrMobileModule] scopes on crt.LoadDataRequest: ["UsrMyEntity_MobileFormPage"]
 * in chrome://inspect. Copy the value into PAGE_SCOPES and REMOVE the handler:
 * with `scopes: []` it fires on every page of the app.
 */
@CrtRequestHandler({
	type: 'usr.ScopeProbeRequestHandler',
	requestType: 'crt.LoadDataRequest',
	scopes: [],
})
export class UsrScopeProbeRequestHandler extends BaseRequestHandler {
	public async handle(request: BaseRequest): Promise<unknown> {
		Logger.console(`[UsrMobileModule] scopes on ${request.type}: ${JSON.stringify(request.scopes)}`);
		return this.next?.handle(request);
	}
}

// ===== page schema: UsrMyEntity_MobileFormPage (SchemaType "MobileSchema") =====
// viewConfigDiff here is a plain array; add the button as a normal element.
// Take parentName from the designer - it is a generated container name.
// {
//   "operation": "insert",
//   "name": "UsrMyButton",
//   "parentName": "GridContainer_a1b2c3d",
//   "propertyName": "items",
//   "index": 0,
//   "values": {
//     "type": "crt.Button",
//     "caption": "Do the thing",
//     "size": "medium",
//     "clicked": {
//       "request": "usr.MyRequest",
//       "params": { "attributeName": "PDS_UsrName_a1b2c3d" }
//     }
//   }
// }
