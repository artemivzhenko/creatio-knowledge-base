// --- How to create a custom Angular view element as a Freedom UI remote module ---
// A custom Freedom UI component is an Angular 17 app built with module federation
// (ngx-build-plus) and shipped as package file content:
//   <Package>/Files/src/js/<module_name>/{remoteEntry.js, main.js, ...}
// The shell discovers remoteEntry.js through the package file content
// descriptors, so after copying the build the file content has to be
// re-registered (compile / "Update packages from file system" / clio pkg-to-db);
// copying the files alone changes nothing. This recipe is the whole project:
// split it at the "===== file:" markers - or copy the ready folder next to this
// file, Frontend/RemoteModule/template/ (the official Academy example, Angular 15),
// and rename the module. Request handlers in the same module are covered by
// HowToCreateRequestHandlerInRemoteModule.
//
// Traps:
// - Four names must agree: webpack `name`/`uniqueName`, the first argument of
//   bootstrapCrtModule(), the folder under Files/src/js/ and `outputPath` in
//   angular.json. A mismatch is a silent "element not rendered".
// - Three selectors must agree: @Component.selector, @CrtViewElement.selector
//   and customElements.define(). @CrtViewElement.type ('usr.MyElement') is the
//   `type` the page schema uses.
// - Every input needs BOTH @Input() and @CrtInput(); every output BOTH
//   @Output() and @CrtOutput(). One decorator alone compiles and binds nothing.
// - An output named `<input>Change` is wired back to the attribute bound to
//   `<input>` (two-way). Any other output is bound to a request in the schema.
// - An input only fires when the bound attribute VALUE changes. Setting the
//   same value (or the same object reference) again is ignored; a handler that
//   needs to push a "new" equal result sets the attribute to null first.
// - `outputHashing: "none"`, `commonChunk: false`, `runtimeChunk: false`,
//   `publicPath: "auto"` and `scriptType: 'text/javascript'` are what lets the
//   shell load the bundle. Keep them.
// - The component is standalone and goes into the NgModule `imports`, not
//   `declarations`. tsconfig needs `experimentalDecorators`,
//   `emitDecoratorMetadata` and `useDefineForClassFields: false`.
// - The shell runs the remote outside Angular's zone; dev builds may throw
//   NG0909 "Expected to be in Angular Zone" on every change. The error handler
//   in app.module.ts silences only that code.
// - Style with the shell's CSS variables (--crt-neutral-*, --crt-primary-color,
//   --crt-font-family) with fallbacks, or the element ignores the theme.

// ===== file: package.json =====
// {
//   "name": "usr_my_module",
//   "version": "0.0.0",
//   "private": true,
//   "engines": { "node": ">=16.17.0", "npm": ">=8.15.0" },
//   "scripts": {
//     "ng": "ng",
//     "start": "ng serve",
//     "build": "ng build",
//     "watch": "ng build --watch --configuration development"
//   },
//   "dependencies": {
//     "@angular-architects/module-federation": "^17.0.8",
//     "@angular/animations": "^17.3.12",
//     "@angular/common": "^17.3.12",
//     "@angular/compiler": "^17.3.12",
//     "@angular/core": "^17.3.12",
//     "@angular/elements": "^17.3.12",
//     "@angular/forms": "^17.3.12",
//     "@angular/platform-browser": "^17.3.12",
//     "@angular/platform-browser-dynamic": "^17.3.12",
//     "@angular/router": "^17.3.12",
//     "@creatio-devkit/common": "^0.822.0",
//     "rxjs": "~7.8.0",
//     "tslib": "^2.3.0",
//     "zone.js": "0.14.10"
//   },
//   "devDependencies": {
//     "@angular-devkit/build-angular": "^17.3.15",
//     "@angular/cli": "^17.3.15",
//     "@angular/compiler-cli": "^17.3.12",
//     "@types/node": "^22.14.0",
//     "ngx-build-plus": "^17.0.0",
//     "typescript": "~5.3.3",
//     "webpack": "5.94.0"
//   }
// }

// ===== file: angular.json =====
// {
//   "$schema": "./node_modules/@angular/cli/lib/config/schema.json",
//   "version": 1,
//   "newProjectRoot": "projects",
//   "projects": {
//     "usr_my_module": {
//       "projectType": "application",
//       "schematics": { "@schematics/angular:component": { "style": "scss", "standalone": true } },
//       "root": "",
//       "sourceRoot": "src",
//       "prefix": "usr",
//       "architect": {
//         "build": {
//           "builder": "ngx-build-plus:browser",
//           "options": {
//             "outputPath": "../packages/UsrPackage/Files/src/js/usr_my_module",
//             "index": "src/index.html",
//             "main": "src/main.ts",
//             "polyfills": ["zone.js"],
//             "tsConfig": "tsconfig.app.json",
//             "inlineStyleLanguage": "scss",
//             "assets": [],
//             "styles": ["src/styles.scss"],
//             "scripts": [],
//             "extraWebpackConfig": "webpack.config.js",
//             "commonChunk": false,
//             "outputHashing": "none"
//           },
//           "configurations": {
//             "production": {
//               "budgets": [
//                 { "type": "initial", "maximumWarning": "500kb", "maximumError": "1mb" },
//                 { "type": "anyComponentStyle", "maximumWarning": "6kb", "maximumError": "10kb" }
//               ],
//               "extraWebpackConfig": "webpack.prod.config.js"
//             },
//             "development": {
//               "buildOptimizer": false,
//               "optimization": false,
//               "vendorChunk": true,
//               "extractLicenses": false,
//               "sourceMap": true,
//               "namedChunks": true
//             }
//           },
//           "defaultConfiguration": "production"
//         },
//         "serve": {
//           "builder": "ngx-build-plus:dev-server",
//           "configurations": {
//             "production": { "browserTarget": "usr_my_module:build:production", "extraWebpackConfig": "webpack.prod.config.js" },
//             "development": { "browserTarget": "usr_my_module:build:development" }
//           },
//           "defaultConfiguration": "development",
//           "options": { "port": 4100, "publicHost": "http://localhost:4100", "extraWebpackConfig": "webpack.config.js" }
//         }
//       }
//     }
//   }
// }

// ===== file: webpack.config.js =====
// const ModuleFederationPlugin = require("webpack/lib/container/ModuleFederationPlugin");
// const mf = require("@angular-architects/module-federation/webpack");
// const path = require("path");
// const share = mf.share;
//
// const sharedMappings = new mf.SharedMappings();
// sharedMappings.register(path.join(__dirname, 'tsconfig.json'), []);
//
// module.exports = {
//   output: {
//     uniqueName: "usr_my_module",
//     publicPath: "auto",
//     scriptType: 'text/javascript'
//   },
//   optimization: { runtimeChunk: false },
//   resolve: { alias: { ...sharedMappings.getAliases() } },
//   plugins: [
//     new ModuleFederationPlugin({
//       name: "usr_my_module",
//       filename: "remoteEntry.js",
//       exposes: { './RemoteEntry': './src/main.ts' },
//       shared: share({ ...sharedMappings.getDescriptors() })
//     }),
//     sharedMappings.getPlugin()
//   ],
// };

// ===== file: webpack.prod.config.js =====
// module.exports = require('./webpack.config');

// ===== file: tsconfig.json =====
// {
//   "compileOnSave": false,
//   "compilerOptions": {
//     "baseUrl": "./",
//     "outDir": "./dist/out-tsc",
//     "forceConsistentCasingInFileNames": true,
//     "strict": true,
//     "noImplicitOverride": true,
//     "noPropertyAccessFromIndexSignature": true,
//     "noImplicitReturns": true,
//     "noFallthroughCasesInSwitch": true,
//     "sourceMap": true,
//     "declaration": false,
//     "downlevelIteration": true,
//     "emitDecoratorMetadata": true,
//     "experimentalDecorators": true,
//     "moduleResolution": "node",
//     "importHelpers": true,
//     "target": "ES2022",
//     "module": "ES2022",
//     "useDefineForClassFields": false,
//     "lib": ["ES2022", "dom"]
//   },
//   "angularCompilerOptions": {
//     "enableI18nLegacyMessageIdFormat": false,
//     "strictInjectionParameters": true,
//     "strictInputAccessModifiers": true,
//     "strictTemplates": true,
//     "types": ["node"]
//   }
// }

// ===== file: tsconfig.app.json =====
// {
//   "extends": "./tsconfig.json",
//   "compilerOptions": { "outDir": "./out-tsc/app", "types": [] },
//   "files": ["src/main.ts"],
//   "include": ["src/**/*.d.ts"]
// }

// ===== file: src/index.html =====
// <!doctype html>
// <html lang="en">
// <head>
//   <meta charset="utf-8">
//   <title>usr_my_module</title>
//   <base href="/">
//   <meta name="viewport" content="width=device-width, initial-scale=1">
// </head>
// <body></body>
// </html>

// ===== file: src/styles.scss =====
// /* Global styles of the remote; usually empty. */

// ===== file: src/main.ts =====
// Module federation needs the real bootstrap behind a dynamic import.
import('./bootstrap').catch(err => console.error(err));

// ===== file: src/bootstrap.ts =====
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';

platformBrowserDynamic().bootstrapModule(AppModule).catch(err => console.error(err));

// ===== file: src/app/app.module.ts =====
import { createCustomElement } from '@angular/elements';
import { BrowserModule } from '@angular/platform-browser';
import { DoBootstrap, ErrorHandler, Injector, NgModule, ProviderToken } from '@angular/core';
import { bootstrapCrtModule, CrtModule } from '@creatio-devkit/common';
import { UsrMyElementComponent } from './view-elements/my-element/my-element.component';

/** Silences NG0909 only: the shell drives the remote outside Angular's zone. */
class ZoneCompatErrorHandler implements ErrorHandler {
	handleError(err: unknown): void {
		if (err instanceof Error && err.message.includes('NG0909')) {
			return;
		}
		console.error(err);
	}
}

@CrtModule({
	viewElements: [UsrMyElementComponent],
})
@NgModule({
	declarations: [],
	imports: [BrowserModule, UsrMyElementComponent],
	providers: [{ provide: ErrorHandler, useClass: ZoneCompatErrorHandler }],
})
export class AppModule implements DoBootstrap {
	constructor(private _injector: Injector) {}

	ngDoBootstrap(): void {
		const element = createCustomElement(UsrMyElementComponent, { injector: this._injector });
		customElements.define('usr-my-element', element);

		// 'usr_my_module' = webpack name = folder under Files/src/js/.
		bootstrapCrtModule('usr_my_module', AppModule, {
			resolveDependency: (token) => this._injector.get(<ProviderToken<unknown>>token),
		});
	}
}

// ===== file: src/app/view-elements/my-element/my-element.component.ts =====
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CrtInput, CrtOutput, CrtViewElement } from '@creatio-devkit/common';

@Component({
	selector: 'usr-my-element',
	templateUrl: './my-element.component.html',
	styleUrls: ['./my-element.component.css'],
	standalone: true,
	imports: [CommonModule, FormsModule],
})
@CrtViewElement({
	selector: 'usr-my-element',
	type: 'usr.MyElement',
})
export class UsrMyElementComponent {
	/** Bound to a page attribute: "value": "$PDS_UsrName_a1b2c3d". */
	@Input() @CrtInput()
	value: string = '';

	/** `valueChange` is wired back to the attribute bound to `value` (two-way). */
	@Output() @CrtOutput()
	valueChange = new EventEmitter<string>();

	/** Bound to a request: "action": { "request": "usr.MyRequest", "params": {} }. */
	@Output() @CrtOutput()
	action = new EventEmitter<void>();

	/** Setter form: use it when the element must react to the push, not just store it. */
	@Input() @CrtInput()
	set state(value: { pending: boolean } | null) {
		this.pending = !!value?.pending;
	}

	pending = false;

	onInput(text: string): void {
		this.value = text;
		this.valueChange.emit(text);
	}

	onAction(): void {
		this.action.emit();
	}
}

// ===== file: src/app/view-elements/my-element/my-element.component.html =====
// <div class="usr-my-element">
//   <input
//     type="text"
//     [ngModel]="value"
//     (ngModelChange)="onInput($event)"
//     [disabled]="pending"
//   />
//   <button type="button" (click)="onAction()" [disabled]="pending">Run</button>
// </div>

// ===== file: src/app/view-elements/my-element/my-element.component.css =====
// :host {
//   display: block;
//   font-family: var(--crt-font-family, "Open Sans", sans-serif);
//   color: var(--crt-neutral-900, #1f1f1f);
// }
// .usr-my-element { display: flex; gap: 8px; }
// input { border: 1px solid var(--crt-neutral-200, #d7d7d7); border-radius: 4px; padding: 6px 8px; }
// button { background: var(--crt-primary-color, #0091ea); color: #fff; border: 0; border-radius: 4px; padding: 6px 12px; }

// ===== page schema: UsrMyPage_FormPage (viewConfigDiff + viewModelConfigDiff + handlers) =====
// viewConfigDiff:
// {
//   "operation": "insert",
//   "name": "UsrMyElement",
//   "values": {
//     "type": "usr.MyElement",
//     "value": "$PDS_UsrName_a1b2c3d",
//     "state": "$UsrElementState",
//     "action": { "request": "usr.MyRequest", "params": {} },
//     "layoutConfig": { "row": 1, "column": 1, "colSpan": 12, "rowSpan": 1 }
//   },
//   "parentName": "GeneralInfoTabContainer_a1b2c3d",
//   "propertyName": "items",
//   "index": 0
// }
//
// viewModelConfigDiff - a page attribute (no modelConfig) feeds the `state` input:
// { "operation": "merge", "path": ["attributes"], "values": { "UsrElementState": {} } }
//
// handlers - the output request, pushing state back into the element:
// {
//   request: "usr.MyRequest",
//   handler: async (request, next) => {
//     request.$context.UsrElementState = { pending: true };
//     const value = await request.$context.PDS_UsrName_a1b2c3d;
//     // ... do the work with `value` ...
//     // Same object shape as before would be ignored: reset first, then set.
//     request.$context.UsrElementState = null;
//     request.$context.UsrElementState = { pending: false };
//     return next?.handle(request);
//   }
// }
